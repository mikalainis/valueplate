# Value Plate Deployment & Operations Guide

This document records the current live infrastructure, ongoing custom domain rollout, deferred automation, and future roadmap for Value Plate (`valueplate.us`).

---

## 1. Current Live Status

### A. Backend (`plan-engine`)
- **Platform:** Google Cloud Run (Fully Managed)
- **Region:** `us-central1`
- **Service Name:** `plan-engine`
- **Live Service URL:** `https://plan-engine-1061535441532.us-central1.run.app`
- **Access:** Public (`roles/run.invoker` granted to `allUsers`)
- **Key Features:**
  - `GET /health` returns `{ "status": "healthy", "service": "plan-engine" }`
  - `GET /api/deals` queries Firestore `sales_v2` (700+ active items)
  - `GET /api/stores` queries Firestore `stores` (270+ active stores)
  - `POST /api/stores/request` logs store interest with strict validation (required fields, string lengths, US ZIP regex, forbidden extras, and 2KB body cap)
  - FastAPI interactive docs (`/docs`, `/redoc`, `/openapi.json`) disabled in production (enabled only if `ENV=dev`)
  - Redis made optional (no Memorystore instance needed)

### B. Frontend & Hosting
- **Platform:** Firebase Hosting
- **Project:** `studio-2558023820-f94a5`
- **Default URL:** `https://studio-2558023820-f94a5.web.app` (also `https://studio-2558023820-f94a5.firebaseapp.com`)
- **Build Output:** Static React/Vite SPA generated in `frontend/dist`
- **Routing & Cache Control (`firebase.json`):**
  - `/api/**` -> Proxied directly to Cloud Run service `plan-engine` (`us-central1`)
  - `**` -> Rewritten to `/index.html` (SPA client routing)
  - `Cache-Control: no-cache, no-store, must-revalidate` on HTML routes (`/`, `/index.html`, SPA routes)
  - `Cache-Control: public, max-age=31536000, immutable` on hashed assets in `/assets/**`

### C. Database Security
- **Platform:** Cloud Firestore `(default)` in `us-central1`
- **Security Rules (`firestore.rules`):**
  - Completely denies direct client reads and writes (`allow read, write: if false;`)
  - All data access is mediated through `plan-engine` using the Google Cloud Admin SDK

---

## 2. In Progress: Custom Domain (`valueplate.us`)

- **Registrar:** GoDaddy
- **Apex Domain:** `valueplate.us`
  - DNS Record: `A` record `@` pointing to `199.36.158.100` (Firebase Hosting)
  - Status: Added at registrar; waiting on DNS propagation and SSL certificate issuance by Let's Encrypt / Google Trust Services via Firebase.
- **Subdomain:** `www.valueplate.us`
  - Target: Configured in Firebase Console to redirect to apex `valueplate.us`.

### Verification Commands:
```bash
# Check DNS propagation for Apex
dig A valueplate.us +short

# Check HTTP status & SSL
curl -I https://valueplate.us

# Check www redirection
curl -I https://www.valueplate.us
```

---

## 3. Deferred: Scraping Automation

Automatic circular scraping is deferred until the core web app launch is complete.

- **Current State:**
  - `shoprite-weekly-scraper` is deployed as a Cloud Run Job in `us-east1`.
  - Cloud Scheduler job `shoprite-weekly-trigger` in `us-central1` is currently **`PAUSED`**.
  - Secret `SCRAPFLY_API_KEY` version 2 is securely stored in Secret Manager.

### Steps to Re-enable Automation:
1. **Grant Secret Access:**
   ```bash
   gcloud secrets add-iam-policy-binding SCRAPFLY_API_KEY \
     --project="studio-2558023820-f94a5" \
     --member="serviceAccount:1061535441532-compute@developer.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor" \
     --account="pmikalainis@gmail.com"
   ```
2. **Update Job to Use Secret:**
   ```bash
   gcloud run jobs update shoprite-weekly-scraper \
     --region=us-east1 \
     --set-secrets=SCRAPFLY_API_KEY=SCRAPFLY_API_KEY:latest \
     --remove-env-vars=SCRAPFLY_API_KEY
   ```
3. **Grant Job Invocation Role:**
   ```bash
   gcloud run jobs add-iam-policy-binding shoprite-weekly-scraper \
     --region=us-east1 \
     --member="serviceAccount:1061535441532-compute@developer.gserviceaccount.com" \
     --role="roles/run.invoker" \
     --account="pmikalainis@gmail.com"
   ```
4. **Update & Unpause Scheduler:**
   ```bash
   gcloud scheduler jobs update http shoprite-weekly-trigger \
     --location=us-central1 \
     --schedule="0 6 * * 0" \
     --time-zone="America/New_York" \
     --uri="https://us-east1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/studio-2558023820-f94a5/jobs/shoprite-weekly-scraper:run" \
     --http-method="POST" \
     --oauth-service-account-email="1061535441532-compute@developer.gserviceaccount.com" \
     --oauth-token-scope="https://www.googleapis.com/auth/cloud-platform"

   gcloud scheduler jobs resume shoprite-weekly-trigger --location=us-central1
   ```

---

## 4. Planned Application Improvements

1. **Deal Sorting & Prioritization:**
   - Update `plan-engine/app/logic/deals_repository.py` to sort items so that actual discounts (`is_deal = True`) and highest percentage savings are prioritized at the top of results.
2. **Circular Expiration Filtering:**
   - Enhance the scraper to populate `valid_from` and `valid_to` timestamps in Firestore so expired items can be automatically filtered out from `/api/deals`.

---

## 5. Phase 6 — CI/CD Pipeline

**Recommendation:** GitHub Actions with **Workload Identity Federation (WIF)**.
- **Why WIF?** Eliminates downloadable, long-lived JSON service account keys. GitHub Actions assumes short-lived OIDC tokens directly federated with GCP IAM.
- **Workflow Scope (`.github/workflows/deploy.yml`):**
  - Trigger: `push` to `main` branch.
  - Step 1: Lint & build frontend (`npm run build`).
  - Step 2: Deploy Firebase Hosting (`firebase deploy --only hosting`).
  - Step 3: Authenticate via WIF and deploy `plan-engine` to Cloud Run (`gcloud run deploy plan-engine ...`).

---

## 6. Phase 7 — Pre-Launch Checklist

- [ ] Confirm HTTPS on `valueplate.us` and 301 redirect on `www.valueplate.us`.
- [ ] Create a Cloud Billing Budget alert in GCP Console (e.g., $10/month threshold).
- [ ] Replace default `vite.svg` with branded Value Plate favicon and app icons.
- [ ] Add Open Graph & Twitter meta tags (`og:title`, `og:description`, `og:image`).
- [ ] Add standard `robots.txt` and `sitemap.xml`.
- [ ] Implement a clean `/privacy` policy page.
- [ ] Implement an in-app 404 page for unmatched routes.

---

## 7. Future Cleanup (Requires User Confirmation First)

1. **Legacy Cloud Run Services:**
   - Retire `price-pilot-service` (`us-central1`) once confirmed obsolete.
   - Retire `ssrstudio2558023820f94a` (`us-east1` Next.js SSR service) now that Firebase Hosting serves the static SPA.
2. **Credential Rotation:**
   - Once GitHub Actions CI/CD with WIF is operational, revoke and delete any long-lived service account keys stored locally or in Codespace environment variables.
