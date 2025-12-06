"""
LLM model client for test case generation
Supports Google Gemini, OpenAI GPT-4, and Hugging Face models
"""

from typing import Optional
import os

from src.utils.exceptions import LLMGenerationError
from src.utils.logger import get_logger, log_execution_time

logger = get_logger(__name__)


class ModelClient:
    """Client for LLM model interactions supporting Gemini, OpenAI, and Hugging Face"""
    
    def __init__(
        self,
        provider: str = "gemini",
        model_name: str = "gemini-1.5-pro",
        api_token: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 300,
        **kwargs
    ):
        """
        Initialize model client
        
        Args:
            provider: 'gemini', 'openai', or 'huggingface'
            model_name: Model name
            api_token: API token/key
            max_retries: Maximum retry attempts
            timeout: Timeout for API calls in seconds
        """
        self.provider = provider.lower()
        self.model_name = model_name
        self.api_token = api_token
        self.max_retries = max_retries
        self.timeout = timeout
        
        logger.info(f"Initializing model client with provider: {self.provider}")
        logger.info(f"Model: {self.model_name}")
        
        if self.provider == "gemini":
            self._init_gemini()
        elif self.provider == "openai":
            self._init_openai()
        elif self.provider == "huggingface":
            self._init_huggingface()
        else:
            raise ValueError(f"Unsupported provider: {provider}. Use 'gemini', 'openai', or 'huggingface'")
    
    def _init_gemini(self):
        """Initialize Google Gemini client"""
        try:
            import google.generativeai as genai
            
            if not self.api_token:
                self.api_token = os.getenv('GEMINI_API_KEY')
            
            if not self.api_token:
                raise ValueError(
                    "Gemini API key is required. Set GEMINI_API_KEY in .env or pass api_token parameter.\n"
                    "Get your FREE API key at: https://makersuite.google.com/app/apikey"
                )
            
            genai.configure(api_key=self.api_token)
            
            # Normalize model name - the API uses 'models/' prefix
            # Map common short names to full model names
            model_mapping = {
                # Legacy names -> modern equivalents
                'gemini-pro': 'models/gemini-2.0-flash',
                'gemini-1.5-pro': 'models/gemini-2.5-pro',
                'gemini-1.5-flash': 'models/gemini-2.0-flash',
                'gemini-flash': 'models/gemini-2.0-flash',
                # Direct full names (without models/ prefix)
                'gemini-2.0-flash': 'models/gemini-2.0-flash',
                'gemini-2.5-flash': 'models/gemini-2.5-flash',
                'gemini-2.5-pro': 'models/gemini-2.5-pro',
                'gemini-2.0-pro-exp': 'models/gemini-2.0-pro-exp',
            }
            
            # Use mapped name or add 'models/' prefix if needed
            if self.model_name in model_mapping:
                actual_model = model_mapping[self.model_name]
            elif not self.model_name.startswith('models/'):
                actual_model = f'models/{self.model_name}'
            else:
                actual_model = self.model_name
            logger.info(f"Using Gemini model: {actual_model}")
            
            self.client = genai.GenerativeModel(actual_model)
            logger.info("Gemini client initialized successfully")
            logger.info("Using Google Gemini API")
            
        except ImportError:
            raise ImportError(
                "Google Generative AI package not installed. Install with: pip install google-generativeai"
            )
    
    def _init_openai(self):
        """Initialize OpenAI client"""
        try:
            from openai import OpenAI
            
            if not self.api_token:
                self.api_token = os.getenv('OPENAI_API_KEY')
            
            if not self.api_token:
                raise ValueError(
                    "OpenAI API key is required. Set OPENAI_API_KEY in .env or pass api_token parameter.\n"
                    "Get your API key at: https://platform.openai.com/api-keys"
                )
            
            self.client = OpenAI(api_key=self.api_token, timeout=self.timeout)
            logger.info("OpenAI client initialized successfully")
            
        except ImportError:
            raise ImportError(
                "OpenAI package not installed. Install with: pip install openai>=1.0.0"
            )
    
    def _init_huggingface(self):
        """Initialize Hugging Face client"""
        self.api_url = "https://router.huggingface.co/v1/chat/completions"
        
        if not self.api_token:
            logger.warning("No Hugging Face API token provided. Requests may be rate-limited.")
            logger.warning("Get a free token at: https://huggingface.co/settings/tokens")
        
        logger.info("Using Hugging Face Router API (OpenAI-compatible format)")
    
    @log_execution_time(logger)
    def generate(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.3,
        top_p: float = 0.9,
        num_return_sequences: int = 1
    ) -> str:
        """
        Generate text from prompt
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            num_return_sequences: Number of sequences to generate
            
        Returns:
            Generated text
            
        Raises:
            LLMGenerationError: If generation fails
        """
        if self.provider == "gemini":
            return self._generate_gemini(prompt, max_tokens, temperature, top_p)
        elif self.provider == "openai":
            return self._generate_openai(prompt, max_tokens, temperature, top_p)
        else:
            return self._generate_huggingface(prompt, max_tokens, temperature, top_p)
    
    def _generate_gemini(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float
    ) -> str:
        """Generate using Google Gemini API"""
        try:
            logger.debug(f"Generating with Gemini {self.model_name}")
            logger.debug(f"Prompt length: {len(prompt)} characters")
            
            generation_config = {
                "max_output_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
            }
            
            response = self.client.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            generated_text = response.text
            
            logger.debug(f"Generated {len(generated_text)} characters")
            logger.info("Gemini API call successful (FREE)")
            
            return generated_text
            
        except Exception as e:
            logger.error(f"Gemini generation failed: {str(e)}")
            raise LLMGenerationError(f"Gemini generation failed: {str(e)}")
    
    def _generate_openai(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float
    ) -> str:
        """Generate using OpenAI API"""
        try:
            logger.debug(f"Generating with OpenAI {self.model_name}")
            logger.debug(f"Prompt length: {len(prompt)} characters")
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert QA engineer specializing in creating detailed, comprehensive test cases for software applications."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                n=1
            )
            
            generated_text = response.choices[0].message.content
            
            logger.debug(f"Generated {len(generated_text)} characters")
            logger.info(f"OpenAI API call successful. Tokens used: {response.usage.total_tokens}")
            
            return generated_text
            
        except Exception as e:
            logger.error(f"OpenAI generation failed: {str(e)}")
            raise LLMGenerationError(f"OpenAI generation failed: {str(e)}")
    
    def _generate_huggingface(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float
    ) -> str:
        """Generate using Hugging Face API"""
        import requests
        import time
        
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": False
        }
        
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Attempt {attempt + 1}/{self.max_retries}")
                
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    generated_text = result['choices'][0]['message']['content']
                    logger.info("Hugging Face generation successful")
                    return generated_text
                
                elif response.status_code == 503:
                    wait_time = min(2 ** attempt, 30)
                    logger.warning(f"Model loading (503). Waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                else:
                    error_msg = f"API error {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    raise LLMGenerationError(error_msg)
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout on attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    raise LLMGenerationError("Request timed out after all retries")
            
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise LLMGenerationError(f"Request failed: {str(e)}")
        
        raise LLMGenerationError("Failed after all retry attempts")
