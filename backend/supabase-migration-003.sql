-- Migration 003: AI Fit System tables
-- Previous: migration-002.sql (Phase 2 tables)

-- 1. Fit Profiles
CREATE TABLE IF NOT EXISTS fit_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id TEXT,
    email TEXT,
    height TEXT, weight TEXT,
    chest TEXT, waist TEXT, hips TEXT, inseam TEXT,
    shoulders TEXT, thigh TEXT, arm_length TEXT, torso_length TEXT,
    usual_shirt_size TEXT, usual_hoodie_size TEXT, usual_pants_size TEXT, usual_jeans_size TEXT,
    shoe_size TEXT, body_type TEXT, preferred_fit TEXT, style_preference TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fit_profiles_customer ON fit_profiles(customer_id);

-- 2. Photo Quality Checks
CREATE TABLE IF NOT EXISTS photo_quality_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id TEXT,
    image_id TEXT,
    photo_quality_score INT,
    detected_photo_type TEXT,
    fit_confidence_level TEXT,
    recommended_mode TEXT,
    issues JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_photo_quality_customer ON photo_quality_checks(customer_id);

-- 3. Size Recommendations
CREATE TABLE IF NOT EXISTS size_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id TEXT,
    product_id TEXT,
    recommended_size TEXT,
    alternate_size TEXT,
    confidence_score INT,
    confidence_label TEXT,
    fit_reason TEXT,
    fit_warning TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_size_recs_customer ON size_recommendations(customer_id);
CREATE INDEX IF NOT EXISTS idx_size_recs_product ON size_recommendations(product_id);

-- 4. Add columns to ai_tryon_results
ALTER TABLE ai_tryon_results ADD COLUMN IF NOT EXISTS selected_mode TEXT;
ALTER TABLE ai_tryon_results ADD COLUMN IF NOT EXISTS confidence_label TEXT;
