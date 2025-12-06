"""
Configuration management for Velora Sync
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from src.utils.exceptions import ConfigurationError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Config:
    """Configuration manager for Velora Sync"""
    
    # Required configuration keys
    REQUIRED_KEYS = [
        'SOURCE_DOCUMENT_PATH',
        'DESTINATION_DOCUMENT_PATH',
    ]
    
    # Default values
    DEFAULTS = {
        'LLM_PROVIDER': 'gemini',  # 'gemini', 'openai', or 'huggingface'
        'GEMINI_MODEL': 'gemini-pro',  # Stable, widely available across all regions
        'OPENAI_MODEL': 'gpt-4-turbo-preview',
        'LLM_MODEL_NAME': 'google/flan-t5-large',  # For Hugging Face
        'DEVICE': 'auto',
        'UPDATE_MODE': 'intelligent',  # 'new_only', 'full_sync', or 'intelligent'
        'LOG_LEVEL': 'INFO',
        'REPORTS_DIR': './reports',
        'CACHE_DIR': './cache',
        'MAX_TOKENS': 2000,  # Increased for detailed responses
        'TEMPERATURE': 0.3,
        'BATCH_SIZE': 5,
        'CREATE_BACKUP': True,
        'MAX_RETRIES': 3,
        'API_TIMEOUT': 300,
    }
    
    # Default test case template (Requirement ID removed as per user feedback)
    DEFAULT_TEMPLATE = {
        "Test Case ID": "TC001",
        "Test Case Title": "Sample test case",
        "Description": "Test case description",
        "Preconditions": "Preconditions for the test",
        "Test Steps": "1. Step one\n2. Step two\n3. Step three\n4. Step four",
        "Expected Result": "Expected outcome",
        "Priority": "Medium",
        "Test Type": "Functional",
        "Status": "Active"
    }
    
    def __init__(self, env_file: Optional[Path] = None):
        """
        Initialize configuration
        
        Args:
            env_file: Path to .env file (defaults to .env in current directory)
        """
        # Load environment variables
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        self._config: Dict[str, Any] = {}
        self._load_config()
        self._validate_config()
    
    def _load_config(self) -> None:
        """Load configuration from environment variables"""
        # Load all configuration with defaults
        for key, default_value in self.DEFAULTS.items():
            env_value = os.getenv(key)
            if env_value is not None:
                # Type conversion
                if isinstance(default_value, bool):
                    self._config[key] = env_value.lower() in ('true', '1', 'yes')
                elif isinstance(default_value, int):
                    self._config[key] = int(env_value)
                elif isinstance(default_value, float):
                    self._config[key] = float(env_value)
                else:
                    self._config[key] = env_value
            else:
                self._config[key] = default_value
        
        # Load required keys
        for key in self.REQUIRED_KEYS:
            value = os.getenv(key)
            if value:
                self._config[key] = value
        
        # Load optional keys
        optional_keys = [
            'GEMINI_API_KEY',
            'OPENAI_API_KEY',
            'HUGGINGFACE_API_TOKEN',
            'SHAREPOINT_TENANT_ID',
            'SHAREPOINT_CLIENT_ID',
            'SHAREPOINT_CLIENT_SECRET',
            'SHAREPOINT_SITE_URL',
        ]
        
        for key in optional_keys:
            value = os.getenv(key)
            if value:
                self._config[key] = value
        
        # Load test case template
        template_json = os.getenv('TEST_CASE_TEMPLATE')
        if template_json:
            try:
                self._config['TEST_CASE_TEMPLATE'] = json.loads(template_json)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid TEST_CASE_TEMPLATE JSON: {e}. Using default template.")
                self._config['TEST_CASE_TEMPLATE'] = self.DEFAULT_TEMPLATE
        else:
            self._config['TEST_CASE_TEMPLATE'] = self.DEFAULT_TEMPLATE
        
        # Convert paths to Path objects
        self._config['REPORTS_DIR'] = Path(self._config['REPORTS_DIR'])
        self._config['CACHE_DIR'] = Path(self._config['CACHE_DIR'])
        
        # Create directories if they don't exist
        self._config['REPORTS_DIR'].mkdir(parents=True, exist_ok=True)
        self._config['CACHE_DIR'].mkdir(parents=True, exist_ok=True)
    
    def _validate_config(self) -> None:
        """Validate configuration"""
        # Check required keys
        missing_keys = []
        for key in self.REQUIRED_KEYS:
            if key not in self._config or not self._config[key]:
                missing_keys.append(key)
        
        if missing_keys:
            raise ConfigurationError(
                f"Missing required configuration keys: {', '.join(missing_keys)}"
            )
        
        # Validate UPDATE_MODE
        if self._config['UPDATE_MODE'] not in ['new_only', 'full_sync', 'intelligent']:
            raise ConfigurationError(
                f"Invalid UPDATE_MODE: {self._config['UPDATE_MODE']}. "
                "Must be 'new_only', 'full_sync', or 'intelligent'"
            )
        
        # Check SharePoint configuration if using SharePoint URLs
        source_path = self._config['SOURCE_DOCUMENT_PATH']
        dest_path = self._config['DESTINATION_DOCUMENT_PATH']
        
        uses_sharepoint = (
            'sharepoint.com' in source_path.lower() or
            'sharepoint.com' in dest_path.lower()
        )
        
        if uses_sharepoint:
            required_sp_keys = [
                'SHAREPOINT_TENANT_ID',
                'SHAREPOINT_CLIENT_ID',
                'SHAREPOINT_CLIENT_SECRET',
                'SHAREPOINT_SITE_URL'
            ]
            missing_sp_keys = [
                key for key in required_sp_keys
                if key not in self._config or not self._config[key]
            ]
            
            if missing_sp_keys:
                raise ConfigurationError(
                    f"SharePoint URLs detected but missing credentials: {', '.join(missing_sp_keys)}"
                )
        
        logger.info("Configuration validated successfully")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        return self._config.get(key, default)
    
    def __getitem__(self, key: str) -> Any:
        """Get configuration value using dictionary syntax"""
        return self._config[key]
    
    def __contains__(self, key: str) -> bool:
        """Check if configuration key exists"""
        return key in self._config
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Get all configuration as dictionary
        
        Returns:
            Configuration dictionary
        """
        # Return copy to prevent modification
        return self._config.copy()
    
    def is_sharepoint_source(self) -> bool:
        """Check if source document is on SharePoint"""
        return 'sharepoint.com' in self._config['SOURCE_DOCUMENT_PATH'].lower()
    
    def is_sharepoint_destination(self) -> bool:
        """Check if destination document is on SharePoint"""
        return 'sharepoint.com' in self._config['DESTINATION_DOCUMENT_PATH'].lower()
    
    def get_log_file_path(self) -> Path:
        """Get path for log file"""
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return self._config['REPORTS_DIR'] / f"velora_sync_{timestamp}.log"
    
    def get_report_file_path(self) -> Path:
        """Get path for report file"""
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return self._config['REPORTS_DIR'] / f"report_{timestamp}.md"
