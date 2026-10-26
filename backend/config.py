import os
from urllib.parse import quote_plus


def _default_database_uri():
    """用环境变量拼出连接串，仓库中不保存口令。

    若未设置任何 DB_* 变量，则回退到本地 SQLite（零配置即可跑起来）：
        sqlite:///<backend>/instance/family_finance.db
    """
    name = os.environ.get('DB_NAME')
    if not name:
        base = os.path.dirname(os.path.abspath(__file__))
        return 'sqlite:///' + os.path.join(base, 'instance', 'family_finance.db')

    user = quote_plus(os.environ.get('DB_USER', 'root'))
    password = quote_plus(os.environ.get('DB_PASSWORD', ''))
    host = os.environ.get('DB_HOST', 'localhost')
    port = os.environ.get('DB_PORT', '3306')
    return (
        f'mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4'
    )


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'family-finance-dev-only-change-me')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or _default_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_SAMESITE = 'Lax'
    # 部署到 HTTPS 后应设为 True
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', '0') == '1'
    SESSION_COOKIE_HTTPONLY = True
