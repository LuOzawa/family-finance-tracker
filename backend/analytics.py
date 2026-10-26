"""
数据处理与分析模块
- Pandas 数据清洗与汇总统计
- K-means 消费聚类
- ARIMA 时序预测
- 财务健康评分
"""
import pandas as pd
import numpy as np


def _to_df(records):
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    df['month'] = df['date'].dt.strftime('%Y-%m')
    return df


def summary_stats(records):
    df = _to_df(records)
    if df.empty:
        return {'category_totals': {}, 'monthly_totals': {}, 'total': 0, 'count': 0, 'avg': 0}
    category_totals = df.groupby('category')['amount'].sum().round(2).to_dict()
    monthly_totals = df.groupby('month')['amount'].sum().round(2).sort_index().to_dict()
    return {
        'category_totals': category_totals,
        'monthly_totals': monthly_totals,
        'total': round(float(df['amount'].sum()), 2),
        'count': int(len(df)),
        'avg': round(float(df['amount'].mean()), 2),
    }


def kmeans_cluster(records, n_clusters=3):
    try:
        from sklearn.cluster import KMeans
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        return {'error': 'scikit-learn未安装，请运行: pip install scikit-learn', 'clusters': [], 'records': []}

    df = _to_df(records)
    if df.empty or len(df) < 3:
        return {'error': '数据不足（至少需要3条记录才能聚类）', 'clusters': [], 'records': []}

    df = df.copy()
    cats = sorted(df['category'].unique().tolist())
    df['cat_code'] = df['category'].apply(lambda x: cats.index(x))
    df['day'] = df['date'].dt.day

    X = StandardScaler().fit_transform(df[['amount', 'cat_code', 'day']].values)
    k = min(n_clusters, len(df))
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    df['cluster'] = km.fit_predict(X)

    cluster_info = []
    colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399']
    for i in range(k):
        sub = df[df['cluster'] == i]
        cluster_info.append({
            'cluster_id': i,
            'label': f'消费群组 {i + 1}',
            'count': int(len(sub)),
            'avg_amount': round(float(sub['amount'].mean()), 2),
            'total_amount': round(float(sub['amount'].sum()), 2),
            'top_category': str(sub['category'].value_counts().index[0]),
            'color': colors[i % len(colors)],
        })

    out = df[['id', 'date', 'category', 'amount', 'note', 'cluster']].copy()
    out['date'] = out['date'].dt.strftime('%Y-%m-%d')
    out['cluster'] = out['cluster'].astype(int)

    return {'clusters': cluster_info, 'records': out.to_dict('records'), 'n_clusters': k}


def _next_month_str(ym: str, n: int) -> str:
    y, m = int(ym[:4]), int(ym[5:7])
    m += n
    while m > 12:
        m -= 12
        y += 1
    return f'{y:04d}-{m:02d}'


def arima_predict(records, periods=3):
    df = _to_df(records)
    if df.empty:
        return {'predictions': [], 'historical': [], 'error': '无历史数据'}

    monthly = df.groupby('month')['amount'].sum().reset_index().sort_values('month')
    monthly['amount'] = monthly['amount'].round(2)
    historical = monthly.to_dict('records')
    last_month = monthly['month'].iloc[-1]

    if len(monthly) < 3:
        avg = float(monthly['amount'].mean())
        preds = [
            {'month': _next_month_str(last_month, i + 1),
             'predicted_amount': round(avg, 2), 'method': 'average'}
            for i in range(periods)
        ]
        return {'predictions': preds, 'historical': historical,
                'note': '历史数据不足3个月，已使用均值替代预测'}

    try:
        from statsmodels.tsa.arima.model import ARIMA
        series = monthly['amount'].values.astype(float)
        fit = ARIMA(series, order=(1, 1, 1)).fit()
        forecast = fit.forecast(steps=periods)
        preds = [
            {'month': _next_month_str(last_month, i + 1),
             'predicted_amount': round(max(0.0, float(v)), 2), 'method': 'arima'}
            for i, v in enumerate(forecast)
        ]
        return {'predictions': preds, 'historical': historical}
    except Exception as e:
        avg = float(monthly['amount'].mean())
        preds = [
            {'month': _next_month_str(last_month, i + 1),
             'predicted_amount': round(avg, 2), 'method': 'average'}
            for i in range(periods)
        ]
        return {'predictions': preds, 'historical': historical,
                'note': f'ARIMA拟合异常，已使用均值替代: {str(e)[:60]}'}


def health_score(records, budgets):
    df = _to_df(records)
    suggestions = []
    scores = {}

    if df.empty:
        return {
            'score': 0, 'grade': 'N/A', 'grade_desc': '无数据',
            'details': {}, 'suggestions': ['请先添加财务记录以生成健康评分']
        }

    # 1. 稳定性 (25分): 月度变异系数越低越好
    monthly = df.groupby('month')['amount'].sum()
    if len(monthly) >= 2:
        cv = float(monthly.std() / monthly.mean()) if monthly.mean() > 0 else 0
        s1 = max(0, int(25 * (1 - min(cv, 1))))
        if cv > 0.4:
            suggestions.append(f'月度支出波动较大（变异系数 {cv:.0%}），建议制定固定预算计划')
    else:
        s1 = 15
    scores['稳定性'] = s1

    # 2. 分类均衡 (25分): 单类占比越低越好
    cat = df.groupby('category')['amount'].sum()
    total = float(cat.sum())
    max_r = float(cat.max() / total) if total > 0 else 1.0
    s2 = max(0, int(25 * (1 - max(0.0, max_r - 0.3) / 0.7)))
    if max_r > 0.5:
        suggestions.append(f'"{cat.idxmax()}"支出占总额 {max_r:.0%}，建议均衡各类支出')
    scores['分类均衡'] = s2

    # 3. 预算执行 (25分): 超预算分类越少越好
    if budgets:
        cur = df['month'].max()
        cur_cat = df[df['month'] == cur].groupby('category')['amount'].sum().to_dict()
        over = 0
        for b in budgets:
            actual = cur_cat.get(b['category'], 0)
            if actual > b['monthly_limit']:
                over += 1
                suggestions.append(f'"{b["category"]}"本月超预算 ¥{actual - b["monthly_limit"]:.2f}，请控制消费')
            elif b['monthly_limit'] > 0 and actual > b['monthly_limit'] * 0.85:
                suggestions.append(f'"{b["category"]}"本月已用 {actual / b["monthly_limit"]:.0%}，即将超预算')
        s3 = max(0, 25 - over * 8)
    else:
        s3 = 15
        suggestions.append('建议为各分类设置月度预算，以便系统评估预算执行情况')
    scores['预算执行'] = s3

    # 4. 消费趋势 (25分): 支出环比下降为好
    if len(monthly) >= 2:
        prev, curr = float(monthly.iloc[-2]), float(monthly.iloc[-1])
        delta = (curr - prev) / prev if prev > 0 else 0
        if delta <= 0:
            s4 = 25
        else:
            s4 = max(0, int(20 - delta * 25))
            if delta > 0.15:
                suggestions.append(f'近期支出环比增加 {delta:.0%}，请注意控制消费节奏')
    else:
        s4 = 15
    scores['消费趋势'] = s4

    total_s = sum(scores.values())
    if total_s >= 80:
        grade, desc = 'A', '优秀'
    elif total_s >= 65:
        grade, desc = 'B', '良好'
    elif total_s >= 45:
        grade, desc = 'C', '一般'
    else:
        grade, desc = 'D', '需改善'

    if not suggestions:
        suggestions.append('各项指标表现良好，继续保持优秀的财务习惯！')

    return {
        'score': total_s,
        'grade': grade,
        'grade_desc': desc,
        'details': scores,
        'suggestions': suggestions,
    }
