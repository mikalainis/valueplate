# Value Plate — Web App Product Spec

**Repo:** github.com/mikalainis/valueplate
**Data source (phase 1):** github.com/mikalainis/shoprite_sales — Scrapfly-based weekly scrape of ShopRite circular sales
**Status:** Draft for initial build with Claude Code
**Infra discovery:** see `docs/existing-infrastructure.md` (2026-09-14) for what already exists in GCP and in this repo before Phase 1 work starts — summarized inline below where it changes the plan.

---

## 1. Vision

Value Plate helps working families spend less on groceries by closing the loop that flyer apps like Flipp leave open:

> **What's on sale this week → what can I cook with it → here's my list and here's what I saved.**

Flipp aggregates flyers and stops there. Value Plate turns the weekly sale into a meal plan, a shopping list, and a running savings total. The product's emotional core is the savings tracker: "You saved $23 this week, $412 this year."

### Target user
A busy parent planning a week of meals on a budget. They shop primarily at one store (ShopRite for launch), have limited time, and want the app to do the thinking: surface real deals, suggest dinners built around them, and produce one consolidated list.

### Non-goals (for now)
- Multi-store price comparison (phase 5 — requires cross-retailer product matching)
- Coupons/loyalty card integration
- Native mobile apps (responsive web first; PWA acceptable)
- Delivery/pickup ordering integration

---

## 2. Feature scope by phase

Each phase is a vertical slice that ships something usable.

### Phase 1 — Ingest + Deals Browser
- Ingestion job: pull shoprite_sales output **from Firestore** (`grocery_sales`/`stores` collections — where the existing Cloud Run Job already writes it, see infra doc §1/§3) → normalize → load into a **new Cloud SQL Postgres instance** (schema in §3; no Postgres instance exists yet, none of the checked-in migrations are wired to one).
- Fix the existing weekly trigger before relying on it: `shoprite-weekly-trigger` (Cloud Scheduler) currently points at a deleted Cloud Run service and has been failing since 2026-01-13 — repoint it at the existing `shoprite-weekly-scraper` Cloud Run Job.
- Deals page: browse this week's sale items, grouped by category, with search and category filters.
- Item cards show: name, brand, size, sale price, regular price (if available), % off, valid dates.
- **First task before any of this:** a data-profiling script that runs against the **existing Firestore `grocery_sales` data** (2,975 products across 280 stores, last populated 2026-01-13 — stale but real, no need to wait on a fresh scrape to start this) and reports: field completeness, name/size format variance, price parsing failures, category coverage. This determines how much normalization work phases 2–4 need. Note from a 2-document spot check: `price_per_unit`/`unit`/`external_id` were null on some rows, and neither sample had a `regular_price`-style field — worth confirming at scale, but if it holds, the open question in §7 about regular vs. sale-only pricing is answered: sale price only, no regular price from this source today.

### Phase 2 — Honest Comparison
- Unit-price normalization: parse sizes into canonical units and compute $/lb, $/oz, $/count. Display unit price on every card.
- Sort by unit price within category.
- Price history: retain past weeks' sale rows; badge items as "best price in N weeks" once history accumulates.
- Better search (typo tolerance, synonyms: "soda"/"pop", "ground beef"/"hamburger").

### Phase 3 — Deal-Aware Recipes
- Recipe library with **structured ingredients** (references to product categories + quantities, not free text — see §4).
- Each recipe shows: estimated cost per serving this week, and "N of M ingredients on sale."
- Recipes ranked/filterable by % on sale.
- Claude API integration (optional but high-value): parse pasted recipe text into structured ingredients; generate budget recipe suggestions from this week's top sale items.

### Phase 4 — Meal Planner + Savings
- Weekly plan builder: pick recipes (and standalone items), assign to days.
- Auto-generated consolidated shopping list, deduped across recipes, with quantities.
- Estimated basket total + estimated savings vs. regular prices.
- Savings tracker: per-week and cumulative totals per user.
- Accounts (email magic link or OAuth), saved plans, pantry-staples exclusion list ("I already have olive oil").
- Weekly email: "Your meal plan ideas for this week's ShopRite sale."

### Phase 5 — Multi-Store (future)
- Additional store scrapers (same Scrapfly pattern as shoprite_sales).
- Cross-retailer product matching against the canonical product table (embedding similarity + brand/size rules + human review queue).
- "Split your trip" and side-by-side store comparison.

---

## 3. Data model (Postgres)

The canonical schema is the most important early decision. Sale data is time-ranged; products are canonical and store-agnostic so phase 5 is a matching problem, not a rewrite.

```sql
-- Canonical, store-agnostic product identity
CREATE TABLE products (
  id            BIGSERIAL PRIMARY KEY,
  name          TEXT NOT NULL,          -- normalized display name
  brand         TEXT,
  category_id   BIGINT REFERENCES categories(id),
  size_value    NUMERIC,                -- 16
  size_unit     TEXT,                   -- 'oz', 'lb', 'ct', 'fl_oz', 'g', 'ml'
  unit_class    TEXT,                   -- 'weight' | 'volume' | 'count'
  search_text   TSVECTOR,               -- for full-text search
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE categories (
  id            BIGSERIAL PRIMARY KEY,
  name          TEXT NOT NULL,          -- 'Meat & Poultry', 'Dairy', ...
  parent_id     BIGINT REFERENCES categories(id),
  slug          TEXT UNIQUE
);

CREATE TABLE stores (
  id            BIGSERIAL PRIMARY KEY,
  name          TEXT NOT NULL,          -- 'ShopRite'
  location      TEXT,                   -- optional store-level granularity later
  scraper_key   TEXT                    -- links to ingestion source
);

-- Raw scrape rows, kept verbatim for reprocessing when normalization improves
CREATE TABLE raw_sale_items (
  id            BIGSERIAL PRIMARY KEY,
  store_id      BIGINT REFERENCES stores(id),
  scrape_batch  TEXT NOT NULL,          -- e.g. '2026-W37'
  payload       JSONB NOT NULL,
  scraped_at    TIMESTAMPTZ,
  processed     BOOLEAN DEFAULT FALSE
);

-- Time-ranged sale prices; history accumulates week over week
CREATE TABLE sale_prices (
  id            BIGSERIAL PRIMARY KEY,
  product_id    BIGINT REFERENCES products(id),
  store_id      BIGINT REFERENCES stores(id),
  raw_item_id   BIGINT REFERENCES raw_sale_items(id),
  sale_price    NUMERIC NOT NULL,
  regular_price NUMERIC,
  deal_type     TEXT,                   -- 'simple' | 'multi_buy' | 'bogo' | 'per_lb'
  deal_qty      INT,                    -- for '2/$5' style deals
  unit_price    NUMERIC,                -- computed: normalized $/oz, $/lb, $/ct
  valid_from    DATE NOT NULL,
  valid_to      DATE NOT NULL,
  UNIQUE (product_id, store_id, valid_from)
);

CREATE TABLE recipes (
  id            BIGSERIAL PRIMARY KEY,
  title         TEXT NOT NULL,
  slug          TEXT UNIQUE,
  servings      INT NOT NULL,
  instructions  TEXT,                   -- markdown
  tags          TEXT[],                 -- 'weeknight', 'slow-cooker', 'kid-friendly'
  created_at    TIMESTAMPTZ DEFAULT now()
);

-- Structured ingredients: category reference, not free text
CREATE TABLE recipe_ingredients (
  id            BIGSERIAL PRIMARY KEY,
  recipe_id     BIGINT REFERENCES recipes(id),
  category_id   BIGINT REFERENCES categories(id),  -- what to match sales against
  descriptor    TEXT,                   -- 'boneless chicken thighs'
  quantity      NUMERIC,
  quantity_unit TEXT,                   -- 'lb', 'oz', 'cup', 'tbsp', 'ct'
  optional      BOOLEAN DEFAULT FALSE,
  pantry_staple BOOLEAN DEFAULT FALSE   -- excluded from cost by default
);

CREATE TABLE users (
  id            BIGSERIAL PRIMARY KEY,
  email         TEXT UNIQUE NOT NULL,
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE meal_plans (
  id            BIGSERIAL PRIMARY KEY,
  user_id       BIGINT REFERENCES users(id),
  week_start    DATE NOT NULL,
  UNIQUE (user_id, week_start)
);

CREATE TABLE meal_plan_entries (
  id            BIGSERIAL PRIMARY KEY,
  meal_plan_id  BIGINT REFERENCES meal_plans(id),
  recipe_id     BIGINT REFERENCES recipes(id),
  day_of_week   INT,                    -- 0–6, nullable for "sometime this week"
  servings_override INT
);

CREATE TABLE savings_ledger (
  id            BIGSERIAL PRIMARY KEY,
  user_id       BIGINT REFERENCES users(id),
  meal_plan_id  BIGINT REFERENCES meal_plans(id),
  week_start    DATE NOT NULL,
  est_total     NUMERIC,
  est_savings   NUMERIC,
  confirmed     BOOLEAN DEFAULT FALSE   -- user can confirm "I shopped this"
);
```

### Ingestion pipeline (shoprite_sales → Postgres)
1. Weekly Cloud Scheduler job (`shoprite-weekly-trigger`) triggers the existing `shoprite-weekly-scraper` Cloud Run Job (Scrapfly-based) → output lands in **Firestore** (`grocery_sales`, `stores`, `metadata/summary` collections), not a flat file. *(This trigger is currently broken — see infra doc §2 — fix the scheduler target before depending on it running automatically.)*
2. Loader reads documents from Firestore `grocery_sales` (paginated) and writes every row verbatim to `raw_sale_items.payload` (never lose the original); `stores` collection seeds/updates the `stores` table directly (280 real ShopRite locations already scraped — no need to re-derive these).
3. Normalizer per row:
   - Parse name → brand, product name, size (`size_value`, `size_unit`).
   - Parse price → `sale_price`, `deal_type`, `deal_qty` (handle "2/$5", "BOGO", "$2.99/lb").
   - Match or create `products` row (exact match on normalized name+brand+size first; fuzzy later).
   - Compute `unit_price`; insert `sale_prices` row with validity dates.
   - Rows that fail parsing → flagged for a review report, not silently dropped.
4. Because raw rows are retained, the normalizer can be re-run over history whenever parsing improves.

---

## 4. Key algorithms

**Unit-price normalization.** Convert all sizes within a `unit_class` to a base unit (oz for weight, fl oz for volume, each for count) and compute price per base unit. Multi-buy deals use effective per-item price (`2/$5` → `$2.50`). Display as the familiar shelf-tag form ($/lb for meat, $/oz for packaged goods).

**Recipe sale-matching.** For each `recipe_ingredient`, find current `sale_prices` rows whose product's `category_id` matches (or is a descendant of) the ingredient's category, optionally filtered by descriptor keywords. Recipe "deal score" = share of non-pantry-staple ingredients with at least one active sale match, weighted by ingredient cost share.

**Estimated cost per serving.** Sum ingredient costs using: matched sale price if on sale, else category median regular price from history, else a maintained fallback price table. Divide by servings. Always label as an estimate.

**Savings math.** `est_savings = Σ (regular_price − sale_price) × qty` over list items with a known regular price. Where regular price is missing, use the item's non-sale median from price history once available; otherwise exclude from savings (never inflate the number — trust is the product).

---

## 5. Tech stack

- **Frontend:** Next.js (App Router), TypeScript, Tailwind CSS. Server components for deals/recipe pages (SEO matters — "shoprite sale this week" is organic traffic), client components for planner interactivity. **Open question:** the repo's current `frontend/` is Vite + React + Apollo/GraphQL, not Next.js — and there's a separate, already-deployed Next.js SSR app ("Price Pilot", Firebase App Hosting) unrelated to this repo's code. Decide before Phase 1's frontend task whether to migrate the in-repo frontend to Next.js, keep Vite, or adopt the already-deployed Next.js app as the real frontend.
- **API:** REST or tRPC endpoints exposed by the valueplate services; frontend never queries Postgres directly.
- **DB:** Postgres, **new Cloud SQL for Postgres instance** in the existing GCP project (`studio-2558023820-f94a5`) — no Postgres instance currently exists there to reuse (Cloud SQL Admin API has never been enabled on that project).
- **Jobs:** weekly scrape + ingest as a scheduled job — **reuse** the existing `shoprite-weekly-trigger` Cloud Scheduler job and `shoprite-weekly-scraper` Cloud Run Job rather than building new scrape infra; the scheduler just needs its target fixed (see §3) and the loader (new) needs to read from Firestore instead of a flat-file drop.
- **AI:** Claude API for recipe-text → structured ingredients, and for "suggest 5 dinners from this week's sale" generation. Keep behind a service so prompts/models can change without touching the frontend.
- **Email:** Resend or similar for the weekly digest (phase 4).

### Core API surface (phase 1–2)
```
GET /api/deals?week=2026-W37&category=meat&sort=unit_price&q=chicken
GET /api/deals/:productId/history
GET /api/categories
GET /api/recipes?sort=deal_score
GET /api/recipes/:slug
POST /api/plans            (phase 4)
GET  /api/plans/:week/list (phase 4)
```

---

## 6. Design notes

- Mobile-first: primary use is a phone in a kitchen or a store aisle.
- Deals page is the front door — fast, scannable cards, obvious % off, unit price always visible.
- Savings framing everywhere: green savings badges, weekly total in the header once signed in.
- Warm, practical tone. No coupon-site clutter, no ads at launch.
- Accessibility: real buttons, adequate contrast on price badges, works without JS for browse pages.

---

## 7. Immediate task order for Claude Code

0. **Fix the scheduler.** Repoint `shoprite-weekly-trigger` (Cloud Scheduler, us-central1) at the existing `shoprite-weekly-scraper` Cloud Run Job (us-east1) — it currently targets a deleted Cloud Run service and has been failing silently since 2026-01-13. Cheap fix, unblocks everything downstream from ever getting fresh data again.
1. **Profile the data.** Script against the existing Firestore `grocery_sales` collection (2,975 products, 280 stores, last populated 2026-01-13 — stale but sufficient to start) that reports field completeness, name/size parse rate, price format inventory, category coverage. Everything downstream depends on this; don't wait on task 0's fixed schedule to actually fire before starting this.
2. Provision a **new Cloud SQL for Postgres instance** (none exists in the GCP project today) and stand up the §3 schema + migration tooling. Retire or explicitly ignore the three inconsistent legacy schemas already in the repo (`devops/migrations/init.sql`, `001_users.sql`/`002_user_profiles.sql`, and `auth-service/database/db.go`'s inline `createTables()`) rather than trying to reconcile them with §3.
3. Build loader (Firestore `grocery_sales`/`stores` → `raw_sale_items`/`stores`) and normalizer v1 (target: ≥90% of rows parsed cleanly; report the rest).
4. Frontend app skeleton + deals browse page against real data — resolve the Next.js-vs-Vite open question (§5) first; don't build this on top of the unrelated already-deployed Next.js app without a deliberate decision to do so.
5. Unit-price computation + sort/filter/search.
6. Then proceed through phases 3–4 as vertical slices.

### Open questions to resolve while building
- What exactly does shoprite_sales output per item today (fields, formats, category labels)? → mostly answered by the infra discovery (`docs/existing-infrastructure.md`) via a 2-doc Firestore sample; task 1 confirms at scale.
- Does the scrape carry regular prices, or sale prices only? Savings math depends on this — the Firestore sample suggests sale-price-only; confirm in task 1.
- Store-level vs. chain-level pricing: are ShopRite circulars regional? The existing `stores` Firestore collection already has 280 individually-addressed ShopRite locations (not one chain-level entry), suggesting pricing may already be store-level in the scrape — check during task 1 whether `grocery_sales.price` varies by `store_id` for the same product.
- Recipe seed content: start with ~30–50 hand-curated family-friendly recipes before generating more.
- What should happen to the already-deployed "Price Pilot" Cloud Run app (`price-pilot-service` + Next.js SSR frontend)? It's unrelated to this repo's current code — retire it, or treat it as the real frontend/API and adjust the plan accordingly?
