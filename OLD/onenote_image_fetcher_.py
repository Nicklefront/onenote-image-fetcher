#!/usr/bin/env python3
"""
OneNote Image Fetcher

This module provides functionality to fetch images from a specific OneNote notebook
in a SharePoint site. It uses the GraphAPIClient for authentication and API access.
"""

import logging
import os
import re
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
from graph_api_client import GraphAPIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("onenote_image_fetcher.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("onenote_image_fetcher")


class OneNoteImageFetcher:
    """Handles fetching images from a specific OneNote notebook."""
    
    def __init__(self, graph_client: GraphAPIClient):
        """Initialize the fetcher with a Graph API client.
        
        Args:
            graph_client: Initialized GraphAPIClient instance
        """
        self.client = graph_client
    
    def get_sharepoint_site_notebooks(self, site_name: str) -> List[Dict[str, Any]]:
        """Get all OneNote notebooks from a specific SharePoint site.
        
        Args:
            site_name: Name of the SharePoint site
            
        Returns:
            List of notebook dictionaries
        """
        # First get the site ID
        site_response = self.client.call_graph_api(f"sites?search={site_name}")
        sites = site_response.get("value", [])
        
        if not sites:
            raise ValueError(f"No SharePoint site found with name: {site_name}")
            
        site_id = sites[0]["id"]
        
        # Get notebooks from the site
        notebooks_response = self.client.call_graph_api(f"sites/{site_id}/onenote/notebooks")
        return notebooks_response.get("value", [])
    
    def get_specific_notebook(self, site_name: str, notebook_name: str) -> Dict[str, Any]:
        """Get a specific notebook from a SharePoint site by name.
        
        Args:
            site_name: Name of the SharePoint site
            notebook_name: Name of the notebook to find
            
        Returns:
            Notebook dictionary if found, None otherwise
        """
        notebooks = self.get_sharepoint_site_notebooks(site_name)
        for notebook in notebooks:
            if notebook.get("displayName") == notebook_name:
                return notebook
        return None
    
    def get_sections(self, notebook_id: str) -> List[Dict[str, Any]]:
        """Get all sections in a notebook.
        
        Args:
            notebook_id: ID of the notebook
            
        Returns:
            List of section dictionaries
        """
        response = self.client.call_graph_api(f"me/onenote/notebooks/{notebook_id}/sections")
        return response.get("value", [])
    
    def get_pages(self, section_id: str) -> List[Dict[str, Any]]:
        """Get all pages in a section.
        
        Args:
            section_id: ID of the section
            
        Returns:
            List of page dictionaries
        """
        response = self.client.call_graph_api(f"me/onenote/sections/{section_id}/pages")
        return response.get("value", [])
    
    def get_page_content(self, page_id: str) -> str:
        """Get the HTML content of a page.
        
        Args:
            page_id: ID of the page
            
        Returns:
            HTML content as string
        """
        return self.client.call_graph_api(f"me/onenote/pages/{page_id}/content")
    
    def download_images(self, notebook_id: str, output_dir: str = "downloaded_images") -> None:
        """Download all images from a specific OneNote notebook.
        
        Args:
            notebook_id: ID of the notebook to download from
            output_dir: Directory to save images to
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Get the notebook
        notebook = self.client.call_graph_api(f"me/onenote/notebooks/{notebook_id}")
        notebook_name = notebook.get("displayName", "unnamed_notebook")
        logger.info(f"Processing notebook: {notebook_name}")

        # Get all sections in the notebook
        sections = self.get_sections(notebook_id)
        logger.info(f"Found {len(sections)} sections in notebook {notebook_name}")

        for section in sections:
            section_name = section.get("displayName", "unnamed_section")
            logger.info(f"Processing section: {section_name}")

            # Get all pages in the section
            pages = self.get_pages(section["id"])
            logger.info(f"Found {len(pages)} pages in section {section_name}")

            for page in pages:
                page_title = page.get("title", "unnamed_page")
                # Clean the page title to make it filesystem-friendly
                page_title = re.sub(r'[^\w\-_\. ]', '_', page_title)
                logger.info(f"Processing page: {page_title}")

                # Get page content
                html_content = self.get_page_content(page["id"])
                soup = BeautifulSoup(html_content, "html.parser")

                # Find all images
                images = soup.find_all("img")
                logger.info(f"Found {len(images)} images in page {page_title}")

                for idx, img in enumerate(images, 1):
                    try:
                        # Get image source URL
                        src = img.get("src")
                        if not src:
                            continue

                        # Get image data-id for unique identification
                        data_id = img.get("data-id", "")
                        if not data_id:
                            data_id = str(idx)

                        # Create a human-readable filename
                        filename = f"{notebook_name}_{section_name}_{page_title}_{data_id}.png"
                        filename = re.sub(r'[^\w\-_\. ]', '_', filename)
                        filepath = os.path.join(output_dir, filename)

                        # Download the image
                        headers = {"Authorization": f"Bearer {self.client.access_token}"}
                        response = self.client.session.get(src, headers=headers)
                        response.raise_for_status()

                        # Save the image
                        with open(filepath, "wb") as f:
                            f.write(response.content)
                        logger.info(f"Saved image: {filename}")

                    except Exception as e:
                        logger.error(f"Error processing image: {e}")
                        continue


def fetch_images_from_notebook(graph_client: GraphAPIClient, notebook_key: str) -> None:
    """Main function to fetch images from a specific notebook using its key.
    
    Args:
        graph_client: Initialized GraphAPIClient instance
        notebook_key: The notebook key in format "name|$|url"
    """
    fetcher = OneNoteImageFetcher(graph_client)
    
    # Extract notebook name from the key
    notebook_name = notebook_key.split("|$|")[0]
    
    try:
        # Get the notebook directly using the key
        notebook = graph_client.call_graph_api(f"me/onenote/notebooks/{notebook_key}")
        if notebook:
            logger.info(f"Found notebook: {notebook.get('displayName')}")
            # Download images from this specific notebook
            fetcher.download_images(notebook["id"])
            logger.info("Successfully downloaded all images from the specified notebook")
        else:
            logger.error(f"Could not find notebook with key: {notebook_key}")
    except Exception as e:
        logger.error(f"Error accessing notebook: {e}") 