# Tallywise · 个人记账系统

[![CI](https://github.com/8ight1een/-Tallywise/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/8ight1een/-Tallywise/actions/workflows/ci.yml)

面向家庭日常记账的全栈项目：多用户隔离的收支记录、幂等创建流水、按月流水与汇总、日报趋势/分类/账户三类统计报表、支持搜索筛选的游标分页，以及先生成草稿、核对后入账的 AI 记账助手。

默认 Docker Compose 使用 React 19 + TypeScript 前端（`frontend-react/`），已覆盖登录注册、流水、账户分类、统计与 AI 助手页面；保留 Vue 3 + TypeScript 实现（`frontend/`）。后端使用 FastAPI + SQLAlchemy 2（异步）+ PostgreSQL，月度汇总接入 Redis 缓存。当前包含 171 个后端测试、21 个 React 测试和 1 条 Playwright 端到端主链路。

[项目亮点](#项目亮点) · [技术选型](#技术选型) · [架构](#架构) · [设计取舍](#设计取舍) · [接口](#接口) · [AI 记账助手](#ai-记账助手) · [工程质量](#工程质量) · [快速开始](#快速开始)

## 项目亮点

- **多用户数据隔离**：所有查询以登录用户为边界；流水关联账户、分类时同时校验归属，跨用户 ID 无法读写。
- **重复提交只创建一次**：创建流水要求 `Idempotency-Key`，用 `(user_id, idem_key)` 唯一约束和 `ON CONFLICT` 抢键；同键同体返回原流水，同键异体返回 409，前端失败重试复用同一个键。
- **多笔 AI 草稿与入账分离**：一段描述最多生成 10 笔草稿，服务端逐笔校验归属与字段；用户切换、补齐并逐笔确认后才调用流水接口，当前笔结果不确定时复用原幂等键重试。
- **月度汇总缓存**：Redis 按用户和月份缓存汇总，TTL 为 60 秒；流水提交成功后清除受影响月份，缓存不可用时回退到数据库查询。
- **游标分页不重不漏**：按 `(transaction_date, id)` 做 keyset 分页，同一天多条记录不会因翻页丢失或重复；深页不随页码变慢，列表另支持关键字（描述/账户/分类）、收支类型与账户筛选。
- **统计报表口径明确**：每日趋势把当月没有流水的日期补 0，分类支出只统计支出并按金额倒序，账户汇总用左外连接，没有流水的账户也会出现且结余为 0。
- **事务边界集中**：每个请求一个逻辑事务，服务层只 `flush()`；所有写接口在返回前 `commit()`，读接口不提交，客户端看到成功时数据已经落库。
- **约束分层**：Pydantic 校验输入、数据库用 `CHECK` / 外键 / 唯一约束兜底，金额用 `NUMERIC(9,2)` 而非浮点。
- **可追踪、可回归**：请求 ID + 结构化日志；CI 覆盖 lint、类型检查、迁移一致性、后端测试、前端单元测试与端到端主链路（数据库相关用例跑在真实 PostgreSQL 上）。

## 技术选型

| 层次 | 技术 | 为什么 |
| --- | --- | --- |
| 前端（默认 Compose） | React 19、React Router 7、TanStack Query 5 | 组件化拆分页面，服务端状态交给查询缓存 |
| 前端（保留实现） | Vue 3、TypeScript、Vite | 组合式 API 管理页面状态，类型约束接口边界 |
| 后端 | FastAPI、Pydantic | 声明式参数校验与 OpenAPI 文档，异常映射集中 |
| AI 接入 | httpx2、Chat Completions 兼容接口、Pydantic | 服务端调用模型并校验结构化输出，密钥不下发前端 |
| 数据访问 | SQLAlchemy 2 AsyncSession、asyncpg | 全链路异步；用表达式构造查询，避免字符串拼接 SQL |
| 数据库 | PostgreSQL 18 | 事务性 DDL、行构造器比较、执行计划可分析 |
| 汇总缓存 | Redis 7、redis-py 异步客户端 | 减少重复月度聚合查询，故障时回退数据库 |
| 迁移 | Alembic | 结构变更可追踪，CI 校验模型与库一致 |
| 认证 | PyJWT、HttpOnly Cookie、Argon2 | 前端不接触令牌，降低 XSS 读取风险 |
| 质量 | Ruff、mypy、pytest、ESLint、Oxlint、vue-tsc、tsc | 静态检查 + 集成测试，CI 与本地命令一致 |

## 架构

```mermaid
flowchart LR
    UI[Vue / React 页面] --> Client[统一 API 请求模块]
    Client --> Routes[FastAPI 路由 / 认证 / 参数校验]
    Routes --> Services[业务服务]
    Services --> Cache[(Redis 月度汇总缓存)]
    Services --> ORM[SQLAlchemy AsyncSession]
    ORM --> PG[(PostgreSQL)]
    Routes --> Draft[AI 草稿服务 / 字段校验]
    Draft --> Model[外部模型 API]
    Migration[Alembic 迁移] --> PG
```

一次请求的路径：路由做参数校验与鉴权 → 服务层构造查询/写入 → 写请求在返回前提交，读请求不提交 → 业务异常在应用入口映射为 HTTP 状态码。服务层不直接面向 HTTP，便于单独测试。

```text
backend/
├── main.py             # 应用入口、异常映射
├── routers/            # HTTP 接口（用户、记账、AI 草稿）
├── ai_config.py        # AI 开关、模型与限额配置
├── ai_drafts.py        # 模型调用、限流、草稿校验
├── ai_schemas.py       # 草稿请求、提取结果与响应模型
├── services/           # 用户、记账、报表、分页、汇总缓存
├── model.py            # ORM 模型、约束与索引
├── schemas.py          # 请求校验与响应模型
├── database.py         # 异步连接池与会话生命周期
├── migrations/         # Alembic 迁移
└── tests/              # 单元测试、模拟模型/缓存测试、PostgreSQL 集成测试
frontend/src/
├── api/                # 请求封装、401 统一处理
├── components/         # 登录、记账、流水、汇总
├── router/ · types/    # 路由与接口类型
└── assets/
frontend-react/src/     # 默认 Compose 前端
├── pages/              # 登录注册、账本工作台、AI 助手
├── components/         # 流水、账户分类、统计图表、弹窗、AI 草稿卡片
├── ai.ts               # 草稿转换、入账校验、待确认提交存储
├── api.ts · api/       # 请求封装与 401 处理
└── useResource.ts      # TanStack Query 封装
backend-ui-preview/     # 独立静态交互原型，不连接真实后端
```

### 事务约定

- 写路由在返回前 `commit()` 一次。
- service 只 `flush()`，不提交。
- 读路由不提交，查询结束后由会话关闭或回滚。
- 一个请求只保留一个明确的提交点。

## 设计取舍

| 决策 | 选择 | 原因 | 代价 |
| --- | --- | --- | --- |
| 分页 | keyset 游标 | 深页只扫一页的量；同日多条有唯一排序 | 不能按页码跳页，要总数就多一次 `COUNT` 查询 |
| 索引 | `(user_id, transaction_date, id)` | 等值 + 范围 + 排序一次满足 | 索引多一列，写入维护成本略增 |
| 幂等 | `(user_id, idem_key)` 主键 + `ON CONFLICT` | 唯一索引原子裁决；重复请求返回原结果 | 键需要保留和清理；客户端必须配合传键 |
| 事务 | 写路由返回前提交，service 只 `flush()` | 一个请求是一个原子单元；2xx 代表数据已落库 | 每个写接口都要显式 `commit()`，漏写会丢数据 |
| 金额 | `NUMERIC(9,2)` + `Decimal` | 精确小数，无浮点误差 | 金额上限 9,999,999.99 |
| 时间 | `DATE` 业务日期 + `timestamptz` 创建时间 | 业务日期与审计时间语义分离 | 展示时区由前端决定 |
| 认证 | JWT 放 HttpOnly Cookie | 前端不接触令牌 | 无状态，签发后无法即时吊销 |
| 迁移 | Alembic + CI `alembic check` | 结构可追溯，模型与库不漂移 | 每次改模型都要配套迁移 |
| 测试 | 真实 PostgreSQL，迁移建表 | 约束、索引、事务行为都能覆盖 | 需要可清空的专用测试库 |
| 汇总缓存 | 先读缓存，未命中查库；写提交后删除缓存 | 降低重复聚合查询开销 | 缓存与数据库不构成原子事务，存在短暂陈旧窗口 |

### 深入：月度汇总缓存

仅 `GET /api/summary` 使用 Redis，流水列表与其他报表仍直接查询数据库。缓存键为 `tallywise:summary:v1:{user_id}:{year}-{month}`，月份补齐两位，TTL 为 60 秒；未指定月份时先按数据库当前日期确定年月。

- 新增流水提交成功后清除对应月份；幂等重放不重复清除。
- 修改流水先锁定记录、保留旧日期，提交后清除新旧月份；删除流水提交后清除原月份。
- 未配置 Redis 时直接查库；Redis 读写超时或连接异常时降级，损坏的缓存数据会回源重算。缓存失效失败不会撤销已经提交的流水。
- 这是允许短暂陈旧的缓存方案。并发读取可能在删除后写回旧结果，失效失败也可能保留旧值；TTL 用于限制缓存条目的存活时间，不提供强一致性保证。

Compose 已配置 `REDIS_URL=redis://redis:6379/0`。本地直接运行后端时，可在 `backend/.env` 设置 `REDIS_URL` 指向可访问的 Redis；不设置即可关闭缓存。当前 Compose 不映射 Redis 宿主机端口，宿主机后端不能直接使用容器服务名 `redis`。

实现见 [`backend/services/summary_cache.py`](backend/services/summary_cache.py)，测试见 [`backend/tests/test_summary_cache.py`](backend/tests/test_summary_cache.py)。现有缓存测试使用模拟客户端，覆盖命中、降级和失效键；真实 Redis 与路由写后失效联调仍需单独验证。

### 深入：游标分页

问题：`LIMIT/OFFSET` 翻到第 N 页要先扫过并丢弃前 `(N-1) × limit` 行；同时，只按日期排序时同一天多条记录的顺序不稳定，翻页会漏项或重复。

做法：按 `(transaction_date DESC, id DESC)` 排序，把上一页最后一条的排序键编码成不透明游标，下一页用行构造器比较继续：

```sql
SELECT ... FROM transactions
WHERE user_id = :user_id
  AND transaction_date >= :month_start
  AND transaction_date <  :next_month_start
  AND (transaction_date, id) < (:last_date, :last_id)
ORDER BY transaction_date DESC, id DESC
LIMIT :limit + 1;
```

几个关键点：

- **行比较代替 `AND`**：`date < d AND id < i` 会漏掉「日期更早但 id 更大」的行，字典序比较才正确。
- **多取一条判断 `has_more`**：翻页本身不依赖 `COUNT(*)`，书签取本页最后一条，不是多出来的那条；`total` / `total_pages` 由同一过滤条件的子查询单独 `COUNT` 一次。
- **游标不透明**：Base64 编码 `{日期, id}`，客户端原样回传；解不开、类型不对、越界统一返回 422，不静默回第一页。
- **索引与排序同向**：索引列为 `(user_id, transaction_date, id)`，与 `ORDER BY transaction_date DESC, id DESC` 一致，可反向扫描；如果索引缺 `id`，同一天内的排序会退化成 `Incremental Sort`。
- **半开区间**：月份用 `[本月第一天, 下月第一天)`，避免月末天数与时区边界问题，也不在日期列上做函数运算。

实现见 [`backend/services/pagination.py`](backend/services/pagination.py)，测试见 [`backend/tests/test_pagination.py`](backend/tests/test_pagination.py)（覆盖同日不漏、满页无书签、空游标/乱码游标 422、跨用户隔离）。

### 深入：幂等创建流水

问题：用户双击、客户端超时重试、网关重投，都可能让同一个“创建流水”请求到达两次。前端按钮防抖只能改善体验，不能保证服务端只执行一次。

做法：创建流水必须带 `Idempotency-Key`；服务端用 `(user_id, idem_key)` 复合主键保存键，并用 `INSERT ... ON CONFLICT DO NOTHING` 抢键：

```sql
INSERT INTO idempotency_keys (user_id, idem_key, request_hash)
VALUES (:user_id, :idem_key, :request_hash)
ON CONFLICT (user_id, idem_key) DO NOTHING
RETURNING user_id;
```

返回值分两种：

- 返回一行：本次请求抢到键，继续校验账户/分类、创建流水，并在同一事务里回填 `transaction_id`；
- 返回 0 行：键已存在，查询原记录；`request_hash` 相同返回原流水，不同返回 409。

几个关键点：

- **唯一索引是仲裁者**：`SELECT` 再 `INSERT` 在并发下不可靠，查和插之间存在窗口；复合主键/唯一索引才能原子裁决。
- **键和流水同事务**：键插入、流水插入、`transaction_id` 回填一次提交；任一步失败，键也回滚，客户端可以安全重试。
- **请求指纹**：对规范化后的 JSON 做 SHA-256，字段顺序不影响结果；同键不同体返回 409，不静默执行第二次。
- **用户隔离**：主键包含 `user_id`，不同用户用同一个 UUID 不会互相阻塞，也不能拿到对方的流水。
- **提交在返回前**：创建接口在返回 `201` 或重放响应前提交，避免“响应成功但事务未提交”。
- **前端配合**：创建请求生成 `crypto.randomUUID()`，失败重试复用；成功或修改表单字段后清空；PUT 编辑不需要幂等键。

实现见 [`backend/services/ledger.py`](backend/services/ledger.py)，迁移见 [`backend/migrations/versions`](backend/migrations/versions)，测试见 [`backend/tests/test_idempotency.py`](backend/tests/test_idempotency.py) 和 [`backend/tests/test_api.py`](backend/tests/test_api.py)（覆盖顺序重复、同键异体、不同键同体、并发抢键、用户隔离和事务失败回滚）。

## 接口

所有接口以 `/api` 为前缀；除注册、登录、退出和健康检查外，其余接口都需要登录 Cookie。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查，包含一次数据库查询 |
| POST | `/api/auth/register` | 注册 |
| POST | `/api/auth/login` | 登录，写入 HttpOnly Cookie |
| POST | `/api/auth/logout` | 退出，清除 Cookie |
| GET | `/api/auth/me` | 当前登录用户 |
| POST | `/api/ai/transaction-draft` | 保留的单笔草稿接口，文本最多 500 字符，不创建流水 |
| POST | `/api/ai/transaction-drafts` | 多笔草稿接口，文本最多 1500 字符、最多 10 笔；需要登录并启用 AI，不创建流水 |
| GET | `/api/transactions` | 当前用户全部流水（兼容旧接口） |
| POST | `/api/transactions` | 新增流水；必须带 `Idempotency-Key`（1—200 字符） |
| PUT | `/api/transactions/{id}` | 修改流水 |
| DELETE | `/api/transactions/{id}` | 删除流水 |
| GET | `/api/transactions/page` | 按月游标分页，参数 `year`、`month`、`limit`、`cursor`；支持 `q`（描述/账户/分类模糊搜索）、`money_type`、`account_id` 筛选，返回 `total`、`total_pages` |
| GET | `/api/transactions/{year}/{month}` | 按月全量（旧接口） |
| GET | `/api/summary` | 月度收入、支出、结余与收支笔数，参数 `year`、`month`；启用 Redis 后缓存 60 秒 |
| GET | `/api/reports/daily-trend` | 当月每日收支趋势，无流水的日期补 0，参数 `year`、`month` |
| GET | `/api/reports/category-expenses` | 当月支出按分类汇总，按金额倒序 |
| GET | `/api/reports/account-summary` | 当月各账户收入、支出与结余，含无流水账户 |
| GET / POST | `/api/accounts` | 账户列表 / 新增 |
| PUT / DELETE | `/api/accounts/{id}` | 修改 / 删除账户 |
| GET / POST | `/api/categories` | 分类列表（`money_type`）/ 新增 |
| PUT / DELETE | `/api/categories/{id}` | 修改 / 删除分类 |

创建流水首次返回 `201`；同键同体重放返回 `200` 并带 `Idempotent-Replayed: true`；同键不同请求体返回 `409`。

分页响应：

```json
{
  "items": [
    {
      "id": 106,
      "account_id": 1,
      "category_id": 4,
      "money": "5000.00",
      "money_type": "收入",
      "description": null,
      "transaction_date": "2026-10-18",
      "created_at": "2026-10-18T09:12:00+08:00"
    }
  ],
  "next_cursor": "eyJkIjoiMjAyNi0xMC0xOCIsImlkIjoxMDZ9",
  "has_more": true,
  "total": 42,
  "total_pages": 3
}
```

最后一页返回 `"next_cursor": null, "has_more": false`。

## AI 记账助手

在 React 导航中打开“AI 助手”（`/assistant`），先创建账户和分类，再输入一段收支，例如“今天用现金付了早餐 8 元、午饭 18 元，两顿合计 26 元”。模型按实际收支拆成草稿，提示词要求合计不重复记账。生成后可切换草稿、修改字段或放弃某笔；逐笔点击“确认入账”才会创建流水，也可以使用手动记账。

React 使用 `/api/ai/transaction-drafts`：接收 `text`（去除首尾空白后不能为空，原始输入最多 1500 字符）和 `reference_date`（`YYYY-MM-DD`，前端传本地日期）。响应包含最多 10 项 `drafts`、整体 `warnings` 和 `prompt_version`；每笔都有 `ready` 或 `needs_input` 状态、提取字段和问题列表，信息缺失时保留草稿供补齐。

模型报告超量或实际返回超过 10 笔时，接口返回 422；输出未正常结束时拒绝返回部分结果。提示词要求跳过转账、外币并给出说明，未识别到交易时可返回空列表。模型仍可能漏记、重复或误判，即使状态为 `ready` 也要核对原文与每笔草稿。原 `/api/ai/transaction-draft` 保留单笔响应结构与 500 字符限制。

### 启用与配置

AI 默认关闭，不影响普通手动记账。本地直接运行后端时，在 `backend/.env` 中追加以下配置并重启后端（现有 `.env.example` 尚未包含这些项）：

```dotenv
AI_ENABLED=true
AI_API_KEY=replace-with-your-provider-key
AI_BASE_URL=https://api.deepseek.com/v1
AI_MODEL=replace-with-a-model-available-to-your-account
AI_OUTPUT_MODE=json_object
AI_TOKEN_FIELD=max_tokens
```

`AI_BASE_URL` 必须使用 HTTPS，代码会在其后拼接 `/chat/completions`；这里的地址对应代码默认值，不代表已验证模型服务可用。模型名称、结构化输出模式和 token 参数需要与所用服务匹配。支持 `json_object` / `json_schema` 两种输出模式，以及 `max_tokens` / `max_completion_tokens` 两种 token 参数名。

**Docker Compose 已支持可选的 `backend/.env`**：`services.backend.env_file` 会把该文件中的变量注入容器，文件不存在也可启动普通记账功能。把上述 AI 配置写入 `backend/.env` 后，在仓库根目录执行 `docker compose up -d backend` 重新创建配置发生变化的容器；生产环境使用 `docker compose -f compose.yaml -f compose.prod.yaml up -d backend`。

根目录 `.env` 仍负责 Compose 中数据库密码与签名密钥等插值，不能用它替代 `backend/.env` 来传入未显式声明的 AI 变量。Compose 的 `environment` 优先于 `env_file`，数据库连接、签名密钥、Cookie、SQL 日志及 `REDIS_URL` 等显式配置会覆盖文件同名值。环境文件不会打包进后端镜像，实际密钥不要提交到仓库。

可选配置及代码默认值：

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| `AI_MAX_OUTPUT_TOKENS` | `800` | 单笔接口模型输出 token 上限 |
| `AI_BATCH_MAX_OUTPUT_TOKENS` | `2400` | 多笔接口模型输出 token 上限 |
| `AI_REASONING_EFFORT` | `none` | 代码对 `api.deepseek.com` 默认发送关闭思考参数；其他值为 `low` / `high` / `max`，需与实际模型能力匹配 |
| `AI_TIMEOUT_SECONDS` | `90` | 后端模型请求超时秒数 |
| `AI_PER_MINUTE` | `5` | 每用户每分钟请求上限 |
| `AI_PER_DAY` | `50` | 每用户每日请求上限 |
| `AI_GLOBAL_PER_DAY` | `200` | 当前进程每日总请求上限 |
| `AI_CONCURRENCY` | `2` | 当前进程并发模型调用上限 |

可选 AI 配置同样可写入 `backend/.env`，Compose 会一并加载。限流计数仍保存在进程内存中，未接入 Redis；重启会清空，多实例之间不共享，每日计数按 UTC 日期重置。限额按模型请求次数计，不按返回草稿笔数计；已尝试的上游调用即使失败也可能消耗次数和费用。

### 数据与验证边界

- 模型服务会收到用户输入、参考日期，以及当前用户候选账户和分类的 ID、名称、分类收支类型；不发送完整历史流水。生成草稿不写数据库。
- 前端将当前待确认入账请求和幂等键保存在当前标签页的 `sessionStorage` 中，按用户 ID 区分；结果不确定时锁定切换，重试同一笔或先核对账本。其他未提交草稿只保存在页面内存，离开或刷新页面会丢失，逐笔入账也不是整批原子事务。
- 当前前端解析等待上限为 125 秒，后端默认 90 秒、可配置上限 120 秒；部署时还需核对 nginx 等中间代理的超时。成功入账后若浏览器存储删除失败，仍可能残留旧待确认记录。
- AI 前后端已有模拟测试，覆盖批量结构与数量边界、逐笔校验、单笔兼容和前端确认重试；真实模型提取效果、服务参数兼容性和费用仍需单独验证。普通账本端到端测试通过不代表真实 AI 链路已验证。

## 工程质量

| 任务 | 检查内容 |
| --- | --- |
| `backend` | Ruff 检查与格式校验、mypy、`alembic upgrade head` + `alembic check`、pytest（PostgreSQL 18 服务） |
| `frontend` | Oxlint / ESLint、`vue-tsc` 类型检查、Vite 构建 |
| `frontend-react` | ESLint、`tsc -b` 类型检查、vitest 单元测试、`vite build` |
| `e2e` | Playwright 主链路：注册 → 登录 → 记一笔 → 编辑 → 删除（PostgreSQL 18 服务） |

后端测试分为纯单元测试和数据库集成测试。集成测试使用真实 PostgreSQL，在会话开始时清理专用测试库并执行 `alembic upgrade head` 建表，各数据库用例前清空业务数据，验证迁移后的真实结构。整体覆盖注册登录、用户隔离、账户/分类约束、流水增删改、幂等重放与并发抢键、事务提交与回滚、分页与筛选、报表、配置校验和离线迁移。

React 测试覆盖筛选、会话、格式化，以及多笔 AI 草稿切换、补齐、逐笔入账和重试等流程，共 21 项；AI 流程使用模拟 API 响应。后端共 171 项测试，包含 AI 草稿和汇总缓存的模拟测试。2026-11-28（北京时间）的 [PR #19 CI](https://github.com/8ight1een/-Tallywise/actions/runs/46031341389) 已通过后端、Vue、React 和端到端四项任务；该 CI 不验证真实模型或真实 Redis 服务。

端到端测试见 `frontend-react/e2e`：`npm run test:e2e` 通过 Playwright 自动拉起后端与前端（本地已运行则复用），执行注册登录、新增流水、编辑金额、删除流水的完整链路。首次运行需要 `npx playwright install chromium`，运行前需要准备已迁移的专用测试库，并让后端的 `DATABASE_NAME` 指向该库。该测试会写入用户和流水，且本地可能复用已有服务，运行前应确认服务连接的是测试库；CI 使用独立 PostgreSQL 服务。

<details>
<summary>本地运行检查</summary>

```powershell
# backend
psql -U postgres -c "CREATE DATABASE tallywise_test;"
$env:TEST_DATABASE_NAME = "tallywise_test"
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m mypy .
.\.venv\Scripts\python.exe -m pytest -q

# frontend
npm run lint:ci
npm run build

# frontend-react（在该目录运行）
npm run check
```

测试库必须可清空，`TEST_DATABASE_NAME` 与 `DATABASE_NAME` 不同，否则测试会拒绝运行。

</details>

## 快速开始

需要 Docker Desktop（或 Docker Engine + Compose）；前端需要 Node.js 24.12+。

```powershell
git clone https://github.com/8ight1een/-Tallywise.git
Set-Location -LiteralPath '.\-Tallywise'
Copy-Item .env.example .env
# 编辑 .env：替换 POSTGRES_PASSWORD 与 SECRET_KEY
docker compose up --build -d
```

Compose 启动 PostgreSQL、Redis、后端和 React 前端：前端由 nginx 托管在 <http://localhost:8080>，`/api` 由 nginx 反向代理到后端，后端只在 `127.0.0.1:8000` 暴露。AI 默认未启用，按上面的配置说明单独开启。

需要前端热更新时，在仓库根目录打开终端，选择其中一套前端运行。Vue 保留实现：

```powershell
cd frontend
npm ci
npm run dev
```

React 前端（另开仓库根目录终端）：

```powershell
cd frontend-react
npm ci
npm run dev
```

- 接口文档：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/api/health>
- 前端：终端输出的地址，默认 <http://localhost:5173>（`/api` 已代理到后端）；两个前端默认端口相同，不要同时启动
- 容器化运行：<http://localhost:8080>（nginx 托管构建产物，见下节）

### 生产运行（Docker Compose）

基础 Compose 包含四个服务；生产启动与更新命令见下方：

| 服务 | 说明 |
| --- | --- |
| `db` | PostgreSQL 18，数据保存在 `pgdata` 卷，不映射宿主机端口 |
| `redis` | Redis 7，供后端缓存月度汇总，不映射宿主机端口；缓存可丢失并重新生成 |
| `backend` | 启动前执行 `alembic upgrade head`，仅暴露在 `127.0.0.1:8000` |
| `frontend-react` | 多阶段构建：Node 构建 `dist`，再由 nginx 托管；`/api` 反代到 `backend:8000` |

nginx 负责三件事：

1. 托管 `dist` 静态文件；`assets/` 下带哈希的文件缓存一年，`index.html` 不缓存
2. SPA 回退：`try_files $uri $uri/ /index.html`，刷新 `/overview` 不会 404
3. `/api` 同源代理：Cookie 的 `SameSite=Lax` 直接生效，不需要 CORS

仓库已提供 [`compose.prod.yaml`](compose.prod.yaml)（开启 `COOKIE_SECURE=true`）、[`deploy/Caddyfile`](deploy/Caddyfile)（HTTPS 反向代理）、[`deploy/bootstrap.sh`](deploy/bootstrap.sh)（服务器初始化）和 [`scripts/backup.sh`](scripts/backup.sh)（数据库备份）。生产更新使用：

```powershell
git pull
docker compose -f compose.yaml -f compose.prod.yaml up -d --build
```

配置文件入库不等于部署完成：仍需设置实际域名、安装并配置宿主机 Caddy、安排备份定时任务和验证恢复，并配置防火墙。生产叠加配置开启 Secure Cookie，需通过 HTTPS 访问。

<details>
<summary>不用 Docker：本地运行后端</summary>

需要 Python 3.14、PostgreSQL 18 和 `psql`。

```powershell
psql -U postgres -c "CREATE DATABASE tallywise;"
cd backend
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env      # 配置数据库连接与 SECRET_KEY
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

已有手工建表的数据库先核对结构再确定迁移起点；`alembic stamp` 只记录版本，不修复表结构。

</details>

### 静态界面原型

直接用浏览器打开 [`backend-ui-preview/index.html`](backend-ui-preview/index.html) 或 [`login.html`](backend-ui-preview/login.html)，无需安装依赖。原型使用浏览器本地演示数据，不连接后端，登录页也不会创建真实用户；详见 [`backend-ui-preview/README.md`](backend-ui-preview/README.md)。

## 边界与后续

- 分页按 `(日期, id)` 向后翻，不支持按页码跳页；`total_pages` 只用于展示进度，翻页仍靠游标。游标不绑定月份，跨月复用会得到空页或残缺一页。
- Vue 页面仍一次加载整月流水，未接入搜索筛选与报表接口；React 前端已支持筛选、游标分页与报表展示。
- React 是默认 Compose 前端，AI 助手目前仅在 React 中提供；Vue 实现继续保留。静态界面原型独立于两套正式前端。
- AI 默认关闭；支持多笔提取和逐笔确认，不提供整批入账事务。真实模型效果、代理超时和浏览器存储异常处理仍需验证或完善。
- 报表统计按自然月：日趋势补齐整月；分类支出不含收入；账户汇总的结余是当月收入减支出，不是账户历史余额。
- 创建流水必须带 `Idempotency-Key`，未带键的旧客户端会收到 422；幂等键当前只增不删，尚未做过期清理。
- `PUT` 编辑按 `id` 更新，不使用幂等键；只有创建流水需要幂等保护。
- 事务提交统一放在写路由返回前，读接口不提交；新增写接口时必须同步加 `commit()`，否则响应成功也不会落库。
- 认证是无状态 JWT，没有即时吊销机制；退出登录仅清除 Cookie。
- 月度汇总已有 Redis 缓存，允许短暂陈旧，真实 Redis 联调与路由失效测试仍需补齐；其他报表未接入缓存。未实现全站限流，AI 仍仅有进程内限流，尚未实现共享限额或验证多实例部署。已有 HTTPS、Secure Cookie 与备份相关配置，仍需按环境落实和验证。

## 可以深入讨论的点

| 话题 | 代码入口 |
| --- | --- |
| 游标分页、索引设计与 `EXPLAIN` | [`services/pagination.py`](backend/services/pagination.py) |
| 报表聚合口径与补零 | [`services/reports.py`](backend/services/reports.py) · [`tests/test_reports.py`](backend/tests/test_reports.py) |
| 汇总缓存、写后失效与故障降级 | [`services/summary_cache.py`](backend/services/summary_cache.py) · [`tests/test_summary_cache.py`](backend/tests/test_summary_cache.py) |
| 幂等键、请求指纹与并发抢键 | [`services/ledger.py`](backend/services/ledger.py) · [`tests/test_idempotency.py`](backend/tests/test_idempotency.py) |
| 分类行锁与并发校验 | [`services/ledger.py`](backend/services/ledger.py) |
| 事务边界与回滚 | [`database.py`](backend/database.py) · [`routers/items.py`](backend/routers/items.py) · [`services/ledger.py`](backend/services/ledger.py) |
| 用户数据隔离与越权防护 | [`routers/items.py`](backend/routers/items.py) |
| 迁移链与结构一致性 | [`migrations/versions`](backend/migrations/versions) |
| 异常映射与请求追踪 | [`main.py`](backend/main.py) · [`middleware.py`](backend/middleware.py) |
| 前端登录失效与请求封装 | [`frontend/src/api/client.ts`](frontend/src/api/client.ts) · [`frontend-react/src/api.ts`](frontend-react/src/api.ts) · [`frontend-react/src/auth.ts`](frontend-react/src/auth.ts) |
| React 端幂等键复用与游标翻页 | [`frontend-react/src/components/TransactionDialog.tsx`](frontend-react/src/components/TransactionDialog.tsx) · [`frontend-react/src/components/TransactionList.tsx`](frontend-react/src/components/TransactionList.tsx) |
| AI 字段提取、服务端校验与限流 | [`backend/ai_drafts.py`](backend/ai_drafts.py) · [`backend/routers/ai.py`](backend/routers/ai.py) |
| AI 草稿确认与待确认提交恢复 | [`frontend-react/src/pages/AiAssistantPage.tsx`](frontend-react/src/pages/AiAssistantPage.tsx) · [`frontend-react/src/ai.ts`](frontend-react/src/ai.ts) |
