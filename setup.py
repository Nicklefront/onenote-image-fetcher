from setuptools import setup, find_packages
import os

# Read the README if it exists
try:
    with open("README.md", "r", encoding="utf-8") as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = "A tool to fetch images from Microsoft OneNote"

setup(
    name="onenote_image_fetcher",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "flask",
        "msal",
        "python-dotenv",
        "requests",
        "beautifulsoup4",
    ],
    python_requires=">=3.6",
    author="Your Name",
    author_email="your.email@example.com",
    description="A tool to fetch images from Microsoft OneNote",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/onenote_image_fetcher",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
) 