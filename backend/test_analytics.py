"""
财务分析纯函数单测

覆盖：空数据兜底、月度/分类聚合、KMeans 聚类边界、ARIMA 降级策略、健康评分四维规则。

这些函数不碰数据库，因此不需要 MySQL —— 直接喂 dict 列表即可。
运行：cd backend && pytest test_analytics.py -v
"""

import analytics


def rec(amount, date, category, rid=None, note=''):
    r = {'amount': amount, 'date': date, 'category': category}
    if rid is not None:
        r['id'] = rid
    if note:
        r['note'] = note
    return r


def monthly_records(n_months=6, amount=1000.0, category='餐饮'):
    """构造 n_months 个月的等额记录，每月 1 条"""
    return [rec(amount, f'2026-{m:02d}-15', category) for m in range(1, n_months + 1)]


# ---------- 空数据兜底 ----------

def test_summary_stats_on_empty_returns_zeroed_payload():
    out = analytics.summary_stats([])
    assert out['total'] == 0 and out['count'] == 0 and out['avg'] == 0
    assert out['category_totals'] == {} and out['monthly_totals'] == {}


def test_health_score_on_empty_is_na_not_crash():
    out = analytics.health_score([], [])
    assert out['score'] == 0 and out['grade'] == 'N/A'
    assert out['suggestions'], "空数据必须给出引导性建议而不是空列表"


def test_arima_on_empty_reports_error():
    out = analytics.arima_predict([])
    assert out['predictions'] == [] and 'error' in out


# ---------- 聚合正确性 ----------

def test_summary_stats_aggregates_by_category_and_month():
    records = [
        rec(100, '2026-01-05', '餐饮'),
        rec(200, '2026-01-20', '餐饮'),
        rec(300, '2026-02-10', '交通'),
    ]
    out = analytics.summary_stats(records)

    assert out['count'] == 3
    assert out['total'] == 600.0
    assert out['avg'] == 200.0
    assert out['category_totals'] == {'餐饮': 300.0, '交通': 300.0}
    assert out['monthly_totals'] == {'2026-01': 300.0, '2026-02': 300.0}


def test_invalid_amount_is_coerced_to_zero_not_dropped_silently():
    """amount 非数字时应记为 0 而不是让整个统计崩掉"""
    records = [rec('abc', '2026-01-05', '餐饮'), rec(100, '2026-01-06', '餐饮')]
    out = analytics.summary_stats(records)
    assert out['count'] == 2
    assert out['total'] == 100.0


def test_invalid_date_rows_are_excluded():
    """日期无法解析的行无法归月，应被排除在统计之外"""
    records = [rec(100, 'not-a-date', '餐饮'), rec(50, '2026-01-05', '餐饮')]
    out = analytics.summary_stats(records)
    assert out['count'] == 1 and out['total'] == 50.0


# ---------- KMeans 边界 ----------

def test_kmeans_requires_at_least_three_records():
    out = analytics.kmeans_cluster([rec(10, '2026-01-01', '餐饮')])
    assert out['clusters'] == [] and 'error' in out


def test_kmeans_cluster_count_never_exceeds_sample_size():
    """n_clusters 大于样本量时必须收敛到样本量，否则 sklearn 会抛错"""
    records = [rec(100 * (i + 1), f'2026-01-{i + 1:02d}', '餐饮', rid=i + 1) for i in range(3)]
    out = analytics.kmeans_cluster(records, n_clusters=5)
    assert 'error' not in out
    assert len(out['clusters']) == 3


def test_kmeans_tolerates_records_without_db_only_columns():
    """少了 id / note 这类数据库字段时，聚类应照常返回而不是 KeyError"""
    records = [rec(100 * (i + 1), f'2026-01-{i + 1:02d}', '餐饮') for i in range(6)]
    out = analytics.kmeans_cluster(records, n_clusters=2)
    assert 'error' not in out
    assert set(out['records'][0]) == {'date', 'category', 'amount', 'cluster'}


# ---------- ARIMA 降级 ----------

def test_arima_falls_back_to_average_when_history_shorter_than_three_months():
    out = analytics.arima_predict(monthly_records(n_months=2), periods=2)
    assert len(out['predictions']) == 2
    assert all(p['method'] == 'average' for p in out['predictions'])
    assert all(p['predicted_amount'] == 1000.0 for p in out['predictions'])


def test_arima_predictions_are_non_negative_and_forward_dated():
    """预测金额不得为负；月份必须严格递增且晚于最后一个历史月"""
    out = analytics.arima_predict(monthly_records(n_months=6), periods=3)
    preds = out['predictions']
    assert len(preds) == 3
    assert all(p['predicted_amount'] >= 0 for p in preds)
    months = [p['month'] for p in preds]
    assert months == sorted(months) and months[0] > '2026-06'


# ---------- 健康评分四维规则 ----------

def test_health_score_returns_all_four_dimensions():
    out = analytics.health_score(monthly_records(), [])
    assert set(out['details']) == {'稳定性', '分类均衡', '预算执行', '消费趋势'}
    assert 0 <= out['score'] <= 100
    assert out['grade'] in {'A', 'B', 'C', 'D'}


def test_stable_flat_spending_scores_higher_than_volatile_spending():
    flat = analytics.health_score(monthly_records(amount=1000.0), [])
    volatile = analytics.health_score(
        [rec(a, f'2026-{i + 1:02d}-15', '餐饮')
         for i, a in enumerate([100, 5000, 200, 8000, 150, 6000])], []
    )
    assert flat['details']['稳定性'] > volatile['details']['稳定性']
    assert flat['score'] > volatile['score']


def test_budget_overrun_is_penalized_and_explained():
    records = monthly_records(n_months=6, amount=1000.0, category='餐饮')
    within = analytics.health_score(records, [{'category': '餐饮', 'monthly_limit': 5000}])
    over = analytics.health_score(records, [{'category': '餐饮', 'monthly_limit': 100}])

    assert over['details']['预算执行'] < within['details']['预算执行']
    assert any('超预算' in s for s in over['suggestions'])


def test_single_category_spending_flags_imbalance():
    """全部金额集中在一个分类时，分类均衡项应被扣分并给出建议"""
    out = analytics.health_score(monthly_records(n_months=6, amount=1000.0, category='娱乐'), [])
    assert out['details']['分类均衡'] < 25
    assert any('建议均衡' in s for s in out['suggestions'])
