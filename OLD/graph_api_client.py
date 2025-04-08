#!/usr/bin/env python3
"""
Graph API Client - Authorization Only

A simplified version that handles only the Microsoft Graph API authorization flow.
"""

import os
import json
import logging
import msal
from typing import Dict, Any, Optional
from flask import Flask, request, redirect, session
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('graph_api_client.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TokenCache:
    """Simple token cache implementation."""
    
    def __init__(self, cache_file: str = "token_cache.json"):
        self.cache_file = cache_file
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict[str, Any]:
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
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get token from cache."""
        return self.cache.get(key)
    
    def set(self, key: str, value: Dict[str, Any]) -> None:
        """Set token in cache."""
        self.cache[key] = value
        self._save_cache()

class GraphAPIClient:
    """Microsoft Graph API client focused on authorization."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Graph API client.
        
        Args:
            config: Configuration dictionary containing:
                - client_id: Azure AD application client ID
                - client_secret: Azure AD application client secret
                - tenant_id: Azure AD tenant ID
                - redirect_uri: Redirect URI for OAuth flow
                - scopes: List of API scopes
                - authority: Authority URL
        """
        self.config = config
        self.token_cache = TokenCache()
        self.app = Flask(__name__)
        self.app.secret_key = os.urandom(24)
        
        # Initialize MSAL client
        self.msal_app = msal.ConfidentialClientApplication(
            config["client_id"],
            authority=config["authority"],
            client_credential=config["client_secret"]
        )
        
        # Set up routes
        self.app.route('/')(self.index)
        self.app.route('/getToken')(self.get_token)
    
    def run(self, host: str = 'localhost', port: int = 5000) -> None:
        """Run the Flask application.
        
        Args:
            host: Host to run the application on
            port: Port to run the application on
        """
        self.app.run(host=host, port=port)
    
    def index(self) -> str:
        """Handle the index route."""
        # Check if we have a token
        token = self.token_cache.get('access_token')
        if token:
            return f"Already authenticated. Access token expires at: {token['expires_at']}"
        
        # Start the auth flow
        auth_url = self.msal_app.get_authorization_request_url(
            self.config["scopes"],
            redirect_uri=self.config["redirect_uri"]
        )
        return f'<a href="{auth_url}">Click here to authenticate</a>'
    
    def get_token(self) -> str:
        """Handle the OAuth callback and get the access token."""
        # Get the auth code from the request
        auth_code = request.args.get('code')
        if not auth_code:
            return "No authorization code received"
        
        try:
            # Acquire token by auth code
            logger.info("Acquiring token by auth code flow")
            result = self.msal_app.acquire_token_by_authorization_code(
                auth_code,
                scopes=self.config["scopes"],
                redirect_uri=self.config["redirect_uri"]
            )
            
            if "access_token" in result:
                # Store the token in cache
                self.token_cache.set('access_token', {
                    'token': result['access_token'],
                    'expires_at': result['expires_in'],
                    'refresh_token': result.get('refresh_token')
                })
                
                # Start the image fetcher
                logger.info("Authentication successful, starting image fetcher")
                from onenote_image_fetcher import OneNoteImageFetcher
                fetcher = OneNoteImageFetcher(self)
                
                # Start the image fetcher process
                fetcher.start()
                
                return "Authentication successful. Check onenote_image_fetcher.log for progress."
            else:
                error = result.get('error_description', 'Unknown error')
                logger.error(f"Token acquisition failed: {error}")
                return f"Authentication failed: {error}"
                
        except Exception as e:
            logger.error(f"Error in token acquisition: {str(e)}")
            return f"Error: {str(e)}"
    
    def ensure_valid_token(self) -> bool:
        """Ensure we have a valid access token.
        
        Returns:
            True if we have a valid token, False otherwise
        """
        token = self.token_cache.get('access_token')
        if not token:
            return False
        
        # Check if token is expired
        if token['expires_at'] <= 0:
            return False
        
        return True

def main():
    """Main function to run the authorization flow."""
    # Load environment variables
    load_dotenv()
    
    # Create configuration dictionary
    config = {
        "client_id": os.getenv("CLIENT_ID"),
        "client_secret": os.getenv("CLIENT_SECRET"),
        "tenant_id": os.getenv("TENANT_ID"),
        "redirect_uri": os.getenv("REDIRECT_URI"),
        "scopes": ["Notes.Read", "Notes.Read.All"],  # Only use valid OneNote scopes
        "authority": f"https://login.microsoftonline.com/{os.getenv('TENANT_ID')}"
    }
    
    # Initialize and run the client
    client = GraphAPIClient(config)
    client.run()

if __name__ == "__main__":
    main()