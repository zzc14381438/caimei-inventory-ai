# 彩美智能库存助手

> 一个基于 LangChain Agent + RAG + SQLite 的服装批发店智能库存管理系统  
> **AI 应用开发实战作品** — 完整实现从数据管理到智能对话的全链路

---

## 功能演示

### 🫎 智能对话（自然语言查库存）
- "红色连衣裙还有哪些？" → 自动调用库存查询工具
- "娟娟供了什么新款？" → 按供应商筛选
- "分析一下连衣裙的库存情况" → 生成带表格的分析报告

### 📊 销售记录（Agent 自动写入）
- "开单：26A09 红色 XL 卖出 1 件，成交价 159" → 自动记录销售并扣减库存
- "今天到货了，26A09 红色 XL 加了 10 件" → 自动调整库存

### 📈 补货建议（基于规则 + AI 分析）
- "哪些货不够了？" → 自动列出低库存商品，给出补货建议

---

## 技术栈

| 模块 | 技术 | 说明 |
|------|------|------|
| **LLM** | DeepSeek-chat (via OpenAI SDK) | 中文场景性价比最高 |
| **Agent 框架** | LangChain + LangGraph | ReAct 模式，自动决策调用工具 |
| **向量检索** | FAISS + sentence-transformers | 384维多语言语义检索 |
| **数据库** | SQLite | 轻量级，适合演示和作品集 |
| **后端** | Flask | 提供 REST API |
| **前端** | 原生 HTML/JS | 聊天界面，支持快捷按钮 |

---

## 项目结构

```
ai-app-dev/
├── caimei_api.py          # Flask 后端（Agent 初始化 + API 路由）
├── inventory_data.py       # 数据层（SQLite 读写）
├── inventory_tools.py      # Agent 工具定义（14个工具）
├── migrate_to_sqlite.py   # 数据迁移脚本（JSON → SQLite）
├── task5_rag_demo.py     # RAG 演示脚本
├── task6_agent_demo.py   # Agent 演示脚本
├── task7_prompt_engineering.py  # 提示词工程演示
├── static/
│   └── index.html        # 前端聊天界面
├── inventory.db           # SQLite 数据库（自动生成）
├── product_catalog.json   # 原始商品数据（201款）
├── faiss_index.bin        # FAISS 向量索引
├── rag_documents.json     # RAG 文档库
└── requirements.txt       # Python 依赖
```

---

## 快速开始

### 1. 克隆项目
```bash
git clone <your-repo-url>
cd ai-app-dev
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置 API Key
创建 `.env` 文件：
```
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

### 4. 初始化数据库
```bash
python migrate_to_sqlite.py
```

### 5. 启动应用
```bash
python caimei_api.py
```

访问：http://localhost:5000

---

## API 接口

### POST `/api/chat`
**请求：**
```json
{
  "message": "红色连衣裙还有哪些？"
}
```

**响应：**
```json
{
  "reply": "找到 3 款红色连衣裙：...",
  "tools_used": ["search_products", "query_by_color"],
  "timestamp": "2026-06-07T23:30:00"
}
```

### GET `/api/health`
健康检查，返回系统状态。

---

## Agent 工具清单（14个）

### 查询工具（8个）
| 工具名 | 功能 |
|--------|------|
| `query_by_sku` | 按款号精确查询 |
| `search_products` | 按名称/风格模糊搜索 |
| `query_by_supplier` | 按供应商查询 |
| `query_by_color` | 按颜色查询 |
| `query_by_size` | 按尺码查询 |
| `query_by_color_and_size` | 按颜色+尺码交叉查询 |
| `list_categories` | 列出所有商品类型 |
| `list_suppliers` | 列出所有供应商 |

### 知识库工具（2个）
| 工具名 | 功能 |
|--------|------|
| `search_knowledge_base` | RAG 语义搜索 |
| `analyze_sales_trend` | 品类销售趋势分析 |

### 写入工具（4个）
| 工具名 | 功能 |
|--------|------|
| `record_sale` | 记录销售并扣减库存 |
| `adjust_stock` | 调整库存（进货/报损） |
| `get_sales_history` | 查询销售记录 |
| `check_low_stock` | 检查低库存商品 |

---

## 核心设计亮点

### 1. ReAct Agent 模式
```
用户提问 → LLM 思考 → 选择工具 → 执行工具 → LLM 再思考 → 最终回答
```

### 2. 多工具串联
用户问："红色连衣裙还有哪些？"  
Agent 自动调用：
1. `search_products("连衣裙")` → 找到连衣裙商品
2. `query_by_color("红色")` → 筛选红色
3. 整合结果，生成回答

### 3. RAG 知识库
将商品文档向量化存储，用户问 "有什么风格的衣服？" 时，语义检索最相关的文档片段，再让 LLM 基于文档回答。

---

## 未来改进方向

- [ ] 对接真实批发系统 API（商陆花/笑铺）
- [ ] 用户登录 + 权限管理（店长/店员）
- [ ] 销售数据统计图表（ECharts）
- [ ] 多店铺支持
- [ ] 微信小程序前端
- [ ] 部署到云端（Hugging Face Spaces / Render）

---

## 作者

**你的名字**  
AI 应用开发学习者 | 服装批发行业数字化探索者  
📧 contact@example.com

---

## 许可证

MIT License
