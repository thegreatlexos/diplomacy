"""
OpenRouter client implementation.
"""

from typing import Dict, Any, Optional
from .llm_client import LLMClient
import logging

logger = logging.getLogger(__name__)


class OpenRouterClient(LLMClient):
    """
    Client for OpenRouter API.
    
    Provides access to 300+ models through OpenRouter's unified API.
    """
    
    def __init__(self, model_id: str, api_key: str):
        """
        Initialize OpenRouter client.
        
        Args:
            model_id: OpenRouter model ID (e.g., "anthropic/claude-4.5-sonnet")
            api_key: OpenRouter API key
        """
        self.model_id = model_id
        self.api_key = api_key
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of OpenRouter client."""
        if self._client is None:
            try:
                from openrouter import OpenRouter
                self._client = OpenRouter(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "OpenRouter SDK not installed. Install with: pip install openrouter"
                )
        return self._client
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Generate a response using OpenRouter.
        
        Args:
            prompt: The user prompt/message
            system_prompt: Optional system prompt for context
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response
            
        Returns:
            Dict with 'content' and 'usage' keys
        """
        client = self._get_client()
        
        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            # Call OpenRouter API
            response = client.chat.send(
                model=self.model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Extract content and usage
            content = response.choices[0].message.content
            usage = {
                'input_tokens': response.usage.prompt_tokens,
                'output_tokens': response.usage.completion_tokens,
                'total_tokens': response.usage.total_tokens
            }
            
            return {
                'content': content,
                'usage': usage
            }
            
        except Exception as e:
            # Log the full error details for debugging
            error_msg = f"OpenRouter API call failed: {e}"
            if hasattr(e, 'response'):
                try:
                    error_msg += f"\nResponse: {e.response.text}"
                except:
                    pass
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def get_model_id(self) -> str:
        """Get the OpenRouter model ID."""
        return self.model_id
