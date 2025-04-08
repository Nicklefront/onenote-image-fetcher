import json
import os
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class TokenCache:
    """Handles token storage and retrieval."""
    
    def __init__(self, cache_file: str = "token_cache.json"):
        self.cache_file = cache_file
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict:
        """Load token cache from file."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading token cache: {e}")
        return {}
    
    def _save_cache(self) -> None:
        """Save token cache to file."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f)
        except Exception as e:
            logger.error(f"Error saving token cache: {e}")
    
    def get_token(self) -> Optional[Dict]:
        """Get the stored token."""
        return self.cache.get('access_token')
    
    def set_token(self, token: Dict) -> None:
        """Set the token in cache."""
        self.cache['access_token'] = token
        self._save_cache()
    
    def clear(self) -> None:
        """Clear the token cache."""
        self.cache = {}
        self._save_cache() 