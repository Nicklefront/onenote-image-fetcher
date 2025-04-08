# OneNote Image Fetcher

A Python application that fetches and downloads images from Microsoft OneNote notebooks using the Microsoft Graph API. The application includes intelligent error handling and self-healing capabilities powered by OpenAI's GPT-4.

## Features

- Fetches images from OneNote notebooks
- Intelligent error handling with self-healing
- Real-time progress updates
- Detailed logging
- OpenAI-powered error analysis
- Automatic retry mechanism
- Organized file structure for downloaded images

## Prerequisites

- Python 3.8+
- Microsoft 365 account with OneNote access
- OpenAI API key (for self-healing feature)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/onenote-image-fetcher.git
cd onenote-image-fetcher
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your credentials:
```env
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
TENANT_ID=your_tenant_id
OPENAI_API_KEY=your_openai_api_key
```

## Usage

1. Run the application:
```bash
python -m src
```

2. Follow the authentication process in your browser

3. The application will:
   - Authenticate with Microsoft Graph API
   - Fetch the specified notebook
   - Download images from pages
   - Save them in an organized directory structure

## Project Structure

```
onenote-image-fetcher/
├── src/
│   ├── __init__.py
│   ├── __main__.py
│   ├── auth/
│   │   ├── __init__.py
│   │   └── graph_client.py
│   ├── onenote/
│   │   ├── __init__.py
│   │   ├── fetcher.py
│   │   └── models.py
│   └── utils/
│       ├── __init__.py
│       └── self_healer.py
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

## Error Handling

The application includes an intelligent self-healing system that:
- Analyzes errors using OpenAI's GPT-4
- Provides context-aware solutions
- Tracks and limits retry attempts
- Analyzes log patterns
- Determines recoverability of errors

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Microsoft Graph API
- OpenAI GPT-4
- Python community 