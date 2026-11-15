# 专栏续读风险试算

分类与阈值选择的真实业务分析小型项目。完整模拟客户、痛点、上下游、算法公式与一天工作剧本见 [BUSINESS.md](BUSINESS.md)。

## 模块与业务流程
数据接入（JSON/CSV、字段验证、批次指纹）→ 参数化分析（异步 Python worker）→ 结果复核（指标、图形、明细、解释、批准）→ 定时分发（本地收件箱、CSV/JSON、SHA256）→ 投递确认（按收件方确认、回执对账、演示收件端）；另有业务总览和审计轨迹。
三个贯穿全栈的实体：Dataset 数据批次、Job 分析任务、Report 分发计划；辅助 User、Audit、Delivery、Recipient、Dispatch。

## 快速启动
```bash
cp .env.example .env
docker compose up -d --build --wait
docker compose exec -T backend python -m scripts.seed_demo
```
访问 http://localhost:18207；后端文档 http://localhost:19207/docs；数据库宿主端口 17707。
`SEED_DEMO=true` 自动幂等 seed；不覆盖用户修改。手动 seed 命令可重复执行。

## 演示账号与权限
|账号|密码|真实权限|
|---|---|---|
|admin@demo.local|Demo123!|接入、执行、批准、分发、暂停、读取与下载|
|analyst@demo.local|Demo123!|接入、执行、读取与下载；不能批准或安排分发|
|viewer@demo.local|Demo123!|只读与下载|

## 投递确认演示路径
1. 打开「投递确认」页：seed 已生成 3 个收件方与首批投递，worker 数秒内完成 待发→已送达。
2. 点「模拟回执丢失」后创建新分发计划（周期选每分钟）或补投：投递转 待确认；收件端已入件但回执丢失。
3. 点「恢复回执通道」：worker 先查接收结果，登记回执转 已送达，全程不重复入件（收件端重复拦截计数保持 0）。
4. 故障期间「撤销」待确认投递：停止发送；恢复后迟到回执只对账——状态转 已送达并标记迟到回执，撤销时间保留，不触发重发。
5. 修改收件方地址：之后的新投递走新地址；旧投递的「重试」仍走台账中的快照地址。
6. `docker compose restart worker` 后投递照常推进：状态全部落库，中断续跑。

## 技术与本地开发
Python 3.12 / FastAPI / SQLAlchemy / NumPy / SciPy / scikit-learn；MySQL 8.0；Redis 7；Nginx；原生 HTML CSS JavaScript ES modules（用户指定）。后端所有校验、持久化和算法在服务端。无前端打包步骤。
后端：安装 backend/requirements.txt，设置 DATABASE_URL、REDIS_URL、JWT_SECRET、ARTIFACT_DIR 后在 backend/ 执行 `python -m migrations.initial`、`python -m scripts.seed_demo`、`uvicorn src.main:app`，另开 `python -m src.worker`。前端使用带 /api 反向代理的 Nginx，直接打开 index.html 不支持 API。

## 目录与工程约定
backend/src/{models,schemas,services,routes,controllers,middlewares,constants,config,utils}；backend/scripts/seed_demo.py；backend/migrations/initial.py。
frontend/src/{api,stores,types,components/common,hooks,pages,router,utils,constants}。
Role 枚举：admin/analyst/viewer；JobStatus：queued/running/completed/failed。后端 backend/src/constants/enums.py，前端 frontend/src/constants/enums.js；路由权限在 middlewares/auth.py；页面按相同角色控制操作入口。

## 环境变量与 Docker
COMPOSE_PROJECT_NAME=reader-risk；FRONTEND_PORT=18207；BACKEND_PORT=19207；DB_PORT=17707；DB_PASSWORD、JWT_SECRET、RECEIVER_TOKEN 见 .env.example；SEED_DEMO 默认 true。共享命名产物卷供后端下载与 worker 写入，数据库/Redis 各持久卷。
恰好五服务均有健康检查。Redis 队列加 SQL 排队状态兜底；worker 按 next_run 生成本地收件箱文件。周期 60 秒至 30 天。分发结果为批准分析的固定快照；若需新数据重新计算并建立新计划。
归档固定后按收件方生成投递：待发/待确认/已送达/失败/已撤销五态独立记录，尝试与回执逐条留痕。回执丢失时重试沿用原投递号并先查接收结果，不重复入件；投递状态全部落库，worker 中断后自动续跑。收件地址修改只影响之后的新投递，重发旧件仍到快照原地址。撤销与回执相撞时保留已接收事实；撤销后未接收的停止发送，迟到回执只对账不触发重发。演示收件端 `POST/GET /receiver/inbox` 以 `RECEIVER_TOKEN` 鉴权，可在投递确认页模拟回执丢失；不连接真实邮件或企业聊天。
错误响应、请求编号、Redis 每 IP 每分钟 240 次限流、JWT 和数据库操作审计。演示密钥与密码仅供本机模拟；生产部署前配置独立密钥与账号。

## 数据与验收
所有数据为固定随机种子生成的模拟业务数据，不能作为实际生产决策证据。项目独立算法、输入边界及业务局限详见 BUSINESS.md。测试与截图统一存放 ../../test-artifacts/gb-1008/，源码不含日志/截图/测试报告。
清理本项目演示数据：`docker compose down -v --remove-orphans`（会删除本项目命名卷）。

## License
MIT，见 LICENSE。
