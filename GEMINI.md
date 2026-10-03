# Value Plate

Grocery savings platform: weekly sale prices, price comparison, recipes, and meal plans,
aimed at helping working families save money. Similar in spirit to flipp.com.
Domain: `valueplate.us`

## Architecture
- **GCP Project:** `studio-2558023820-f94a5` (Project Number: `1061535441532`)
- **Frontend:** Static React 18 + Vite SPA served directly from `frontend/dist` via **Firebase Hosting**.
- **Backend API:** `plan-engine` (FastAPI) deployed as Cloud Run service `plan-engine` in **`us-central1`**.
- **Routing (`firebase.json`):** `/api/**` rewrites to Cloud Run service `plan-engine`; all other routes rewrite to `/index.html` (SPA fallback). Hashed assets in `/assets/**` use immutable 1-year caching; HTML routes use `no-cache`.
- **Database:** Firestore `(default)` in **`us-central1`** (native mode). Client access is completely disabled via deny-all `firestore.rules`. `plan-engine` queries collections (`sales_v2`, `stores`, `store_requests`) using the Admin SDK.
- **Scraper:** Cloud Run Job `shoprite-weekly-scraper` in **`us-east1`** (automation currently deferred).

## Permissions & IAM Note
- The dev service account (`studio-2558023820-f94a5@appspot.gserviceaccount.com`) has `roles/editor` only.
- It cannot execute IAM mutations (`setIamPolicy`). Any IAM policy binding (Secret Manager accessor, Cloud Run invoker, etc.) must be run by the project owner using `--account="pmikalainis@gmail.com"`. Never attempt them directly; output the command for the owner.

## Rules
- Never commit secrets; use Secret Manager (`SCRAPFLY_API_KEY`)
- Reuse existing GCP services, databases, and secrets before creating new ones
- Ask before deleting resources, changing IAM, or anything that adds cost
- Work in feature branches; open PRs instead of pushing to main
- Detailed operational notes and next steps are in `docs/DEPLOYMENT.md`

## Commands
- **Frontend build:** `npm --prefix frontend run build`
- **Frontend local dev:** `npm --prefix frontend run dev`
- **Plan-engine local dev:** `cd plan-engine && uvicorn app.main:app --port 8000 --reload`
- **Full local stack:** `./scripts/dev-start.sh`
- **Deploy backend (Cloud Run):**
  `gcloud run deploy plan-engine --source plan-engine --region us-central1 --allow-unauthenticated --min-instances 0 --max-instances 5 --set-env-vars GOOGLE_CLOUD_PROJECT=studio-2558023820-f94a5`
- **Deploy frontend (Firebase Hosting):**
  `npm --prefix frontend run build && firebase deploy --only hosting`
- **Deploy Firestore security rules:**
  `firebase deploy --only firestore:rules`
