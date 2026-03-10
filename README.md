# RedFlow

小红书自动化运营助手（个人博主/一人公司场景），支持内容管理、发布队列、数据回收与复盘，当前以 **“半自动发布”** 为主（本机浏览器手动点击发布），更稳定、更安全。

> 状态：MVP

---

## ✨ 功能概览

- 内容管理：标题/正文/标签/图片
- 发布队列：定时/排期/状态追踪
- 半自动发布：一键打开发布页 + 复制内容
- 数据回收：采集已发布笔记数据（待完善）

---

## 🧩 技术栈

- **Frontend**: Next.js (App Router) + Tailwind
- **Backend**: Flask + SQLAlchemy + Celery
- **DB**: MySQL（UTF8MB4）
- **Cache/Queue**: Redis
- **Metrics**: TDengine（可选）
- **Automation**: Playwright（保留接口）

---

## 🛠️ 快速开始（Docker）

```bash
# 1) 启动后端依赖
cd redflow

# 2) 启动后端/worker/beat
# （首次会构建镜像）
docker-compose up -d backend celery celery-beat mysql redis tdengine

# 3) 启动前端
cd frontend
npm install
npm run dev
```

前端默认地址：
```
http://localhost:3000
```

---

## 🔐 环境变量（backend/.env）

> 已内置默认 `.env`，可按需调整

关键项：
```
DATABASE_URL=mysql+pymysql://redflow:redflow123@mysql:3306/redflow?charset=utf8mb4
JWT_SECRET_KEY=***
ENCRYPTION_KEY=***
PUBLISH_MODE=local
XHS_PUBLISH_IMAGE_URL=https://creator.xiaohongshu.com/publish/publish?source=official&from=menu&target=image
```

---

## 🚀 发布流程（当前为半自动）

1. 在内容管理中点击 **发布**
2. 队列处理后状态变为 **“待手动发布”**
3. 点击 **“一键发布”**：
   - 自动复制 **标题 + 正文 + 标签 + 图片路径** 到剪贴板
   - 自动打开小红书图文发布页
4. 手动上传图片并点击发布

> 原因：容器环境易触发风控，优先保证可用性。

---

## 🧪 发布队列说明

- `publishing`：队列处理中
- `manual`：已准备好，等待手动发布
- `published`：已发布
- `failed`：失败（可重试）

---

## 📌 TODO

- 自动发布 selector 补齐（Playwright）
- 可视化发布回放与失败诊断
- 更稳定的数据采集与复盘报告
- 素材库与模板库

---

## 🧷 免责声明

请遵守平台规则。本项目仅用于学习与个人效率提升，不保证任何自动化操作在平台侧长期稳定。

---

## 📫 联系

如需协作或定制版本，请提 Issue 或 PR。
