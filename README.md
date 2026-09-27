#  Tallywise

个人记账学习项目，目前使用FastAPI，SQLALchemy,MySQL。
该项目因家人需求而创造，并会根据用户使用反馈进行迭代，也会根据本人技术栈的更新来迭代。


## 目录
- `database/schema.sql`:MySQL建表脚本
- `backend/`：后端源码、依赖清单



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

