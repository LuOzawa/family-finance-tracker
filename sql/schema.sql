-- ===========================================================================
--  家庭理财记账系统 · MySQL 建库脚本
--  生成来源：backend/models.py 的 SQLAlchemy 元数据（与实际运行表结构一致）
--
--  ⚠️ 警告：本脚本会 DROP 并重建全部表。库中已有数据时请先备份：
--      mysqldump -u root -p --databases family_finance > backup_$(date +%F).sql
--
--  说明：应用启动时会用 db.create_all() 自动建表（仅当表不存在），
--        本文件用于「看得见的表结构」——评审、交接、迁移时不必去读 ORM 代码。
--        金额字段用 DOUBLE 而非 FLOAT：FLOAT 只有 7 位有效数字，累加会掉精度。
-- ===========================================================================

CREATE DATABASE IF NOT EXISTS family_finance
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE family_finance;

DROP TABLE IF EXISTS finance_records;
DROP TABLE IF EXISTS budgets;
DROP TABLE IF EXISTS users;

-- ---------------------------------------------------------------------------
-- 用户
-- ---------------------------------------------------------------------------
CREATE TABLE users (
  id            INT           NOT NULL AUTO_INCREMENT,
  username      VARCHAR(80)   NOT NULL,
  password_hash VARCHAR(256)  NOT NULL COMMENT 'Werkzeug 生成的哈希，绝不存明文',
  created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户';

-- ---------------------------------------------------------------------------
-- 财务流水
-- ---------------------------------------------------------------------------
CREATE TABLE finance_records (
  id         INT          NOT NULL AUTO_INCREMENT,
  user_id    INT          NOT NULL,
  category   VARCHAR(50)  NOT NULL COMMENT '消费分类（餐饮/交通/娱乐...）',
  amount     DOUBLE       NOT NULL COMMENT '金额，正数',
  date       VARCHAR(20)  NOT NULL COMMENT 'YYYY-MM-DD；沿用 VARCHAR 以兼容历史数据',
  note       VARCHAR(200) NOT NULL DEFAULT '',
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  -- 按用户按月统计（summary_stats / ARIMA 的主查询路径）
  KEY idx_records_user_date (user_id, date),
  -- 按用户按分类聚合（分类占比、预算执行）
  KEY idx_records_user_category (user_id, category),
  CONSTRAINT fk_records_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='财务流水';

-- ---------------------------------------------------------------------------
-- 月度预算
-- ---------------------------------------------------------------------------
CREATE TABLE budgets (
  id            INT         NOT NULL AUTO_INCREMENT,
  user_id       INT         NOT NULL,
  category      VARCHAR(50) NOT NULL,
  monthly_limit DOUBLE      NOT NULL DEFAULT 0,
  created_at    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_user_category (user_id, category) COMMENT '同一用户同一分类只允许一条预算',
  CONSTRAINT fk_budgets_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='月度预算';
