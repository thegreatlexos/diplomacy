"""
Abstract base class for LLM clients.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class LLMClient(ABC):
    """
    Abstract base class for LLM clients.
    
    All LLM clients (Bedrock, OpenRouter, etc.) must implement this interface
    to ensure consistent behavior across providers.
    """
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Generate a response from the LLM.
        
        Args:
            prompt: The user prompt/message
            system_prompt: Optional system prompt for context
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response
            
        Returns:
            Dict with the following structure:
            {
                'content': str,  # The generated text
                'usage': {
                    'input_tokens': int,
                    'output_tokens': int,
                    'total_tokens': int
                }
            }
            
        Raises:
            Exception: If the API call fails
        """
        pass
    
    @abstractmethod
    def get_model_id(self) -> str:
        """
        Get the model ID being used by this client.
        
        Returns:
            The model ID string
        """
        pass
