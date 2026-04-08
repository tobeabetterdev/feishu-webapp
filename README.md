# 工厂订单数据核对系统

一个基于 FastAPI 和 React 的工厂订单数据核对系统，支持恒逸和新凤鸣两大集团的数据对比功能。

## 功能特性

- **多集团支持**: 支持恒逸和新凤鸣两大工厂集团的数据对比
- **Excel 解析**: 智能解析工厂侧和久鼎侧的 Excel 文档格式
- **智能对比**: 自动对比订单数据，识别差异并生成报告
- **实时进度**: 上传文件后实时显示处理进度
- **结果下载**: 生成 Excel 格式的对比结果报告，支持下载
- **响应式设计**: 支持桌面端和移动端访问
- **Docker 部署**: 提供完整的 Docker 化部署方案

## 技术栈

### 前端
- **框架**: React 18 + TypeScript
- **构建工具**: Vite
- **样式**: Tailwind CSS
- **图标**: Lucide React
- **路由**: React Router v6

### 后端
- **框架**: FastAPI (Python)
- **数据处理**: Pandas, OpenPyXL
- **Web 服务器**: Uvicorn
- **API 文档**: Swagger UI (自动生成)

## 项目结构

```
feishu-webapp/
├── frontend/                    # 前端代码 (根目录)
│   ├── src/
│   │   ├── components/         # 可复用组件
│   │   ├── pages/              # 页面组件
│   │   ├── services/           # API 服务
│   │   ├── types/              # TypeScript 类型定义
│   │   ├── App.tsx            # 主应用组件
│   │   └── main.tsx           # 入口文件
│   ├── Dockerfile             # 前端 Docker 配置
│   ├── nginx.conf             # Nginx 配置
│   └── vite.config.ts         # Vite 配置
├── backend/                    # 后端代码
│   ├── api/                   # API 路由
│   │   ├── compare.py        # 对比 API
│   │   └── __init__.py
│   ├── services/             # 业务逻辑
│   │   ├── excel_parser.py   # Excel 解析
│   │   ├── data_comparator.py # 数据对比
│   │   └── __init__.py
│   ├── config/               # 配置文件
│   ├── tests/                # 测试文件
│   ├── outputs/              # 输出文件目录
│   ├── Dockerfile            # 后端 Docker 配置
│   ├── main.py               # FastAPI 应用入口
│   └── requirements.txt      # Python 依赖
├── docs/                     # 文档目录
│   └── SETUP.md             # 安装部署指南
├── docker-compose.yml        # Docker Compose 配置
├── README.md                # 项目说明 (本文件)
├── .dockerignore           # Docker 忽略文件
└── package.json            # Node.js 依赖
```

## 快速开始

### 方式一：使用 Docker Compose（推荐）

1. 克隆仓库：
```bash
git clone <repository-url>
cd feishu-webapp
```

2. 启动服务：
```bash
docker-compose up -d
```

3. 访问应用：
- 前端: http://localhost
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

### 方式二：本地开发

#### 前端开发

1. 安装依赖：
```bash
npm install
```

2. 启动开发服务器：
```bash
npm run dev
```

3. 访问: http://localhost:5173

#### 后端开发

1. 进入后端目录：
```bash
cd backend
```

2. 创建虚拟环境：
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. 安装依赖：
```bash
pip install -r requirements.txt
```

4. 启动服务器：
```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

5. 访问 API 文档: http://localhost:8000/docs

## 使用指南

### 工厂集团配置

系统支持两大工厂集团：

#### 恒逸集团
- 浙江恒逸高新材料有限公司
- 浙江双兔新材料有限公司
- 海宁恒逸新材料有限公司

#### 新凤鸣集团
- 桐乡市中鸿新材料有限公司
- 湖州市中磊化纤有限公司
- 湖州市中跃化纤有限公司
- 桐乡市中益化纤有限公司
- 新凤鸣集团湖州中石科技有限公司
- 桐乡中欣化纤有限公司
- 桐乡市中维化纤有限公司
- 新凤鸣集团股份有限公司
- 浙江独山能源有限公司
- 新凤鸣江苏新拓新材有限公司

### 订单数据核对流程

1. **选择集团**: 在工作台中选择要对比的工厂集团（恒逸或新凤鸣）
2. **上传文件**: 
   - 上传工厂侧 Excel 文件
   - 上传久鼎侧 Excel 文件
3. **开始核对**: 点击"开始核对"按钮启动对比流程
4. **查看进度**: 实时查看文件解析和数据对比进度
5. **获取结果**: 对比完成后查看结果表格
6. **下载报告**: 点击"下载 Excel"按钮获取完整对比报告

### API 接口

系统提供以下 REST API：

- `POST /api/compare` - 创建对比任务
- `GET /api/compare/{task_id}/status` - 获取任务状态
- `GET /api/compare/{task_id}/result` - 获取对比结果
- `GET /api/compare/{task_id}/download` - 下载结果文件
- `GET /api/factory-groups` - 获取工厂集团配置

详细的 API 文档可以在 Swagger UI 中查看: http://localhost:8000/docs

## 开发指南

### 前端开发

#### 添加新组件
```typescript
// src/components/YourComponent.tsx
export default function YourComponent() {
  return <div>Your Component</div>
}
```

#### 添加新页面
```typescript
// src/pages/YourPage.tsx
export default function YourPage() {
  return <div>Your Page</div>
}
```

#### API 调用
```typescript
import { createComparison, getTaskStatus, getTaskResult, getDownloadUrl } from '../services/api'
```

### 后端开发

#### 添加新 API 端点
```python
# backend/api/your_api.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/your-endpoint")
async def your_endpoint():
    return {"message": "Hello"}
```

在 `backend/main.py` 中注册路由：
```python
from api.your_api import router as your_router
app.include_router(your_router, prefix="/api")
```

#### 数据处理
```python
# backend/services/your_service.py
import pandas as pd

def process_data(data):
    df = pd.DataFrame(data)
    # 处理逻辑
    return df
```

## 部署指南

详细的部署指南请参考 [docs/SETUP.md](docs/SETUP.md)

## 性能优化

- 前端使用 Vite 进行快速构建和热更新
- 后端使用异步 FastAPI 框架提升并发性能
- 数据处理使用 Pandas 进行高效数据分析
- Nginx 配置 Gzip 压缩和静态资源缓存

## 测试

### 前端测试
```bash
npm run test
```

### 后端测试
```bash
cd backend
pytest
```

## 常见问题

### 1. 文件上传失败
- 确保文件格式为 Excel (.xlsx 或 .xls)
- 检查文件大小是否在限制范围内
- 确认网络连接正常

### 2. 对比结果不正确
- 检查上传的文件格式是否符合要求
- 确认选择的工厂集团是否正确
- 查看 API 日志获取详细错误信息

### 3. Docker 启动失败
- 检查 Docker 服务是否正常运行
- 确认端口 80 和 8000 未被占用
- 查看容器日志：`docker-compose logs`

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支: `git checkout -b feature/your-feature`
3. 提交更改: `git commit -m 'Add some feature'`
4. 推送到分支: `git push origin feature/your-feature`
5. 提交 Pull Request

## 许可证

MIT License

## 联系方式

如有问题或建议，请联系项目维护者。

## 更新日志

### v1.0.0 (2025-04-08)
- 初始版本发布
- 支持恒逸和新凤鸣集团数据对比
- 实现文件上传和实时进度显示
- 添加 Excel 结果下载功能
- 完成响应式设计和移动端优化
- 提供 Docker 部署方案