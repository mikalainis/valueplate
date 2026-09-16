# Existing Infrastructure — Discovery Notes

**Date:** 2026-09-14
**GCP project:** `studio-2558023820-f94a5` (project number `1061535441532`, display name "Price Pilot", Firebase-enabled, created 2026-01-01)

This document inventories what already exists — in the repo and in the live GCP project — before starting spec §7 build work. Everything below is read-only discovery; nothing in GCP was modified.

---

## 1. What's in the repo

The repo (`valueplate`) contains three services plus devops scaffolding. None of it is the app currently live in GCP (see §3) — more on that below.

| Path | Purpose | Stack | Deployed? |
|---|---|---|---|
| `auth-service/` | Auth + user profile + GraphQL gateway | Go, gqlgen (GraphQL), also a parallel Gin/GORM REST path | Not currently deployed anywhere |
| `plan-engine/` | Meal-plan optimizer, nutrition calc | Python, FastAPI | Not currently deployed anywhere |
| `frontend/` | User-facing web app | React + Vite (not Next.js) | Not currently deployed anywhere |
| `devops/` | Migrations, Redis seed script, devcontainer | SQL, Python | N/A |

### auth-service (Go)
- Two competing implementations coexist: a **gqlgen GraphQL** server (`graph/schema.graphqls`, `schema.resolvers.go`, wired up in `main.go`) and an unwired **Gin + GORM REST** handler set (`internal/handler/auth.go`, `profile_handler.go`, using `models.User` / `domain.UserProfile`). `main.go` only starts the GraphQL server — the Gin handlers aren't mounted anywhere.
- GraphQL schema exposes: `login`, `signup`, `items(search)`, `suggestedRecipes`, `salesReceipt(limit)` (stubbed, returns `[]`), `updatePreferences`, `savePlan`, `sendWeeklyPlan` (stubbed, `panic`s).
- Talks to Postgres directly via `database/sql` + `lib/pq` (`database/db.go`) and to Redis via `go-redis` (`database/redis.go`). Both connections are read from env vars (`DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `REDIS_ADDR`) — **no managed instance of either currently exists in this GCP project** (see §3).
- `internal/location/client.go` wraps Google Places/Geocoding for "find nearby stores by zip" — needs a Maps API key, not confirmed enabled/present.
- `database/createTables()` in `db.go` creates its own `users`/`user_preferences`/`items` schema at boot time, which **duplicates and drifts from** the checked-in SQL migrations (see below) — e.g. `db.go` uses `SERIAL` ids while `devops/migrations/001_users.sql` uses `UUID`. These two schema definitions are inconsistent with each other.
- `auth-service/database/shoprite_master_dump_20251211-042546.csv` — a **805-line static CSV** of ShopRite sale items (columns: `Store_ID, Store_Name, Store_Zip, Search_Term, SKU, Name, Brand, Price_Current, Price_Regular, Price_Label, Discount_End, Unit_Size, Unit_Type, Is_Keto, Is_Vegan, Is_GlutenFree, Image_URL`), dated 2025-12-11. This looks like a one-off manual export used for local dev/seeding, checked directly into git — **not a live pipeline**.

### plan-engine (Python/FastAPI)
- Single endpoint: `POST /generate-optimized-plan` — takes family members + store IDs, computes nutrition targets (`nutrition_calculator.py`, Harris-Benedict), and cross-references Redis keys shaped `sale:{store_id}:{item_name}` for sale prices. Recipe retrieval is **hardcoded/mocked** ("Mocking recipe retrieval for architectural flow").
- `devops/seed_redis.py` seeds exactly those `sale:{store_id}:{item_name}` keys with 4 hardcoded mock rows (Whole Foods/Kroger, not ShopRite) — dev-only fixture, not connected to the CSV or any real scrape.

### frontend (React + Vite)
- Uses Apollo Client + GraphQL — matches the Go gqlgen server, not a REST API.
- Components: `LocationPicker.tsx`, `RegisterFrom.tsx`, `Preferences.js`, `SavingsDashboard.tsx` — auth/profile/store-selection UI, no deals-browse or recipe UI yet.

### devops/migrations (SQL, order-numbered but not wired to a migration tool)
- `init.sql`: `users` (SERIAL id), `user_preferences` (store ids + vegan/keto flags), `items` (flat SKU/price/category table for the plan engine).
- `001_users.sql`: a **different** `users` table, UUID id, no zip/preferences columns.
- `002_user_profiles.sql`: `user_profiles` keyed by that UUID `users.id`, with JSONB `family_composition`, dietary restrictions, cached calorie target.
- These three files are not consistent with each other or with `db.go`'s inline schema — there is no single source of truth for the current Postgres schema, and no migration runner (no Flyway/golang-migrate/Alembic config found).
- None of this resembles spec §3's schema (`products`, `categories`, `sale_prices`, `recipes`, `recipe_ingredients`, `savings_ledger`, etc.) — it's a simpler, earlier data model built around a flat `items` table.

### GCP config in-repo
- No Terraform, no `app.yaml`, no `cloudbuild.yaml`, no `firebase.json`/`.firebaserc`/`apphosting.yaml`.
- Three plain `Dockerfile`s (`auth-service`, `plan-engine`, `frontend`) and a devcontainer config (`devops/.devcontainer/devcontainer.json`, just adds the Claude Code feature to a stock Node devcontainer image). No `docker-compose.yml` was found despite the README describing one.
- No `.env`/`.env.example` files anywhere.

---

## 2. Live GCP resources (project `studio-2558023820-f94a5`)

Read-only inventory via `gcloud`/`gsutil`/Firestore REST, run 2026-09-14.

**Databases**
- **Cloud SQL: none.** `sqladmin.googleapis.com` has never been enabled — no Postgres instance exists anywhere in this project.
- **Memorystore (Redis): none.** `redis.googleapis.com` disabled/unused.
- **BigQuery: enabled but empty.** `bq ls` returns no datasets.
- **Firestore: one database exists** — `(default)`, Native mode, `us-central1`, created 2026-01-01. This is the **only live database** in the project. Root collections:
  - `grocery_sales` — sale-item documents, ids like `SS_{store_id}_{external_id}`, fields `name, brand(missing on some), category, price, price_per_unit, unit, store_id, external_id, image_url`. This is where the **ShopRite scrape output actually lands**.
  - `stores` — 280 ShopRite store location docs (id, name, address, city, state, zip, phone, lastUpdated).
  - `metadata/summary` — one doc: `total_stores: 280, total_products: 2975, total_categories: 37, last_fetch: 2026-01-13T03:50:02Z`.

**Compute / hosting**
- **Cloud Run services:** `price-pilot-service` (us-central1, image `ssr-repo/price-pilot-service`, a backend API) and `ssrstudio2558023820f94a` (us-east1, Firebase-App-Hosting-managed Next.js SSR frontend, image `ssr-repo/ssr-frontend`, env `NEXT_PUBLIC_API_BASE_URL` → the service above). **This is a different, already-deployed app** ("Price Pilot", built via Firebase Studio) — it's a Next.js frontend, not the Vite frontend in this repo, and none of the Cloud Build history references this git repo (no linked source repo; builds are one-off `--source` deploys from mid-January 2026). Treat it as a separate/earlier prototype, not the thing spec §7 is building on top of.
- **Cloud Run jobs:** `shoprite-weekly-scraper` (us-east1) — a containerized scraper, 2Gi/1cpu, env var `SCRAPFLY_KEY` set **in plaintext** (not Secret Manager — flagging as a hygiene issue to fix, not urgent to rotate unless this doc becomes widely shared). Executed 26 times; **last execution 2026-01-13**, matching the Firestore `last_fetch` timestamp above.
- **Cloud Functions:** just the one auto-generated by Firebase App Hosting for the SSR frontend (`ssrstudio2558023820f94a`, us-east1) — not a separate function.
- **GCE:** none (`compute.googleapis.com` disabled).

**Scheduled jobs**
- **Cloud Scheduler `shoprite-weekly-trigger`** (us-central1, `0 1 * * 0` America/New_York, weekly Sunday). **This job is broken**: its HTTP target is `https://sunday-scraper-cpoxn6rt7a-uc.a.run.app/`, a Cloud Run *service* that no longer exists (superseded by the `shoprite-weekly-scraper` Cloud Run *job* in us-east1, which the scheduler was never repointed at). Last attempt (2026-09-13) failed with NOT_FOUND. **This is why Firestore data is 8 months stale** — the pipeline hasn't run since mid-January despite the job/infra otherwise being intact.

**Storage / registries**
- **Storage buckets:** only auto-created Cloud Functions/Cloud Build buckets (`gcf-v2-sources-*`, `gcf-v2-uploads-*`, `..._cloudbuild`). No bucket holds scrape output or app data.
- **Artifact Registry:** `grocery-repo` (us-central1, "Docker repository for GrocerySmart microservices" — holds one old `price-pilot-api` image from 2026-01-09, unused by any live service), `ssr-repo` (both regions, backs the live Cloud Run services above), plus auto-created `cloud-run-source-deploy` and `gcf-artifacts` repos.

**Identity**
- `identitytoolkit.googleapis.com` (Firebase Auth) is enabled on the project, but nothing in the repo's `auth-service` uses it — the Go service rolls its own bcrypt+JWT auth instead. Worth deciding which auth strategy to standardize on before Phase 4 (spec §2 calls for "email magic link or OAuth").

---

## 3. Answers to the two specific questions

**(a) Where does the shoprite_sales scraper output currently land?**
Firestore, collections `grocery_sales` + `stores` + `metadata/summary`, written by the `shoprite-weekly-scraper` Cloud Run Job. It is **not** landing anywhere the repo code reads from — `auth-service`'s checked-in CSV is a stale, disconnected manual export, and `plan-engine`/`devops/seed_redis.py` only ever see hardcoded mock data. The pipeline itself is currently broken (scheduler points at a deleted service) and hasn't run since 2026-01-13.

**(b) Which existing database should hold the spec §3 schema?**
None can, as-is. The only live database is Firestore, which is a document store — spec §3's schema is explicitly relational (FK joins between `products`/`categories`/`sale_prices`, category-based recipe-ingredient matching, unit-price sorting/history queries). Forcing that model into Firestore would fight the data model spec §4's algorithms depend on. There is no existing Postgres instance to reuse (Cloud SQL was never provisioned) — **a new Cloud SQL for Postgres instance is needed**, but the *scraper and scheduling infrastructure* (Cloud Run Job + Artifact Registry + Cloud Scheduler) already exists and just needs its schedule target fixed and a loader added that reads from Firestore instead of assuming a fresh flat-file drop.

---

## 4. Notable risks/discrepancies to flag

1. Scheduler → deleted service (broken pipeline, 8 months stale) — needs fixing regardless of what else changes.
2. `SCRAPFLY_KEY` stored as plaintext env var on the Cloud Run job — recommend Secret Manager when that job is next touched.
3. Three inconsistent Postgres schema definitions in-repo (`init.sql`, `001_users.sql`+`002_user_profiles.sql`, and `db.go`'s inline `createTables()`) — none matches spec §3. Worth deciding whether to keep any of this user/auth schema or start clean.
4. The live Cloud Run app ("Price Pilot" / `price-pilot-service` + Next.js SSR frontend) is unrelated to this repo's current code and isn't backed by a source-linked build — confirm with the user whether it should be retired, reused, or ignored before Phase 1 work assumes a clean slate.
5. `auth-service` has two unwired auth implementations (GraphQL resolvers vs. Gin/GORM handlers) — only the GraphQL path is actually served.
