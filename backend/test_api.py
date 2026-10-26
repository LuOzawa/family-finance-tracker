"""
自动化测试用例
覆盖：登录、记录CRUD、数据筛选、分析接口、预算管理、健康评分、预测
运行：cd backend && pytest test_api.py -v

⚠️ 安全提醒：本文件会在 fixture 里执行 db.drop_all()。
为避免误删真实数据库，必须在 import app **之前** 把 DATABASE_URL
指向临时 SQLite 文件（下面 14-20 行就是这么做的），并在 fixture 里
加一道断言兵底。请勿删除这两处防护。
"""
import pytest
import json
import os
import sys
import tempfile
import pathlib
from sqlalchemy.pool import StaticPool

# ---- 必须在 import app 之前设置，否则 Config 已经用真实 MySQL 连接串初始化 ----
_TEST_DB = pathlib.Path(tempfile.gettempdir()) / 'family_finance_test.db'
os.environ['DATABASE_URL'] = 'sqlite:///' + _TEST_DB.as_posix()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app as flask_app
from models import db, User


@pytest.fixture(scope='function')
def client():
    flask_app.config['TESTING'] = True
    flask_app.config['SECRET_KEY'] = 'test-secret-key'

    # 兵底断言：绝不允许测试连到真实数据库
    uri = flask_app.config['SQLALCHEMY_DATABASE_URI']
    assert uri.startswith('sqlite'), (
        f'测试只能跑在 SQLite 上，当前 URI 为 {uri!r}。\n'
        '请检查 test_api.py 顶部的 DATABASE_URL 设置是否在 import app 之前生效。'
    )

    with flask_app.app_context():
        db.drop_all()
        db.create_all()
        admin = User(username='admin')
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()

    with flask_app.test_client() as c:
        yield c

    with flask_app.app_context():
        db.session.remove()
        db.drop_all()


def _login(client):
    return client.post('/login', json={'username': 'admin', 'password': 'admin'})


def _j(res):
    return json.loads(res.data)


# ===================== 基础接口 =====================

def test_health_endpoint(client):
    res = client.get('/health')
    assert res.status_code == 200
    assert _j(res)['status'] == 'ok'


# ===================== 登录模块 =====================

def test_login_success(client):
    res = _login(client)
    data = _j(res)
    assert res.status_code == 200
    assert data['success'] is True
    assert data['username'] == 'admin'


def test_login_wrong_password(client):
    res = client.post('/login', json={'username': 'admin', 'password': 'wrong'})
    assert res.status_code == 401
    assert _j(res)['success'] is False


def test_login_wrong_username(client):
    res = client.post('/login', json={'username': 'nobody', 'password': 'admin'})
    assert res.status_code == 401


def test_logout(client):
    _login(client)
    res = client.post('/logout')
    assert res.status_code == 200
    assert _j(res)['success'] is True


# ===================== 财务记录 CRUD =====================

def test_records_requires_auth(client):
    res = client.get('/records')
    assert res.status_code == 401


def test_record_create(client):
    _login(client)
    res = client.post('/records', json={
        'category': '餐饮', 'amount': 88.5, 'date': '2024-03-15', 'note': '午饭'
    })
    assert res.status_code == 201
    data = _j(res)
    assert data['category'] == '餐饮'
    assert data['amount'] == 88.5
    assert 'id' in data


def test_record_read_list(client):
    _login(client)
    client.post('/records', json={'category': '餐饮', 'amount': 100, 'date': '2024-01-01', 'note': ''})
    client.post('/records', json={'category': '交通', 'amount': 30, 'date': '2024-01-02', 'note': ''})
    res = client.get('/records')
    assert res.status_code == 200
    assert len(_j(res)) == 2


def test_record_filter_by_category(client):
    _login(client)
    client.post('/records', json={'category': '餐饮', 'amount': 100, 'date': '2024-01-01', 'note': ''})
    client.post('/records', json={'category': '交通', 'amount': 30, 'date': '2024-01-02', 'note': ''})
    res = client.get('/records?category=餐饮')
    records = _j(res)
    assert len(records) == 1
    assert records[0]['category'] == '餐饮'


def test_record_filter_by_date_range(client):
    _login(client)
    client.post('/records', json={'category': '餐饮', 'amount': 50, 'date': '2024-01-10', 'note': ''})
    client.post('/records', json={'category': '餐饮', 'amount': 80, 'date': '2024-02-10', 'note': ''})
    res = client.get('/records?date_from=2024-02-01&date_to=2024-02-28')
    records = _j(res)
    assert len(records) == 1
    assert records[0]['amount'] == 80.0


def test_record_update(client):
    _login(client)
    res = client.post('/records', json={'category': '餐饮', 'amount': 100, 'date': '2024-01-01', 'note': ''})
    rid = _j(res)['id']
    res = client.put(f'/records/{rid}', json={'amount': 200, 'note': '已修改'})
    data = _j(res)
    assert data['amount'] == 200.0
    assert data['note'] == '已修改'


def test_record_delete(client):
    _login(client)
    res = client.post('/records', json={'category': '餐饮', 'amount': 100, 'date': '2024-01-01', 'note': ''})
    rid = _j(res)['id']
    client.delete(f'/records/{rid}')
    assert len(_j(client.get('/records'))) == 0


def test_record_delete_not_found(client):
    _login(client)
    res = client.delete('/records/9999')
    assert res.status_code == 404


# ===================== 数据分析 =====================

def test_analytics_summary_empty(client):
    _login(client)
    res = client.get('/analytics/summary')
    data = _j(res)
    assert res.status_code == 200
    assert data['total'] == 0


def test_analytics_summary_with_data(client):
    _login(client)
    client.post('/records', json={'category': '餐饮', 'amount': 200, 'date': '2024-01-10', 'note': ''})
    client.post('/records', json={'category': '交通', 'amount': 50, 'date': '2024-01-15', 'note': ''})
    res = client.get('/analytics/summary')
    data = _j(res)
    assert data['total'] == 250.0
    assert data['count'] == 2
    assert '餐饮' in data['category_totals']
    assert '2024-01' in data['monthly_totals']


def test_analytics_cluster_insufficient(client):
    _login(client)
    client.post('/records', json={'category': '餐饮', 'amount': 100, 'date': '2024-01-01', 'note': ''})
    res = client.get('/analytics/cluster')
    data = _j(res)
    assert 'error' in data


def test_analytics_cluster_ok(client):
    _login(client)
    for i in range(6):
        client.post('/records', json={
            'category': ['餐饮', '交通', '购物'][i % 3],
            'amount': 100 + i * 50,
            'date': f'2024-0{(i // 2) + 1}-{(i % 4) * 5 + 5:02d}',
            'note': ''
        })
    res = client.get('/analytics/cluster')
    data = _j(res)
    assert res.status_code == 200
    assert 'clusters' in data
    assert len(data['clusters']) >= 1


# ===================== 预算管理 =====================

def test_budget_create(client):
    _login(client)
    res = client.post('/budgets', json={'category': '餐饮', 'monthly_limit': 2000})
    assert res.status_code == 201
    assert _j(res)['category'] == '餐饮'


def test_budget_upsert(client):
    _login(client)
    client.post('/budgets', json={'category': '餐饮', 'monthly_limit': 2000})
    res = client.post('/budgets', json={'category': '餐饮', 'monthly_limit': 3000})
    assert _j(res)['monthly_limit'] == 3000.0
    assert len(_j(client.get('/budgets'))) == 1


def test_budget_update(client):
    _login(client)
    res = client.post('/budgets', json={'category': '交通', 'monthly_limit': 500})
    bid = _j(res)['id']
    res = client.put(f'/budgets/{bid}', json={'monthly_limit': 800})
    assert _j(res)['monthly_limit'] == 800.0


def test_budget_delete(client):
    _login(client)
    res = client.post('/budgets', json={'category': '购物', 'monthly_limit': 1000})
    bid = _j(res)['id']
    client.delete(f'/budgets/{bid}')
    assert len(_j(client.get('/budgets'))) == 0


def test_budget_status(client):
    _login(client)
    from datetime import date
    today = date.today().strftime('%Y-%m-%d')
    client.post('/budgets', json={'category': '餐饮', 'monthly_limit': 1000})
    client.post('/records', json={'category': '餐饮', 'amount': 600, 'date': today, 'note': ''})
    res = client.get('/analytics/budget-status')
    data = _j(res)
    assert 'budgets' in data
    assert data['budgets'][0]['percentage'] == 60.0
    assert data['budgets'][0]['status'] == 'normal'


def test_budget_status_over(client):
    _login(client)
    from datetime import date
    today = date.today().strftime('%Y-%m-%d')
    client.post('/budgets', json={'category': '餐饮', 'monthly_limit': 500})
    client.post('/records', json={'category': '餐饮', 'amount': 800, 'date': today, 'note': ''})
    res = client.get('/analytics/budget-status')
    status = _j(res)['budgets'][0]
    assert status['status'] == 'over'
    assert status['remaining'] == -300.0


# ===================== 财务健康评分 =====================

def test_health_score_no_data(client):
    _login(client)
    res = client.get('/analytics/health')
    data = _j(res)
    assert data['grade'] == 'N/A'


def test_health_score_with_data(client):
    _login(client)
    for i in range(6):
        m = (i // 2) + 1
        client.post('/records', json={
            'category': ['餐饮', '交通', '购物'][i % 3],
            'amount': 300 + i * 20,
            'date': f'2024-{m:02d}-15',
            'note': ''
        })
    res = client.get('/analytics/health')
    data = _j(res)
    assert res.status_code == 200
    assert 0 <= data['score'] <= 100
    assert data['grade'] in ('A', 'B', 'C', 'D')
    assert 'details' in data
    assert 'suggestions' in data


# ===================== ARIMA 预测 =====================

def test_predict_insufficient(client):
    _login(client)
    client.post('/records', json={'category': '餐饮', 'amount': 300, 'date': '2024-01-15', 'note': ''})
    res = client.get('/analytics/predict')
    data = _j(res)
    assert 'predictions' in data
    assert len(data['predictions']) == 3
    assert 'note' in data


def test_predict_with_enough_data(client):
    _login(client)
    for m in range(1, 6):
        for d in [5, 15, 25]:
            client.post('/records', json={
                'category': '餐饮', 'amount': 300 + m * 10,
                'date': f'2024-{m:02d}-{d:02d}', 'note': ''
            })
    res = client.get('/analytics/predict')
    data = _j(res)
    assert res.status_code == 200
    assert 'predictions' in data
    assert len(data['predictions']) == 3
    assert 'historical' in data
    for p in data['predictions']:
        assert p['predicted_amount'] >= 0

def test_analytics_cluster_invalid_param(client):
    _login(client)
    res = client.get('/analytics/cluster?n_clusters=abc')
    data = _j(res)
    assert res.status_code == 400
    assert data['success'] is False


def test_predict_invalid_param(client):
    _login(client)
    res = client.get('/analytics/predict?periods=abc')
    data = _j(res)
    assert res.status_code == 400
    assert data['success'] is False
