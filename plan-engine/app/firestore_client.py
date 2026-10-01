import json
import os
from functools import lru_cache
from typing import Optional

from google.auth.exceptions import DefaultCredentialsError, GoogleAuthError
from google.cloud import firestore


class FirestoreCredentialsError(Exception):
    """Raised when Google Cloud / Firestore credentials are missing or invalid."""
    pass


@lru_cache
def get_firestore_client() -> firestore.Client:
    project = os.getenv("GOOGLE_CLOUD_PROJECT")

    # Cloud Run/local dev use ambient Application Default Credentials. Vercel
    # has none, so it authenticates via a service account key pasted into an
    # env var instead (see devops/plan-engine-vercel/README.md).
    creds_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if creds_json and creds_json.strip():
        try:
            from google.oauth2 import service_account

            info = json.loads(creds_json.strip())
            project_id = project or info.get("project_id")
            credentials = service_account.Credentials.from_service_account_info(info)
            return firestore.Client(project=project_id, credentials=credentials)
        except Exception as exc:
            raise FirestoreCredentialsError(
                f"Failed to initialize Firestore client from GOOGLE_SERVICE_ACCOUNT_JSON: {exc}"
            ) from exc

    try:
        return firestore.Client(project=project)
    except (DefaultCredentialsError, GoogleAuthError) as exc:
        raise FirestoreCredentialsError(
            "Google Cloud credentials not found. Set GOOGLE_SERVICE_ACCOUNT_JSON or configure Application Default Credentials."
        ) from exc

