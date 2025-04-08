import logging
from .auth.graph_client import GraphAPIClient, load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Main entry point for the application."""
    try:
        # Load configuration
        config = load_config()
        
        # Initialize and run the Graph API client
        client = GraphAPIClient(config)
        client.run()
        
    except Exception as e:
        logging.error(f"Application error: {str(e)}")
        raise

if __name__ == "__main__":
    main() 