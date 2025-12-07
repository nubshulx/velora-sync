"""
Cloud file downloader for various cloud storage providers
Supports: OneDrive, Google Drive, Dropbox, and generic URLs
"""

import re
import base64
import tempfile
import requests
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse, quote, unquote

from src.utils.exceptions import DocumentReadError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CloudFileDownloader:
    """
    Downloads files from cloud storage providers using public sharing links.
    Converts sharing links to direct download URLs.
    """
    
    # Timeout for HTTP requests (seconds)
    REQUEST_TIMEOUT = 60
    
    # Provider detection patterns
    PROVIDER_PATTERNS = {
        'onedrive': [
            r'1drv\.ms',
            r'onedrive\.live\.com',
            r'sharepoint\.com.*personal',  # Personal OneDrive via SharePoint
        ],
        'google_drive': [
            r'drive\.google\.com',
            r'docs\.google\.com',
        ],
        'dropbox': [
            r'dropbox\.com',
            r'db\.tt',
        ],
        'sharepoint': [
            r'sharepoint\.com(?!.*personal)',  # Enterprise SharePoint, not personal OneDrive
        ],
    }
    
    def __init__(self, timeout: int = 60):
        """
        Initialize cloud file downloader
        
        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def detect_provider(self, url: str) -> Optional[str]:
        """
        Detect which cloud storage provider the URL belongs to
        
        Args:
            url: The sharing URL
            
        Returns:
            Provider name ('onedrive', 'google_drive', 'dropbox', 'sharepoint') or None
        """
        url_lower = url.lower()
        
        for provider, patterns in self.PROVIDER_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url_lower):
                    return provider
        
        return None
    
    def is_cloud_url(self, url: str) -> bool:
        """
        Check if URL is a cloud storage URL (not local file)
        
        Args:
            url: Path or URL to check
            
        Returns:
            True if it's a cloud URL, False if local
        """
        if not url:
            return False
        
        # Check if it's a URL (starts with http/https)
        if url.startswith(('http://', 'https://')):
            return True
        
        # Check for common cloud storage domains
        provider = self.detect_provider(url)
        return provider is not None
    
    def download_file(self, url: str, local_path: Optional[Path] = None) -> Path:
        """
        Download file from cloud storage to local path
        
        Args:
            url: Cloud storage sharing URL
            local_path: Optional local path to save file (auto-generates if None)
            
        Returns:
            Path to downloaded file
            
        Raises:
            DocumentReadError: If download fails
        """
        provider = self.detect_provider(url)
        
        logger.info(f"Downloading from {provider or 'direct URL'}: {url[:80]}...")
        
        try:
            # Get direct download URL based on provider
            if provider == 'onedrive':
                download_url = self._get_onedrive_download_url(url)
            elif provider == 'google_drive':
                download_url = self._get_google_drive_download_url(url)
            elif provider == 'dropbox':
                download_url = self._get_dropbox_download_url(url)
            elif provider == 'sharepoint':
                # SharePoint requires authentication, raise error suggesting to use SharePointClient
                raise DocumentReadError(
                    "SharePoint URLs require authentication. Please configure SharePoint credentials in .env"
                )
            else:
                # Assume direct download URL
                download_url = url
            
            # Create local path if not provided
            if local_path is None:
                suffix = self._guess_file_extension(url)
                temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
                local_path = Path(temp_file.name)
                temp_file.close()
            
            # Download the file
            self._download_to_file(download_url, local_path)
            
            logger.info(f"Downloaded successfully to: {local_path}")
            return local_path
            
        except DocumentReadError:
            raise
        except Exception as e:
            logger.error(f"Failed to download from {url}: {str(e)}")
            raise DocumentReadError(f"Failed to download file: {str(e)}")
    
    def _get_onedrive_download_url(self, share_url: str) -> str:
        """
        Convert OneDrive sharing link to direct download URL
        
        OneDrive public links work by following redirects and extracting
        the resid parameter to construct a download URL.
        """
        try:
            logger.info(f"Converting OneDrive URL: {share_url[:60]}...")
            
            # Method 1: Follow redirects and get the final view URL
            response = self.session.get(
                share_url, 
                allow_redirects=True, 
                timeout=self.timeout,
                stream=True
            )
            final_url = response.url
            
            # Get the HTML content to extract download link
            content = response.content.decode('utf-8', errors='ignore')
            response.close()
            
            logger.debug(f"OneDrive redirect URL: {final_url[:100]}...")
            
            # Method 2: Try to find direct download URL in the HTML
            # Look for download URL patterns in the page
            download_patterns = [
                r'"downloadUrl"\s*:\s*"([^"]+)"',
                r'href="([^"]*download[^"]*)"',
                r'"url"\s*:\s*"([^"]*\.(?:docx|xlsx|doc|xls)[^"]*)"',
            ]
            
            for pattern in download_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    download_url = match.group(1)
                    # Unescape URL
                    download_url = download_url.replace('\\u0026', '&').replace('\\/', '/')
                    logger.info(f"Found download URL in page")
                    return download_url
            
            # Method 3: Extract resid and authkey from URL to construct download
            resid_match = re.search(r'resid=([^&]+)', final_url)
            authkey_match = re.search(r'authkey=([^&]+)', final_url)
            
            if resid_match:
                resid = resid_match.group(1)
                authkey = authkey_match.group(1) if authkey_match else ''
                
                # Construct the download URL
                download_url = f"https://onedrive.live.com/download?resid={resid}"
                if authkey:
                    download_url += f"&authkey={authkey}"
                
                logger.info(f"Constructed download URL from resid")
                return download_url
            
            # Method 4: Extract cid and id from URL path
            # Pattern: /c/{cid}/{id}
            cid_match = re.search(r'/c/([a-f0-9]+)/([A-Za-z0-9_-]+)', share_url)
            if cid_match:
                cid = cid_match.group(1)
                file_id = cid_match.group(2)
                download_url = f"https://onedrive.live.com/download?cid={cid}&resid={cid.upper()}!{file_id}"
                logger.info(f"Constructed download URL from cid/id")
                return download_url
            
            # Method 5: Fallback - add download parameter
            if '?' in final_url:
                download_url = final_url + '&download=1'
            else:
                download_url = final_url + '?download=1'
            
            return download_url
            
        except Exception as e:
            logger.warning(f"OneDrive URL conversion failed: {e}")
            # Fallback
            if '?' in share_url:
                return share_url + '&download=1'
            else:
                return share_url + '?download=1'
    
    def _get_google_drive_download_url(self, share_url: str) -> str:
        """
        Convert Google Drive sharing link to direct download URL
        
        Formats:
        - https://drive.google.com/file/d/{file_id}/view
        - https://drive.google.com/open?id={file_id}
        - https://docs.google.com/document/d/{file_id}/edit
        """
        try:
            # Extract file ID
            file_id = None
            
            # Pattern 1: /file/d/{id}/
            match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', share_url)
            if match:
                file_id = match.group(1)
            
            # Pattern 2: /document/d/{id}/
            if not file_id:
                match = re.search(r'/document/d/([a-zA-Z0-9_-]+)', share_url)
                if match:
                    file_id = match.group(1)
            
            # Pattern 3: ?id={id}
            if not file_id:
                match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', share_url)
                if match:
                    file_id = match.group(1)
            
            if not file_id:
                raise DocumentReadError(f"Could not extract file ID from Google Drive URL: {share_url}")
            
            # Construct download URL
            download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            
            return download_url
            
        except DocumentReadError:
            raise
        except Exception as e:
            raise DocumentReadError(f"Failed to parse Google Drive URL: {str(e)}")
    
    def _get_dropbox_download_url(self, share_url: str) -> str:
        """
        Convert Dropbox sharing link to direct download URL
        
        Simply replace dl=0 with dl=1, or add ?dl=1
        """
        if 'dl=0' in share_url:
            return share_url.replace('dl=0', 'dl=1')
        elif 'dl=1' in share_url:
            return share_url
        elif '?' in share_url:
            return share_url + '&dl=1'
        else:
            return share_url + '?dl=1'
    
    def _download_to_file(self, url: str, local_path: Path, max_retries: int = 3) -> None:
        """
        Download file from URL to local path with retries
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout, stream=True)
                response.raise_for_status()
                
                # Check content type
                content_type = response.headers.get('content-type', '')
                if 'text/html' in content_type:
                    # Might be a login page or error page
                    content_preview = response.content[:500].decode('utf-8', errors='ignore')
                    if 'sign in' in content_preview.lower() or 'login' in content_preview.lower():
                        raise DocumentReadError(
                            "The file requires authentication. Make sure the sharing link is set to 'Anyone with the link'."
                        )
                
                # Write to file
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # Verify file was downloaded
                if not local_path.exists() or local_path.stat().st_size == 0:
                    raise DocumentReadError("Downloaded file is empty")
                
                return
                
            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < max_retries - 1:
                    logger.warning(f"Download attempt {attempt + 1} failed, retrying...")
                    continue
        
        raise DocumentReadError(f"Failed to download file after {max_retries} attempts: {last_error}")
    
    def _guess_file_extension(self, url: str) -> str:
        """
        Guess file extension from URL
        """
        # Parse URL path
        parsed = urlparse(url)
        path = unquote(parsed.path)
        
        # Check for common extensions
        for ext in ['.docx', '.doc', '.xlsx', '.xls', '.pdf', '.txt']:
            if ext in path.lower():
                return ext
        
        # Default to .docx for Word documents
        return '.docx'
