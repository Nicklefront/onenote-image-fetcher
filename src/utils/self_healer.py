import os
import json
import logging
import openai
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class SelfHealer:
    """Intelligent self-healing system using OpenAI to analyze errors and logs."""
    
    def __init__(self, api_key: str):
        """Initialize the self-healer with OpenAI API key."""
        if not api_key:
            raise ValueError("OpenAI API key is required for self-healing")
        self.api_key = api_key
        openai.api_key = api_key
        self.attempts: Dict[str, int] = {}  # Track attempts per error type
        self.max_attempts = 3
    
    def _analyze_error_with_gpt(self, error_type: str, error_context: Dict[str, Any], logs: str) -> Dict[str, Any]:
        """Use GPT to analyze the error and provide intelligent suggestions."""
        try:
            prompt = f"""
            Analyze this error in a OneNote image fetching application:
            
            Error Type: {error_type}
            Context: {json.dumps(error_context, indent=2)}
            Recent Logs: {logs}
            
            Please provide:
            1. A clear explanation of what went wrong
            2. Specific, actionable solutions
            3. Whether this is a recoverable error
            4. Any patterns or trends in the logs that might help
            5. Recommended next steps
            
            Format the response as JSON with these keys:
            - explanation
            - solutions (array)
            - is_recoverable
            - patterns
            - next_steps
            """
            
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert in debugging Microsoft Graph API and OneNote integration issues."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            analysis = json.loads(response.choices[0].message.content)
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze error with GPT: {str(e)}")
            return {
                "explanation": "Failed to analyze error with AI",
                "solutions": ["Check the logs manually for more details"],
                "is_recoverable": False,
                "patterns": [],
                "next_steps": ["Review the error logs manually"]
            }
    
    def _read_recent_logs(self, log_file: str = "app.log", lines: int = 100) -> str:
        """Read recent lines from the log file."""
        try:
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    return ''.join(f.readlines()[-lines:])
            return "No log file found"
        except Exception as e:
            logger.error(f"Failed to read logs: {str(e)}")
            return "Failed to read logs"
    
    def analyze_and_suggest(self, error_type: str, error_context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the error and provide intelligent suggestions."""
        # Track attempts
        if error_type not in self.attempts:
            self.attempts[error_type] = 0
        self.attempts[error_type] += 1
        
        # If we've tried too many times, stop
        if self.attempts[error_type] > self.max_attempts:
            return {
                "explanation": "Maximum self-healing attempts reached",
                "solutions": ["Manual intervention required"],
                "is_recoverable": False,
                "patterns": [],
                "next_steps": ["Contact support or review logs manually"]
            }
        
        # Get recent logs
        logs = self._read_recent_logs()
        
        # Analyze with GPT
        analysis = self._analyze_error_with_gpt(error_type, error_context, logs)
        
        # Log the analysis
        logger.info(f"Self-healing analysis for {error_type}: {json.dumps(analysis, indent=2)}")
        
        return analysis
    
    def should_retry(self, error_type: str) -> bool:
        """Determine if we should retry based on error type and attempts."""
        return self.attempts.get(error_type, 0) < self.max_attempts
    
    def reset_attempts(self, error_type: Optional[str] = None) -> None:
        """Reset attempt counters."""
        if error_type:
            self.attempts[error_type] = 0
        else:
            self.attempts.clear() 