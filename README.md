# 家庭理财记账系统

[![CI](https://github.com/LuOzawa/family-finance-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/LuOzawa/family-finance-tracker/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)


面向个人与家庭的记账与财务分析系统。**Flask + Vue 3 前后端分离**，支持日常收支记录、
月度预算管控，并内置 KMeans 消费聚类、ARIMA 支出预测与财务健康评分三组分析模型。

项目为本科毕业设计作品，目标是把"记账"这件事从流水账推进到**可解释的消费洞察**。

---

## 功能概览

| 模块 | 功能 |
| --- | --- |
| 用户认证 | 注册初始化、登录、退出，基于 Flask session；密码用 Werkzeug scrypt 加盐哈希 |
| 记账管理 | 收支记录增删改查，支持按分类、日期区间筛选，按日期倒序展示 |
| 预算管控 | 按分类设置月度上限；实时计算已用金额、占比、剩余额度，超支/接近上限自动标红 |
| 数据看板 | 分类支出占比、月度趋势、总额/均值/笔数汇总（ECharts） |
| 聚类分析 | KMeans 将消费行为分成 2–4 群，输出每群的记录数、均值、合计与主要分类 |
| 支出预测 | ARIMA 时序模型预测未来 3 或 6 个月支出；历史不足 3 个月时退化为均值预测 |
| 健康评分 | 百分制评分 + 等级，从稳定性、分类均衡、预算执行、储蓄率等维度拆解，并给出改进建议 |

## 技术栈

| 层次 | 技术 |
| --- | --- |
| 后端 | Python 3.8+、Flask 3.0、Flask-SQLAlchemy 3.1、Flask-CORS、Werkzeug |
| 数据分析 | pandas、NumPy、scikit-learn（KMeans、StandardScaler）、statsmodels（ARIMA） |
| 前端 | Vue 3、Vue Router 4、Element Plus、ECharts 5、Axios、Vite 5 |
| 数据库 | MySQL 8（PyMySQL 驱动）；未配置时自动回退 SQLite |
| 测试 | pytest，29 个用例覆盖认证、CRUD、筛选、分析与预算全链路 |

## 项目结构

```
.
├── backend/                        # Flask 后端
│   ├── app.py                      # 应用入口、路由、登录校验装饰器
│   ├── models.py                   # User / FinanceRecord / Budget
│   ├── analytics.py                # 汇总统计、KMeans、ARIMA、健康评分
│   ├── config.py                   # 配置，数据库连接支持环境变量与 SQLite 回退
│   ├── seed_data.py                # 生成 4000 条演示记录
│   ├── migrate_sqlite_to_mysql.py  # 一次性迁移脚本（SQLite → MySQL）
│   ├── test_api.py                 # pytest 测试套件（29 个用例）
│   ├── requirements.txt
│   └── instance/                   # Flask 实例目录（SQLite 文件，不提交）
├── frontend/                       # Vue 3 前端
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js              # 开发代理 /api → localhost:5000
│   └── src/
│       ├── main.js
│       ├── App.vue
│       ├── router/index.js         # 路由 + 登录守卫
│       └── components/
│           ├── Login.vue           # 登录页
│           ├── Home.vue            # 布局与侧边导航
│           ├── Dashboard.vue       # 记账台账 + 汇总图表
│           ├── Analytics.vue       # 聚类分析
│           ├── Budget.vue          # 预算管理
│           └── Predict.vue         # 支出预测
├── README.md
├── docs/
│   └── 启动说明.md                       # 完整运行步骤与常见问题
├── .env.example
└── .gitignore
```

## 快速开始

> 完整步骤与常见问题见 **[docs/启动说明.md](docs/启动说明.md)**，下面是精简版。

### 1. 环境要求

- Python 3.8+
- Node.js 18+
- MySQL 8（可选，不装则自动用 SQLite）

### 2. 后端

```bash
cd backend
pip install -r requirements.txt
```

选择数据库，二选一：

**方式 A：MySQL**

```powershell
$env:DB_NAME     = "family_finance"
$env:DB_PASSWORD = "你的数据库密码"
```

**方式 B：零配置（SQLite）**

不设置任何 `DB_*` 变量即可，程序会在 `backend/instance/` 下自动建 SQLite 文件。

然后启动：

```bash
python app.py
```

首次启动会自动建表并创建默认账号 `admin / admin`，服务监听 `http://localhost:5000`。

### 3. 前端

**另开一个终端**：

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:3000`。

### 4. 灌入演示数据（可选）

```bash
cd backend
python seed_data.py
```

生成 4000 条 2026-01-20 至 2026-03-20 区间的模拟消费记录，方便直接看到图表效果。

## 默认账号

| 用户名 | 密码 |
| --- | --- |
| `admin` | `admin` |

> 首次启动由 `init_db()` 自动创建，生产使用请立即修改。

## 接口一览

统一前缀：后端直连 `http://localhost:5000`，前端通过 Vite 代理走 `/api`（转发时剥掉 `/api` 前缀）。

| 方法 | 路径 | 说明 | 需登录 |
| --- | --- | --- | --- |
| GET | `/` | 服务信息 | |
| GET | `/health` | 健康检查 | |
| POST | `/login` | 登录 | |
| POST | `/logout` | 退出 | |
| GET | `/records` | 记录列表，支持 `category`、`date_from`、`date_to` | ✅ |
| POST | `/records` | 新增记录 | ✅ |
| PUT | `/records/<id>` | 修改记录 | ✅ |
| DELETE | `/records/<id>` | 删除记录 | ✅ |
| GET | `/analytics/summary` | 汇总统计 | ✅ |
| GET | `/analytics/cluster?n_clusters=3` | 聚类分析（1–5 群） | ✅ |
| GET | `/analytics/predict?periods=3` | 支出预测（1–6 个月） | ✅ |
| GET | `/analytics/health` | 健康评分 | ✅ |
| GET | `/budgets` | 预算列表 | ✅ |
| POST | `/budgets` | 新增或更新预算（按分类 upsert） | ✅ |
| PUT | `/budgets/<id>` | 修改预算 | ✅ |
| DELETE | `/budgets/<id>` | 删除预算 | ✅ |
| GET | `/analytics/budget-status` | 本月预算执行情况 | ✅ |

响应约定：成功返回数据本体或 `{"success": true, ...}`；失败返回
`{"success": false, "message": "..."}` 并带对应 HTTP 状态码（401 未登录 / 404 不存在 / 400 参数错误）。

## 数据模型

```
User ──┬── FinanceRecord     （1:N，级联删除）
       └── Budget            （1:N，user_id + category 唯一）
```

| 表 | 字段 |
| --- | --- |
| `users` | id、username（唯一）、password_hash、created_at |
| `finance_records` | id、user_id、category、amount、date、note、created_at |
| `budgets` | id、user_id、category、monthly_limit、created_at |

- 密码使用 `werkzeug.security.generate_password_hash`（scrypt），**不存明文**
- 所有记录查询都带 `user_id` 过滤，不存在跨用户越权读取

## 分析模型说明

**KMeans 聚类**（`analytics.kmeans_cluster`）
把每条记录映射到 `[金额, 分类编码, 日]` 三维空间，先做 `StandardScaler` 标准化再加权聚类，
输出每群的人数、均值、合计、主要分类，用于识别"大额低频""小额高频"等消费形态。

**ARIMA 预测**（`analytics.arima_predict`）
按月度汇总后拟合 ARIMA(1,1,1)，预测未来 N 个月。历史不足 3 个月时自动退化为均值预测，
并在响应里用 `method` 字段标明用了哪种方法，避免把退化结果当成模型输出。

**健康评分**（`analytics.health_score`）
百分制，四个维度各 25 分：

| 维度 | 判定方式 |
| --- | --- |
| 稳定性 | 月度支出变异系数，越低分越高 |
| 分类均衡 | 单一分类占比过高扣分 |
| 预算执行 | 超出月度上限的分类数，每个扣 8 分 |
| 储蓄/结余 | 剩余可支配比例 |

同时生成可读建议，例如「"购物"支出占总额 34%，建议均衡各类支出」。

## 测试

```bash
cd backend
pytest test_api.py test_analytics.py -q     # 44 个用例
```

**两部分测试，职责不同：**

| 文件 | 用例 | 依赖 | 覆盖 |
|---|---|---|---|
| `test_api.py` | 29 | SQLite 临时库 | 登录/登出、记录 CRUD、分类与日期筛选、分析接口（含数据不足分支）、预算 upsert、健康评分 |
| `test_analytics.py` | 15 | **无依赖**（纯函数） | 空数据兜底、分类/月度聚合、非法金额与非法日期、KMeans 样本边界、ARIMA 三级降级、健康评分四维规则 |

`test_analytics.py` 不碰数据库，因此 CI 里直接跑它；`test_api.py` 需要 SQLite fixture，
留作本地全量回归。当前状态：**44 passed**。

> ⚠️ `test_api.py` 会在 fixture 里执行 `db.drop_all()`。文件顶部已把 `DATABASE_URL`
> 强制指向临时 SQLite 文件，并加了断言兜底，**不会**碰真实数据库。
> 这段防护不要删除 —— 早期版本没有它，导致过一次误删真实库的事故。

## 安全说明

相比同类课程项目，本项目在几个基础点上是对的：

| 项 | 现状 |
| --- | --- |
| 密码存储 | Werkzeug scrypt 加盐哈希（非 MD5、非明文） |
| 越权访问 | 所有资源查询都带 `user_id` 过滤 |
| CORS | 白名单限定 `localhost:3000` / `127.0.0.1:3000`，未使用 `*` |
| 数据库口令 | 不写死在代码里，来自环境变量；无配置时回退 SQLite |
| 会话 Cookie | `HttpOnly` + `SameSite=Lax` |

仍需注意：

1. **`app.run(debug=True)`** —— 生产部署必须关掉 debug，并换用 gunicorn / uWSGI。
2. **无登录频率限制** —— 登录接口未做防暴力破解。
3. **`SESSION_COOKIE_SECURE` 默认关闭** —— 上 HTTPS 后应设 `SESSION_COOKIE_SECURE=1`。
4. **`SECRET_KEY` 有开发默认值** —— 部署时务必用环境变量覆盖。
5. **分析在请求内同步计算** —— 记录量大时 `/analytics/*` 会变慢，可改预计算或缓存。
6. **无数据库迁移工具** —— 表结构靠 `db.create_all()`，改模型后需手工处理。

## 关于 `archive/` 目录

原始项目里有一个 22MB 的 `archive/Family Income and Expenditure.csv`，是前期探索用的
公开数据集，**未参与程序运行**（代码中无任何引用），因此未纳入本仓库。

## 许可

本项目仅用于学习与毕业设计交流，不用于商业用途。
