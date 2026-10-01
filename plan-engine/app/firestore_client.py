import json
import os
from functools import lru_cache

from google.cloud import firestore


@lru_cache
def get_firestore_client() -> firestore.Client:
    project = os.getenv("GOOGLE_CLOUD_PROJECT")

    # Cloud Run/local dev use ambient Application Default Credentials. Vercel
    # has none, so it authenticates via a service account key pasted into an
    # env var instead (see devops/plan-engine-vercel/README.md).
    creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if creds_json:
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_info(json.loads(creds_json))
        return firestore.Client(project=project, credentials=credentials)

    return firestore.Client(project=project)
