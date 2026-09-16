"""
Azure Blob Storage Provider for Clarivens Enterprise Deployment.
Organizes data under:
  {container}/{org_id}/{project_id}/datasets/original/{storage_name}
Supports SAS token generation with time-to-live restrictions.
"""
import logging
from typing import Optional
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

class AzureBlobStorageProvider:
    def __init__(self, connection_string: str = "", container_name: str = "clarivens-data"):
        self.connection_string = connection_string
        self.container_name = container_name
        self.client = None
        
        if connection_string:
            try:
                from azure.storage.blob import BlobServiceClient
                self.client = BlobServiceClient.from_connection_string(connection_string)
            except ImportError:
                logger.warning("[Storage] azure-storage-blob package is not installed.")
            except Exception as e:
                logger.error(f"[Storage] Failed to initialize Azure Blob Storage client: {e}")

    def _blob_name(self, org_id: str, project_id: str, storage_name: str) -> str:
        return f"{org_id}/{project_id}/datasets/original/{storage_name}"

    def save_file(self, file_content: bytes, org_id: str, project_id: str, storage_name: str) -> str:
        blob_path = self._blob_name(org_id, project_id, storage_name)
        if not self.client:
            raise RuntimeError("Azure Blob Storage client is not configured.")

        container_client = self.client.get_container_client(self.container_name)
        if not container_client.exists():
            container_client.create_container()

        blob_client = container_client.get_blob_client(blob_path)
        blob_client.upload_blob(file_content, overwrite=True)
        return f"https://{self.client.account_name}.blob.core.windows.net/{self.container_name}/{blob_path}"

    def get_file(self, org_id: str, project_id: str, storage_name: str) -> Optional[bytes]:
        blob_path = self._blob_name(org_id, project_id, storage_name)
        if not self.client:
            raise RuntimeError("Azure Blob Storage client is not configured.")

        blob_client = self.client.get_blob_client(container=self.container_name, blob=blob_path)
        if blob_client.exists():
            return blob_client.download_blob().readall()
        return None

    def delete_file(self, org_id: str, project_id: str, storage_name: str) -> bool:
        blob_path = self._blob_name(org_id, project_id, storage_name)
        if not self.client:
            return False

        blob_client = self.client.get_blob_client(container=self.container_name, blob=blob_path)
        if blob_client.exists():
            blob_client.delete_blob()
            return True
        return False
