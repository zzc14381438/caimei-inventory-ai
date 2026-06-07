"""
Task 7：提示词工程基础
=======================
演示三种核心 Prompt 技巧：
  1. Few-shot Prompting — 给示例，AI 照格式输出
  2. Chain-of-Thought   — 让 AI 一步步推理
  3. 彩美业务模板       — 库存查询 / 销售分析 / 补货建议

运行：python task7_prompt_engineering.py
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)


def call_deepseek(system: str, user: str, temp: float = 0.3) -> str:
    """封装 DeepSeek 调用"""
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temp,
        max_tokens=600,
    )
    return resp.choices[0].message.content


# ============================================================
# PART 1: Few-shot Prompting
# ============================================================
def demo_few_shot():
    print("=" * 60)
    print("📚 PART 1: Few-shot Prompting（少样本提示）")
    print("=" * 60)
    print()
    print("核心概念：给 AI 看几个例子，它就能照葫芦画瓢，按同样格式输出。")
    print("这在「格式要求严格」的场景特别有用 —— 比如客服分类、数据提取。")
    print()

    # --- 对比实验 ---
    user_input = "有个顾客说26A09款红色的M码还有没有货，帮我查一下库存"

    # ❌ 普通 Prompt（不给示例）
    print("A) 普通 Prompt（不给示例）")
    print("-" * 40)
    result_a = call_deepseek(
        system="你是一个服装店助手。",
        user=f"根据以下用户需求，输出一个标准化的查询指令：\n{user_input}",
    )
    print(f"  AI 输出:\n    {result_a}")
    print()

    # ✅ Few-shot Prompt（给3个示例）
    print("B) Few-shot Prompt（给3个示例 × 同样的输入）")
    print("-" * 40)
    system_b = """你是一个服装店助手。将用户的自然语言需求转化为标准化查询指令。

【输出格式要求】
- 只输出一行 JSON，不要多余文字
- JSON 格式：{"intent": "意图类型", "params": {"字段": "值"}}

【示例】
用户：帮我看看短袖还有哪些
输出：{"intent": "search_product", "params": {"keyword": "短袖"}}

用户：娟娟最近供了什么新款
输出：{"intent": "query_supplier", "params": {"supplier": "娟娟"}}

用户：红色连衣裙M码库存多少
输出：{"intent": "query_color_size", "params": {"color": "红色", "size": "M", "keyword": "连衣裙"}}"""

    result_b = call_deepseek(system=system_b, user=user_input)
    print(f"  AI 输出:\n    {result_b}")
    print()
    print("  👆 看到区别了吗？不加示例 → AI 随心所欲。加示例 → 格式完全统一。")
    print()


# ============================================================
# PART 2: Chain-of-Thought (CoT)
# ============================================================
def demo_cot():
    print("=" * 60)
    print("🧠 PART 2: Chain-of-Thought（思维链）")
    print("=" * 60)
    print()
    print("核心概念：让 AI「一步一步想」，而不是直接蹦出答案。")
    print("复杂问题的准确率能提升 30%~50%。")
    print()

    question = "彩美店里上个月进了 200 件连衣裙，单价 ¥189。卖出 140 件后打了 8 折促销，又卖出 50 件。最后剩下的 10 件按成本价 ¥95 清仓。问：这批连衣裙的总利润是多少？"

    # ❌ 直接回答（不要求推理）
    print("A) 直接要求回答")
    print("-" * 40)
    result_a = call_deepseek(
        system="你是一个财务助手，直接回答用户的问题。",
        user=question,
    )
    print(f"  AI 输出:\n    {result_a[:200]}")
    print()

    # ✅ CoT 提示
    print("B) Chain-of-Thought（要求一步步推理）")
    print("-" * 40)
    result_b = call_deepseek(
        system="你是一个财务助手。请逐步推理，每一步写出计算过程，最后给出答案。",
        user=f"{question}\n\n请分步骤计算：\n步骤1：计算原价销售的收入\n步骤2：计算8折销售的收入\n步骤3：计算清仓销售收入\n步骤4：计算总收入\n步骤5：计算总成本\n步骤6：计算总利润",
    )
    print(f"  AI 输出:\n    {result_b}")
    print()
    print("  👆 CoT 的关键是「请你分步骤计算」这半句话 —— 相当于给 AI 打开慢思考模式。")
    print()


# ============================================================
# PART 3: 彩美业务提示词模板
# ============================================================
def demo_templates():
    print("=" * 60)
    print("🏪 PART 3: 彩美业务提示词模板（实战）")
    print("=" * 60)
    print()

    # --- 模板1：库存查询 ---
    print("📦 模板1：智能库存查询")
    print("-" * 40)
    print("""【Prompt 模板】
你是一个服装批发店（彩美南宁新和平店）的库存助手。
你的知识库包含 201 款商品，1849 条颜色×尺码的库存记录。

当用户询问库存时，你必须：
1. 理解用户问的是什么品类（短袖、连衣裙、牛仔裤等）
2. 理解颜色和尺码的筛选条件
3. 输出清晰的数量和可选项
4. 如果某个颜色/尺码缺货，主动推荐替代选择

【用户问题】
帮我查一下黑色宽松短袖L码还有多少库存？
""")
    result = call_deepseek(
        system="""你是一个服装批发店（彩美南宁新和平店）的库存助手。
你的知识库包含 201 款商品，1849 条颜色×尺码的库存记录。

当用户询问库存时，你必须：
1. 理解用户问的是什么品类
2. 理解颜色和尺码的筛选条件
3. 输出清晰的数量和可选项
4. 如果某个颜色/尺码缺货，主动推荐替代选择""",
        user="帮我查一下黑色宽松短袖L码还有多少库存？",
    )
    print(f"  AI 输出:\n    {result[:300]}")
    print()

    # --- 模板2：销售分析 ---
    print("📊 模板2：销售趋势分析")
    print("-" * 40)
    print("""【Prompt 模板】
你是彩美服装店的销售分析师。根据以下销售数据，给出专业的分析建议。

要求：
1. 找出表现最好和最差的 3 款商品
2. 分析可能的原因（季节、颜色、尺码、价格）
3. 给出下周补货或促销建议
4. 用表格呈现关键数据

【本周销售数据】
- 26A09 国风短袖（红色）: 卖出 45 件，库存剩余 12 件，进价 ¥85，售价 ¥168
- 26A11 宽松T恤（黑色）: 卖出 82 件，库存剩余 8 件，进价 ¥55，售价 ¥118
- 26B03 吊带连衣裙（白色）: 卖出 5 件，库存剩余 67 件，进价 ¥120，售价 ¥238
- 26B08 牛仔短裤（蓝色）: 卖出 31 件，库存剩余 22 件，进价 ¥65，售价 ¥128
- 26C02 针织开衫（米色）: 卖出 3 件，库存剩余 45 件，进价 ¥98，售价 ¥198
""")
    result = call_deepseek(
        system="你是彩美服装店的销售分析师。给出专业分析。用表格呈现数据。",
        user="""分析以下本周销售数据，找出表现最好/最差的商品并给出建议：

- 26A09 国风短袖（红色）: 卖出 45，库存 12，进价 ¥85，售价 ¥168
- 26A11 宽松T恤（黑色）: 卖出 82，库存 8，进价 ¥55，售价 ¥118
- 26B03 吊带连衣裙（白色）: 卖出 5，库存 67，进价 ¥120，售价 ¥238
- 26B08 牛仔短裤（蓝色）: 卖出 31，库存 22，进价 ¥65，售价 ¥128
- 26C02 针织开衫（米色）: 卖出 3，库存 45，进价 ¥98，售价 ¥198""",
    )
    print(f"  AI 输出:\n    {result}")
    print()

    # --- 模板3：补货建议 ---
    print("🔄 模板3：智能补货建议")
    print("-" * 40)
    print("""【Prompt 模板】
你是彩美服装店的采购顾问。根据当前库存和销售速度，给出补货建议。

分析规则：
- 库存 < 15 件 → "紧急补货"
- 库存 15~30 件 → "关注库存，下周补货"
- 库存 > 30 件 → "库存充足"

【当前库存】
- 26B08 牛仔短裤: 蓝色S码5件/M码12件/L码8件，售价 ¥128，上周卖了 22 件
- 26C02 针织开衫: 米色均码 45 件，售价 ¥198，上周卖了 3 件
""")
    result = call_deepseek(
        system="""你是彩美服装店的采购顾问。

分析规则：
- 库存 < 15 件 → "紧急补货"
- 库存 15~30 件 → "关注库存，下周补货"
- 库存 > 30 件 → "库存充足"

请给出每条建议时说明理由，用表格总结。""",
        user="""分析以下商品是否需要补货：
- 26B08 牛仔短裤: 蓝色S码5件/M码12件/L码8件，售价 ¥128，上周卖了 22 件
- 26C02 针织开衫: 米色均码 45 件，售价 ¥198，上周卖了 3 件""",
    )
    print(f"  AI 输出:\n    {result}")
    print()

    print("✅ 三个业务模板演示完毕。")
    print("   这些模板可以直接嵌入到 Agent 的 system_prompt 里，让 AI 助手效果翻倍。")


# ============================================================
# 主入口
# ============================================================
if __name__ == "__main__":
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("❌ 请在 .env 文件中设置 DEEPSEEK_API_KEY")
        exit(1)

    print()
    print("╔══════════════════════════════════════════════════╗")
    print("║        Task 7：提示词工程三大核心技巧           ║")
    print("╚══════════════════════════════════════════════════╝")
    print()

    demo_few_shot()
    demo_cot()
    demo_templates()

    print()
    print("=" * 60)
    print("🎓 总结：提示词工程的三个层次")
    print("=" * 60)
    print("""
  Level 1 · 基础问答
      "帮我查库存" → AI 随便答
      
  Level 2 · Few-shot     
      给 3 个示例 → AI 按格式输出 → 格式统一
      
  Level 3 · CoT + 模板化
      分步推理 + 规则约束 → AI 像老员工一样工作

  把这三层技巧用到彩美 Agent 里，就是从「能用」到「好用」的关键一跃。
    """)
