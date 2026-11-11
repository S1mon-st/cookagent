# 灶边 AI · 私厨管家

基于 FastAPI、LangChain、React/Vite 和阿里云百炼 `qwen3.7-plus` 的多模态食谱推荐应用。上传冰箱或厨房食材照片，确认识别结果后，系统会结合人数、口味、过敏原、用时和难度生成可执行菜谱，并支持上下文追问。

## 功能

- `qwen3.7-plus` 原生视觉识别食材
- 可编辑的结构化食材清单
- Tavily 菜谱资料检索与真实来源展示
- 食材覆盖、偏好、营养、难度和来源的可解释排序
- 过敏原绝对过滤，普通忌口独立处理
- 菜谱步骤、缺少食材、营养搭配与上下文问答
- Tavily 不可用时自动降级为 AI 生成建议

## 目录

```text
backend/   FastAPI + LangChain Python
frontend/  React + TypeScript + Vite
docs/      需求设计和实施计划
```

## 环境要求

- Python 3.11+
- Node.js 20+
- npm 10+

## 配置

项目根目录的 `.env` 保存真实配置，应用启动时由 `python-dotenv` 的 `load_dotenv()` 加载。不要把 `.env` 提交到版本控制。

```dotenv
DASHSCOPE_API_KEY=你的百炼APIKey
MODEL_BASE_URL=https://你的业务空间.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
MODEL_NAME=qwen3.7-plus
TAVILY_API_KEY=你的TavilyKey
CORS_ORIGINS=http://localhost:5173
```

## 启动后端

```powershell
cd D:\cookagent\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m uvicorn app.main:app --reload --port 8000
```

访问 API 文档：<http://localhost:8000/docs>

## 启动前端

另开一个终端：

```powershell
cd D:\cookagent\frontend
npm install
npm run dev
```

访问：<http://localhost:5173>

## 验证

```powershell
cd D:\cookagent\backend
python -m pytest

cd D:\cookagent\frontend
npm test
npm run build
```

## 安全说明

- API Key 只在后端读取，绝不会打包到前端。
- 图片只在请求期间处理，首版不持久化。
- Tavily 来源仅在模型实际引用时展示。
- 过敏和营养提示不能替代食品标签核验或专业医疗意见。

