-- Migration 006: 3D Asset pipeline
-- Previous: migration-005.sql (sales tracking)

CREATE TABLE IF NOT EXISTS product_3d_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_submission_id UUID REFERENCES brand_product_submissions(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    asset_type TEXT NOT NULL DEFAULT 'model',
    input_image_url TEXT,
    input_prompt TEXT,
    output_url TEXT,
    thumbnail_url TEXT,
    status TEXT DEFAULT 'pending',
    confidence_score INTEGER DEFAULT 0,
    geometry_quality INTEGER DEFAULT 0,
    texture_quality INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_3d_product ON product_3d_assets(product_submission_id);
CREATE INDEX IF NOT EXISTS idx_3d_status ON product_3d_assets(status);

ALTER TABLE brand_product_submissions
    ADD COLUMN IF NOT EXISTS has_3d_asset BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS best_3d_thumbnail TEXT;
