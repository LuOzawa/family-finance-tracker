"""
seed_data.py — Insert 4000 realistic finance records for the admin user.
Run from the backend/ directory: python seed_data.py
"""
import sys, os, random
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app
from models import db, User, FinanceRecord

TOTAL_RECORDS = 4000
BATCH_SIZE    = 500
DATE_START    = date(2026, 1, 20)
DATE_SPAN     = 59  # days to 2026-03-20

CATEGORIES = ['餐饮', '交通', '购物', '娱乐', '医疗', '教育', '住房', '水电', '其他']
WEIGHTS    = [  25,    15,    18,    10,     6,     7,     4,     7,     8  ]
AMOUNT_RANGES = {
    '餐饮': (10,    800),
    '交通': (5,     500),
    '购物': (20,   3000),
    '娱乐': (10,   1000),
    '医疗': (20,   5000),
    '教育': (50,   3000),
    '住房': (500, 10000),
    '水电': (50,   1500),
    '其他': (10,   2000),
}
NOTES = {
    '餐饮': ['午饭', '晚饭', '早饭', '外卖', '聚餐', '咖啡', '奶茶', ''],
    '交通': ['打车', '地铁', '公交', '加油', '高铁票', '停车费', ''],
    '购物': ['超市购物', '网购', '日用品', '服装', '家电', '生鲜', ''],
    '娱乐': ['电影票', '游戏充值', '健身', 'KTV', '景点门票', ''],
    '医疗': ['门诊', '药品', '体检', '住院费', '牙科', ''],
    '教育': ['书本费', '培训班', '在线课程', '文具', '学费', ''],
    '住房': ['房租', '物业费', '水电押金', '家具', '装修', '房贷', ''],
    '水电': ['电费', '水费', '燃气费', '网费', '物业水电', ''],
    '其他': ['杂费', '礼品', '快递', '维修', '捐款', ''],
}


def random_record(user_id):
    cat = random.choices(CATEGORIES, weights=WEIGHTS, k=1)[0]
    lo, hi = AMOUNT_RANGES[cat]
    return FinanceRecord(
        user_id  = user_id,
        category = cat,
        amount   = round(random.uniform(lo, hi), 2),
        date     = (DATE_START + timedelta(days=random.randint(0, DATE_SPAN))).strftime('%Y-%m-%d'),
        note     = random.choice(NOTES[cat]),
    )


def main():
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print('[ERROR] Admin user not found. Run app.py once first to initialise the DB.')
            sys.exit(1)
        print(f'[INFO]  Admin user found: id={admin.id}, username={admin.username}')
        existing = FinanceRecord.query.filter_by(user_id=admin.id).count()
        print(f'[INFO]  Existing records: {existing}')

        inserted = 0
        for i in range(0, TOTAL_RECORDS, BATCH_SIZE):
            count = min(BATCH_SIZE, TOTAL_RECORDS - i)
            batch = [random_record(admin.id) for _ in range(count)]
            db.session.bulk_save_objects(batch)
            db.session.commit()
            inserted += count
            print(f'[INFO]  {inserted:>5}/{TOTAL_RECORDS}  ({inserted / TOTAL_RECORDS * 100:.1f}%)')

        total = FinanceRecord.query.filter_by(user_id=admin.id).count()
        print(f'\n[DONE]  Records added this run : {inserted}')
        print(f'[DONE]  Total records in DB     : {total}')


if __name__ == '__main__':
    main()
