ALTER TABLE feedback
    ADD COLUMN IF NOT EXISTS result VARCHAR(16),
    ADD COLUMN IF NOT EXISTS feedback_time TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS agent_id VARCHAR(128) NOT NULL DEFAULT 'lead_agent',
    ADD COLUMN IF NOT EXISTS agent_name VARCHAR(128) NOT NULL DEFAULT '';

UPDATE feedback
SET result = CASE
    WHEN rating = 1 THEN 'positive'
    WHEN rating = -1 THEN 'negative'
    ELSE NULL
END
WHERE result IS NULL;
