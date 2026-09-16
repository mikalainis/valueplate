import os
from functools import lru_cache

from google.cloud import firestore


@lru_cache
def get_firestore_client() -> firestore.Client:
    return firestore.Client(project=os.getenv("GOOGLE_CLOUD_PROJECT"))
