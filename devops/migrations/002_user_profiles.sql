CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE, -- This must match users.id type
    zip_code VARCHAR(10) NOT NULL,
    store_preferences TEXT[], -- e.g., ["ShopRite", "Aldi"]
    
    -- "Lactose Intolerant", "Vegan", "Peanut Allergy"
    dietary_restrictions TEXT[], 
    
    -- JSONB for flexibility: 
    -- [{"age": 32, "gender": "male", "activity_level": "moderate"}, ...]
    family_composition JSONB NOT NULL DEFAULT '[]', 
    
    -- Cached calculations to save compute on every read
    weekly_calorie_target INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for geo-lookups later
CREATE INDEX idx_zip_code ON user_profiles(zip_code);