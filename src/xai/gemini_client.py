"""
Gemini AI API Client for QuadNova XAI
Uses Google's Gemini LLM for outlet explanation generation
"""

import google.generativeai as genai
import logging
from typing import Optional
import time

logger = logging.getLogger(__name__)


class GeminiClient:
    """Google Gemini AI Client for generating outlet explanations."""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Google Gemini API key
            model: Model name (gemini-1.5-pro, gemini-1.5-flash, etc.)
        """
        self.api_key = api_key
        self.model_name = model
        self.initialize_client()
    
    def initialize_client(self):
        """Initialize and configure Gemini client."""
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.model_name)
            logger.info(f"✅ Gemini client initialized with model: {self.model_name}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini client: {e}")
            raise
    
    def call(self, prompt: str, system_prompt: str = None, retries: int = 3) -> Optional[str]:
        """
        Call Gemini API with retry logic.
        
        Args:
            prompt: User prompt with outlet data
            system_prompt: System context (optional - prepended to prompt for Gemini)
            retries: Number of retry attempts
        
        Returns:
            Generated explanation or None if failed
        """
        # Gemini doesn't support system prompts separately, so prepend it
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        else:
            full_prompt = prompt
        
        for attempt in range(retries):
            try:
                logger.debug(f"Gemini API call (attempt {attempt + 1}/{retries})...")
                
                response = self.model.generate_content(
                    full_prompt,
                    generation_config={
                        'temperature': 0.7,
                        'top_p': 0.95,
                        'top_k': 40,
                        'max_output_tokens': 500,
                    }
                )
                
                if response and response.text:
                    logger.info(f"✅ Gemini API call successful. Length: {len(response.text)} chars")
                    return response.text.strip()
                else:
                    logger.warning(f"⚠️ Gemini returned empty response (attempt {attempt + 1}/{retries})")
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)
                    continue
                    
            except Exception as e:
                logger.warning(f"⚠️ Gemini API call failed (attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"  Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"❌ Gemini API failed after {retries} attempts")
                    return None
        
        return None
    
    def test_connection(self) -> bool:
        """Test API connection with simple prompt."""
        try:
            response = self.model.generate_content(
                "Respond with 'OK' if you are working properly.",
                generation_config={'max_output_tokens': 10}
            )
            if response and response.text:
                logger.info("✅ Gemini API connection test PASSED")
                return True
        except Exception as e:
            logger.error(f"❌ Gemini API connection test FAILED: {e}")
        return False
