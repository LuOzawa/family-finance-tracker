from flask import Flask, request, jsonify, session
from flask_cors import CORS
from functools import wraps
from datetime import date as date_today
from models import db, User, FinanceRecord, Budget
from config import Config
import analytics as anal

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, supports_credentials=True, origins=['http://localhost:3000', 'http://127.0.0.1:3000'])

db.init_app(app)


def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin')
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()
            print('Admin user created: admin/admin')


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': '未登录，请先登录'}), 401
        return f(*args, **kwargs)
    return decorated


@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'success': True,
        'message': 'family-finance backend is running',
        'health': '/health',
    })


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200


# ---- 认证 ----

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '请求格式错误'}), 400
    user = User.query.filter_by(username=data.get('username')).first()
    if user and user.check_password(data.get('password', '')):
        session['user_id'] = user.id
        return jsonify({'success': True, 'message': '登录成功', 'username': user.username})
    return jsonify({'success': False, 'message': '用户名或密码错误'}), 401


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'success': True, 'message': '已退出登录'})


# ---- 财务记录 CRUD ----

@app.route('/records', methods=['GET'])
@login_required
def get_records():
    q = FinanceRecord.query.filter_by(user_id=session['user_id'])
    category = request.args.get('category')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    if category:
        q = q.filter(FinanceRecord.category == category)
    if date_from:
        q = q.filter(FinanceRecord.date >= date_from)
    if date_to:
        q = q.filter(FinanceRecord.date <= date_to)
    records = q.order_by(FinanceRecord.date.desc()).all()
    return jsonify([r.to_dict() for r in records])


@app.route('/records', methods=['POST'])
@login_required
def create_record():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': '请求格式错误'}), 400
    record = FinanceRecord(
        user_id=session['user_id'],
        category=data.get('category', '其他'),
        amount=float(data.get('amount', 0)),
        date=data.get('date', ''),
        note=data.get('note', ''),
    )
    db.session.add(record)
    db.session.commit()
    return jsonify(record.to_dict()), 201


@app.route('/records/<int:record_id>', methods=['PUT'])
@login_required
def update_record(record_id):
    record = FinanceRecord.query.filter_by(id=record_id, user_id=session['user_id']).first()
    if not record:
        return jsonify({'success': False, 'message': '记录不存在'}), 404
    data = request.get_json()
    record.category = data.get('category', record.category)
    record.amount = float(data.get('amount', record.amount))
    record.date = data.get('date', record.date)
    record.note = data.get('note', record.note)
    db.session.commit()
    return jsonify(record.to_dict())


@app.route('/records/<int:record_id>', methods=['DELETE'])
@login_required
def delete_record(record_id):
    record = FinanceRecord.query.filter_by(id=record_id, user_id=session['user_id']).first()
    if not record:
        return jsonify({'success': False, 'message': '记录不存在'}), 404
    db.session.delete(record)
    db.session.commit()
    return jsonify({'success': True, 'message': '删除成功'})


# ---- 数据分析 ----

def _user_records():
    return [r.to_dict() for r in FinanceRecord.query.filter_by(user_id=session['user_id']).all()]


@app.route('/analytics/summary', methods=['GET'])
@login_required
def analytics_summary():
    return jsonify(anal.summary_stats(_user_records()))


@app.route('/analytics/cluster', methods=['GET'])
@login_required
def analytics_cluster():
    raw = request.args.get('n_clusters', '3')
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'n_clusters must be an integer'}), 400
    if n < 1:
        return jsonify({'success': False, 'message': 'n_clusters must be >= 1'}), 400
    n = min(n, 5)
    return jsonify(anal.kmeans_cluster(_user_records(), n_clusters=n))


@app.route('/analytics/predict', methods=['GET'])
@login_required
def analytics_predict():
    raw = request.args.get('periods', '3')
    try:
        periods = int(raw)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'periods must be an integer'}), 400
    if periods < 1:
        return jsonify({'success': False, 'message': 'periods must be >= 1'}), 400
    periods = min(periods, 6)
    return jsonify(anal.arima_predict(_user_records(), periods=periods))


@app.route('/analytics/health', methods=['GET'])
@login_required
def analytics_health():
    records = _user_records()
    budgets = [b.to_dict() for b in Budget.query.filter_by(user_id=session['user_id']).all()]
    return jsonify(anal.health_score(records, budgets))


# ---- 预算管理 ----

@app.route('/budgets', methods=['GET'])
@login_required
def get_budgets():
    budgets = Budget.query.filter_by(user_id=session['user_id']).all()
    return jsonify([b.to_dict() for b in budgets])


@app.route('/budgets', methods=['POST'])
@login_required
def create_budget():
    data = request.get_json()
    existing = Budget.query.filter_by(
        user_id=session['user_id'], category=data.get('category')
    ).first()
    if existing:
        existing.monthly_limit = float(data.get('monthly_limit', existing.monthly_limit))
        db.session.commit()
        return jsonify(existing.to_dict())
    budget = Budget(
        user_id=session['user_id'],
        category=data.get('category'),
        monthly_limit=float(data.get('monthly_limit', 0)),
    )
    db.session.add(budget)
    db.session.commit()
    return jsonify(budget.to_dict()), 201


@app.route('/budgets/<int:budget_id>', methods=['PUT'])
@login_required
def update_budget(budget_id):
    budget = Budget.query.filter_by(id=budget_id, user_id=session['user_id']).first()
    if not budget:
        return jsonify({'success': False, 'message': '预算不存在'}), 404
    data = request.get_json()
    budget.monthly_limit = float(data.get('monthly_limit', budget.monthly_limit))
    db.session.commit()
    return jsonify(budget.to_dict())


@app.route('/budgets/<int:budget_id>', methods=['DELETE'])
@login_required
def delete_budget(budget_id):
    budget = Budget.query.filter_by(id=budget_id, user_id=session['user_id']).first()
    if not budget:
        return jsonify({'success': False, 'message': '预算不存在'}), 404
    db.session.delete(budget)
    db.session.commit()
    return jsonify({'success': True})


@app.route('/analytics/budget-status', methods=['GET'])
@login_required
def budget_status():
    current_month = date_today.today().strftime('%Y-%m')
    budgets = Budget.query.filter_by(user_id=session['user_id']).all()
    records = FinanceRecord.query.filter(
        FinanceRecord.user_id == session['user_id'],
        FinanceRecord.date.like(f'{current_month}%')
    ).all()

    actuals = {}
    for r in records:
        actuals[r.category] = round(actuals.get(r.category, 0) + r.amount, 2)

    result = []
    for b in budgets:
        actual = round(actuals.get(b.category, 0), 2)
        pct = round(actual / b.monthly_limit * 100, 1) if b.monthly_limit > 0 else 0
        result.append({
            'id': b.id,
            'category': b.category,
            'monthly_limit': b.monthly_limit,
            'actual': actual,
            'percentage': pct,
            'remaining': round(b.monthly_limit - actual, 2),
            'status': 'over' if actual > b.monthly_limit else ('warning' if pct >= 80 else 'normal'),
        })

    return jsonify({'month': current_month, 'budgets': result})


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
