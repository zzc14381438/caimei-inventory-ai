"""
彩美智能库存助手 — Flask 后端 API
=================================
提供 REST API 给前端调用，整合 Agent + RAG + 库存工具

运行：python caimei_api.py
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

# ============ 全局初始化 ============
agent = None
rag_ready = False
rag_search_fn = None
system_info = {}


def init_agent():
    """初始化 Agent、RAG、工具"""
    global agent, rag_ready, rag_search_fn, system_info

    from langgraph.prebuilt import create_react_agent
    from langchain_openai import ChatOpenAI
    from langchain_core.tools import tool

    # ----- RAG 引擎 -----
    try:
        import faiss
        from sentence_transformers import SentenceTransformer

        index_path = os.path.join(os.path.dirname(__file__), "faiss_index.bin")
        docs_path = os.path.join(os.path.dirname(__file__), "rag_documents.json")

        index = faiss.read_index(index_path)
        with open(docs_path, "r", encoding="utf-8") as f:
            documents = json.load(f)
        embed_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        rag_ready = True

        def rag_search(query: str, top_k: int = 5) -> str:
            import numpy as np
            query_vec = embed_model.encode([query], normalize_embeddings=True)
            distances, indices = index.search(query_vec.astype(np.float32), top_k)
            lines = [f"RAG 检索结果（共 {top_k} 条）："]
            for i, (idx, d) in enumerate(zip(indices[0], distances[0]), 1):
                if idx < len(documents):
                    doc = documents[idx]
                    content = doc.get("content", str(doc))[:200]
                    lines.append(f"  {i}. [{d:.3f}] {content}")
            return "\n".join(lines)

        rag_search_fn = rag_search
    except Exception as e:
        rag_ready = False
        print(f"[WARN] RAG 加载失败: {e}")

    # ----- 库存工具（复用）-----
    from inventory_tools import TOOLS as INVENTORY_TOOLS

    # ----- 自定义工具 -----
    @tool
    def search_knowledge_base(query: str) -> str:
        """在商品知识库中语义搜索。当用户问"有什么类型的衣服"、"有没有某种风格"时使用。"""
        if rag_ready and rag_search_fn:
            return rag_search_fn(query)
        return "⚠️ RAG 知识库未就绪"

    @tool
    def analyze_sales_trend(category: str = "") -> str:
        """分析某品类的库存状况。输入品类关键词如"连衣裙"、"短袖"。"""
        from inventory_data import search_by_name, get_all_products

        products = search_by_name(category) if category else get_all_products()
        if not products:
            return f"未找到品类「{category}」"
        if len(products) > 200:
            products = products[:200]

        total_stock = sum(sum(cs["stock"] for cs in p["color_size_stock"]) for p in products)
        total_sku = len(products)
        avg_price = sum(p["retail_price"] for p in products) / total_sku if total_sku else 0

        low_stock = []
        for p in products:
            stock = sum(cs["stock"] for cs in p["color_size_stock"])
            if stock < 10:
                low_stock.append((p["sku"], p["name"], stock, p["retail_price"]))

        lines = [f"品类「{category or '全部'}」分析："]
        lines.append(f"  款数：{total_sku} | 总库存：{total_stock}件 | 均价：¥{avg_price:.0f}")
        if low_stock:
            lines.append(f"  ⚠️ 低库存款（<10件）：{len(low_stock)}款")
            for sku, name, s, price in low_stock[:5]:
                lines.append(f"    {sku} {name} 库存{s}件 ¥{price:.0f}")
        return "\n".join(lines)

    all_tools = INVENTORY_TOOLS + [search_knowledge_base, analyze_sales_trend]

    system_prompt = """你是彩美服装批发店（南宁新和平店）的智能库存助手。

【店铺信息】
- 店名：彩美 | 位置：南宁新和平商场
- 主营：女装批发零售
- 库存：约200款，1800+条颜色×尺码记录，约20家供应商

【能力范围】
1. 查库存 — 按款号/名称/颜色/尺码/供应商查询
2. 记录销售 — 开单成交时记录销售并自动扣减库存
3. 调整库存 — 到货进货（增加）或报损退货（减少）
4. 销售查询 — 查看历史销售记录
5. 低库存提醒 — 自动检查哪些商品需要补货
6. 知识库搜索 — 了解商品种类、风格特色
7. 销售分析 — 分析品类库存，给出补货建议

【行为规则】
- 查完后用清晰列表或表格回复
- 缺货时推荐替代选择
- 用户说"开单"、"成交"、"卖出"时：
   → 先确认款号、颜色、尺码、数量、成交价
   → 然后调用 record_sale 工具记录
- 用户说"到货"、"进了一批货"时：
   → 确认款号、颜色、尺码、到货数量
   → 调用 adjust_stock 增加库存（delta 为正数）
- 用户说"有退货"、"衣服破了"时：
   → 调用 adjust_stock 减少库存（delta 为负数）
- 用户问"今天卖了什么"、"销售记录"时：
   → 调用 get_sales_history 查看
- 用户问"需要补货吗"、"哪些不够了"时：
   → 调用 check_low_stock 检查
- 不在能力范围内则诚实告知"""

    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com",
        temperature=0.3,
    )

    agent = create_react_agent(llm, all_tools)

    system_info = {
        "tool_count": len(all_tools),
        "rag_enabled": rag_ready,
        "product_count": 201,
        "sku_count": 1849,
    }

    print(f"[INIT] Agent 就绪 | {len(all_tools)} 工具 | RAG: {rag_ready}")
    return agent, system_info


# ============ API 路由 ============

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """聊天接口：接收用户消息，返回 Agent 回复"""
    data = request.get_json()
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400

    try:
        config = {"configurable": {"thread_id": "caimei-session"}}
        final_message = ""
        tool_calls_seen = []

        for event in agent.stream(
            {"messages": [{"role": "user", "content": user_message}]},
            config,
            stream_mode="values",
        ):
            if "messages" not in event:
                continue
            last_msg = event["messages"][-1]

            if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                for tc in last_msg.tool_calls:
                    tool_name = tc.get("name", "unknown")
                    if tool_name not in tool_calls_seen:
                        tool_calls_seen.append(tool_name)

            if hasattr(last_msg, "content") and last_msg.content:
                if not hasattr(last_msg, "tool_calls") or not last_msg.tool_calls:
                    final_message = last_msg.content

        return jsonify({
            "reply": final_message or "抱歉，未能生成回复，请重试。",
            "tools_used": tool_calls_seen,
            "timestamp": datetime.now().isoformat(),
        })

    except Exception as e:
        return jsonify({
            "reply": f"❌ 处理出错：{str(e)}",
            "error": str(e),
        }), 500


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify(system_info)


# ============ 启动 ============
if __name__ == "__main__":
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("❌ 请在 .env 中设置 DEEPSEEK_API_KEY")
        sys.exit(1)

    print("=" * 50)
    print("  彩美智能库存助手 API")
    print("=" * 50)

    try:
        agent, info = init_agent()
        print(f"  ✅ {info['tool_count']} 个工具已加载")
        print(f"  {'✅' if info['rag_enabled'] else '⚠️'} RAG {'已' if info['rag_enabled'] else '未'}加载")
        print(f"\n  🌐 访问: http://localhost:5000")
        print("=" * 50)
        app.run(host="0.0.0.0", port=5000, debug=False)
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
