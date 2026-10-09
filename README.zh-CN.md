# Wiki 知识库管理系统

基于 LLM-Wiki 理念的 Markdown 知识库管理系统，用于管理知识页面、目录、标签、页面关系、知识图谱与基础检索。

> 第一阶段只做 Wiki 知识管理，不开发 Agent 工作流。

## 技术方案

| 模块 | 技术 |
| --- | --- |
| 前端 | Next.js + React + TypeScript + App Router + Tailwind CSS |
| 前端工程 | Monorepo (pnpm workspace) |
| 后端 | Python + FastAPI + Uvicorn + Pydantic |
| 数据库 | 阶段 1 使用 SQLite，后续可迁移 PostgreSQL |
| 知识内容 | Markdown |
| 部署 | Docker Compose |

## 目录结构

```text
llm-wiki/
├── frontend/                 # 前端 Monorepo
│   ├── apps/wiki-web/        # Next.js 应用
│   ├── packages/ui/          # UI 组件库
│   ├── packages/types/       # 共享类型
│   ├── packages/config/      # 共享配置
│   ├── package.json
│   └── pnpm-workspace.yaml
├── backend/                  # 后端 FastAPI
│   ├── app/
│   │   ├── main.py
│   │   ├── api/v1/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   └── utils/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
└── dev-prompts/              # 开发阶段提示词
```

## 环境要求

- Node.js 22.x
- Python 3.11.x
- pnpm 9.x

## 启动方式

> 依赖导入（首次或 `requirements.txt` / `package.json` 变更后执行，见下方各小节）。

### 后端

```bash
cd backend

# 1) 创建并激活虚拟环境
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 2) 安装后端依赖（包含新增的 cryptography 等）
pip install -r requirements.txt

# 3) 复制配置并设置 API Key 加密密钥
cp .env.example .env   # Windows 用: copy .env.example .env
# 编辑 .env，设置 MODEL_API_KEY_SECRET=<随机长字符串>

# 4) 建库并执行数据库迁移（首次运行、或拉取新代码后均须执行）
#    若已有 wiki.db，需要确保迁移至最新版本，否则新增表（如 model_config、
#    document_task 等）会缺失导致启动失败。
alembic upgrade head

# 5) 启动后端
uvicorn app.main:app --reload --port 9001
```

- 健康检查：http://localhost:9001/health
- 接口文档：http://localhost:9001/docs

### 前端

```bash
cd frontend

# 1) 安装前端依赖
pnpm install

# 2) 复制前端配置
cp apps/wiki-web/.env.example apps/wiki-web/.env.local   # Windows 用: copy

# 3) 启动开发服务器 == pnpm --filter @wiki/web dev
pnpm dev
```

- 应用地址：http://localhost:3000
- 前端通过 `NEXT_PUBLIC_API_BASE_URL` 连接后端，默认 `http://localhost:8000`（若后端用 9001 端口，请在 `.env.local` 中设为 `http://localhost:9001`）。

## 配置

复制环境变量示例文件并按需修改：

```bash
cp backend/.env.example backend/.env
cp frontend/apps/wiki-web/.env.example frontend/apps/wiki-web/.env.local
```

关键配置项：

| 文件 | 配置项 | 说明 |
| --- | --- | --- |
| 后端 `.env` | `DATABASE_URL` | 数据库地址，默认 `sqlite:///./wiki.db` |
| 后端 `.env` | `MODEL_API_KEY_SECRET` | **模型 API Key 加密密钥**，生产环境必须设置为足够随机的长字符串；未设置时后端会从 `JWT_SECRET` 派生（仅便于开发/测试） |
| 前端 `.env.local` | `NEXT_PUBLIC_API_BASE_URL` | 后端 API 基础地址，默认 `http://localhost:8000` |

> 模型配置（API Base URL、API Key、模型名称、超时、启用/停用、默认配置）可在应用的「设置 → 模型配置」页面进行管理；API Key 加密后存储，接口与日志均不返回明文。

## 测试

### 后端

```bash
cd backend
python -m pytest
```

### 前端（类型检查与构建）

```bash
cd frontend
pnpm typecheck   # 各包 TypeScript 类型检查
pnpm build       # 应用生产构建 == pnpm --filter @wiki/web build
pnpm lint        # ESLint
```

## 阶段进度

- [x] 阶段 1：工程初始化
- [x] 阶段 2：工程规范
- [x] 阶段 3：数据库和模型
- [x] 阶段 4：知识库后端 CRUD
- [ ] 后续阶段（按 dev-prompts 顺序推进）
