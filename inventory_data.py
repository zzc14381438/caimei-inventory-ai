"""
彩美服装商品数据层 — SQLite 版本
=====================================
提供所有库存/商品查询函数，供 inventory_tools.py 调用。
写入操作（销售记录、库存调整）也在这里实现。

数据库文件：inventory.db
表结构：products / stock / sales
"""

import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "inventory.db")

# 内存缓存（加速读取，写入后清除）
_CACHE = None


# ========== 数据库自动初始化 ==========

def _init_db_if_needed():
    """首次启动时自动建表+从 product_catalog.json 导入（如果表不存在）"""
    # 先检查文件是否已经是有效的数据库
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("SELECT 1 FROM products LIMIT 1")
        conn.close()
        return  # 表已存在，跳过
    except sqlite3.OperationalError:
        pass  # 表不存在
    conn.close()

    # 需要初始化：从 product_catalog.json 导入
    import json
    json_path = os.path.join(BASE_DIR, "product_catalog.json")
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"product_catalog.json 不存在: {json_path}")

    print(f"[DB-INIT] 初始化数据库，从 {json_path} 加载...")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    products = data.get("products", [])
    print(f"[DB-INIT] 共 {len(products)} 款商品")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    c = conn.cursor()

    # 建表
    c.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            status TEXT DEFAULT '正常',
            purchase_price REAL DEFAULT 0,
            retail_price REAL DEFAULT 0,
            supplier TEXT DEFAULT '',
            category TEXT DEFAULT '',
            style TEXT DEFAULT '',
            season TEXT DEFAULT '',
            fabric TEXT DEFAULT '',
            is_special TEXT DEFAULT '否',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        );
        CREATE TABLE IF NOT EXISTS stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            sku TEXT NOT NULL,
            color TEXT NOT NULL,
            size TEXT NOT NULL,
            stock INTEGER DEFAULT 0,
            FOREIGN KEY (product_id) REFERENCES products(id),
            UNIQUE(sku, color, size)
        );
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            sku TEXT NOT NULL,
            color TEXT NOT NULL,
            size TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_amount REAL NOT NULL,
            sale_date TEXT DEFAULT (datetime('now', 'localtime')),
            note TEXT DEFAULT '',
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        CREATE INDEX IF NOT EXISTS idx_stock_sku ON stock(sku);
        CREATE INDEX IF NOT EXISTS idx_sales_sku ON sales(sku);
        CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(sale_date);
    """)

    # 插入数据
    total_stock = 0
    for p in products:
        sku = p["sku"]
        c.execute(
            """INSERT INTO products
               (sku, name, status, purchase_price, retail_price,
                supplier, category, style, season, fabric, is_special)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (sku, p["name"], p.get("status", "正常"),
             p.get("purchase_price", 0), p.get("retail_price", 0),
             p.get("supplier", ""), p.get("category", ""),
             p.get("style", ""), p.get("season", ""),
             p.get("fabric", ""), p.get("is_special", "否")),
        )
        pid = c.lastrowid
        for cs in p.get("color_size_stock", []):
            c.execute(
                "INSERT INTO stock (product_id, sku, color, size, stock) VALUES (?,?,?,?,?)",
                (pid, sku, cs["color"], cs["size"], cs["stock"]),
            )
            total_stock += 1

    conn.commit()
    conn.close()
    print(f"[DB-INIT] 完成: {len(products)} products, {total_stock} stock rows")


# ========== 数据库连接 ==========

def _get_conn():
    _init_db_if_needed()  # 确保表存在
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 让结果可以通过列名访问
    return conn


def _invalidate_cache():
    global _CACHE
    _CACHE = None


def _load_all():
    """从 DB 加载全部商品，组装成原有格式（list of dicts）并缓存"""
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    conn = _get_conn()
    rows = conn.execute("SELECT * FROM products ORDER BY id").fetchall()
    products = []
    for row in rows:
        sku = row["sku"]
        # 查询该 sku 的所有库存记录
        stock_rows = conn.execute(
            "SELECT color, size, stock FROM stock WHERE sku = ?", (sku,)
        ).fetchall()

        colors = sorted(set(r["color"] for r in stock_rows))
        sizes = sorted(set(r["size"] for r in stock_rows), key=_size_sort_key)
        color_size_stock = [
            {"color": r["color"], "size": r["size"], "stock": r["stock"]}
            for r in stock_rows
        ]
        total_excel_stock = sum(r["stock"] for r in stock_rows)

        products.append({
            "sku": sku,
            "name": row["name"],
            "status": row["status"],
            "purchase_price": row["purchase_price"],
            "retail_price": row["retail_price"],
            "supplier": row["supplier"],
            "category": row["category"],
            "style": row["style"],
            "season": row["season"],
            "fabric": row["fabric"],
            "is_special": row["is_special"],
            "colors": colors,
            "sizes": sizes,
            "color_size_stock": color_size_stock,
            "total_excel_stock": total_excel_stock,
        })
    conn.close()
    _CACHE = products
    return products


def _size_sort_key(size):
    """尺码排序：XS<S<M<L<XL<XXL..."""
    order = {"XS": 0, "S": 1, "M": 2, "L": 3, "XL": 4, "2XL": 5, "3XL": 6, "4XL": 7, "5XL": 8}
    # 提取数字部分
    for k, v in order.items():
        if k in size.upper():
            return v
    return 99


# ========== 读取函数（兼容旧接口） ==========

def get_all_products():
    return _load_all()


def get_product_by_sku(sku: str) -> dict | None:
    for p in _load_all():
        if p["sku"].upper() == sku.upper().strip():
            return p
    return None


def search_by_name(keyword: str) -> list[dict]:
    kw = keyword.strip().lower()
    return [
        p for p in _load_all()
        if kw in p["name"].lower() or kw in p.get("style", "").lower()
    ]


def search_by_supplier(supplier: str) -> list[dict]:
    sup = supplier.strip().lower()
    return [p for p in _load_all() if sup in p["supplier"].lower()]


def search_by_color(color: str) -> list[dict]:
    c = color.strip()
    return [p for p in _load_all() if c in p["colors"]]


def search_by_size(size: str) -> list[dict]:
    s = size.strip().upper()
    return [p for p in _load_all() if s in [x.upper() for x in p["sizes"]]]


def search_by_season(season: str) -> list[dict]:
    s = season.strip()
    return [p for p in _load_all() if s in p.get("season", "")]


def get_all_categories() -> list[str]:
    return sorted(set(p["name"] for p in _load_all()))


def get_all_suppliers() -> list[str]:
    return sorted(set(p["supplier"] for p in _load_all() if p["supplier"]))


def get_all_colors() -> list[str]:
    colors = set()
    for p in _load_all():
        for c in p["colors"]:
            colors.add(c)
    return sorted(colors)


def get_all_sizes() -> list[str]:
    sizes = set()
    for p in _load_all():
        for s in p["sizes"]:
            sizes.add(s)
    return sorted(sizes, key=_size_sort_key)


def get_stock_by_color_size(sku: str, color: str, size: str) -> int | None:
    conn = _get_conn()
    row = conn.execute(
        "SELECT stock FROM stock WHERE sku = ? AND color = ? AND size = ?",
        (sku, color, size),
    ).fetchone()
    conn.close()
    return row["stock"] if row else 0


def format_product_detail(product: dict) -> str:
    lines = []
    lines.append(f"【{product['sku']}】{product['name']}")
    lines.append(f"  供应商: {product['supplier']}")
    lines.append(f"  采购价: ¥{product['purchase_price']:.0f}  |  零售价: ¥{product['retail_price']:.0f}")
    if product.get("style"):
        lines.append(f"  风格: {product['style']}")
    if product.get("season"):
        lines.append(f"  季节: {product['season']}")
    if product.get("fabric"):
        lines.append(f"  面料: {product['fabric']}")
    if product.get("is_special") == "是":
        lines.append(f"  ⚠️ 特价商品")
    lines.append(f"  颜色: {', '.join(product['colors'])}")
    lines.append(f"  尺码: {', '.join(product['sizes'])}")
    lines.append(f"  库存明细:")
    for cs in product["color_size_stock"]:
        lines.append(f"    {cs['color']}/{cs['size']}: {cs['stock']}件")
    return "\n".join(lines)


def format_product_summary(product: dict) -> str:
    total_stock = sum(cs["stock"] for cs in product["color_size_stock"])
    return (
        f"【{product['sku']}】{product['name']} | "
        f"颜色: {', '.join(product['colors'])} | "
        f"尺码: {', '.join(product['sizes'])} | "
        f"总库存: {total_stock}件 | "
        f"零售价: ¥{product['retail_price']:.0f} | "
        f"供应商: {product['supplier']}"
    )


# ========== 写入函数（Step 2 新增） ==========

def record_sale(sku: str, color: str, size: str, quantity: int,
                unit_price: float, note: str = "") -> dict:
    """
    记录一笔销售，同时扣减库存。
    返回：{"success": True, "message": "...", "new_stock": N}
    """
    conn = _get_conn()
    try:
        conn.execute("BEGIN")

        # 1. 查 product_id
        prod = conn.execute(
            "SELECT id FROM products WHERE sku = ?", (sku,)
        ).fetchone()
        if not prod:
            return {"success": False, "message": f"未找到款号 {sku}"}
        product_id = prod["id"]

        # 2. 查当前库存
        stock_row = conn.execute(
            "SELECT id, stock FROM stock WHERE sku = ? AND color = ? AND size = ?",
            (sku, color, size),
        ).fetchone()
        if not stock_row:
            return {"success": False, "message": f"未找到 {sku} 的 {color}/{size} 库存记录"}
        current_stock = stock_row["stock"]
        if current_stock < quantity:
            return {
                "success": False,
                "message": f"库存不足！当前仅剩 {current_stock} 件，请求销售 {quantity} 件",
            }

        # 3. 扣减库存
        new_stock = current_stock - quantity
        conn.execute(
            "UPDATE stock SET stock = ? WHERE id = ?",
            (new_stock, stock_row["id"]),
        )

        # 4. 写入销售记录
        total_amount = quantity * unit_price
        conn.execute(
            """INSERT INTO sales (product_id, sku, color, size, quantity, unit_price, total_amount, note)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (product_id, sku, color, size, quantity, unit_price, total_amount, note),
        )

        conn.commit()
        _invalidate_cache()  # 清除缓存，下次重新加载
        return {
            "success": True,
            "message": f"✅ 销售记录成功：{sku} {color}/{size} 售出 {quantity} 件，收款 ¥{total_amount:.0f}",
            "new_stock": new_stock,
            "total_amount": total_amount,
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"销售记录失败：{str(e)}"}
    finally:
        conn.close()


def update_stock(sku: str, color: str, size: str, delta: int) -> dict:
    """
    调整库存（delta 为正=增加，为负=减少，不直接设置绝对值）。
    返回：{"success": bool, "message": "...", "new_stock": N}
    """
    conn = _get_conn()
    try:
        conn.execute("BEGIN")

        stock_row = conn.execute(
            "SELECT id, stock FROM stock WHERE sku = ? AND color = ? AND size = ?",
            (sku, color, size),
        ).fetchone()
        if not stock_row:
            return {"success": False, "message": f"未找到 {sku} 的 {color}/{size} 库存记录"}

        new_stock = stock_row["stock"] + delta
        if new_stock < 0:
            return {
                "success": False,
                "message": f"调整后库存为负数（{new_stock}），拒绝操作。当前库存：{stock_row['stock']}",
            }

        conn.execute(
            "UPDATE stock SET stock = ? WHERE id = ?",
            (new_stock, stock_row["id"]),
        )
        conn.commit()
        _invalidate_cache()
        op = "增加" if delta > 0 else "减少"
        return {
            "success": True,
            "message": f"✅ 库存调整成功：{sku} {color}/{size} {op} {abs(delta)} 件，新库存：{new_stock} 件",
            "new_stock": new_stock,
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"库存调整失败：{str(e)}"}
    finally:
        conn.close()


def get_sales_history(sku: str = "", limit: int = 20) -> list[dict]:
    """查询销售记录，可按 sku 过滤"""
    conn = _get_conn()
    if sku:
        rows = conn.execute(
            """SELECT * FROM sales WHERE sku = ?
               ORDER BY sale_date DESC LIMIT ?""",
            (sku, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM sales ORDER BY sale_date DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_low_stock_products(threshold: int = 10) -> list[dict]:
    """找出低库存商品（任一颜色/尺码低于阈值）"""
    conn = _get_conn()
    rows = conn.execute(
        """SELECT s.sku, s.color, s.size, s.stock, p.name, p.retail_price
           FROM stock s
           JOIN products p ON s.sku = p.sku
           WHERE s.stock < ?
           ORDER BY s.stock ASC
           LIMIT 50""",
        (threshold,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
