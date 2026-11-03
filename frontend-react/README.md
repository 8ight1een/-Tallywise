# Tallywise React 前端

这是产品前端的最小起点，使用 React、TypeScript 和 Vite。

## 启动

在 PowerShell 中执行：

```powershell
Set-Location 'D:\tallywisee\frontend-react'
npm.cmd run dev
```

打开终端显示的地址。当前首页显示“Tallywise / 前端工程已就绪”。
首次在其他机器安装依赖时先运行 `npm.cmd ci`。Node 使用 24 系列，依赖版本以锁文件为准。

## 当前目录

- `src/main.tsx`：React 挂载入口。
- `src/App.tsx`：最小首页，后续作为产品入口。
- `src/index.css`：基础全局样式。
- `public/`：暂为空，按业务需要加入静态资源。
- `index.html`：HTML 入口。
- `vite.config.ts`：保留 `/api` 到 `http://127.0.0.1:8000` 的开发代理。

当前未实现登录、路由、记账或报表。页面启动不要求后端运行，调用 `/api` 时需要后端和数据库可用。

## 检查与构建

```powershell
npm.cmd run lint
npm.cmd run build
```

build 包含 TypeScript 检查，随后生成 dist。`npm.cmd run preview` 用于本地查看构建产物，不用作正式服务器。

## 继续开发

实施文档：`D:\学习\工程能力\前端\Tallywise-React实战\00.项目实施入口.md`。
视觉参考：`D:\tallywisee\backend-ui-preview\login.html` 与 `index.html`。

2026-11-02 已将原练习、旧页面及相关资源移到同级 `frontend-react-practice-20261102`，正式工程不再导入它们。配置与依赖保持原样，不在初始化阶段提前安装业务库。
