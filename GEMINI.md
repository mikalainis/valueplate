# Value Plate

Grocery savings platform: weekly sale prices, price comparison, recipes, and meal plans,
aimed at helping working families save money. Similar in spirit to flipp.com.
Domain: valueplate.us

## Architecture
- Microservices on Google Cloud Platform (existing project; reuse it, don't create new ones)
- Existing databases and APIs already deployed on GCP
- Web frontend served via Firebase Hosting in front of Cloud Run
- ShopRite sale data scraped weekly via Scrapfly (separate repo: mikalainis/shoprite_sales)

## Rules
- Never commit secrets; use Secret Manager
- Reuse existing GCP services, databases, and secrets before creating new ones
- Ask before deleting resources, changing IAM, or anything that adds cost
- Work in feature branches; open PRs instead of pushing to main

## Commands
- Build: <fill in, e.g. npm run build>
- Local dev: <fill in>
- Deploy: <fill in once CI/CD is set up>
