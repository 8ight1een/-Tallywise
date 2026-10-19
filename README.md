#  Tallywise

个人记账学习项目，目前使用 FastAPI、SQLAlchemy 和 PostgreSQL。前期使用 MySQL，切换过程记录在第 17 节。
该项目因家人需求而创造，并会根据用户使用反馈进行迭代，也会根据本人技术栈的更新来迭代。


## 目录
- `database/schema.sql`:MySQL建表脚本
- `database/schema_pg.sql`：PostgreSQL 建表脚本
- `backend/`：后端源码、依赖清单
- `frontend/`:前端源码



## 学习过程
### 1. 准备数据库

在 MySQL 中自行创建一个空数据库（例如 tallywise，使用 utf8mb4 字符集），选择该数据库后执行 `database/schema.sql`。
脚本只建表，不创建数据库或 MySQL 用户。请勿在已有数据的库中重复执行。
脚本不包含演示数据，可自行添加。

### 2.后端连接数据库
在 `backend/database.py` 中配置数据库访问，使用 SQLAlchemy 和 `aiomysql` 驱动进行异步数据库操作。

连接信息通过以下环境变量提供：

|环境变量|含义|
|---|---|
|`DATABASE_USERNAME`|MySQL 用户名|
|`DATABASE_PASSWORD`|MySQL 密码|
|`DATABASE_HOST`|MySQL 服务器地址，本机通常为 `localhost`|
|`DATABASE_NAME`|第一步创建的数据库名称|

当前代码使用端口 `3306`，如果本机 MySQL 使用其他端口，需要同步修改。

数据库访问代码分为四部分：

1. 使用 `URL.create()` 组织数据库连接信息。
    
2. 使用 `create_async_engine()` 创建异步引擎，管理数据库连接池。
    
3. 使用 `async_sessionmaker()` 创建会话工厂，为后续数据库操作提供 `AsyncSession`。
    
4. 封装 `commit_session()`，统一处理事务提交和数据完整性异常：
    
    - 调用 `session.commit()` 提交事务。
        
    - 如果发生 `IntegrityError`（例如违反唯一约束或外键约束），调用 `session.rollback()` 回滚事务。
        
    - 返回 HTTP `409 Conflict`，由调用方通过 `detail` 提供具体的错误提示。

创建引擎并不代表已经连接成功，需要实际执行数据库查询，才能验证连接配置是否可用。

### 3. 定义 ORM 模型

使用 SQLAlchemy ORM 建立 Python 类与数据库表之间的映射，模型结构与 `database/schema.sql` 中的表定义保持一致。

1. 定义统一的 ORM 基类 `Base`，所有模型继承该基类。
    
2. 优先编写没有外键依赖的表对应的模型，再编写依赖其他表的模型。
    
3. 对照建表脚本，配置表名、字段类型、主键、外键、非空和唯一约束。
    
4. 可以使用 `AsyncSession` 执行一次简单查询，检查模型映射是否可用。空表返回空结果属于正常情况。
    

ORM 模型的定义不会自动创建或修改数据库表。如果调整表结构，需要同步修改模型。

### 4. 定义接口数据模型

在 `backend/schemas.py` 中使用 Pydantic 定义接口接收和返回的数据结构。

1. 定义新增数据的请求模型，声明客户端需要提供的字段、类型和校验规则。
    
2. 定义响应模型，明确接口返回的字段，排除密码哈希等敏感信息。
    
3. 请求模型通常不包含由数据库生成的主键；响应模型可根据需要包含主键和创建时间。

ORM 模型负责描述数据库表的映射，Pydantic 模型负责接口数据的校验和序列化，两者按各自用途分别定义。

### 5. 封装 JWT 工具

在 `backend/security.py` 中封装 JWT 的生成和校验逻辑，为登录和身份验证提供基础功能。

1. 从环境变量读取签名密钥，并配置签名算法与令牌有效期。真实密钥不提交到 Git。
    
2. 编写令牌生成函数，将用户 ID 以字符串形式写入 `sub`，并通过 `exp` 设置过期时间。
    
3. 编写令牌校验函数，固定允许的签名算法，验证签名和有效期，并要求包含 `sub`、`exp` 字段。
    
4. 对过期、被篡改或缺少必要字段的令牌，统一按身份验证失败处理。
   

### 6. 创建应用入口和健康检查接口

在 `backend/main.py` 中创建 FastAPI 应用，并添加 `/health` 接口，用于检查后端服务是否能够正常响应。
在 `backend` 目录下，使用已安装项目依赖的 Python 环境启动服务：

```powershell
python -m uvicorn main:app --reload
```
访问 `http://127.0.0.1:8000/health`，正常情况下返回 HTTP 200 和以下内容：
```json
{"status": "ok"}
```
该接口只检查应用是否能响应请求，不检查数据库连接或 JWT 功能。`--reload` 用于本地开发。

### 7. 实现用户注册功能

编写注册接口，接收用户信息，将密码哈希处理后保存到数据库。

1. 定义注册请求模型，校验账号、密码等字段的格式和长度。
    
2. 使用密码哈希工具处理密码，数据库只保存密码哈希，不保存明文密码。
    
3. 创建用户 ORM 对象，通过数据库会话添加并提交。
    
4. 为账号或邮箱等需要唯一的字段设置数据库唯一约束；发生重复冲突时回滚事务，返回明确的错误提示。
    
5. 使用响应模型返回用户编号、账号等必要信息，不返回密码或密码哈希。
    
6. 将注册路由注册到 `main.py` 的 FastAPI 应用中（先增加环境变量再导入读取环境变量的模块）。
    

本步骤只负责创建账号。注册成功后，由用户通过后续登录接口建立登录状态。可以通过docs来测试注册接口。

### 8. 编写用户登录和退出接口

在 `backend/routers/users.py` 中添加登录和退出接口，使用 JWT 与 Cookie 管理登录凭证。

1. 在 `backend/schemas.py` 中新增 `UserLogin` 请求模型，接收邮箱和密码。

2. 登录时根据邮箱查询用户，使用 `verify_password()` 比较输入的密码与数据库中的密码哈希；用户不存在或密码错误时，返回 HTTP 401。

3. 通过 `response: Response` 获取响应对象，将生成的 JWT 写入名为 `access_token` 的 Cookie。

4. 设置 `HttpOnly`、`SameSite`、`Secure` 和有效期，控制 Cookie 的读取权限、发送条件和保存时间。

5. 添加退出接口，通过 `delete_cookie("access_token")` 通知浏览器删除登录 Cookie。

当前接口代码仍需修正和验证：密码哈希字段应使用 `user.password_hash`，生成 JWT 时应将用户 ID 转为字符串，`jwt.encode()` 的 `algorithm` 参数应使用 `"HS256"`。

修正后，通过 `/docs` 检查正确密码登录、错误密码拒绝、不存在的邮箱拒绝，以及退出响应是否设置删除 Cookie 的指令。删除 Cookie 不会立即使已经签发的 JWT 失效（JWT弊端）。

### 9. 初始化前端开发环境

在 `frontend` 目录中使用 create-vue 初始化 Vue 项目，通过 Vite 启动本地开发服务器。

1. 检查 Node.js 和 npm 是否安装：

   ```powershell
   node --version
   npm.cmd --version
   ```

   Node.js 版本需要满足 `frontend/package.json` 中的 `engines.node` 要求。当前要求为 `^22.18.0 || >=24.12.0`。

2. 首次初始化时，创建并进入前端目录：

   ```powershell
   New-Item -ItemType Directory -Force -Path "D:\tallywisee\frontend"
   Set-Location "D:\tallywisee\frontend"
   ```

3. 使用 Vue 官方脚手架在当前目录创建项目：

   ```powershell
   npm.cmd create vue@latest .
   ```

   命令末尾的 `.` 表示在当前目录生成项目，不再创建一层子目录。按照交互提示选择功能，当前项目包含 TypeScript、Vue Router、ESLint、Oxlint 和 Prettier。

   此命令只在首次创建项目时执行。如果目录中已有 `package.json` 和源码，跳过此步，避免覆盖现有文件。

4. 安装项目依赖：

   ```powershell
   npm.cmd install
   ```

   安装后生成 `node_modules` 和 `package-lock.json`。提交源码时保留锁文件，`node_modules` 由 `.gitignore` 排除。

5. 启动本地开发服务器：

   ```powershell
   npm.cmd run dev
   ```

   在浏览器中打开终端显示的 Local 地址。开发服务器会持续占用当前终端，按 `Ctrl+C` 停止。

6. 停止开发服务器后，检查项目能否构建：

   ```powershell
   npm.cmd run build
   ```

   当前构建命令包含 TypeScript 类型检查和生产构建，生成的 `dist` 目录由 `.gitignore` 排除。

本步骤用于建立前端工程和开发环境。页面能够打开、项目能够构建，不代表已经完成与 FastAPI 后端的接口联调。

### 10. 配置开发代理并封装 API 请求工具

前端由 Vite 开发服务器提供（默认 `http://localhost:5173`），后端由 uvicorn 提供（默认 `http://127.0.0.1:8000`），端口不同即属于跨源。先在 `frontend/vite.config.ts` 中配置开发代理，再在 `frontend/src/api/client.ts` 中封装基于 `fetch()` 的请求工具，为后续页面调用后端接口提供统一入口。

1. 在 `frontend/vite.config.ts` 中配置 `server.proxy`，把 `/api` 开头的请求转发给后端：

   ```ts
   server: {
     proxy: {
       '/api': {
         target: 'http://127.0.0.1:8000',
         changeOrigin: true,
       },
     },
   },
   ```


2. 前端统一使用相对路径 `/api/...` 请求接口。写成后端的完整地址会重新变成跨源请求，`credentials: 'same-origin'` 在跨源时不会携带 Cookie，登录状态无法建立；经过代理后浏览器只看到开发服务器这一个源，后端也不需要配置 CORS。

3. 定义 `request<T>()`，统一处理请求选项、JSON 请求体和响应解析，通过泛型声明预期的返回数据类型。

4. 使用 `credentials: 'same-origin'`，在同源请求中携带登录 Cookie。

5. 定义 `ApiRequestError`，保存错误信息和 HTTP 状态码，统一处理网络错误、接口失败和响应格式错误。

6. 优先读取后端返回的字符串 `detail` 作为错误提示，没有可用信息时使用默认提示。

7. 提供未登录回调、会话重置和错误判断工具，通过会话版本区分请求所属的登录状态，避免旧请求的 401 干扰新会话。登录成功后需要调用 `resetApiSession()` 恢复会话状态。

8. 对 HTTP 204 响应直接返回，不尝试解析 JSON。

9. 修改代理配置后需要重启开发服务器才会生效。可以在浏览器控制台用 `fetch('/api/...')` 验证请求能否到达后端，以及响应头中的 `Set-Cookie` 是否被浏览器保存。

本步骤只配置开发代理并封装请求工具，页面调用留到下一步。


### 11. 实现前端登录页

在 `frontend/src/components/LoginForm.vue` 中实现登录表单，由 `frontend/src/App.vue` 根据当前登录用户切换登录页和主界面。本步骤先用组件状态控制显示，暂不引入 vue-router。

1. 在 `frontend/src/types/index.ts` 中定义接口数据类型，与后端返回保持一致：

   ```ts
   export interface User {
     id: number
     email: string
     nickname: string | null
   }

   export interface LoginResponse {
     message: string
     user: User
   }
   ```

2. 后端 `POST /api/auth/login` 需要返回登录结果，登录成功的响应体为：

   ```json
   {"message": "登录成功", "user": {"id": 1, "email": "me@example.com", "nickname": "测试"}}
   ```

   登录接口此前只写入 Cookie、没有返回值，前端会拿到 `null`，读取 `user` 时直接抛错。

3. 在 `LoginForm.vue` 中定义 `email`、`password`、`isLoading`、`errorMessage` 四个响应式状态，输入框用 `v-model` 绑定，表单用 `@submit.prevent="handleLogin"` 阻止默认提交跳转。

4. 组件通过 props 接收 `initialEmail` 和 `notice`，邮箱输入框用前者初始化，后者用于显示"注册成功，请重新登录"之类的提示；通过 `defineEmits` 声明 `loginSuccess` 事件，把登录结果交给父组件。

5. 使用 `request<LoginResponse>()` 调用登录接口，传入 `method: 'POST'`、`json` 请求体和 `fallbackMessage` 默认提示，并用泛型声明返回类型，避免把响应当成 `any` 使用。

6. 登录接口是公开接口，调用时显式传入 `requiresAuth: false`。否则密码错误返回的 401 会被当成"登录状态已失效"，触发未登录回调。

7. 登录成功后清空密码框，调用 `resetApiSession()` 恢复会话状态，再通过 `emit('loginSuccess', user)` 把用户信息交给父组件。

8. 登录失败时用 `errorMessage()` 取出后端返回的提示显示在表单上方，`isLoading` 为真时禁用提交按钮，避免重复提交。

9. 在 `App.vue` 中用 `currentUser` 保存当前用户：为 `null` 时渲染 `LoginForm`，通过 `@login-success` 接收子组件事件；登录成功后渲染主界面，显示昵称或邮箱。

10. 样式统一定义在 `frontend/src/assets/main.css`：登录页使用 `auth-screen`、`auth-card`、`auth-brand`、`brand-mark`、`auth-subtitle`、`auth-form`、`auth-submit`、`auth-error` 等类名，主界面使用 `app`、`header`、`user-info`、`greeting` 等类名，组件内不再重复写样式。`frontend/src/main.ts` 引入该样式文件，`frontend/index.html` 设置页面标题。

本步骤只实现登录。注册、退出登录和主界面内容留到下一步。

### 12. 实现注册、登录态恢复与退出登录

在 `frontend/src/components/RegisterForm.vue` 中实现注册页，在 `frontend/src/components/DashboardView.vue` 中搭出主界面，并在 `frontend/src/App.vue` 中集中管理登录状态：注册成功后回到登录页、刷新页面时用 `/api/auth/me` 恢复登录态、退出登录时清除状态。后端在 `backend/routers/users.py` 中新增 `/api/auth/me` 接口。

1. 后端新增 `GET /api/auth/me`，通过 `Depends(get_current_user)` 读取 Cookie 中的 JWT 并返回当前用户的编号、邮箱和昵称，未登录或令牌失效时统一返回 401。这是 `get_current_user` 第一次被真正调用，登录 Cookie 的有效性也第一次得到验证。

2. 在 `App.vue` 中集中管理状态：`currentUser`（当前用户）、`authMode`（`login` / `register`）、`loginEmail`（注册成功后预填的邮箱）、`authNotice`（提示信息）、`isCheckingAuth`（是否正在检查登录状态）、`isLoggingOut`（是否正在退出）。

3. 首次加载时调用 `GET /api/auth/me` 恢复登录态。因为"没有登录"是正常情况而不是错误，所以传入 `requiresAuth: false`，并且只有非 401 的错误才写入 `authNotice`，401 直接当作未登录处理。

4. 用 `onUnauthorized()` 注册全局的登录过期回调：清空 `currentUser`、切回登录页、保留邮箱并显示"登录已过期，请重新登录。"；组件卸载时通过 `onUnmounted` 注销回调，避免回调重复注册。

5. 登录成功后调用 `resetApiSession()` 并清空提示，恢复会话状态；退出登录调用 `POST /api/auth/logout`，成功后同样调用 `resetApiSession()` 并清空 `currentUser`，重新回到登录页。

6. 注册页包含昵称、邮箱、密码和确认密码四个输入框，提交前先在前端比对两次密码是否一致，避免多打一次接口；请求成功后清空密码框，通过 `emit('registerSuccess', email)` 把邮箱交回父组件。

7. 父组件收到注册成功事件后切回登录页并预填邮箱，用户只需再输入密码即可登录。

8. 主界面通过 props 接收 `user` 和 `isLoggingOut`，顶部显示昵称、邮箱和退出按钮，`isLoggingOut` 为真时禁用按钮并显示"退出中…"，避免重复点击。

9. `LoginForm.vue` 同步调整：请求期间禁用输入框，`handleLogin` 开头判断 `isLoading` 防止重复提交。

10. 页面按状态依次渲染四种视图：正在检查登录状态 → 登录页 → 注册页 → 主界面。

本步骤完成后，前端已经能和后端跑通"注册 → 登录 → 主界面 → 退出"的完整闭环，刷新页面也能恢复登录态。

### 13. 实现记账接口与主界面本月收支汇总

在 `backend/routers/items.py` 中实现交易、账户、分类的接口和月度汇总，并在 `backend/main.py` 中注册路由；前端在 `frontend/src/components/DashboardView.vue` 中读取本月汇总，通过 `frontend/src/components/SummaryCards.vue` 显示结余、收入和支出。交易表单、交易列表和月份切换留到后续步骤。

1. 所有记账接口都通过 `Depends(get_current_user)` 取得当前用户，查询和写入时都带上 `user_id` 条件，避免读到或改到其他用户的数据。

2. 封装 `owned_resource()`，按"资源编号 + 当前用户"查询账户或分类，查不到统一返回 404；查询时加 `with_for_update()`，避免校验通过之后资源被并发删除。

3. 封装 `validate_references()`：新增或修改流水前先校验账户和分类都属于当前用户，并且分类的 `money_type` 与流水的收支类型一致，不一致返回 422。

4. 交易接口：`GET /api/transactions` 查询当前用户的全部流水，`POST /api/transactions` 新增，`POST /api/transactions/{transaction_id}` 更新，`DELETE /api/transactions/{transaction_id}` 删除。更新沿用 POST，删除返回 204。

5. 账户接口 `/api/accounts` 和分类接口 `/api/categories` 各自提供查询、新增、更新、删除。分类名在数据库中有 `(user_id, name_categories)` 唯一约束，新增或改名冲突时由 `commit_session()` 转成 409 和中文提示。

6. 删除账户或分类时数据库外键是 `ON DELETE RESTRICT`，如果名下已有流水会触发完整性错误，同样由 `commit_session()` 转成 409"账户已有流水，不能删除"。

7. 修改分类的收支类型前先检查该分类是否已有流水，有则返回 409，避免历史流水的类型与分类对不上。

8. 新增 `GET /api/transactions/{year}/{month}`，按年月查询流水，结果按 `transaction_date`、`id` 倒序返回，供后续交易列表使用。

9. 新增 `GET /api/summary`，接收可选的 `year` 和 `month`：两者必须同时提供，只给一个返回 422；都不提供时使用数据库的当前年月。按当前用户和指定年月分别统计收入与支出，返回：

   ```json
   {"money_in": 1000, "money_out": 300, "money_sum": 700}
   ```

   `money_sum` 为收入减支出，可以为负数；没有交易时 `SUM` 返回 `NULL`，用 `or 0` 兜底成 0。统计必须带 `user_id` 条件，否则会把其他用户的流水算进来。

10. 前端在 `frontend/src/types/index.ts` 中新增 `Summary` 类型，字段与接口返回保持一致：

    ```ts
    export interface Summary {
      money_in: number
      money_out: number
      money_sum: number
    }
    ```

11. 在 `DashboardView.vue` 中定义 `summary`、`isSummaryLoading` 和 `summaryError`，分别保存汇总结果、加载状态和错误提示。汇总初始值为 `null`，不把尚未读取的数据当作真实的零收入、零支出。

12. 编写 `loadSummary(year, month)`，用 `request<Summary>()` 请求 `/api/summary?year=年份&month=月份`；请求前清空错误并进入加载状态，成功后保存响应，失败时用 `errorMessage()` 取提示，在 `finally` 中结束加载。该接口需要登录，沿用 `requiresAuth` 的默认值，401 继续交给 `App.vue` 中已有的登录过期回调。

13. 主界面挂载时用 `new Date()` 取浏览器本地年份和月份发起请求；`getMonth()` 返回 0–11，传给后端时需要加 1。本步骤固定查看本月。

14. `SummaryCards.vue` 通过 props 接收 `summary`、`isLoading`、`errorMessage` 和 `periodLabel`，按结余、收入、支出的顺序显示三张卡片。金额用 `formatMoney()` 格式化为人民币符号加两位小数；加载时显示“读取中…”，出错或还没有数据时显示“—”，只有接口成功返回时才显示金额（含 `¥0.00` 和负结余）。样式使用 `var(--sage)`、`var(--line)` 等全局变量，窄屏下改为两列和单列。

15. 账户、分类、交易的新增、编辑、删除接口已经写好，但前端还没有调用方，尚未联调；`GET /api/transactions/{year}/{month}` 同理。

本步骤完成"记账接口 + 本月汇总展示"。下一步接交易列表、交易表单和月份切换；接口是否真的可用需要在后端连接 MySQL 后用 `/docs` 或页面手动验证。

### 14. 实现交易记录列表与月份切换

在 `frontend/src/components/TransactionList.vue` 中展示所选月份的交易记录，在 `frontend/src/components/MonthPicker.vue` 中提供月份切换，并在 `frontend/src/components/DashboardView.vue` 中让汇总卡片和记录列表按同一个月份联动加载。后端沿用第 13 点已经写好的 `/api/transactions/{year}/{month}` 和 `/api/categories`。

1. 在 `frontend/src/types/index.ts` 中新增接口类型：`MoneyType` 用字面量联合约束为 `'收入' | '支出'`，`MonthSelection` 用 `'current' | 1 | 2 | … | 12` 同时表示"本月"和具体月份，另外定义 `Category` 和 `Transaction`。

2. `Transaction.money` 声明为 `number | string`：金额经过 JSON 序列化后类型并不稳定，展示前统一转换，避免对接口返回做过于乐观的类型假设。

3. `MonthPicker.vue` 用 props 的 `modelValue` 加 `update:modelValue` 事件实现 `v-model`。选项数组由"本月"和 1–12 月组成，上下箭头按钮按 `selectedIndex` 前后移动，到达边界或 `disabled` 为真时禁用按钮。

4. `DashboardView.vue` 用 `selectedPeriod` 保存当前选择，用 `computed` 的 `periodLabel` 把 `'current'` 转成"本月"、把数字转成"N月"，同一个标签同时用于汇总卡片和记录面板标题。

5. 用 `getQueryPeriod()` 统一算出请求用的 `{ year, month }`：年份取 `new Date().getFullYear()`，选择"本月"时用 `getMonth() + 1`，选择具体月份时直接用该数字。

6. `changePeriod()` 在 `isSummaryLoading` 或 `isTransactionsLoading` 为真时直接返回，值没有变化时也返回，避免连续点击产生交叉请求或重复加载。

7. `loadTransactions(year, month)` 用 `Promise.all` 并行请求三件事：所选月份的流水、`money_type=收入` 的分类、`money_type=支出` 的分类。中文查询参数用 `encodeURIComponent` 编码，取回后把两组分类合并成一个数组，供列表按 `category_id` 查找名称。

8. `refreshFinancialData()` 把汇总和记录放在一起刷新，`onMounted` 时调用；切换月份后两者同时更新，保证卡片数字和列表内容属于同一个月。

9. `TransactionList.vue` 通过 props 接收 `transactions`、`categories`、`isLoading`、`errorMessage`、`selectedPeriod` 和 `isPeriodLoading`，通过 `month-change` 事件把月份变化交回父组件；列表组件本身不直接发请求，数据和状态都由父组件维护。

10. 分类名用 `categories.find()` 按 `category_id` 映射，找不到时显示"未知分类"；这样即使分类被删除，历史记录也不会出现空白。

11. 面板右上角提供"全部 / 支出 / 收入"三个筛选项，用 `computed` 在已经取回的记录上过滤，属于纯前端筛选，不会重新请求接口。

12. 空状态分开处理：加载中显示"正在读取记录……"，请求失败显示错误提示，没有数据时区分"该月份暂无记录"和"当前筛选下暂无记录"。

13. 组件样式写在 scoped `<style>` 中，颜色和边框沿用 `main.css` 中的 `var(--line)`、`var(--card)`、`var(--muted)`、`var(--sage)`、`var(--rose)` 等变量，不重复定义主题色。

本步骤只做展示：还没有新增、编辑、删除入口，第 13 点写好的增删改接口仍未被前端调用；记录里也没有显示所属账户；月份切换只换"月"，年份固定取当前年份，跨年查看留到后续步骤。

### 15. 实现新增交易表单与保存后刷新

在主界面接入新增交易表单，并提供快捷创建账户和分类的入口，让新账号也能录入第一笔账。保存成功后刷新第 14 点的记录列表与汇总，本步骤不接入交易编辑和删除。

1. 在 `frontend/src/types/index.ts` 中新增 `Account` 类型，包含 `id` 和 `name_accounts`，其余字段复用已有的 `MoneyType`、`Category` 和 `Transaction`。

2. 新增 `frontend/src/components/TransactionForm.vue`，用 `ref()` 保存收支类型、金额、分类、账户、备注和日期，表单通过 `@submit.prevent` 调用 `handleSubmit()`。布局、类名和 scoped 样式沿用原项目，只保留新增流程。

3. 组件挂载时读取 `GET /api/accounts` 和当前收支类型的 `GET /api/categories?money_type=...`，成功后默认选中第一个选项；没有账户或分类时保持未选择，允许通过快捷入口创建。并行读取使用 `Promise.allSettled()`，等两项请求结束后再解除加载状态，失败时提供重新读取按钮。

4. 点击“收入 / 支出”时重新读取对应分类，并先清空原分类编号，避免沿用另一种收支类型的分类。账户保持不变，中文查询参数继续使用 `encodeURIComponent()` 编码。

5. 快捷创建账户调用 `POST /api/accounts`，请求体为 `{ "name_accounts": "账户名称" }`；创建分类调用 `POST /api/categories`，请求体为 `{ "name_categories": "分类名称", "money_type": "支出" }`。成功后把返回对象加入下拉选项、选中新编号并清空名称输入框；失败则显示错误并保留输入。

6. 金额使用 `v-model.number`，输入框限制最小值 `0.01`、步长 `0.01`、最大值 `9999999.99`，与后端金额字段的位数约束对应；提交函数再次检查金额是否为有限正数，以及账户、分类和日期是否填写。前端校验用于改善交互，最终仍由后端 Pydantic 和资源归属检查决定是否接受。

7. 使用已有的 `request<Transaction>()` 调用 `POST /api/transactions`，发送 `account_id`、`category_id`、`money`、`money_type`、`description` 和 `transaction_date`。空备注传 `null`；备注长度沿用原表单的 30 字符限制，日期由用户明确选择，不根据列表月份自动推断。

8. 保存成功后清空金额、备注和日期，保留收支类型、账户及分类，方便连续记账；通过 `created` 事件通知父组件。失败时保留本次填写内容并显示错误，不发出成功事件。

9. `DashboardView.vue` 接收 `created` 后调用已有的 `refreshFinancialData()`，重新读取当前所选月份的汇总、交易与分类名称。视图月份保持不变：如果录入日期不在该月份，保存仍然成功，但需要切换到对应月份才能看到；跨年查看仍未实现。

10. 表单读取选项、创建账户或分类、提交交易，以及父组件刷新期间，用禁用的 `fieldset` 统一锁定操作；提交和快捷创建函数也检查忙碌状态，避免重复请求或创建分类时切换收支类型。账户、分类创建是独立写入，之后取消或保存交易失败不会撤销它们。

11. 主界面沿用原项目的两栏布局，左侧放交易表单，右侧放记录列表；窄屏改为上下排列。`TransactionList.vue` 继续只负责展示、筛选和月份事件，不负责保存请求。

12. 本步骤所需的账户查询与新增、分类查询与新增、交易新增接口均已在当前后端定义，未修改后端。联调时先用空账号创建账户和分类，再保存收入、支出，验证列表与汇总刷新；另外检查重复分类、非法金额、失败重试、连续点击和跨月份录入。类型检查与模拟响应检查不能替代真实数据库和 Cookie 联调。

本步骤完成“准备账户和分类 → 填写交易 → 保存 → 刷新展示”的前端流程。交易编辑、删除、账户和分类的完整管理。

### 16. 接入交易编辑与删除

上一阶段已经能新增交易并刷新列表，但记错金额或日期后，还不能直接在页面上修正。这一步把编辑和删除接到已有列表上，复用交易表单，不再单独写一套编辑页面。

1. 先对照后端确认接口：修改记录使用 `POST /api/transactions/{transaction_id}`，提交完整交易字段；删除使用 `DELETE /api/transactions/{transaction_id}`，成功返回 204。这里沿用项目已经定义的方法，没有擅自改成 PUT，也没有修改后端和 `client.ts`。

2. 在 `TransactionList.vue` 的每条记录后添加“编辑”和“删除”按钮，用 `edit-request`、`delete-request` 把选中的交易传给父组件。列表只负责发出事件，当前编辑对象、删除请求和刷新逻辑仍集中在 `DashboardView.vue`。

3. 用 `editingTransaction` 保存当前编辑对象，进入编辑时复制这条记录，避免表单操作直接改动列表数据。切换前先确认，因为进入编辑会清空新增表单中尚未保存的内容。

4. 给 `TransactionForm.vue` 增加 `editingTransaction` prop，沿用原项目的 `isEditing`、`updated` 和 `cancelEdit` 思路。与原项目通过 watch 回填不同，这一步我用交易编号作为组件 `key`，新增模式使用 `'new'`：切换模式会重新创建表单，挂载时再回填收支类型、金额、备注和日期，避免上一条记录的临时状态留到下一条。

5. 读取账户和分类后，优先选中原记录的编号。如果原账户或分类已不可用，就保持未选择，让我重新确认，而不是自动替换成第一个选项。切换收支类型时仍重新查询分类，避免把收入记录挂到支出分类下。

6. 让同一个 `handleSubmit()` 根据是否存在编辑编号选择新增或更新地址。更新失败时保留填写内容；成功时发出 `updated`，父组件退出编辑模式并刷新当前月份的列表和汇总。列表不会在服务器确认前提前显示修改结果。

7. 增加“取消编辑”按钮，只清除前端编辑状态并回到新的新增表单，不调用更新接口，也不保留这次未提交的修改。请求进行中暂时不能取消，以免旧请求完成后影响新的表单。

8. 把备注输入上限调整为后端允许的 250 字符。之前新增表单沿用原项目的 30 字符限制，但已有记录可能由接口写入更长备注；编辑时需要能完整保留这些内容。

9. 删除前使用确认框提示操作不可撤销，取消确认不发送请求。确认后通过 `deletingTransactionId` 标记目标行，显示“删除中…”；只有服务器返回成功才刷新数据，失败时显示错误并保留原列表，便于检查和重试。

10. 通过表单的 `busyChange` 事件把选项加载、快捷创建和保存状态交给父组件，请求期间禁用记录操作及月份切换。编辑模式下也暂时禁止切月和操作其他记录，需要先更新或取消，避免编辑对象与当前列表脱节。

11. 保留前一步的汇总和列表请求版本判断，防止较早发出的查询覆盖新结果。如果我把日期改到其他月份，更新后该记录会从当前月列表消失，这是查询范围变化，不代表记录丢失；查看其他年份仍需后续补跨年功能。

12. 继续让受保护接口的 401 走已有的登录失效流程。其他删除错误显示在主界面，更新错误显示在表单内；写入成功和后续查询成功是两件事，所以刷新失败时仍可能同时看到“记录已更新”和汇总或列表的读取错误，我不能据此重复提交同一笔写入。

13. 这一步的代码检查包括 TypeScript、ESLint、内存构建和模拟接口验证。我把模拟检查与真实联调分开记录：还需要在连接 MySQL 的页面中验证修改金额、收支类型和日期，取消编辑，删除确认与取消，以及接口失败后重试；不能仅凭模拟响应就写成数据库联调已经完成。

到这里，把新增、查询、编辑、删除的前端入口接齐了，也进一步区分了“子组件发事件”“父组件管理状态”和“后端真正保存数据”的职责。账户和分类的完整管理、跨年查看暂时不放进这一步，实际运行结果仍以真实接口验证为准。

### 17. 创建 PostgreSQL 数据库并切换后端数据库连接

这一步把后端使用的数据库从 MySQL 切换到 PostgreSQL，从空库重新开始，不迁移原来的账号和记账数据。先建立与现有后端匹配的表，再修改连接配置和驱动，最后通过真实数据库验证接口。前面 MySQL 相关章节保留为学习过程记录。

1. 在 PostgreSQL 中创建目标数据库，准备有相应权限的连接账号，连接到目标库后执行 `database/schema_pg.sql`，建立 `users`、`accounts`、`categories`、`transactions` 四张表。脚本只负责建表和索引，不创建数据库或账号，也不会自动更新已经存在的表。

2. 对照 `backend/model.py` 统一字段类型：主键和外键使用 `INT`，自增主键使用 `GENERATED ALWAYS AS IDENTITY`；邮箱、密码哈希、昵称、账户名、分类名和备注的长度与 ORM 模型一致。

3. 保持原有金额规则：收入、支出都存正数，通过 `money_type` 区分，金额使用 `NUMERIC(9, 2)` 并添加 `CHECK (money > 0)`。最初的 PG 脚本把支出限制成负数，与请求模型的 `gt=0` 和汇总中的“收入减支出”冲突，因此修正脚本，不改变后端的计算规则。

4. `transaction_date` 使用 `DATE NOT NULL`，对应请求模型的 `date` 和 ORM 的 `Date`；`created_at` 使用 `TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()`，对应当前不带时区的 `DateTime`。这是按现有后端选择的类型，不代表所有 PostgreSQL 项目都应该去掉时区。

5. 保留邮箱唯一、同一用户分类名唯一，以及收支类型只能为“收入”或“支出”的约束；去掉最初 PG 脚本额外添加的昵称唯一、同一用户账户名唯一限制。外键删除规则沿用原 MySQL 表的 `RESTRICT`，已有流水引用的账户和分类不能直接删除。

6. 根据当前查询建立索引：`accounts(user_id)` 用于按用户查账户；`transactions(user_id, transaction_date)` 对应用户流水查询和日期排序；`transactions(account_id)`、`transactions(category_id)` 对应关联检查。索引是否带来性能收益仍需看执行计划，当前月份查询使用 `EXTRACT()`，后续可以改成起止日期范围查询再验证。

7. 在 `backend/requirements.txt` 中加入 `asyncpg`，并在运行后端的虚拟环境中安装依赖。依赖清单暂时保留 `aiomysql` 和已有的其他依赖，实际使用哪个数据库驱动由连接 URL 决定，不会因为两个驱动都安装就同时连接两个数据库。

8. 修改 `backend/database.py`：把 `drivername` 从 `mysql+aiomysql` 改为 `postgresql+asyncpg`，端口从 `3306` 改为 `5432`，移除原来的 `query={"charset": "utf8"}`。继续使用 `URL.create()`、`create_async_engine()` 和 `async_sessionmaker()`，保留连接池、会话依赖以及提交失败后的回滚处理。

9. 在本地 `backend/.env` 中把 `DATABASE_USERNAME`、`DATABASE_PASSWORD`、`DATABASE_HOST`、`DATABASE_NAME` 换成 PG 的连接配置。`main.py` 在导入路由前加载该文件，修改后需要重启后端；端口目前仍写在 `database.py` 中，不会自动读取 `.env` 中新增的端口变量。`.env` 由 Git 忽略，不随代码提交。

10. 现有注册登录、账户、分类和流水接口继续使用 SQLAlchemy 查询，本步骤没有重写路由或 ORM 模型。SQLAlchemy 会按数据库方言生成 SQL，但不能由此推断任意 MySQL 原生语句、事务行为或锁行为都能原样迁移；字段和业务规则仍要逐项核对。

11. 使用当前配置连接真实 PG，核对实际表结构并执行四张表的 ORM 查询；通过进程内接口请求验证注册登录、账户和分类操作、流水增删改查、月度汇总及跨月修改。例如收入 100、支出 30 时结余为 70，把支出改为 40 后结余为 60；把支出移到下月后，本月和下月的汇总分别变化。

12. 同时检查失败路径：重复分类返回 409，非法金额或收支类型不匹配返回 422，删除已有流水的账户或分类返回 409，跨用户读写受到限制。接口测试共用一个最终回滚的外层事务，测试记录未保留，自增编号可能出现正常跳号。此次验证覆盖真实 PG 读写，但不包含持久化提交、浏览器联调、部署环境、并发和性能测试；`/api/health` 本身没有查询数据库，不能单凭它成功就判断 PG 已连通。

到这里，当前本地配置下的后端已经通过 PostgreSQL 核心接口验证。后续还需要在页面上完成实际联调，并把数据库切换、业务规则调整和性能优化分别验证。

### 18. 拆分记账写操作的路由层与服务层

之前账户、分类和交易的路由函数同时负责接收请求、校验资源归属、执行业务规则和提交数据库。这一步先把记账的新增、修改、删除逻辑移到服务层，让路由负责 HTTP 接口，让服务函数负责具体业务。查询、月度汇总和用户认证暂时保留原结构，并不是整个后端都已经完成分层。

1. 新建 `backend/services/` 包，在 `ledger.py` 中定义账户、分类、交易各自的创建、更新和删除服务，共九个写操作。`__init__.py` 用于标识包，`errors.py` 集中定义业务异常。

2. `routers/items.py` 继续声明接口路径、请求模型、状态码和依赖，通过 `Depends(get_session)` 获取会话，通过 `Depends(get_current_user)` 获取当前用户，再把 `db`、请求数据、资源编号和 `user_id` 传给对应服务。服务不直接读取 Cookie，也不自己创建数据库会话。

3. 以新增流水为例，调用过程变成“路由接收并校验请求 → `create_transaction_service()` 校验账户和分类 → 构造 ORM 对象 → 提交 → 路由返回结果”。修改仍使用原来的 POST 接口，删除流水仍返回 204，账户和分类删除成功的消息也保持原样。

4. 把 `owned_resource()` 和 `validate_references()` 一并移入服务层。校验继续按“资源编号 + 当前用户编号”查询，保留 `with_for_update()` 行锁；账户和分类必须属于当前用户，分类的收支类型必须与流水一致。分层没有取消原来的归属检查。

5. 在 `services/errors.py` 中定义 `ResourceNotFoundError`、`MoneyTypeMismatchError` 和 `BusinessConflictError`。服务层抛出业务异常，不再直接抛 FastAPI 的 `HTTPException`，也不在这里决定 HTTP 状态码。

6. 在 `main.py` 注册异常处理器，分别把资源不存在、收支类型不匹配、业务冲突转换为 404、422、409，响应体保持 `{"detail": "错误说明"}`。这样服务表达业务失败原因，HTTP 入口负责将它转换成客户端能识别的响应。

7. 写服务负责提交，并在事务失败时显式回滚、重新抛出异常。删除和更新查不到资源时仍然报错，不把失败包装成成功。需要区分提交前失败和提交后读取失败：已经成功 `commit()` 的数据，不能靠之后的 `rollback()` 撤销；当前部分创建流程会在提交后调用 `refresh()`。

8. 分类重名、删除已有流水的账户或分类，不再把所有 `IntegrityError` 都当作同一种业务冲突。通过 `is_constraint_violation()` 同时匹配 PG 的 SQLSTATE 和约束名称：`23505` 对应指定的分类唯一约束，`23503` 对应指定的流水外键；符合条件才转换为业务异常，其他完整性错误继续向外抛出。

9. 约束名与 `database/schema_pg.sql` 实际生成的名称对应，包括 `categories_user_id_name_categories_key`、`transactions_category_id_fkey` 和 `transactions_account_id_fkey`。以后如果通过迁移改了约束名，也需要同步调整这里的判断，不能只修改数据库。

10. 当前异常识别通过 SQLAlchemy 的 `IntegrityError.driver_exception` 取得底层驱动异常，该接口要求 SQLAlchemy 2.1，因此把依赖最低版本标为 `SQLAlchemy>=2.1`。本次分层没有新增独立的数据访问层，服务仍直接使用 SQLAlchemy 操作 ORM 模型，也仍使用现有的 Pydantic 请求模型作为参数。

这一步完成记账写操作的“路由 → 服务 → 数据库”调用划分，以及“业务异常 → HTTP 响应”的统一转换。读取逻辑和认证逻辑的进一步拆分、后台任务和数据库迁移工具不计入本次分层完成范围。

### 19. 拆分月度流水查询与收支汇总服务

第 18 步先拆出了记账写操作，这一步继续把按月份查询流水和计算月度汇总的逻辑移到 `backend/services/reports.py`。接口路径和返回字段保持原样，让路由负责请求参数与身份信息，让报表服务负责构造查询和整理结果。

1. 新建 `services/reports.py`，提供 `get_transactions_by_month_service()` 和 `get_summary_service()`。两个函数接收已有的数据库会话和当前用户编号，不依赖 FastAPI 的 `Depends`，也不自行读取登录 Cookie。

2. `GET /api/transactions/{year}/{month}` 继续在路由层用 `Path` 限制年份和月份范围，再把 `db`、`user_id`、`year`、`month` 传给查询服务。服务按用户和年月筛选流水，继续按 `transaction_date`、`id` 倒序排列，返回 ORM 记录列表。

3. `GET /api/summary` 继续使用可选的 `year`、`month` 查询参数。路由负责范围校验，并要求两个参数同时提供或同时省略；只提供一个时返回 422 和“年份和月份必须一起提供”，通过校验后才调用汇总服务。

4. 汇总服务也检查年份和月份是否成对出现，不完整时抛出 `ValueError`，防止以后绕过路由直接调用服务时静默使用错误的月份。当前 HTTP 请求由路由提前拦截这种情况，服务不负责将它转换成 HTTP 响应；直接调用服务的其他调用方仍需要传入有效范围的年月。

5. 两个参数都省略时，继续通过数据库的 `now()` 和 `EXTRACT()` 获取当前年月；都提供时使用指定年月。这里保留原有行为，没有改成使用浏览器或 Python 进程的当前时间。

6. 分别查询当前用户当月收入、支出的 `SUM(money)`，没有记录时用零兜底，返回 `money_in`、`money_out`、`money_sum`。收入、支出仍存正数，结余仍按收入减支出计算，可以为负数。两条汇总查询都保留 `user_id` 条件。

7. 这两个服务只读取数据，不调用 `commit()`，也不负责开启新的独立会话。会话仍由路由依赖提供，函数中使用 `await db.execute()` 完成异步查询；新增、修改、删除继续使用第 18 步的 `ledger.py`。

8. 本次主要调整代码职责，没有更换查询算法。按年月筛选仍使用 `EXTRACT()`，汇总仍执行两条查询，没有加入分页或性能优化。全部流水、账户列表、分类列表以及用户认证仍留在原路由中，不能把这一步描述成整个后端都已完成服务层拆分。

到这里，记账写操作集中在 `ledger.py`，月度查询和汇总集中在 `reports.py`，路由通过传入当前用户和请求参数调用对应服务。后续增加报表调用方时，可以复用这些函数，并继续明确参数校验和会话管理由谁负责。

### 20. 拆分普通列表查询与注册登录服务

前两步已拆出记账写操作和月度查询，这一步继续把全部流水、账户列表、分类列表，以及注册登录中的业务逻辑移到服务层。同时提取共用的数据库约束识别函数，清理数据库模块中已经没有调用方的旧提交工具。

1. 在 `services/ledger.py` 新增 `get_transactions_service()`、`get_accounts_service()` 和 `get_categories_service()`。三个函数接收数据库会话和当前用户编号，分类查询额外接收 `money_type`，保留原来的用户过滤和分类类型过滤，返回 ORM 记录列表。

2. `routers/items.py` 中对应的三个 GET 接口改为调用服务，移除不再使用的 `select` 和记账 ORM 模型导入。接口路径、参数和返回方式没有改变，也没有顺便添加分页、排序或分类类型的新限制。

3. 新建 `services/users.py`，提供 `register_user_service()` 和 `login_user_service()`。用户路由继续负责接收 Pydantic 请求模型和注入会话，服务负责查询用户、验证注册条件和检查密码，不负责设置浏览器 Cookie。

4. 注册服务先对邮箱执行 `strip().lower()`，查询是否已注册；未注册时在线程池中执行密码哈希，再构造用户对象并提交。路由只返回用户编号、邮箱和昵称，不返回密码哈希。密码处理继续复用 `auth.py` 的辅助函数，没有更换密码算法。

5. 注册不能只依赖“先查询、再插入”的检查：两个请求可能都查到邮箱尚不存在，因此仍由数据库唯一约束兜底。提交发生完整性错误时先回滚，只把 SQLSTATE 为 `23505` 且约束名为 `users_email_key` 的错误转换为“该邮箱已注册”；其他完整性错误继续向外抛出，避免误报原因。

6. 登录服务同样规范化邮箱，查询用户并在线程池中验证密码。用户不存在或密码错误都抛出 `AuthenticationError("邮箱或密码错误")`，成功则返回用户对象。登录路由继续负责签发 JWT、设置 `access_token` Cookie，并返回原来的登录成功消息和用户信息。

7. 在 `services/errors.py` 新增 `AuthenticationError`，在 `main.py` 注册对应处理器，将它转换成 HTTP 401 和 `{"detail": "错误说明"}`。注册中的业务冲突复用已有的 `BusinessConflictError`，仍由统一处理器转换成 409。

8. 把 `is_constraint_violation()` 从 `ledger.py` 移到 `services/db_errors.py`，供记账服务和用户服务共同调用。判断方式继续使用 `IntegrityError.driver_exception`，同时匹配底层 PG 错误的 SQLSTATE 和约束名称，沿用 SQLAlchemy 2.1 的最低版本要求。

9. 删除 `database.py` 中已经没有调用方的 `commit_session()`，同时移除该模块对 `IntegrityError` 和 FastAPI `HTTPException` 的导入。数据库模块保留连接、会话工厂和会话依赖；注册和记账写入的提交、失败回滚及具体业务错误转换由对应服务承担。

10. 退出登录仍由路由删除 Cookie，`/api/auth/me` 仍通过 `get_current_user` 获取登录用户。`auth.py` 中的令牌校验、鉴权依赖和用户查询保留原实现，用户服务也仍复用其中的密码函数，因此本次没有把整个认证模块拆成完全独立的业务组件。

到这里，普通记账查询和写入由 `ledger.py` 承担，月度查询由 `reports.py` 承担，注册登录业务由 `users.py` 承担，共用数据库错误判断放在 `db_errors.py`。路由继续管理请求参数、依赖和 HTTP 响应，Cookie 与 JWT 的签发入口保持在用户路由中。

### 21. 为接口补充响应模型

之前请求参数已经使用 Pydantic 模型校验，但不少接口直接返回 ORM 对象或字典，没有明确声明对外返回哪些字段。这一步在 `backend/schemas.py` 中新增出参模型，通过路由的 `response_model` 统一校验、筛选和序列化成功响应，并让接口文档展示返回结构。

1. 新增 `OrmOut` 基类，通过 `ConfigDict(from_attributes=True)` 允许响应模型读取 ORM 对象的属性。`TransactionOut`、`AccountOut`、`CategoryOut` 和 `UserOut` 继承这个配置，服务仍可返回 ORM 对象，不需要为每个接口手动转换成字典。

2. 请求模型和响应模型分开：`TransactionCreate` 等请求模型继续描述客户端要提交的数据；`TransactionOut` 等响应模型描述服务器允许返回的数据，包含数据库生成的编号和相应时间字段。响应模型不会替代数据库约束，也不会自动修改表结构。

3. 为交易、账户、分类的列表接口声明 `list[对应出参模型]`，为新增和修改接口声明单个出参模型。返回字段按模型筛选，例如记账对象不再对外返回 `user_id`；服务内部的用户归属校验仍然保留，隐藏字段不能替代权限检查。

4. `TransactionOut` 保留账户编号、分类编号、金额、收支类型、备注、交易日期和创建时间。备注允许为 `None`，对应 JSON 的 `null`；交易日期按日期形式输出，创建时间按日期时间形式输出。

5. 用户注册和 `/api/auth/me` 使用 `UserOut`，只包含编号、邮箱和可为空的昵称，不包含密码哈希。登录使用 `LoginOut`，由 `message` 和嵌套的 `UserOut` 组成；登录 Cookie 仍由路由设置，没有因为增加响应模型而改动登录流程。

6. 新增 `SummaryOut`，明确汇总返回 `money_in`、`money_out`、`money_sum` 三个字段。交易金额和汇总金额使用 `Decimal`，当前 JSON 序列化会把它们输出为字符串，例如 `"12.30"`；这是接口数据类型的变化，不能只当成给文档添加说明。

7. 同步把 `frontend/src/types/index.ts` 中汇总的三个金额字段改为 `number | string`，与已有流水金额类型一致。当前页面格式化金额时已使用 `Number(value)`，因此本次只调整类型声明。`Decimal` 字符串保留服务端金额表达，前端转换成数字用于显示不代表适合用浮点数承担精确记账计算。

8. 健康检查、退出登录、删除账户和分类使用 `MessageOut`，统一声明成功响应中的 `message` 字段。删除流水继续返回 HTTP 204 和空响应体，没有给它附加消息模型。

9. 响应模型也会检查服务返回的数据。缺少必填字段或字段类型不符合要求时，属于服务器响应校验失败，不能把它误认为客户端请求校验的 422。既有业务异常仍由异常处理器转换为对应状态码和 `detail`，本次没有把错误响应改成 `MessageOut`。

10. 自动生成的 OpenAPI 文档会包含出参模型、嵌套结构和金额字符串类型，便于调用方确认接口约定。本次没有改变服务层查询、数据库字段、接口路径和提交方式；主要变化是成功响应的字段边界与序列化规则。

到这里，请求模型约束“传进来什么”，响应模型约束“返回去什么”。以后调整服务返回值时，需要同时检查响应模型和前端类型，避免后端能返回数据但调用方仍按旧结构处理。

### 22. 添加分层测试并修正接口行为

这一步新增 pytest 测试套件，分别检查请求模型、数据库异常识别、业务服务和 HTTP 接口。同时把三个更新接口统一改为 PUT，限制分类查询的收支类型，并修复删除被流水引用的账户或分类时，部分外键错误没有转换为 409 的问题。

1. 新增 `backend/requirements-dev.txt`，通过 `-r requirements.txt` 复用运行依赖，再添加 `pytest`、`pytest-asyncio` 和 `httpx2`。当前环境的 Starlette TestClient 使用 `httpx2`。`pytest.ini` 指定测试目录、模块搜索路径以及异步测试模式，测试依赖与正式运行依赖分开维护。

2. `test_schemas.py` 检查金额范围、小数位数、资源编号、名称长度、空白处理和注册参数；`test_db_errors.py` 用模拟驱动异常检查 SQLSTATE 与约束名必须同时匹配。这两组是纯单元测试，不需要连接数据库，也不触发建表或清表。

3. `test_users.py` 和 `test_ledger.py` 使用真实 PostgreSQL 测试库，覆盖注册、邮箱归一化、密码哈希、登录、流水归属校验、收支类型匹配、分类重名和删除引用冲突。更新成功后使用独立数据库会话读取数据，验证另一个事务能看到修改，避免同一会话中的 ORM 缓存或自动刷新掩盖漏掉 `commit()` 的问题。

4. `test_api.py` 使用 FastAPI 的 TestClient，覆盖登录 Cookie、未登录 401、重复资源 409、非法参数 422、越权访问 404、删除流水 204 空响应体，以及响应字段和金额字符串。这是进程内 HTTP 与真实数据库的集成测试，不代表已经完成浏览器端或部署环境的端到端测试。

5. `conftest.py` 只在测试显式依赖 `db` 或 `client` 时初始化数据库。数据库测试必须设置 `TEST_DATABASE_NAME`，名称以 `_test` 结尾，不能与原来的 `DATABASE_NAME` 相同，实际连接目标也必须匹配。测试会删除并重建四张业务表，每个数据库测试前清空数据并重置编号，因此必须使用专用、允许清空的测试库；库名检查不能代替数据隔离。

6. 测试使用 `NullPool`，避免把连接跨不同事件循环复用；HTTP 测试替换会话依赖，结束后恢复原来的依赖覆盖。测试进程还设置独立签名密钥和适用于 TestClient 的 Cookie 配置，不修改 `.env`。当前清库方式适用于串行执行，不能让多个测试进程共享同一个测试库并行运行。

7. 更新流水、账户和分类的接口由 `POST /api/资源/{id}` 改成 `PUT /api/资源/{id}`，新增资源仍然使用 POST。接口测试覆盖三个更新入口的 PUT 成功及旧 POST 返回 405，调用方需要同步请求方法。当前工作区的流水编辑已使用 PUT，但包含它的前端编辑功能尚未纳入本次提交。

8. 分类查询参数改为 `Literal["收入", "支出"]`，HTTP 层对其他值返回 422。服务函数同步补充类型标注，但 Python 类型标注本身不会在直接调用服务时执行参数校验，不能把它当成第二层运行时验证。

9. 删除引用冲突同时识别 `23001` 和 `23503`，仍要求约束名是对应的流水账户或分类外键。当前 PostgreSQL 18 中，RESTRICT 删除引用冲突使用 `23001`，NO ACTION 使用 `23503`；只检查后者可能漏掉现有建表脚本中的 RESTRICT 情况。两种状态码及不匹配的约束名都有单元测试，真实数据库测试验证被引用资源删除返回 409。相关行为可对照 [PostgreSQL 18 外键触发器实现](https://raw.githubusercontent.com/postgres/postgres/REL_18_STABLE/src/backend/utils/adt/ri_triggers.c)。这也修正了第 18 节只列出 `23503` 的处理范围。

10. 本次在新建的随机命名 PostgreSQL 18.6 临时库上运行完整测试，结果为 **70 项通过**，随后删除该临时库；单独运行纯单元测试为 **37 项通过**。前端类型检查也通过。这些结果对应本次环境与用例，不代表已经验证并发竞争、生产部署或所有业务边界。

在 `backend` 目录安装测试依赖并运行纯单元测试：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests/test_schemas.py tests/test_db_errors.py -q
```

运行全部测试前，先在 PostgreSQL 中创建一个允许清空的专用数据库，再设置它的名字。下面的命令不会替你创建数据库；连接账号、密码和主机沿用后端配置：

```powershell
$env:TEST_DATABASE_NAME = "tallywise_test"
.\.venv\Scripts\python.exe -m pytest -q
```

到这里，修改后端逻辑后可以先用模型和异常识别测试快速检查，再通过独立测试库检查服务行为与接口约定。测试记录与运行结果分开描述，新增功能时继续补充能发现实际回归的用例。
