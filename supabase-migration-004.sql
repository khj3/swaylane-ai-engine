-- Brand Portal — Full tables

CREATE TABLE IF NOT EXISTS brands (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_user_id TEXT,
  brand_name TEXT NOT NULL,
  brand_slug TEXT UNIQUE,
  logo_url TEXT,
  description TEXT,
  website TEXT,
  instagram TEXT,
  tiktok TEXT,
  contact_email TEXT,
  contact_phone TEXT,
  password_hash TEXT,
  brand_story TEXT,
  legal_business_name TEXT,
  business_address TEXT,
  city TEXT,
  state TEXT,
  zip TEXT,
  country TEXT,
  brand_category TEXT,
  brand_style TEXT,
  target_customer TEXT,
  price_range TEXT,
  fit_identity TEXT,
  shipping_policy TEXT,
  return_policy TEXT,
  processing_time TEXT,
  customer_support_email TEXT,
  status TEXT DEFAULT 'pending',
  admin_notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS brand_users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  role TEXT DEFAULT 'owner',
  status TEXT DEFAULT 'active',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS brand_product_submissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
  shopify_product_id TEXT,
  title TEXT NOT NULL,
  description TEXT,
  category TEXT,
  product_type TEXT,
  price DECIMAL(10,2),
  compare_at_price DECIMAL(10,2),
  sku TEXT,
  inventory_quantity INTEGER DEFAULT 0,
  shipping_weight DECIMAL(8,2),
  tags TEXT,
  material_composition TEXT,
  fabric_weight TEXT,
  stretch_level TEXT,
  thickness TEXT,
  care_instructions TEXT,
  season TEXT,
  fit_type TEXT,
  fit_notes TEXT,
  model_height TEXT,
  model_weight TEXT,
  model_wearing_size TEXT,
  runs_small BOOLEAN DEFAULT FALSE,
  true_to_size BOOLEAN DEFAULT TRUE,
  runs_large BOOLEAN DEFAULT FALSE,
  garment_type TEXT,
  ai_ready BOOLEAN DEFAULT FALSE,
  prompt_guidance TEXT,
  tryon_image_url TEXT,
  fabric_behavior TEXT,
  stretch_level_ai TEXT,
  ai_limitations TEXT,
  supports_full_body_tryon BOOLEAN DEFAULT TRUE,
  supports_style_preview BOOLEAN DEFAULT TRUE,
  rack_ready BOOLEAN DEFAULT FALSE,
  layer_category TEXT,
  can_layer BOOLEAN DEFAULT TRUE,
  recommended_pairings TEXT,
  conflicting_categories TEXT,
  styling_notes TEXT,
  outfit_prompt_guidance TEXT,
  status TEXT DEFAULT 'draft',
  admin_notes TEXT,
  ai_readiness_score INTEGER DEFAULT 0,
  rack_readiness_score INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS product_variants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_submission_id UUID REFERENCES brand_product_submissions(id) ON DELETE CASCADE,
  size TEXT,
  color TEXT,
  sku TEXT,
  price DECIMAL(10,2),
  inventory_quantity INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS product_images (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_submission_id UUID REFERENCES brand_product_submissions(id) ON DELETE CASCADE,
  image_url TEXT NOT NULL,
  image_type TEXT,
  alt_text TEXT,
  sort_order INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS garment_measurements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_submission_id UUID REFERENCES brand_product_submissions(id) ON DELETE CASCADE,
  size TEXT,
  chest_width DECIMAL(8,2),
  body_length DECIMAL(8,2),
  shoulder_width DECIMAL(8,2),
  sleeve_length DECIMAL(8,2),
  hem_width DECIMAL(8,2),
  waist DECIMAL(8,2),
  hip DECIMAL(8,2),
  thigh DECIMAL(8,2),
  inseam DECIMAL(8,2),
  rise DECIMAL(8,2),
  leg_opening DECIMAL(8,2),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS brand_activity_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
  user_id TEXT,
  action TEXT NOT NULL,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Update existing rack_items if it exists, otherwise create
CREATE TABLE IF NOT EXISTS rack_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id TEXT NOT NULL,
  product_id TEXT,
  shopify_product_id TEXT,
  variant_id TEXT,
  brand_id TEXT,
  brand_name TEXT,
  product_title TEXT,
  product_image_url TEXT,
  category TEXT,
  selected_size TEXT,
  selected_color TEXT,
  added_at TIMESTAMPTZ DEFAULT NOW()
);

-- Update existing outfits table
CREATE TABLE IF NOT EXISTS outfits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id TEXT NOT NULL,
  outfit_name TEXT,
  outfit_slug TEXT,
  result_image_url TEXT,
  fit_confidence_label TEXT,
  style_notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS outfit_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  outfit_id UUID REFERENCES outfits(id) ON DELETE CASCADE,
  product_id TEXT,
  shopify_product_id TEXT,
  brand_id TEXT,
  category TEXT,
  selected_size TEXT,
  selected_color TEXT,
  layer_order INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
