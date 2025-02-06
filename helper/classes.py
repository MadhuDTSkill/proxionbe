import os
import json
import threading
from typing import Any, Optional
from cryptography.fernet import Fernet
from helper.exceptions import SmoothException


class EncryptionHelper:
    
    def __init__(self, key: str = None):
        if key is None:
            key = os.environ.get('FIELD_ENCRYPTION_KEY')

        if not key:
            raise ValueError("Encryption key is missing! Set FIELD_ENCRYPTION_KEY in environment variables.")

        self.key = key.encode() if isinstance(key, str) else key
        self.fernet = Fernet(self.key)

    def encrypt(self, data):
        if isinstance(data, str):
            data = data.encode('utf-8')
        return self.fernet.encrypt(data).decode('utf-8')

    def decrypt(self, data):
        return self.fernet.decrypt(data.encode('utf-8')).decode('utf-8')


class ContextEncryptStorage:
    """A utility class for managing encrypted request-related context variables using threading.local."""
    
    def __init__(self):
        self._storage = threading.local()
        self.encryption_helper = EncryptionHelper()
        self._initialize_storage()

    def _initialize_storage(self):
        """Initialize thread-local storage if not already set."""
        if not hasattr(self._storage, "data"):
            self._storage.data = {}

    def _encrypt(self, value: Any) -> str:
        """Helper method to encrypt a value."""
        return self.encryption_helper.encrypt(value)

    def _decrypt(self, encrypted_value: Optional[str]) -> Any:
        """Helper method to decrypt a value."""
        if encrypted_value is None:
            return None
        return self.encryption_helper.decrypt(encrypted_value)

    def store(self, key: str, value: Any):
        """Store an encrypted value in thread-local storage."""
        self._initialize_storage()
        self._storage.data[key] = self._encrypt(value)

    def retrieve(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """Retrieve and decrypt a value from thread-local storage."""
        self._initialize_storage()
        return self._decrypt(self._storage.data.get(key, default))

    def set_current_user_id(self, user_id: str):
        """Set the current user ID."""
        self.store("current_user_id", user_id)

    def get_current_user_id(self, default: Optional[str] = None) -> Optional[str]:
        """Get the current user ID."""
        return self.retrieve("current_user_id", default)

    def set_current_consumer_object(self, consumer_object):
        """Set the current consumer object."""
        self._initialize_storage()
        self._storage.data['current_consumer_object'] = consumer_object
        
    def get_current_consumer_object(self, default: Optional[Any] = None) -> Optional[Any]:
        """Get the current consumer object."""
        return self._storage.data.get('current_consumer_object', default)
    
    def show(self):
        """Print the current thread-local storage."""
        self._initialize_storage()
        print(self._storage.data)
    
    def clear(self):
        """Reset the thread-local storage."""
        self._storage.data = {}
        
      