"""
一次性数据迁移脚本：将 SQLite 数据迁移到 MySQL
用法：cd backend && python migrate_sqlite_to_mysql.py
"""
import sqlite3
import os
import sys

# SQLite 数据库路径
SQLITE_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'family_finance.db')

# MySQL 连接信息
MYSQL_URI = 'mysql+pymysql://root:1234@localhost:3306/family_finance?charset=utf8mb4'

def migrate():
    # 检查 SQLite 文件是否存在
    if not os.path.exists(SQLITE_PATH):
        print(f"未找到 SQLite 数据库文件: {SQLITE_PATH}")
        print("如果你是全新安装，直接启动后端即可，无需迁移。")
        sys.exit(0)

    # 从 SQLite 读取数据
    print("正在读取 SQLite 数据...")
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM users")
    users = [dict(row) for row in cur.fetchall()]

    cur.execute("SELECT * FROM finance_records")
    records = [dict(row) for row in cur.fetchall()]

    cur.execute("SELECT * FROM budgets")
    budgets = [dict(row) for row in cur.fetchall()]

    conn.close()

    print(f"  用户: {len(users)} 条")
    print(f"  财务记录: {len(records)} 条")
    print(f"  预算: {len(budgets)} 条")

    # 先用 PyMySQL 直接创建数据库（如果不存在）
    print("\n正在创建 MySQL 数据库（如果不存在）...")
    import pymysql
    conn_mysql = pymysql.connect(host='localhost', port=3306, user='root', password='1234', charset='utf8mb4')
    cur_mysql = conn_mysql.cursor()
    cur_mysql.execute("CREATE DATABASE IF NOT EXISTS family_finance CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    conn_mysql.commit()
    conn_mysql.close()
    print("  数据库 family_finance 已就绪。")

    # 连接 MySQL 并建表
    print("\n正在连接 MySQL 并创建表结构...")
    from flask import Flask
    from config import Config
    from models import db, User, FinanceRecord, Budget

    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    with app.app_context():
        db.create_all()
        print("表结构创建成功。")

        # 写入用户
        print("\n正在迁移用户数据...")
        for u in users:
            if not User.query.get(u['id']):
                user = User(
                    id=u['id'],
                    username=u['username'],
                    password_hash=u['password_hash'],
                    created_at=u.get('created_at'),
                )
                db.session.add(user)
        db.session.commit()
        print(f"  已写入 {len(users)} 个用户。")

        # 写入财务记录
        print("正在迁移财务记录...")
        for r in records:
            if not FinanceRecord.query.get(r['id']):
                record = FinanceRecord(
                    id=r['id'],
                    user_id=r['user_id'],
                    category=r['category'],
                    amount=r['amount'],
                    date=r['date'],
                    note=r.get('note', ''),
                    created_at=r.get('created_at'),
                )
                db.session.add(record)
        db.session.commit()
        print(f"  已写入 {len(records)} 条财务记录。")

        # 写入预算
        print("正在迁移预算数据...")
        for b in budgets:
            if not Budget.query.get(b['id']):
                budget = Budget(
                    id=b['id'],
                    user_id=b['user_id'],
                    category=b['category'],
                    monthly_limit=b['monthly_limit'],
                    created_at=b.get('created_at'),
                )
                db.session.add(budget)
        db.session.commit()
        print(f"  已写入 {len(budgets)} 条预算记录。")

    print("\n迁移完成！现在可以启动后端：python app.py")

if __name__ == '__main__':
    migrate()
