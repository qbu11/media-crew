-- Taste Profile Tables Migration
-- 用户口味档案系统

-- 口味档案表
CREATE TABLE IF NOT EXISTS taste_profiles (
    id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    version INTEGER DEFAULT 1,
    phase VARCHAR(20) DEFAULT 'manual',

    -- Factor B: 显式偏好
    explicit_preferences JSONB NOT NULL DEFAULT '{}',

    -- Factor C: 数据洞察
    analytics_insights JSONB NOT NULL DEFAULT '{}',

    -- 聚合口味向量
    taste_vectors JSONB NOT NULL DEFAULT '[]',

    -- Factor A: 反馈信号 (最近500条)
    feedback_signals JSONB NOT NULL DEFAULT '[]',

    -- 进化追踪
    total_feedback_count INTEGER DEFAULT 0,
    approval_count INTEGER DEFAULT 0,
    rejection_count INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_taste_profiles_user ON taste_profiles(user_id);

-- 口味反馈日志表
CREATE TABLE IF NOT EXISTS taste_feedback_logs (
    id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    draft_id VARCHAR(50),
    action VARCHAR(50) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}',
    taste_signals_extracted JSONB NOT NULL DEFAULT '[]',
    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_taste_feedback_user ON taste_feedback_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_taste_feedback_draft ON taste_feedback_logs(draft_id);
CREATE INDEX IF NOT EXISTS idx_taste_feedback_created ON taste_feedback_logs(created_at DESC);

-- Auto-update triggers
CREATE TRIGGER update_taste_profiles_updated_at
    BEFORE UPDATE ON taste_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_taste_feedback_logs_updated_at
    BEFORE UPDATE ON taste_feedback_logs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
