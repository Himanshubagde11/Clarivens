"""
Storage factory for Clarivens.
Dynamically provides the storage provider based on environment configuration.
"""
from backend.config import settings
from backend.storage.local_storage import LocalStorageProvider
from backend.storage.azure_blob_storage import AzureBlobStorageProvider

_provider_instance = None

def get_storage_provider():
    global _provider_instance
    if _provider_instance is None:
        if settings.storage_backend == "azure" and settings.azure_storage_connection_string:
            _provider_instance = AzureBlobStorageProvider(
                connection_string=settings.azure_storage_connection_string,
                container_name=settings.azure_storage_container
            )
        else:
            _provider_instance = LocalStorageProvider()
    return _provider_instance
