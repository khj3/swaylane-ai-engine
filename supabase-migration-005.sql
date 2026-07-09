-- Migration 005: Brand sales tracking, ledger, and payouts
-- Previous: migration-004.sql (brand portal tables)

-- Add platform_fee_percent to brands
ALTER TABLE brands ADD COLUMN IF NOT EXISTS platform_fee_percent DECIMAL(5,2) DEFAULT 20.00;

-- Brand product connections: maps Shopify products to brands
CREATE TABLE IF NOT EXISTS brand_product_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shopify_product_id TEXT NOT NULL,
    shopify_variant_id TEXT,
    brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    product_title TEXT,
    vendor_name TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bpc_product ON brand_product_connections(shopify_product_id);
CREATE INDEX IF NOT EXISTS idx_bpc_variant ON brand_product_connections(shopify_variant_id);
CREATE INDEX IF NOT EXISTS idx_bpc_brand ON brand_product_connections(brand_id);

-- Sales ledger: line-item level earnings records
CREATE TABLE IF NOT EXISTS sales_ledger (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shopify_order_id TEXT NOT NULL,
    shopify_line_item_id TEXT NOT NULL,
    shopify_product_id TEXT,
    shopify_variant_id TEXT,
    brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL DEFAULT 0,
    gross_sales DECIMAL(12,2) NOT NULL DEFAULT 0,
    discounts DECIMAL(12,2) DEFAULT 0,
    refunds DECIMAL(12,2) DEFAULT 0,
    net_sales DECIMAL(12,2) DEFAULT 0,
    platform_fee DECIMAL(12,2) DEFAULT 0,
    platform_fee_percent DECIMAL(5,2) DEFAULT 20.00,
    brand_earnings DECIMAL(12,2) DEFAULT 0,
    currency TEXT DEFAULT 'USD',
    status TEXT DEFAULT 'earned',
    order_created_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sl_order ON sales_ledger(shopify_order_id);
CREATE INDEX IF NOT EXISTS idx_sl_line_item ON sales_ledger(shopify_line_item_id);
CREATE INDEX IF NOT EXISTS idx_sl_brand ON sales_ledger(brand_id);
CREATE INDEX IF NOT EXISTS idx_sl_status ON sales_ledger(status);

-- Payout records
CREATE TABLE IF NOT EXISTS payouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    payout_period_start TIMESTAMPTZ,
    payout_period_end TIMESTAMPTZ,
    gross_sales DECIMAL(12,2) DEFAULT 0,
    total_discounts DECIMAL(12,2) DEFAULT 0,
    total_refunds DECIMAL(12,2) DEFAULT 0,
    total_platform_fees DECIMAL(12,2) DEFAULT 0,
    total_brand_earnings DECIMAL(12,2) DEFAULT 0,
    amount_paid DECIMAL(12,2) DEFAULT 0,
    payout_status TEXT DEFAULT 'pending',
    paid_at TIMESTAMPTZ,
    payment_reference TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payouts_brand ON payouts(brand_id);
CREATE INDEX IF NOT EXISTS idx_payouts_status ON payouts(payout_status);
