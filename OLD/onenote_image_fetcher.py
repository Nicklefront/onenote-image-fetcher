#!/usr/bin/env python3
"""
OneNote Image Fetcher MVP

A minimal version that downloads a single image from a OneNote page,
creating a folder structure that reflects the page's hierarchy.
"""

import os
import logging
import requests
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('onenote_image_fetcher_mvp.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OneNoteImageFetcherMVP:
    def __init__(self, graph_client):
        """Initialize the image fetcher with a Graph API client.
        
        Args:
            graph_client: An instance of GraphAPIClient
        """
        self.graph_client = graph_client
        self.output_dir = "downloaded_images"
        
    def start(self) -> None:
        """Start the image fetching process."""
        try:
            # Get all notebooks
            notebooks = self.graph_client.call_graph_api("me/onenote/notebooks")
            if not notebooks['value']:
                logger.error("No notebooks found")
                return
            
            # Print available notebooks
            logger.info("\nAvailable notebooks:")
            for i, notebook in enumerate(notebooks['value'], 1):
                logger.info(f"{i}. {notebook['displayName']}")
            
            # Let user choose a notebook
            while True:
                try:
                    choice = int(input("\nEnter the number of the notebook to scan: "))
                    if 1 <= choice <= len(notebooks['value']):
                        selected_notebook = notebooks['value'][choice - 1]
                        break
                    print("Invalid choice. Please try again.")
                except ValueError:
                    print("Please enter a valid number.")
            
            # Scan the notebook for images
            logger.info(f"\nScanning notebook: {selected_notebook['displayName']}")
            pages_with_images = self.scan_notebook_for_images(selected_notebook['id'])
            
            if not pages_with_images:
                logger.error("No pages with images found in the selected notebook")
                return
            
            # Print pages with images
            logger.info("\nPages containing images:")
            for i, page_info in enumerate(pages_with_images, 1):
                logger.info(f"{i}. {page_info['page']['title']} ({page_info['image_count']} images)")
            
            # Let user choose a page
            while True:
                try:
                    choice = int(input("\nEnter the number of the page to download an image from: "))
                    if 1 <= choice <= len(pages_with_images):
                        selected_page = pages_with_images[choice - 1]
                        break
                    print("Invalid choice. Please try again.")
                except ValueError:
                    print("Please enter a valid number.")
            
            # Download an image from the selected page
            result = self.download_single_image(selected_page['page']['id'])
            
            if result:
                logger.info(f"Successfully downloaded image to: {result}")
            else:
                logger.error("Failed to download image")
                
        except Exception as e:
            logger.error(f"Error in image fetching process: {str(e)}")
    
    def get_page_hierarchy(self, page_id: str) -> Dict[str, Any]:
        """Get the complete hierarchy for a page (notebook -> section group -> section -> page).
        
        Args:
            page_id: The ID of the page to get hierarchy for
            
        Returns:
            Dictionary containing the complete hierarchy
        """
        logger.info(f"Getting hierarchy for page: {page_id}")
        
        # Get page details
        page = self.graph_client.call_graph_api(f"me/onenote/pages/{page_id}")
        logger.info(f"Page details: {page}")
        
        # Get section details
        section_id = page["parentSection"]["id"]
        section = self.graph_client.call_graph_api(f"me/onenote/sections/{section_id}")
        logger.info(f"Section details: {section}")
        
        # Get notebook details
        notebook_id = section["parentNotebook"]["id"]
        notebook = self.graph_client.call_graph_api(f"me/onenote/notebooks/{notebook_id}")
        logger.info(f"Notebook details: {notebook}")
        
        # Initialize hierarchy
        hierarchy = {
            "notebook": {
                "id": notebook_id,
                "name": notebook["displayName"],
                "url": notebook["links"]["oneNoteWebUrl"]["href"]
            },
            "section": {
                "id": section_id,
                "name": section["displayName"],
                "url": section["links"]["oneNoteWebUrl"]["href"]
            },
            "page": {
                "id": page_id,
                "name": page["title"],
                "url": page["links"]["oneNoteWebUrl"]["href"]
            }
        }
        
        # Check for section group
        if "parentSectionGroup" in section:
            group_id = section["parentSectionGroup"]["id"]
            group = self.graph_client.call_graph_api(f"me/onenote/sectionGroups/{group_id}")
            logger.info(f"Section group details: {group}")
            
            hierarchy["section_group"] = {
                "id": group_id,
                "name": group["displayName"],
                "url": group["links"]["oneNoteWebUrl"]["href"]
            }
        
        # Check for parent section
        if "parentSection" in section:
            parent_section_id = section["parentSection"]["id"]
            parent_section = self.graph_client.call_graph_api(f"me/onenote/sections/{parent_section_id}")
            logger.info(f"Parent section details: {parent_section}")
            
            hierarchy["parent_section"] = {
                "id": parent_section_id,
                "name": parent_section["displayName"],
                "url": parent_section["links"]["oneNoteWebUrl"]["href"]
            }
        
        logger.info(f"Page hierarchy: {hierarchy}")
        return hierarchy
    
    def create_folder_structure(self, hierarchy: Dict[str, Any]) -> str:
        """Create folder structure based on hierarchy.
        
        Args:
            hierarchy: Dictionary containing the page hierarchy
            
        Returns:
            Path to the created folder
        """
        # Create base directory if it doesn't exist
        base_dir = Path(self.output_dir)
        base_dir.mkdir(exist_ok=True)
        
        # Create path components
        path_components = []
        
        # Add notebook
        path_components.append(hierarchy["notebook"]["name"].replace(" ", "_"))
        
        # Add section group if exists
        if "section_group" in hierarchy:
            path_components.append(hierarchy["section_group"]["name"].replace(" ", "_"))
        
        # Add parent section if exists
        if "parent_section" in hierarchy:
            path_components.append(hierarchy["parent_section"]["name"].replace(" ", "_"))
        
        # Add section
        path_components.append(hierarchy["section"]["name"].replace(" ", "_"))
        
        # Create the full path
        folder_path = base_dir.joinpath(*path_components)
        folder_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Created directory structure: {folder_path}")
        return str(folder_path)
    
    def get_notebook_pages(self, notebook_id: str) -> List[Dict[str, Any]]:
        """Get all pages in a notebook.
        
        Args:
            notebook_id: The ID of the notebook to scan
            
        Returns:
            List of page dictionaries
        """
        logger.info(f"Getting pages for notebook: {notebook_id}")
        pages = []
        
        # Get all sections in the notebook
        sections = self.graph_client.call_graph_api(f"me/onenote/notebooks/{notebook_id}/sections")
        logger.info(f"Found {len(sections['value'])} sections in notebook")
        
        # Get pages from each section
        for section in sections['value']:
            section_id = section['id']
            section_pages = self.graph_client.call_graph_api(f"me/onenote/sections/{section_id}/pages")
            logger.info(f"Found {len(section_pages['value'])} pages in section: {section['displayName']}")
            pages.extend(section_pages['value'])
        
        return pages
    
    def scan_notebook_for_images(self, notebook_id: str) -> List[Dict[str, Any]]:
        """Scan a notebook for pages containing images.
        
        Args:
            notebook_id: The ID of the notebook to scan
            
        Returns:
            List of dictionaries containing page and image information
        """
        logger.info(f"Scanning notebook {notebook_id} for images")
        pages_with_images = []
        
        # Get all pages in the notebook
        pages = self.get_notebook_pages(notebook_id)
        
        for page in pages:
            page_id = page['id']
            logger.info(f"Checking page: {page['title']}")
            
            try:
                # Get page content
                content = self.graph_client.call_graph_api(f"me/onenote/pages/{page_id}/content")
                
                # Parse HTML content
                soup = BeautifulSoup(content, 'html.parser')
                images = soup.find_all('img')
                
                if images:
                    logger.info(f"Found {len(images)} images in page: {page['title']}")
                    pages_with_images.append({
                        'page': page,
                        'image_count': len(images),
                        'first_image_url': images[0].get('src')
                    })
                else:
                    logger.info(f"No images found in page: {page['title']}")
                    
            except Exception as e:
                logger.error(f"Error scanning page {page['title']}: {str(e)}")
                continue
        
        return pages_with_images
    
    def download_single_image(self, page_id: str) -> Optional[str]:
        """Download a single image from a OneNote page.
        
        Args:
            page_id: The ID of the page to download image from
            
        Returns:
            Path to the downloaded image if successful, None otherwise
        """
        try:
            # Get page hierarchy
            hierarchy = self.get_page_hierarchy(page_id)
            
            # Create folder structure
            folder_path = self.create_folder_structure(hierarchy)
            
            # Get page content
            logger.info(f"Requesting content for page: {page_id}")
            content = self.graph_client.call_graph_api(f"me/onenote/pages/{page_id}/content")
            logger.info("Received page content response")
            
            # Parse HTML content
            logger.info("Parsing HTML content for images")
            soup = BeautifulSoup(content, 'html.parser')
            images = soup.find_all('img')
            
            if not images:
                logger.warning("No images found in page")
                return None
            
            # Get the first image
            img = images[0]
            img_url = img.get('src')
            
            if not img_url:
                logger.warning("Image URL not found")
                return None
            
            # Generate filename based on hierarchy
            filename_parts = []
            if "section_group" in hierarchy:
                filename_parts.append(hierarchy["section_group"]["name"].replace(" ", "_"))
            if "parent_section" in hierarchy:
                filename_parts.append(hierarchy["parent_section"]["name"].replace(" ", "_"))
            filename_parts.append(hierarchy["section"]["name"].replace(" ", "_"))
            
            filename = "_".join(filename_parts) + ".png"
            file_path = os.path.join(folder_path, filename)
            
            # Download image
            logger.info(f"Downloading image from: {img_url}")
            response = requests.get(img_url)
            response.raise_for_status()
            
            # Save image
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Image saved to: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Error downloading image: {str(e)}")
            return None

def main():
    """Main function to scan a notebook for images and download one."""
    from graph_api_client import GraphAPIClient
    from dotenv import load_dotenv
    import os
    
    # Load environment variables
    load_dotenv()
    
    # Create configuration dictionary
    config = {
        "client_id": os.getenv("CLIENT_ID"),
        "client_secret": os.getenv("CLIENT_SECRET"),
        "tenant_id": os.getenv("TENANT_ID"),
        "redirect_uri": os.getenv("REDIRECT_URI"),
        "scopes": os.getenv("SCOPES", "Notes.Read Notes.Read.All").split(),
        "authority": f"https://login.microsoftonline.com/{os.getenv('TENANT_ID')}"
    }
    
    # Initialize Graph API client
    graph_client = GraphAPIClient(config)
    
    # Initialize image fetcher
    fetcher = OneNoteImageFetcherMVP(graph_client)
    
    # Start the image fetching process
    fetcher.start()

if __name__ == "__main__":
    main() 