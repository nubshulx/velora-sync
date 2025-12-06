"""
SharePoint client for document operations using Microsoft Graph API
"""

import requests
from typing import Optional, Dict, Any
from pathlib import Path
import msal
import time

from src.utils.exceptions import SharePointAuthError, SharePointOperationError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SharePointClient:
    """Client for SharePoint operations via Microsoft Graph API"""
    
    GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"
    AUTHORITY_URL = "https://login.microsoftonline.com/{tenant_id}"
    SCOPE = ["https://graph.microsoft.com/.default"]
    
    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        site_url: str,
        timeout: int = 300
    ):
        """
        Initialize SharePoint client
        
        Args:
            tenant_id: Azure AD tenant ID
            client_id: Azure AD application (client) ID
            client_secret: Azure AD client secret
            site_url: SharePoint site URL (e.g., https://company.sharepoint.com/sites/sitename)
            timeout: Request timeout in seconds
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.site_url = site_url
        self.timeout = timeout
        
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0
        
        logger.info(f"Initialized SharePoint client for site: {site_url}")
    
    def _get_access_token(self) -> str:
        """
        Get access token for Microsoft Graph API
        
        Returns:
            Access token string
            
        Raises:
            SharePointAuthError: If authentication fails
        """
        # Check if token is still valid
        if self._access_token and time.time() < self._token_expiry:
            return self._access_token
        
        try:
            logger.debug("Acquiring new access token")
            
            authority = self.AUTHORITY_URL.format(tenant_id=self.tenant_id)
            app = msal.ConfidentialClientApplication(
                self.client_id,
                authority=authority,
                client_credential=self.client_secret
            )
            
            result = app.acquire_token_for_client(scopes=self.SCOPE)
            
            if "access_token" in result:
                self._access_token = result["access_token"]
                # Set expiry to 5 minutes before actual expiry for safety
                self._token_expiry = time.time() + result.get("expires_in", 3600) - 300
                logger.info("Successfully acquired access token")
                return self._access_token
            else:
                error_msg = result.get("error_description", "Unknown error")
                raise SharePointAuthError(f"Failed to acquire token: {error_msg}")
                
        except Exception as e:
            logger.error(f"SharePoint authentication failed: {str(e)}")
            raise SharePointAuthError(f"Authentication failed: {str(e)}")
    
    def _get_site_id(self) -> str:
        """
        Get SharePoint site ID from site URL
        
        Returns:
            Site ID string
            
        Raises:
            SharePointOperationError: If site lookup fails
        """
        try:
            # Parse site URL to get hostname and site path
            from urllib.parse import urlparse
            parsed = urlparse(self.site_url)
            hostname = parsed.hostname
            site_path = parsed.path
            
            token = self._get_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            
            # Get site by hostname and path
            url = f"{self.GRAPH_API_ENDPOINT}/sites/{hostname}:{site_path}"
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            site_data = response.json()
            site_id = site_data["id"]
            logger.debug(f"Retrieved site ID: {site_id}")
            return site_id
            
        except Exception as e:
            logger.error(f"Failed to get site ID: {str(e)}")
            raise SharePointOperationError(f"Failed to get site ID: {str(e)}")
    
    def _get_file_item_id(self, file_url: str) -> str:
        """
        Get file item ID from SharePoint URL
        
        Args:
            file_url: Full SharePoint file URL
            
        Returns:
            File item ID
            
        Raises:
            SharePointOperationError: If file lookup fails
        """
        try:
            # Extract file path from URL
            from urllib.parse import urlparse, unquote
            parsed = urlparse(file_url)
            file_path = unquote(parsed.path)
            
            # Remove site path to get relative file path
            site_parsed = urlparse(self.site_url)
            site_path = site_parsed.path
            relative_path = file_path.replace(site_path, "").lstrip("/")
            
            site_id = self._get_site_id()
            token = self._get_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            
            # Get file by path
            url = f"{self.GRAPH_API_ENDPOINT}/sites/{site_id}/drive/root:/{relative_path}"
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            file_data = response.json()
            item_id = file_data["id"]
            logger.debug(f"Retrieved file item ID: {item_id}")
            return item_id
            
        except Exception as e:
            logger.error(f"Failed to get file item ID: {str(e)}")
            raise SharePointOperationError(f"Failed to get file item ID: {str(e)}")
    
    def download_file(self, file_url: str, local_path: Path, max_retries: int = 3) -> None:
        """
        Download file from SharePoint
        
        Args:
            file_url: SharePoint file URL
            local_path: Local path to save file
            max_retries: Maximum number of retry attempts
            
        Raises:
            SharePointOperationError: If download fails
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"Downloading file from SharePoint (attempt {attempt + 1}/{max_retries})")
                
                site_id = self._get_site_id()
                item_id = self._get_file_item_id(file_url)
                
                token = self._get_access_token()
                headers = {"Authorization": f"Bearer {token}"}
                
                # Download file content
                url = f"{self.GRAPH_API_ENDPOINT}/sites/{site_id}/drive/items/{item_id}/content"
                response = requests.get(url, headers=headers, timeout=self.timeout, stream=True)
                response.raise_for_status()
                
                # Save to local file
                local_path.parent.mkdir(parents=True, exist_ok=True)
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                logger.info(f"Successfully downloaded file to {local_path}")
                return
                
            except Exception as e:
                logger.warning(f"Download attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise SharePointOperationError(f"Failed to download file after {max_retries} attempts: {str(e)}")
                time.sleep(2 ** attempt)  # Exponential backoff
    
    def upload_file(self, local_path: Path, file_url: str, max_retries: int = 3) -> None:
        """
        Upload file to SharePoint
        
        Args:
            local_path: Local file path
            file_url: SharePoint destination URL
            max_retries: Maximum number of retry attempts
            
        Raises:
            SharePointOperationError: If upload fails
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"Uploading file to SharePoint (attempt {attempt + 1}/{max_retries})")
                
                if not local_path.exists():
                    raise SharePointOperationError(f"Local file not found: {local_path}")
                
                site_id = self._get_site_id()
                
                # Extract file path from URL
                from urllib.parse import urlparse, unquote
                parsed = urlparse(file_url)
                file_path = unquote(parsed.path)
                
                # Remove site path to get relative file path
                site_parsed = urlparse(self.site_url)
                site_path = site_parsed.path
                relative_path = file_path.replace(site_path, "").lstrip("/")
                
                token = self._get_access_token()
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/octet-stream"
                }
                
                # Upload file content
                url = f"{self.GRAPH_API_ENDPOINT}/sites/{site_id}/drive/root:/{relative_path}:/content"
                
                with open(local_path, 'rb') as f:
                    response = requests.put(url, headers=headers, data=f, timeout=self.timeout)
                    response.raise_for_status()
                
                logger.info(f"Successfully uploaded file to SharePoint")
                return
                
            except Exception as e:
                logger.warning(f"Upload attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise SharePointOperationError(f"Failed to upload file after {max_retries} attempts: {str(e)}")
                time.sleep(2 ** attempt)  # Exponential backoff
