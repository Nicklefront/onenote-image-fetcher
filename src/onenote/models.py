from dataclasses import dataclass
from typing import Optional, List

@dataclass
class Notebook:
    """Represents a OneNote notebook."""
    id: str
    name: str
    url: str

@dataclass
class Section:
    """Represents a OneNote section."""
    id: str
    name: str
    url: str
    notebook_id: str
    parent_section_group_id: Optional[str] = None

@dataclass
class Page:
    """Represents a OneNote page."""
    id: str
    title: str
    url: str
    section_id: str
    content_url: Optional[str] = None

@dataclass
class Image:
    """Represents an image in a OneNote page."""
    url: str
    page_id: str
    section_id: str
    notebook_id: str
    filename: Optional[str] = None 