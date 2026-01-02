"""
Google Drive client for file upload/download operations.
Uses service account authentication for CI environments.
"""

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

from src.utils.exceptions import DocumentReadError, DocumentWriteError
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Optional imports - will fail gracefully if not installed
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    logger.debug("Google API libraries not installed. Install with: pip install google-api-python-client google-auth")


class GoogleDriveClient:
    """
    Google Drive client using service account authentication.
    
    Works in CI environments (GitHub Actions) without user interaction.
    Requires sharing the Drive file/folder with the service account email.
    """
    
    # Scopes required for file read/write
    # Note: 'drive' scope is needed to access files shared with the service account
    # 'drive.file' only allows access to files the app has created
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    def __init__(
        self,
        service_account_json: Optional[str] = None,
        service_account_file: Optional[str] = None
    ):
        """
        Initialize Google Drive client.
        
        Args:
            service_account_json: JSON string containing service account credentials
            service_account_file: Path to service account JSON file
        """
        if not GOOGLE_API_AVAILABLE:
            raise DocumentReadError(
                "Google API libraries not installed. "
                "Install with: pip install google-api-python-client google-auth"
            )
        
        self.credentials = None
        self.service = None
        
        # Try to get credentials from various sources
        if service_account_json:
            self._auth_from_json(service_account_json)
        elif service_account_file:
            self._auth_from_file(service_account_file)
        else:
            # Try environment variables
            env_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
            env_file = os.environ.get('GOOGLE_SERVICE_ACCOUNT_FILE')
            
            if env_json:
                self._auth_from_json(env_json)
            elif env_file:
                self._auth_from_file(env_file)
            else:
                logger.warning("No Google service account credentials provided")
    
    def _auth_from_json(self, json_str: str) -> None:
        """Authenticate using JSON string."""
        try:
            creds_dict = json.loads(json_str)
            self.credentials = service_account.Credentials.from_service_account_info(
                creds_dict, scopes=self.SCOPES
            )
            self.service = build('drive', 'v3', credentials=self.credentials)
            logger.info("Authenticated with Google Drive using service account")
        except Exception as e:
            logger.error(f"Failed to authenticate with Google service account: {e}")
            raise DocumentReadError(f"Google authentication failed: {e}")
    
    def _auth_from_file(self, file_path: str) -> None:
        """Authenticate using JSON file."""
        try:
            self.credentials = service_account.Credentials.from_service_account_file(
                file_path, scopes=self.SCOPES
            )
            self.service = build('drive', 'v3', credentials=self.credentials)
            logger.info("Authenticated with Google Drive using service account file")
        except Exception as e:
            logger.error(f"Failed to authenticate with Google service account file: {e}")
            raise DocumentReadError(f"Google authentication failed: {e}")
    
    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        return self.service is not None
    
    @staticmethod
    def extract_file_id(url: str) -> Optional[str]:
        """
        Extract file ID from Google Drive URL.
        
        Supports various URL formats:
        - https://drive.google.com/file/d/{id}/view
        - https://drive.google.com/open?id={id}
        - https://docs.google.com/spreadsheets/d/{id}/edit
        """
        patterns = [
            r'/file/d/([a-zA-Z0-9_-]+)',
            r'/spreadsheets/d/([a-zA-Z0-9_-]+)',
            r'/document/d/([a-zA-Z0-9_-]+)',
            r'[?&]id=([a-zA-Z0-9_-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    @staticmethod
    def is_google_drive_url(url: str) -> bool:
        """Check if URL is a Google Drive URL."""
        if not url:
            return False
        return 'drive.google.com' in url.lower() or 'docs.google.com' in url.lower()
    
    def download_file(self, url: str, local_path: Optional[Path] = None) -> Path:
        """
        Download file from Google Drive.
        
        Args:
            url: Google Drive sharing URL
            local_path: Optional local path to save file
            
        Returns:
            Path to downloaded file
        """
        if not self.is_authenticated():
            raise DocumentReadError("Google Drive client not authenticated")
        
        file_id = self.extract_file_id(url)
        if not file_id:
            raise DocumentReadError(f"Could not extract file ID from URL: {url}")
        
        try:
            # Get file metadata
            file_metadata = self.service.files().get(
                fileId=file_id,
                fields='name, mimeType'
            ).execute()
            
            file_name = file_metadata.get('name', 'downloaded_file')
            mime_type = file_metadata.get('mimeType', '')
            
            logger.info(f"Downloading {file_name} from Google Drive")
            
            # Create local path if not provided
            if local_path is None:
                suffix = Path(file_name).suffix or '.xlsx'
                temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
                local_path = Path(temp_file.name)
                temp_file.close()
            
            # Handle Google Workspace files (Sheets, Docs) - export as Office format
            if 'spreadsheet' in mime_type:
                # Export Google Sheets as Excel
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            elif 'document' in mime_type:
                # Export Google Docs as Word
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                )
            else:
                # Regular file download
                request = self.service.files().get_media(fileId=file_id)
            
            # Download the file
            with open(local_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            
            logger.info(f"Downloaded to: {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"Failed to download from Google Drive: {e}")
            raise DocumentReadError(f"Google Drive download failed: {e}")
    
    def upload_file(self, local_path: Path, url: str) -> str:
        """
        Upload/update file on Google Drive.
        
        Args:
            local_path: Path to local file
            url: Google Drive sharing URL (file to update)
            
        Returns:
            Updated file URL
        """
        if not self.is_authenticated():
            raise DocumentWriteError("Google Drive client not authenticated")
        
        file_id = self.extract_file_id(url)
        if not file_id:
            raise DocumentWriteError(f"Could not extract file ID from URL: {url}")
        
        try:
            # Get file metadata to check mime type
            file_metadata = self.service.files().get(
                fileId=file_id,
                fields='name, mimeType'
            ).execute()
            
            file_name = file_metadata.get('name', 'uploaded_file')
            mime_type = file_metadata.get('mimeType', '')
            
            logger.info(f"Uploading {local_path.name} to Google Drive as {file_name}")
            
            # Determine mime type for upload
            if local_path.suffix.lower() == '.xlsx':
                upload_mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            elif local_path.suffix.lower() == '.docx':
                upload_mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            else:
                upload_mime_type = 'application/octet-stream'
            
            # Create media upload object
            media = MediaFileUpload(
                str(local_path),
                mimetype=upload_mime_type,
                resumable=True
            )
            
            # Update existing file
            updated_file = self.service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
            
            logger.info(f"Successfully uploaded to Google Drive: {file_name}")
            return f"https://drive.google.com/file/d/{file_id}/view"
            
        except Exception as e:
            error_str = str(e)
            
            # Check for common errors and provide helpful messages
            if '404' in error_str or 'not found' in error_str.lower():
                service_email = self.get_service_account_email()
                error_msg = (
                    f"File not accessible by service account.\n"
                    f"Please share your Google Drive file with the service account email:\n"
                    f"  {service_email}\n"
                    f"(Give Editor permission, then try again)"
                )
                logger.error(error_msg)
                raise DocumentWriteError(error_msg)
            elif '403' in error_str or 'forbidden' in error_str.lower():
                logger.error("Permission denied. Ensure the file is shared with Editor permission.")
                raise DocumentWriteError("Google Drive permission denied. Share the file with Editor permission.")
            else:
                logger.error(f"Failed to upload to Google Drive: {e}")
                raise DocumentWriteError(f"Google Drive upload failed: {e}")
    
    def get_service_account_email(self) -> Optional[str]:
        """Get the service account email for sharing instructions."""
        if self.credentials:
            return self.credentials.service_account_email
        return None
