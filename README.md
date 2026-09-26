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