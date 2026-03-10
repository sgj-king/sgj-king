"""
TDengine 时序数据库服务
"""
import uuid
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# TDengine client may be unavailable in some runtime images (e.g. celery-beat).
try:
    import taos  # type: ignore
except Exception:  # noqa: S110
    taos = None


class TDengineService:
    """TDengine 时序数据库服务"""
    
    def __init__(self):
        self.host = os.getenv('TDENGINE_HOST', 'localhost')
        self.port = int(os.getenv('TDENGINE_PORT', '6030'))
        self.username = os.getenv('TDENGINE_USER', 'root')
        self.password = os.getenv('TDENGINE_PASSWORD', 'taosdata')
        self.database = os.getenv('TDENGINE_DATABASE', 'redflow_metrics')
        self._conn = None
    
    def _get_connection(self):
        """获取数据库连接"""
        if self._conn is None:
            if taos is None:
                print("TDengine client not available (taos import failed).")
                return None
            try:
                self._conn = taos.connect(
                    host=self.host,
                    port=self.port,
                    user=self.username,
                    password=self.password,
                    database=self.database
                )
            except Exception as e:
                print(f"TDengine connection failed: {e}")
                # 如果数据库不存在，先创建
                try:
                    temp_conn = taos.connect(
                        host=self.host,
                        port=self.port,
                        user=self.username,
                        password=self.password
                    )
                    temp_conn.execute(f"CREATE DATABASE IF NOT EXISTS {self.database} KEEP 365 DURATION 10 BUFFER 16")
                    temp_conn.close()
                    # 重试连接
                    self._conn = taos.connect(
                        host=self.host,
                        port=self.port,
                        user=self.username,
                        password=self.password,
                        database=self.database
                    )
                except Exception as e2:
                    print(f"TDengine init failed: {e2}")
                    return None
        return self._conn
    
    def init_tables(self):
        """初始化表结构"""
        conn = self._get_connection()
        if not conn:
            return False
        
        # 创建超级表 - 笔记互动数据
        conn.cursor().execute("""
        CREATE STABLE IF NOT EXISTS note_metrics (
            ts TIMESTAMP,
            likes INT,
            collects INT,
            comments INT,
            shares INT,
            views INT,
            read_complete_rate FLOAT,
            engagement_rate FLOAT
        ) TAGS (
            note_id BINARY(50),
            account_id BINARY(50),
            user_id BINARY(50)
        )
        """)
        
        # 创建超级表 - 发布效果数据
        conn.cursor().execute("""
        CREATE STABLE IF NOT EXISTS publish_performance (
            ts TIMESTAMP,
            impressions INT,
            click_rate FLOAT,
            save_rate FLOAT,
            share_rate FLOAT,
            comment_rate FLOAT
        ) TAGS (
            note_id BINARY(50),
            account_id BINARY(50),
            hour_of_day TINYINT,
            day_of_week TINYINT
        )
        """)
        
        return True
    
    def write_note_metrics(self, note_id: str, account_id: str, user_id: str,
                           likes: int, collects: int, comments: int, shares: int,
                           views: int, read_complete_rate: float = None,
                           engagement_rate: float = None):
        """写入笔记互动数据"""
        conn = self._get_connection()
        if not conn:
            return False
        
        table_name = f"note_{note_id.replace('-', '')}"
        
        # 创建子表（如果不存在）
        cursor = conn.cursor()
        cursor.execute(f"""
        CREATE STABLE IF NOT EXISTS {table_name} USING note_metrics
        TAGS ('{note_id}', '{account_id}', '{user_id}')
        """)
        
        # 写入数据
        ts = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        cursor.execute(f"""
        INSERT INTO {table_name} VALUES (
            '{ts}',
            {likes}, {collects}, {comments}, {shares}, {views},
            {read_complete_rate or 'NULL'}, {engagement_rate or 'NULL'}
        )
        """)
        
        return True
    
    def get_note_metrics(self, note_id: str) -> List[Dict]:
        """获取笔记指标历史"""
        conn = self._get_connection()
        if not conn:
            return []
        
        table_name = f"note_{note_id.replace('-', '')}"
        
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {table_name} ORDER BY ts DESC LIMIT 100")
            rows = cursor.fetchall()
            
            metrics = []
            for row in rows:
                metrics.append({
                    'ts': row[0].isoformat() if isinstance(row[0], datetime) else row[0],
                    'likes': row[1],
                    'collects': row[2],
                    'comments': row[3],
                    'shares': row[4],
                    'views': row[5],
                    'read_complete_rate': row[6],
                    'engagement_rate': row[7]
                })
            return metrics
        except:
            return []
    
    def get_metrics_trend(self, user_id: str, account_id: Optional[str],
                          metric: str, days: int = 7) -> List[Dict]:
        """获取指标趋势"""
        conn = self._get_connection()
        if not conn:
            return []
        
        # 简化的趋势查询 - 按天聚合
        start_time = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        query = f"""
        SELECT 
            DATE_TREND(ts, 1d) as date,
            SUM(likes) as likes,
            SUM(collects) as collects,
            SUM(comments) as comments,
            SUM(shares) as shares,
            SUM(views) as views
        FROM note_metrics
        WHERE ts >= '{start_time}'
        """
        
        if account_id:
            query += f" AND account_id = '{account_id}'"
        
        query += " GROUP BY date ORDER BY date"
        
        try:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            
            trends = []
            for row in rows:
                trends.append({
                    'date': str(row[0])[:10],
                    'likes': row[1] or 0,
                    'collects': row[2] or 0,
                    'comments': row[3] or 0,
                    'shares': row[4] or 0,
                    'views': row[5] or 0
                })
            return trends
        except:
            return []
    
    def get_best_publish_times(self, user_id: str, account_id: Optional[str] = None) -> List[Dict]:
        """分析最佳发布时间"""
        conn = self._get_connection()
        if not conn:
            return []
        
        # 按小时和星期分析互动数据
        query = """
        SELECT 
            HOUR(ts) as hour,
            DAYOFWEEK(ts) as day_of_week,
            AVG(likes + collects + comments) as avg_engagement
        FROM note_metrics
        WHERE ts >= NOW() - 30d
        """
        
        if account_id:
            query += f" AND account_id = '{account_id}'"
        
        query += " GROUP BY hour, day_of_week ORDER BY avg_engagement DESC LIMIT 10"
        
        try:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            
            best_times = []
            day_names = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
            
            for row in rows:
                best_times.append({
                    'hour': row[0],
                    'day_of_week': row[1],
                    'day_name': day_names[row[1] % 7] if row[1] else '周日',
                    'avg_engagement': float(row[2] or 0)
                })
            return best_times
        except:
            return []


# 全局实例
tdengine_service = TDengineService()