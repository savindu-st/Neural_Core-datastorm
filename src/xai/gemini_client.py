"""
Gemini AI API Client for QuadNova XAI
Uses Google's modern genai SDK for outlet explanation generation
"""

from google import genai
from google.genai import types, errors
import logging
from typing import Optional
import time

logger = logging.getLogger(__name__)

class GeminiClient:
    """Google Gemini AI Client for generating outlet explanations."""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        """
        Initialize modern Gemini client.
        
        Args:
            api_key: Google Gemini API key
            model: Model name (gemini-1.5-flash is recommended for speed/free tier)
        """
        self.api_key = api_key
        self.model_name = model
        self.initialize_client()
    
    def initialize_client(self):
        """Initialize and configure Gemini client."""
        try:
            # New SDK initialization standard
            self.client = genai.Client(api_key=self.api_key)
            logger.info(f"✅ Gemini client initialized targeting model: {self.model_name}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini client: {e}")
            raise
    
    def call(self, prompt: str, system_prompt: str = None, retries: int = 3) -> Optional[str]:
        """
        Call Gemini API with retry logic.
        
        Args:
            prompt: User prompt with outlet data
            system_prompt: System context (Now natively supported by the API!)
            retries: Number of retry attempts
        
        Returns:
            Generated explanation or None if failed
        """
        
        # The new SDK uses a dedicated GenerateContentConfig object
        config = types.GenerateContentConfig(
            system_instruction=system_prompt, # Native system prompt injection
            temperature=0.7,
            top_p=0.95,
            top_k=40,
            max_output_tokens=500,
        )
        
        for attempt in range(retries):
            try:
                logger.debug(f"Gemini API call (attempt {attempt + 1}/{retries})...")
                
                # New SDK call format
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config
                )
                
                if response and response.text:
                    logger.info(f"✅ Gemini API call successful. Length: {len(response.text)} chars")
                    return response.text.strip()
                else:
                    logger.warning(f"⚠️ Gemini returned empty response (attempt {attempt + 1}/{retries})")
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)
                    continue
                    
            except errors.APIError as e:
                logger.warning(f"⚠️ Gemini API Error (attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"   Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ Gemini API failed after {retries} attempts")
                    return None
            except Exception as e:
                logger.error(f"❌ Unexpected Gemini error: {e}")
                return None
        
        return None
    
    def test_connection(self) -> bool:
        """Test API connection with simple prompt."""
        try:
            config = types.GenerateContentConfig(max_output_tokens=10)
            response = self.client.models.generate_content(
                model=self.model_name,
                contents="Respond with 'OK' if you are working properly.",
                config=config
            )
            if response and response.text:
                logger.info("✅ Gemini API connection test PASSED")
                return True
        except Exception as e:
            logger.error(f"❌ Gemini API connection test FAILED: {e}")
        return False