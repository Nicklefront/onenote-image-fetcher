import os
import logging
from typing import Dict, Any, Optional, List
import msal
from flask import Flask, request, redirect, Response, stream_with_context
from dotenv import load_dotenv
import webbrowser
import threading
import requests
import time
import json

from ..utils.token_cache import TokenCache
from ..utils.self_healer import SelfHealer

logger = logging.getLogger(__name__)

def load_config() -> Dict[str, Any]:
    """Load configuration from environment variables."""
    load_dotenv()
    
    config = {
        "client_id": os.getenv("CLIENT_ID", "your_client_id"),
        "client_secret": os.getenv("CLIENT_SECRET", "your_client_secret"),
        "tenant_id": os.getenv("TENANT_ID", "your_tenant_id"),
        "redirect_uri": os.getenv("REDIRECT_URI", "http://localhost:5000/getToken"),
        "scopes": ["Notes.Read", "Notes.Read.All"],
        "openai_api_key": os.getenv("OPENAI_API_KEY")
    }
    
    # Set authority based on tenant_id
    config["authority"] = f"https://login.microsoftonline.com/{config['tenant_id']}"
    
    # Validate OpenAI API key
    if not config["openai_api_key"]:
        logger.warning("OpenAI API key not found. Self-healing features will be limited.")
    
    return config

class GraphAPIClient:
    """Handles Microsoft Graph API authentication and requests."""
    
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
        self.progress_messages = []
        
        # Initialize MSAL client
        self.msal_app = msal.ConfidentialClientApplication(
            config["client_id"],
            authority=config["authority"],
            client_credential=config["client_secret"]
        )
        
        # Initialize self-healer if OpenAI API key is available
        if config["openai_api_key"]:
            self.self_healer = SelfHealer(config["openai_api_key"])
        else:
            self.self_healer = None
            logger.warning("Self-healing disabled: OpenAI API key not configured")
        
        # Set up routes
        self.app.route('/')(self.index)
        self.app.route('/getToken')(self.get_token)
        self.app.route('/progress')(self.progress)
        self.app.route('/handle_option')(self.handle_option)
    
    def add_progress(self, message: str) -> None:
        """Add a progress message."""
        self.progress_messages.append({
            'timestamp': time.time(),
            'message': message
        })
        logger.info(message)
    
    def add_user_prompt(self, message: str, options: List[str]) -> None:
        """Add a user prompt message."""
        self.progress_messages.append({
            'timestamp': time.time(),
            'type': 'prompt',
            'message': message,
            'options': options
        })
        logger.info(f"User prompt: {message}")
        logger.info(f"Options: {', '.join(options)}")
    
    def run(self, host: str = 'localhost', port: int = 5000) -> None:
        """Run the Flask application."""
        # Open browser for authentication
        threading.Timer(1.25, lambda: webbrowser.open(f'http://{host}:{port}')).start()
        self.app.run(host=host, port=port)
    
    def index(self) -> str:
        """Handle the index route."""
        token = self.token_cache.get_token()
        if token:
            # Start the image fetcher in a separate thread
            def start_fetcher():
                try:
                    self.add_progress("Starting image fetcher...")
                    # Import here to avoid circular import
                    from ..onenote.fetcher import OneNoteImageFetcher
                    fetcher = OneNoteImageFetcher(self)
                    fetcher.start()
                except Exception as e:
                    self.add_progress(f"Error starting image fetcher: {str(e)}")
                    logger.exception("Full traceback:")
            
            threading.Thread(target=start_fetcher).start()
            
            return """
            <!DOCTYPE html>
            <html>
                <head>
                    <title>OneNote Image Fetcher</title>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 20px; }
                        #progress { 
                            margin-top: 20px;
                            padding: 10px;
                            border: 1px solid #ccc;
                            border-radius: 5px;
                            max-height: 400px;
                            overflow-y: auto;
                        }
                        .message { margin: 5px 0; padding: 5px; }
                        .error { color: red; }
                        .success { color: green; }
                        .prompt { 
                            margin: 10px 0;
                            padding: 10px;
                            background-color: #f0f0f0;
                            border-radius: 5px;
                        }
                        .options {
                            margin-top: 10px;
                        }
                        .option {
                            display: inline-block;
                            margin-right: 10px;
                            padding: 5px 10px;
                            background-color: #4CAF50;
                            color: white;
                            border: none;
                            border-radius: 3px;
                            cursor: pointer;
                        }
                        .option:hover {
                            background-color: #45a049;
                        }
                    </style>
                </head>
                <body>
                    <h2>OneNote Image Fetcher</h2>
                    <div id="progress"></div>
                    <script>
                        const progressDiv = document.getElementById('progress');
                        const eventSource = new EventSource('/progress');
                        
                        eventSource.onmessage = function(e) {
                            const data = JSON.parse(e.data);
                            
                            if (data.type === 'prompt') {
                                // Create prompt container
                                const promptDiv = document.createElement('div');
                                promptDiv.className = 'prompt';
                                
                                // Add message
                                const messageDiv = document.createElement('div');
                                messageDiv.textContent = data.message;
                                promptDiv.appendChild(messageDiv);
                                
                                // Add options
                                const optionsDiv = document.createElement('div');
                                optionsDiv.className = 'options';
                                
                                data.options.forEach(option => {
                                    const button = document.createElement('button');
                                    button.className = 'option';
                                    button.textContent = option;
                                    button.onclick = function() {
                                        // Handle option selection
                                        const messageDiv = document.createElement('div');
                                        messageDiv.className = 'message';
                                        messageDiv.textContent = `Selected: ${option}`;
                                        progressDiv.appendChild(messageDiv);
                                        
                                        // Send selection to server
                                        fetch('/handle_option', {
                                            method: 'POST',
                                            headers: {
                                                'Content-Type': 'application/json',
                                            },
                                            body: JSON.stringify({ option }),
                                        });
                                    };
                                    optionsDiv.appendChild(button);
                                });
                                
                                promptDiv.appendChild(optionsDiv);
                                progressDiv.appendChild(promptDiv);
                            } else {
                                const messageDiv = document.createElement('div');
                                messageDiv.className = 'message';
                                if (data.message.includes('Error')) {
                                    messageDiv.className += ' error';
                                } else if (data.message.includes('Success')) {
                                    messageDiv.className += ' success';
                                }
                                messageDiv.textContent = data.message;
                                progressDiv.appendChild(messageDiv);
                            }
                            
                            progressDiv.scrollTop = progressDiv.scrollHeight;
                        };
                        
                        eventSource.onerror = function(e) {
                            console.error('EventSource failed:', e);
                            eventSource.close();
                        };
                    </script>
                </body>
            </html>
            """
        
        auth_url = self.msal_app.get_authorization_request_url(
            self.config["scopes"],
            redirect_uri=self.config["redirect_uri"]
        )
        return f'<a href="{auth_url}">Click here to authenticate</a>'
    
    def progress(self) -> Response:
        """Stream progress updates to the browser."""
        def generate():
            last_index = 0
            while True:
                if last_index < len(self.progress_messages):
                    for message in self.progress_messages[last_index:]:
                        yield f"data: {json.dumps(message)}\n\n"
                    last_index = len(self.progress_messages)
                time.sleep(0.1)
        
        return Response(stream_with_context(generate()), mimetype='text/event-stream')
    
    def get_token(self) -> str:
        """Handle the OAuth callback and get the access token."""
        auth_code = request.args.get('code')
        if not auth_code:
            return "No authorization code received"
        
        try:
            self.add_progress("Acquiring access token...")
            result = self.msal_app.acquire_token_by_authorization_code(
                auth_code,
                scopes=self.config["scopes"],
                redirect_uri=self.config["redirect_uri"]
            )
            
            if "access_token" in result:
                self.token_cache.set_token({
                    'token': result['access_token'],
                    'expires_at': result['expires_in'],
                    'refresh_token': result.get('refresh_token')
                })
                self.add_progress("Access token acquired successfully!")
                
                # Start the image fetcher in a separate thread
                def start_fetcher():
                    try:
                        self.add_progress("Starting image fetcher...")
                        # Import here to avoid circular import
                        from ..onenote.fetcher import OneNoteImageFetcher
                        fetcher = OneNoteImageFetcher(self)
                        fetcher.start()
                    except Exception as e:
                        self.add_progress(f"Error starting image fetcher: {str(e)}")
                        logger.exception("Full traceback:")
                
                threading.Thread(target=start_fetcher).start()
                
                return """
                <!DOCTYPE html>
                <html>
                    <head>
                        <title>OneNote Image Fetcher</title>
                        <style>
                            body { font-family: Arial, sans-serif; margin: 20px; }
                            #progress { 
                                margin-top: 20px;
                                padding: 10px;
                                border: 1px solid #ccc;
                                border-radius: 5px;
                                max-height: 400px;
                                overflow-y: auto;
                            }
                            .message { margin: 5px 0; padding: 5px; }
                            .error { color: red; }
                            .success { color: green; }
                        </style>
                    </head>
                    <body>
                        <h2>Authentication Successful!</h2>
                        <div id="progress"></div>
                        <script>
                            const progressDiv = document.getElementById('progress');
                            const eventSource = new EventSource('/progress');
                            
                            eventSource.onmessage = function(e) {
                                const data = JSON.parse(e.data);
                                const messageDiv = document.createElement('div');
                                messageDiv.className = 'message';
                                if (data.message.includes('Error')) {
                                    messageDiv.className += ' error';
                                } else if (data.message.includes('Success')) {
                                    messageDiv.className += ' success';
                                }
                                messageDiv.textContent = data.message;
                                progressDiv.appendChild(messageDiv);
                                progressDiv.scrollTop = progressDiv.scrollHeight;
                            };
                            
                            eventSource.onerror = function(e) {
                                console.error('EventSource failed:', e);
                                eventSource.close();
                            };
                        </script>
                    </body>
                </html>
                """
            else:
                error = result.get('error_description', 'Unknown error')
                self.add_progress(f"Token acquisition failed: {error}")
                return f"Authentication failed: {error}"
                
        except Exception as e:
            self.add_progress(f"Error in token acquisition: {str(e)}")
            return f"Error: {str(e)}"
    
    def handle_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Handle errors using the self-healing mechanism."""
        try:
            self.add_progress(f"Error occurred: {str(error)}")
            
            if self.self_healer:
                self.add_progress("Analyzing error and attempting self-healing...")
                
                # Get analysis from ChatGPT
                analysis = self.self_healer.analyze_error(error, context)
                
                # Add analysis to progress messages
                self.add_progress(f"Analysis: {analysis['explanation']}")
                self.add_progress("Suggested fixes:")
                for step in analysis['steps_to_fix']:
                    self.add_progress(f"- {step}")
                
                # Apply fixes
                if self.self_healer.apply_fix(analysis):
                    self.add_progress("Self-healing completed successfully")
                else:
                    self.add_progress("Self-healing failed to apply fixes")
            else:
                self.add_progress("Self-healing is disabled. Please configure OpenAI API key for advanced error handling.")
                self.add_progress("Error details:")
                self.add_progress(f"Type: {type(error).__name__}")
                self.add_progress(f"Message: {str(error)}")
                if hasattr(error, 'response') and error.response is not None:
                    self.add_progress(f"Response status: {error.response.status_code}")
                    self.add_progress(f"Response body: {error.response.text}")
            
        except Exception as e:
            self.add_progress(f"Error in error handling process: {str(e)}")
            logger.exception("Full traceback:")
    
    def call_graph_api(self, endpoint: str, method: str = "GET", **kwargs) -> Dict:
        """Make a call to the Microsoft Graph API.
        
        Args:
            endpoint: The API endpoint to call
            method: HTTP method to use
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            The API response as a dictionary
        """
        token = self.token_cache.get_token()
        if not token:
            raise ValueError("No access token available")
        
        headers = {
            "Authorization": f"Bearer {token['token']}",
            "Content-Type": "application/json"
        }
        
        try:
            # Make the API call
            self.add_progress(f"Making API call to: {endpoint}")
            response = requests.request(
                method,
                f"https://graph.microsoft.com/v1.0/{endpoint}",
                headers=headers,
                **kwargs
            )
            
            if response.status_code == 401:
                # Token expired, try to refresh
                self.add_progress("Token expired, attempting to refresh...")
                result = self.msal_app.acquire_token_by_refresh_token(
                    token['refresh_token'],
                    scopes=self.config["scopes"]
                )
                
                if "access_token" in result:
                    self.add_progress("Token refresh successful")
                    self.token_cache.set_token({
                        'token': result['access_token'],
                        'expires_at': result['expires_in'],
                        'refresh_token': result.get('refresh_token')
                    })
                    
                    # Retry the request with new token
                    headers["Authorization"] = f"Bearer {result['access_token']}"
                    response = requests.request(
                        method,
                        f"https://graph.microsoft.com/v1.0/{endpoint}",
                        headers=headers,
                        **kwargs
                    )
                else:
                    error = ValueError("Failed to refresh token")
                    self.handle_error(error, {
                        'endpoint': endpoint,
                        'method': method,
                        'status_code': 401,
                        'response': result
                    })
                    raise error
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            self.handle_error(e, {
                'endpoint': endpoint,
                'method': method,
                'status_code': getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None,
                'response_text': getattr(e.response, 'text', None) if hasattr(e, 'response') else None
            })
            raise 
    
    def handle_option(self, option: str) -> None:
        """Handle user option selection."""
        self.add_progress(f"User selected: {option}")
        
        if option == "Exit":
            self.add_progress("Exiting application...")
            # Here you would implement the exit logic
            pass
        elif option == "Try again":
            self.add_progress("Restarting image fetcher...")
            # Here you would implement the restart logic
            pass
        elif option == "Try another section":
            self.add_progress("Trying another section...")
            # Here you would implement the section selection logic
            pass
        elif option == "Try another notebook":
            self.add_progress("Trying another notebook...")
            # Here you would implement the notebook selection logic
            pass 