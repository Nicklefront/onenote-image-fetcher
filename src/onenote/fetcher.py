import os
import logging
from typing import List, Dict, Optional, Protocol, Any
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime
from ..utils.self_healer import SelfHealer

from .models import Notebook, Section, Page, Image

logger = logging.getLogger(__name__)

class GraphAPIInterface(Protocol):
    """Interface for Graph API clients."""
    def call_graph_api(self, endpoint: str, method: str = "GET", **kwargs) -> Dict:
        """Make a call to the Microsoft Graph API."""
        ...
    
    def add_progress(self, message: str) -> None:
        """Add a progress message."""
        ...
    
    def handle_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Handle errors using the self-healing mechanism."""
        ...
    
    def add_user_prompt(self, message: str, options: List[str]) -> None:
        """Add a user prompt message."""
        ...

class OneNoteImageFetcher:
    """Handles fetching images from OneNote pages."""
    
    def __init__(self, graph_client: GraphAPIInterface, openai_api_key: Optional[str] = None):
        """Initialize the image fetcher."""
        self.graph_client = graph_client
        self.output_dir = "downloaded_images"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize self-healer if API key is provided
        self.self_healer = SelfHealer(openai_api_key) if openai_api_key else None
        
        # SharePoint and Notebook configuration
        self.site_id = "02531bc3-49a7-427a-a1b6-d7d48e4e6397"
        self.notebook_name = "Notizbuch für Operatives"
        self.notebook_path = "https://juniorunimg.sharepoint.com/sites/Intranet/SiteAssets/Notizbuch für Operatives"
    
    def _handle_error(self, error_type: str, error_context: Dict[str, Any]) -> None:
        """Handle errors using the self-healing system."""
        if not self.self_healer:
            self.graph_client.add_progress(f"Error: {error_type}")
            return
        
        analysis = self.self_healer.analyze_and_suggest(error_type, error_context)
        
        # Display the analysis
        self.graph_client.add_progress(f"\nError Analysis: {analysis['explanation']}")
        
        if analysis['solutions']:
            self.graph_client.add_progress("\nSuggested Solutions:")
            for solution in analysis['solutions']:
                self.graph_client.add_progress(f"- {solution}")
        
        if analysis['patterns']:
            self.graph_client.add_progress("\nPatterns Found:")
            for pattern in analysis['patterns']:
                self.graph_client.add_progress(f"- {pattern}")
        
        if analysis['next_steps']:
            self.graph_client.add_progress("\nNext Steps:")
            for step in analysis['next_steps']:
                self.graph_client.add_progress(f"- {step}")
        
        if not analysis['is_recoverable']:
            self.graph_client.add_progress("\nThis error is not recoverable. Manual intervention may be required.")
    
    def start(self) -> None:
        """Start the image fetching process."""
        try:
            self.graph_client.add_progress(f"Fetching notebook: {self.notebook_name}")
            
            # Get the specific notebook
            notebooks = self.graph_client.call_graph_api("me/onenote/notebooks")
            target_notebook = None
            
            for notebook in notebooks.get('value', []):
                if notebook['displayName'] == self.notebook_name:
                    target_notebook = notebook
                    break
            
            if not target_notebook:
                error_context = {
                    "notebook_name": self.notebook_name,
                    "available_notebooks": [n['displayName'] for n in notebooks.get('value', [])],
                    "api_response": notebooks
                }
                self._handle_error("notebook_not_found", error_context)
                return
            
            self.graph_client.add_progress(f"Found notebook: {target_notebook['displayName']}")
            
            # Get sections
            self.graph_client.add_progress("Fetching sections...")
            sections = self.graph_client.call_graph_api(f"me/onenote/notebooks/{target_notebook['id']}/sections")
            
            if not sections.get('value'):
                error_context = {
                    "notebook_id": target_notebook['id'],
                    "notebook_name": target_notebook['displayName'],
                    "api_response": sections
                }
                self._handle_error("no_sections", error_context)
                return
            
            self.graph_client.add_progress(f"Found {len(sections['value'])} sections.")
            
            # Process each section
            for section in sections['value']:
                self.graph_client.add_progress(f"Processing section: {section['displayName']}")
                
                # Get pages
                self.graph_client.add_progress("Fetching pages...")
                pages = self.graph_client.call_graph_api(f"me/onenote/sections/{section['id']}/pages")
                
                if not pages.get('value'):
                    error_context = {
                        "section_id": section['id'],
                        "section_name": section['displayName'],
                        "api_response": pages
                    }
                    self._handle_error("no_pages", error_context)
                    continue
                
                self.graph_client.add_progress(f"Found {len(pages['value'])} pages.")
                
                # Process each page
                for page in pages['value']:
                    self.graph_client.add_progress(f"Processing page: {page['title']}")
                    
                    try:
                        # Get page preview
                        preview = self.graph_client.call_graph_api(
                            f"sites/{self.site_id}/pages/{page['id']}/preview"
                        )
                        
                        if not preview.get('previewImageUrl'):
                            error_context = {
                                "page_id": page['id'],
                                "page_title": page['title'],
                                "api_response": preview
                            }
                            self._handle_error("preview_error", error_context)
                            continue
                        
                        # Download the preview image
                        self.graph_client.add_progress("Downloading preview image...")
                        response = requests.get(preview['previewImageUrl'])
                        
                        if response.status_code == 200:
                            # Create directory structure
                            section_path = os.path.join(
                                self.output_dir,
                                self.notebook_name,
                                section['displayName']
                            )
                            os.makedirs(section_path, exist_ok=True)
                            
                            # Save the image
                            filename = f"{page['title']}.png"
                            filepath = os.path.join(section_path, filename)
                            
                            with open(filepath, 'wb') as f:
                                f.write(response.content)
                            
                            self.graph_client.add_progress(f"Successfully downloaded preview to: {filepath}")
                        else:
                            error_context = {
                                "page_id": page['id'],
                                "page_title": page['title'],
                                "status_code": response.status_code,
                                "response_text": response.text,
                                "preview_url": preview['previewImageUrl']
                            }
                            self._handle_error("download_error", error_context)
                            
                    except Exception as e:
                        error_context = {
                            "page_id": page['id'],
                            "page_title": page['title'],
                            "error": str(e),
                            "error_type": type(e).__name__
                        }
                        self._handle_error("processing_error", error_context)
                        continue
            
            self.graph_client.add_progress("Finished processing all sections.")
            
        except Exception as e:
            error_context = {
                "error": str(e),
                "error_type": type(e).__name__,
                "output_dir": self.output_dir
            }
            self._handle_error("general_error", error_context)
            logger.exception("Full traceback:")
    
    def get_notebooks(self) -> List[Notebook]:
        """Get all OneNote notebooks."""
        response = self.graph_client.call_graph_api("me/onenote/notebooks")
        return [
            Notebook(
                id=notebook["id"],
                name=notebook["displayName"],
                url=notebook["links"]["oneNoteWebUrl"]["href"]
            )
            for notebook in response["value"]
        ]
    
    def get_sections(self, notebook_id: str) -> List[Section]:
        """Get all sections in a notebook."""
        response = self.graph_client.call_graph_api(f"me/onenote/notebooks/{notebook_id}/sections")
        return [
            Section(
                id=section["id"],
                name=section["displayName"],
                url=section["links"]["oneNoteWebUrl"]["href"],
                notebook_id=notebook_id,
                parent_section_group_id=section.get("parentSectionGroup", {}).get("id")
            )
            for section in response["value"]
        ]
    
    def get_pages(self, section_id: str) -> List[Page]:
        """Get all pages in a section."""
        response = self.graph_client.call_graph_api(f"me/onenote/sections/{section_id}/pages")
        return [
            Page(
                id=page["id"],
                title=page["title"],
                url=page["links"]["oneNoteWebUrl"]["href"],
                section_id=section_id,
                content_url=page["contentUrl"]
            )
            for page in response["value"]
        ]
    
    def scan_notebook_for_images(self, notebook: Notebook) -> List[Page]:
        """Scan a notebook for pages containing images."""
        pages_with_images = []
        
        # Get all sections
        sections = self.get_sections(notebook.id)
        for section in sections:
            # Get all pages in section
            pages = self.get_pages(section.id)
            for page in pages:
                try:
                    # Get page content
                    content = self.graph_client.call_graph_api(f"me/onenote/pages/{page.id}/content")
                    
                    # Parse HTML content
                    soup = BeautifulSoup(content, 'html.parser')
                    images = soup.find_all('img')
                    
                    if images:
                        logger.info(f"Found {len(images)} images in page: {page.title}")
                        pages_with_images.append(page)
                    else:
                        logger.info(f"No images found in page: {page.title}")
                        
                except Exception as e:
                    logger.error(f"Error scanning page {page.title}: {str(e)}")
                    continue
        
        return pages_with_images
    
    def download_image(self, page: Page) -> Optional[str]:
        """Download an image from a page."""
        try:
            # Get page content
            content = self.graph_client.call_graph_api(f"me/onenote/pages/{page.id}/content")
            
            # Parse HTML content
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
            
            # Create folder structure
            folder_path = self._create_folder_structure(page)
            
            # Generate filename
            filename = f"{page.title.replace(' ', '_')}.png"
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
    
    def _create_folder_structure(self, page: Page) -> str:
        """Create folder structure based on page hierarchy."""
        # Get section details
        section = self.graph_client.call_graph_api(f"me/onenote/sections/{page.section_id}")
        section_name = section["displayName"].replace(" ", "_")
        
        # Get notebook details
        notebook_id = section["parentNotebook"]["id"]
        notebook = self.graph_client.call_graph_api(f"me/onenote/notebooks/{notebook_id}")
        notebook_name = notebook["displayName"].replace(" ", "_")
        
        # Create path components
        path_components = [notebook_name, section_name]
        
        # Add section group if exists
        if "parentSectionGroup" in section:
            group = self.graph_client.call_graph_api(
                f"me/onenote/sectionGroups/{section['parentSectionGroup']['id']}"
            )
            path_components.insert(1, group["displayName"].replace(" ", "_"))
        
        # Create the full path
        folder_path = Path(self.output_dir).joinpath(*path_components)
        folder_path.mkdir(parents=True, exist_ok=True)
        
        return str(folder_path)
    
    def _select_notebook(self, notebooks: List[Notebook]) -> Optional[Notebook]:
        """Let user select a notebook."""
        logger.info("\nAvailable notebooks:")
        for i, notebook in enumerate(notebooks, 1):
            logger.info(f"{i}. {notebook.name}")
        
        while True:
            try:
                choice = int(input("\nEnter the number of the notebook to scan: "))
                if 1 <= choice <= len(notebooks):
                    return notebooks[choice - 1]
                print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
    
    def _select_page(self, pages: List[Page]) -> Optional[Page]:
        """Let user select a page."""
        logger.info("\nPages containing images:")
        for i, page in enumerate(pages, 1):
            logger.info(f"{i}. {page.title}")
        
        while True:
            try:
                choice = int(input("\nEnter the number of the page to download an image from: "))
                if 1 <= choice <= len(pages):
                    return pages[choice - 1]
                print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a valid number.") 