"""
Celery 定时任务配置
"""
from celery import Celery
from celery.schedules import crontab
import asyncio
from datetime import datetime, timedelta

from app.main import create_app
from app.models import db, Content, XHSAccount, PublishQueue
from app.services.scraper import DataCollector
from app.services.encryption import decrypt_data

# 创建 Celery 应用
flask_app = create_app('development')

celery_app = Celery(
    'redflow',
    broker=flask_app.config['CELERY_BROKER_URL'],
    backend=flask_app.config['CELERY_RESULT_BACKEND']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 分钟超时
)

# 定时任务配置
celery_app.conf.beat_schedule = {
    # Publish queue processor
    'process-publish-queue-every-minute': {
        'task': 'app.celery_tasks.process_publish_queue',
        'schedule': crontab(),  # 每分钟执行
    },

    # Collectors
    'collect-every-hour': {
        'task': 'app.celery_tasks.collect_published_notes',
        'schedule': crontab(minute=0),  # 每小时执行
    },
    'collect-daily-report': {
        'task': 'app.celery_tasks.generate_daily_report',
        'schedule': crontab(hour=23, minute=0),  # 每天 23:00
    },
}


@celery_app.task(bind=True, max_retries=3)
def process_publish_queue(self, batch_size: int = 5):
    """处理发布队列（最小可用版本）

    当前版本只负责：
    - 扫描到期的 publish_queue pending 任务
    - 标记为 running / failed
    - 写入错误信息，便于前端展示与排障

    真正的发布执行器（Playwright 自动发布）后续再接入。
    """

    with flask_app.app_context():
        now = datetime.utcnow()

        # 找到到期且未处理的任务
        items = (
            PublishQueue.query.filter(
                PublishQueue.status == 'pending',
                PublishQueue.scheduled_at <= now,
            )
            .order_by(PublishQueue.scheduled_at.asc())
            .limit(batch_size)
            .all()
        )

        claimed = 0
        results = []

        # 先 claim：标记 running，避免重复处理（简易方式）
        for item in items:
            item.status = 'running'
            item.processed_at = now
            claimed += 1

        db.session.commit()

        for item in items:
            try:
                content = Content.query.get(item.content_id)
                if not content:
                    item.status = 'failed'
                    item.error_message = '内容不存在'
                    results.append({'queue_id': str(item.id), 'status': 'failed', 'error': item.error_message})
                    continue

                account = XHSAccount.query.get(item.account_id)
                if not account or not account.cookies_encrypted:
                    item.status = 'failed'
                    item.error_message = '账号未配置 Cookie'
                    content.status = 'failed'
                    content.error_message = item.error_message
                    results.append({'queue_id': str(item.id), 'content_id': str(content.id), 'status': 'failed', 'error': item.error_message})
                    continue

                cookies_dict = decrypt_data(account.cookies_encrypted)
                cookies = [
                    {'name': k, 'value': v, 'domain': '.xiaohongshu.com', 'path': '/'}
                    for k, v in (cookies_dict or {}).items()
                ]

                # 发布执行器（当前为最小骨架；后续补齐 selector）
                from app.services.publisher import XiaohongshuPublisher

                async def do_publish():
                    async with XiaohongshuPublisher(headless=True, timeout_ms=flask_app.config.get('PLAYWRIGHT_TIMEOUT', 30000)) as pub:
                        return await pub.publish_note(
                            cookies=cookies,
                            title=content.title,
                            body=content.body,
                            tags=content.tags or [],
                        )

                publish_result = asyncio.run(do_publish())

                if getattr(publish_result, 'ok', False):
                    item.status = 'success'
                    item.error_message = None
                    item.processed_at = datetime.utcnow()

                    content.status = 'published'
                    content.published_at = datetime.utcnow()
                    content.error_message = None
                    content.xhs_note_id = publish_result.note_id
                    content.xhs_note_url = publish_result.note_url

                    results.append({'queue_id': str(item.id), 'content_id': str(content.id), 'status': 'success', 'note_id': publish_result.note_id})

                    # 发布成功后立即触发一次采集（如果 note_id 已拿到）
                    if publish_result.note_id:
                        try:
                            collect_single_note.delay(str(content.id))
                        except Exception:
                            pass
                else:
                    item.status = 'failed'
                    item.error_message = getattr(publish_result, 'error', None) or '发布失败'
                    item.processed_at = datetime.utcnow()

                    content.status = 'failed'
                    content.error_message = item.error_message

                    # 重试策略：对于未知异常/临时故障，让 Celery 负责重试
                    if self.request.retries < self.max_retries:
                        raise self.retry(exc=Exception(item.error_message), countdown=60)

                    results.append({'queue_id': str(item.id), 'content_id': str(content.id), 'status': 'failed', 'error': item.error_message})

            except Exception as exc:
                item.status = 'failed'
                item.error_message = str(exc)
                item.processed_at = datetime.utcnow()
                results.append({'queue_id': str(item.id), 'status': 'failed', 'error': item.error_message})

        db.session.commit()

        return {
            'now': now.isoformat(),
            'claimed': claimed,
            'processed': len(items),
            'results': results,
        }


@celery_app.task(bind=True, max_retries=3)
def collect_published_notes(self):
    """采集已发布笔记数据"""
    with flask_app.app_context():
        # 获取所有需要采集的笔记
        contents = Content.query.filter(
            Content.status == 'published',
            Content.xhs_note_id.isnot(None)
        ).all()
        
        results = []
        for content in contents:
            try:
                # 获取账号 Cookie
                account = XHSAccount.query.get(content.account_id)
                if not account or not account.cookies_encrypted:
                    continue
                
                cookies_dict = decrypt_data(account.cookies_encrypted)
                cookies = [
                    {'name': k, 'value': v, 'domain': '.xiaohongshu.com', 'path': '/'}
                    for k, v in cookies_dict.items()
                ]
                
                # 采集数据
                collector = DataCollector()
                
                async def collect():
                    await collector.scraper.login_with_cookies(cookies)
                    note_url = f'https://www.xiaohongshu.com/explore/{content.xhs_note_id}'
                    data = await collector.scraper.get_note_metrics(note_url)
                    await collector.scraper.close()
                    return data
                
                data = asyncio.run(collect())
                
                # 更新缓存
                if 'metrics' in data:
                    content.likes_cached = data['metrics'].get('likes', 0)
                    content.collects_cached = data['metrics'].get('collects', 0)
                    content.comments_cached = data['metrics'].get('comments', 0)
                    content.shares_cached = data['metrics'].get('shares', 0)
                    content.stats_cached_at = datetime.utcnow()
                
                results.append({
                    'note_id': content.xhs_note_id,
                    'status': 'success'
                })
                
            except Exception as e:
                results.append({
                    'note_id': content.xhs_note_id,
                    'status': 'failed',
                    'error': str(e)
                })
                
                # 重试
                if self.request.retries < self.max_retries:
                    raise self.retry(exc=e, countdown=60)
        
        db.session.commit()
        
        return {
            'total': len(contents),
            'success': sum(1 for r in results if r['status'] == 'success'),
            'failed': sum(1 for r in results if r['status'] == 'failed'),
            'results': results
        }


@celery_app.task
def collect_single_note(content_id: str):
    """采集单篇笔记数据"""
    with flask_app.app_context():
        content = Content.query.get(content_id)
        if not content or not content.xhs_note_id:
            return {'error': '内容不存在'}
        
        account = XHSAccount.query.get(content.account_id)
        if not account or not account.cookies_encrypted:
            return {'error': '账号未配置 Cookie'}
        
        cookies_dict = decrypt_data(account.cookies_encrypted)
        cookies = [
            {'name': k, 'value': v, 'domain': '.xiaohongshu.com', 'path': '/'}
            for k, v in cookies_dict.items()
        ]
        
        collector = DataCollector()
        
        async def collect():
            await collector.scraper.login_with_cookies(cookies)
            note_url = f'https://www.xiaohongshu.com/explore/{content.xhs_note_id}'
            data = await collector.scraper.get_note_metrics(note_url)
            await collector.scraper.close()
            return data
        
        data = asyncio.run(collect())
        
        if 'metrics' in data:
            content.likes_cached = data['metrics'].get('likes', 0)
            content.collects_cached = data['metrics'].get('collects', 0)
            content.comments_cached = data['metrics'].get('comments', 0)
            content.shares_cached = data['metrics'].get('shares', 0)
            content.stats_cached_at = datetime.utcnow()
            db.session.commit()
        
        return {'status': 'success', 'data': data}


@celery_app.task
def generate_daily_report():
    """生成每日报告"""
    with flask_app.app_context():
        today = datetime.utcnow().date()
        start_of_day = datetime.combine(today, datetime.min.time())
        
        # 统计今日发布
        published_today = Content.query.filter(
            Content.status == 'published',
            Content.published_at >= start_of_day
        ).count()
        
        # 统计总互动
        contents = Content.query.filter(
            Content.status == 'published',
            Content.published_at >= start_of_day
        ).all()
        
        total_likes = sum(c.likes_cached or 0 for c in contents)
        total_collects = sum(c.collects_cached or 0 for c in contents)
        total_comments = sum(c.comments_cached or 0 for c in contents)
        
        report = {
            'date': today.isoformat(),
            'published_count': published_today,
            'total_likes': total_likes,
            'total_collects': total_collects,
            'total_comments': total_comments,
            'total_engagement': total_likes + total_collects + total_comments
        }
        
        # TODO: 发送邮件或保存报告
        
        return report