"""
库存查询工具 — 供AI Agent调用的LangChain Tool
基于真实商品档案（201款商品，1849个颜色×尺码条目）
"""
from langchain_core.tools import tool
from inventory_data import (
    get_product_by_sku,
    search_by_name,
    search_by_supplier,
    search_by_color,
    search_by_size,
    search_by_season,
    format_product_detail,
    format_product_summary,
    get_all_categories,
    get_all_suppliers,
    get_all_colors,
    get_all_sizes,
    get_stock_by_color_size,
)


@tool
def query_by_sku(sku: str) -> str:
    """
    按款号精确查询商品详情和库存。
    适用于用户明确说出款号时，如"查一下26A09"。
    """
    product = get_product_by_sku(sku)
    if not product:
        return f"❌ 未找到款号「{sku}」的商品，请检查款号是否正确。"
    return format_product_detail(product)


@tool
def search_products(keyword: str) -> str:
    """
    按商品名称或风格关键词搜索商品列表。
    适用于用户说品类名时，如"查一下短袖"、"国风系列有哪些"。
    返回匹配商品的摘要列表（不超过15条）。
    """
    results = search_by_name(keyword)
    if not results:
        return f"❌ 没有找到名称包含「{keyword}」的商品。\n可用的商品类型有：{', '.join(get_all_categories()[:30])}..."
    
    lines = [f"🔍 搜索「{keyword}」共找到 {len(results)} 款商品："]
    for i, p in enumerate(results[:15], 1):
        total_stock = sum(cs["stock"] for cs in p["color_size_stock"])
        lines.append(f"  {i}. 【{p['sku']}】{p['name']} | {', '.join(p['colors'])} | "
                     f"{', '.join(p['sizes'])} | 库存{total_stock}件 | ¥{p['retail_price']:.0f} | {p['supplier']}")
    if len(results) > 15:
        lines.append(f"  ...还有 {len(results) - 15} 款，可以缩小搜索范围或指定款号查看详情。")
    return "\n".join(lines)


@tool
def query_by_supplier(supplier_name: str) -> str:
    """
    按供应商名称查询其供应的所有商品。
    适用于用户问"娟娟供了什么货"时。
    """
    results = search_by_supplier(supplier_name)
    if not results:
        all_sups = get_all_suppliers()
        return f"❌ 没有找到供应商「{supplier_name}」。\n可选供应商：{', '.join(all_sups)}"
    
    lines = [f"🏭 供应商「{supplier_name}」共供应 {len(results)} 款商品："]
    for i, p in enumerate(results, 1):
        total_stock = sum(cs["stock"] for cs in p["color_size_stock"])
        lines.append(f"  {i}. 【{p['sku']}】{p['name']} | {', '.join(p['colors'])} | "
                     f"库存{total_stock}件 | ¥{p['retail_price']:.0f}")
    return "\n".join(lines)


@tool
def query_by_color(color: str) -> str:
    """
    按颜色查询包含该颜色的所有商品。
    适用于用户问"红色有哪些衣服"时。
    """
    results = search_by_color(color)
    if not results:
        all_colors = get_all_colors()
        return f"❌ 没有找到颜色「{color}」的商品。\n可选颜色：{', '.join(all_colors)}"
    
    lines = [f"🎨 颜色「{color}」共匹配 {len(results)} 款商品："]
    for i, p in enumerate(results[:15], 1):
        total_stock = sum(cs["stock"] for cs in p["color_size_stock"])
        lines.append(f"  {i}. 【{p['sku']}】{p['name']} | 尺码{', '.join(p['sizes'])} | "
                     f"库存{total_stock}件 | ¥{p['retail_price']:.0f} | {p['supplier']}")
    if len(results) > 15:
        lines.append(f"  ...还有 {len(results) - 15} 款，可用尺码或品类进一步筛选。")
    return "\n".join(lines)


@tool
def query_by_size(size: str) -> str:
    """
    按尺码查询包含该尺码的所有商品。
    适用于用户问"3XL有哪些衣服"时。
    """
    results = search_by_size(size)
    if not results:
        all_sizes = get_all_sizes()
        return f"❌ 没有找到尺码「{size}」的商品。\n可选尺码：{', '.join(all_sizes)}"
    
    lines = [f"📏 尺码「{size}」共匹配 {len(results)} 款商品："]
    for i, p in enumerate(results[:15], 1):
        total_stock = sum(cs["stock"] for cs in p["color_size_stock"])
        lines.append(f"  {i}. 【{p['sku']}】{p['name']} | {', '.join(p['colors'])} | "
                     f"库存{total_stock}件 | ¥{p['retail_price']:.0f} | {p['supplier']}")
    if len(results) > 15:
        lines.append(f"  ...还有 {len(results) - 15} 款，可用颜色或品类进一步筛选。")
    return "\n".join(lines)


@tool
def query_by_color_and_size(color: str, size: str) -> str:
    """
    同时按颜色和尺码查询商品（交叉筛选）。
    适用于用户同时指定颜色和尺码，如"红色XL码有哪些"。
    """
    color_results = search_by_color(color)
    size_results = search_by_size(size)
    # 取交集
    color_skus = {p["sku"] for p in color_results}
    results = [p for p in size_results if p["sku"] in color_skus]
    
    if not results:
        return (f"❌ 没有同时满足 颜色={color} 且 尺码={size} 的商品。\n"
                f"单独查{color}有{len(color_results)}款，{size}有{len(size_results)}款。")
    
    lines = [f"🎨📏 颜色「{color}」+ 尺码「{size}」共匹配 {len(results)} 款："]
    for i, p in enumerate(results, 1):
        # 找出该颜色+尺码的具体库存
        stock_for_combo = get_stock_by_color_size(p["sku"], color, size)
        lines.append(f"  {i}. 【{p['sku']}】{p['name']} | {color}/{size}库存{stock_for_combo}件 | "
                     f"¥{p['retail_price']:.0f} | {p['supplier']}")
    return "\n".join(lines)


@tool
def list_categories() -> str:
    """
    列出所有商品名称种类，用于帮助用户了解有哪些品类。
    当用户问"你们有什么类型的衣服"时调用。
    """
    from collections import Counter
    categories = Counter()
    from inventory_data import get_all_products
    for p in get_all_products():
        categories[p["name"]] += 1
    
    lines = [f"📋 彩美南宁新和平店共有 {len(categories)} 种商品类型："]
    for name, count in categories.most_common(30):
        lines.append(f"  · {name}（{count}款）")
    if len(categories) > 30:
        lines.append(f"  ...共{len(categories)}种，可用具体名称搜索更多。")
    return "\n".join(lines)


@tool
def list_suppliers() -> str:
    """
    列出所有供应商，帮助用户了解有哪些供应商。
    当用户问"有哪些供应商"时调用。
    """
    from collections import Counter
    sups = Counter()
    from inventory_data import get_all_products
    for p in get_all_products():
        sups[p["supplier"]] += 1
    
    lines = [f"🏭 共 {len(sups)} 家供应商："]
    for s, count in sups.most_common(20):
        lines.append(f"  · {s}（{count}款）")
    if len(sups) > 20:
        lines.append(f"  ...共{len(sups)}家，可用供应商名查询具体商品。")
    return "\n".join(lines)


# 导出所有工具供Agent使用
TOOLS = [
    query_by_sku,
    search_products,
    query_by_supplier,
    query_by_color,
    query_by_size,
    query_by_color_and_size,
    list_categories,
    list_suppliers,
]


# ========== 写入工具（Step 2 新增）==========

from inventory_data import (
    record_sale as _record_sale,
    update_stock as _update_stock,
    get_sales_history as _get_sales_history,
    get_low_stock_products as _get_low_stock,
)


@tool
def record_sale(sku: str, color: str, size: str,
                quantity: int, unit_price: float,
                note: str = "") -> str:
    """
    记录一笔销售并自动扣减库存。
    当用户说"卖出了一件"、"开单"、"成交"等场景时调用。
    参数说明：
    - sku: 款号，如 "26A09"
    - color: 颜色，如 "红色"
    - size: 尺码，如 "XL"
    - quantity: 销售数量，如 1
    - unit_price: 实际成交单价（可能低于零售价），如 159.0
    - note: 可选备注，如 "顾客议价后成交"
    """
    result = _record_sale(sku.strip(), color.strip(), size.strip(),
                          quantity, unit_price, note)
    if result["success"]:
        return result["message"]
    return f"❌ {result['message']}"


@tool
def adjust_stock(sku: str, color: str, size: str, delta: int) -> str:
    """
    调整某款商品的库存（进货填正数，报损/退货填负数）。
    当用户说"到货了"、"进了一批货"、"有退货"、"衣服破了"等场景时调用。
    注意：是增减量，不是设置绝对值。例如到货 10 件填 delta=10，退货 2 件填 delta=-2。
    """
    result = _update_stock(sku.strip(), color.strip(), size.strip(), delta)
    if result["success"]:
        return result["message"]
    return f"❌ {result['message']}"


@tool
def get_sales_history(sku: str = "", limit: int = 10) -> str:
    """
    查询销售记录。
    可指定款号查某款的销售历史，也可不指定查看最近所有销售。
    当用户问"今天卖了什么"、"这款卖了多少"时调用。
    """
    rows = _get_sales_history(sku.strip() if sku else "", limit)
    if not rows:
        return f"📊 没有找到{'款号 ' + sku + ' 的' if sku else ''}销售记录。"
    lines = [f"📊 销售记录（最近 {len(rows)} 条）："]
    for r in rows:
        lines.append(
            f"  · {r['sale_date'][:16]} | {r['sku']} {r['color']}/{r['size']} "
            f"×{r['quantity']}件 | ¥{r['total_amount']:.0f} | {r.get('note', '')}"
        )
    return "\n".join(lines)


@tool
def check_low_stock(threshold: int = 10) -> str:
    """
    检查库存低于阈值的商品，用于补货提醒。
    当用户问"哪些货不够了"、"需要补什么货"时调用。
    默认阈值 10 件，也可指定其他值。
    """
    rows = _get_low_stock(threshold)
    if not rows:
        return f"✅ 所有商品库存均 ≥ {threshold} 件，无需补货。"
    lines = [f"⚠️ 库存低于 {threshold} 件的商品（共 {len(rows)} 条）："]
    for r in rows[:20]:
        lines.append(
            f"  · {r['sku']} {r['name']} | {r['color']}/{r['size']} "
            f"仅剩 {r['stock']} 件 | 零售价 ¥{r['retail_price']:.0f}"
        )
    if len(rows) > 20:
        lines.append(f"  ...还有 {len(rows) - 20} 条，建议尽快补货！")
    return "\n".join(lines)


# 更新工具列表（加入写入工具）
TOOLS.extend([
    record_sale,
    adjust_stock,
    get_sales_history,
    check_low_stock,
])
