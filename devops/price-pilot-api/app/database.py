import logging
import os
from google.cloud import firestore

# Configure Logging
logger = logging.getLogger("uvicorn")

class FirestoreClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            logger.info("Initializing Firestore Client...")
            try:
                # In GKE/Cloud Run, this uses the attached Service Account automatically.
                # Locally, it looks for GOOGLE_APPLICATION_CREDENTIALS env var.
                cls._instance = firestore.Client()
                logger.info("Firestore Client Connected.")
            except Exception as e:
                logger.error(f"Failed to connect to Firestore: {e}")
                raise e
        return cls._instance

def get_db():
    """Dependency injection helper."""
    return FirestoreClient()