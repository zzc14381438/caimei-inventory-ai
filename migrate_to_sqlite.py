"""
数据迁移脚本：product_catalog.json → inventory.db (SQLite)
=================================================
运行一次即可，生成 inventory.db 供后续读写使用。

运行：python migrate_to_sqlite.py
"""

import json
import os
import sqlite3

# ========== 配置 ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "product_catalog.json")
DB_PATH = os.path.join(BASE_DIR, "inventory.db")

# ========== 建表 ==========
CREATE_SQL = [
    """CREATE TABLE IF NOT EXISTS products (
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
    )""",
    """CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        sku TEXT NOT NULL,
        color TEXT NOT NULL,
        size TEXT NOT NULL,
        stock INTEGER DEFAULT 0,
        FOREIGN KEY (product_id) REFERENCES products(id),
        UNIQUE(sku, color, size)
    )""",
    """CREATE TABLE IF NOT EXISTS sales (
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
    )""",
    """CREATE INDEX IF NOT EXISTS idx_stock_sku ON stock(sku)""",
    """CREATE INDEX IF NOT EXISTS idx_sales_sku ON sales(sku)""",
    """CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(sale_date)""",
]


def migrate():
    # 读取 JSON
    print(f"📂 读取: {JSON_PATH}")
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    products = data.get("products", [])
    print(f"   共 {len(products)} 款商品")

    # 连接数据库（不存在会自动创建）
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()

    # 建表
    print("📝 创建表结构...")
    for sql in CREATE_SQL:
        cursor.execute(sql)

    # 清空旧数据（如果重复跑）
    cursor.execute("DELETE FROM sales")
    cursor.execute("DELETE FROM stock")
    cursor.execute("DELETE FROM products")
    conn.commit()

    # 插入 products + stock
    print("🔄 迁移数据中...")
    sku_to_id = {}
    total_stock_rows = 0

    for p in products:
        sku = p["sku"]

        cursor.execute(
            """INSERT INTO products
               (sku, name, status, purchase_price, retail_price,
                supplier, category, style, season, fabric, is_special)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                sku,
                p["name"],
                p.get("status", "正常"),
                p.get("purchase_price", 0),
                p.get("retail_price", 0),
                p.get("supplier", ""),
                p.get("category", ""),
                p.get("style", ""),
                p.get("season", ""),
                p.get("fabric", ""),
                p.get("is_special", "否"),
            ),
        )
        product_id = cursor.lastrowid
        sku_to_id[sku] = product_id

        # 插入 stock 行
        for cs in p.get("color_size_stock", []):
            cursor.execute(
                """INSERT INTO stock (product_id, sku, color, size, stock)
                   VALUES (?, ?, ?, ?, ?)""",
                (product_id, sku, cs["color"], cs["size"], cs["stock"]),
            )
            total_stock_rows += 1

    conn.commit()

    # 验证
    cursor.execute("SELECT COUNT(*) FROM products")
    prod_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM stock")
    stock_count = cursor.fetchone()[0]

    print(f"✅ 迁移完成!")
    print(f"   products 表: {prod_count} 行")
    print(f"   stock 表:    {stock_count} 行")
    print(f"   数据库文件: {DB_PATH}")

    conn.close()


if __name__ == "__main__":
    migrate()
