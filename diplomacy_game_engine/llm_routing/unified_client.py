"""
Unified client adapter for backward compatibility.

This adapter wraps both BedrockClient and OpenRouterClient to provide
a consistent interface matching the original BedrockClient API signature.
"""

from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class UnifiedLLMClient:
    """
    Unified adapter that wraps LLM routing clients to match BedrockClient interface.
    
    This allows existing code using bedrock_client.invoke_model() to work
    transparently with any LLM provider (Bedrock, OpenRouter, etc.).
    """
    
    def __init__(self, routing_client):
        """
        Initialize unified client.
        
        Args:
            routing_client: An LLMClient instance (BedrockClientWrapper or OpenRouterClient)
        """
        self.routing_client = routing_client
        logger.info(f"UnifiedLLMClient initialized with {type(routing_client).__name__}")
    
    def invoke_model(
        self,
        model_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> Tuple[str, Dict[str, int]]:
        """
        Invoke model using unified interface (matches BedrockClient signature).
        
        Args:
            model_id: Model identifier (used for logging, actual model set at init)
            prompt: The user prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            
        Returns:
            Tuple of (response_text, token_usage_dict)
            token_usage_dict contains: {"input_tokens": int, "output_tokens": int, "total_tokens": int}
        """
        try:
            # Call the routing client's generate method
            response = self.routing_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Extract text and usage from response
            text = response['content']
            usage = response['usage']
            
            # Convert to BedrockClient format (ensure integers)
            token_usage = {
                'input_tokens': int(usage['input_tokens']),
                'output_tokens': int(usage['output_tokens']),
                'total_tokens': int(usage['total_tokens'])
            }
            
            return text, token_usage
            
        except Exception as e:
            logger.error(f"UnifiedLLMClient error: {e}")
            raise
    
    def generate(
        self,
        model_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Alternative interface that returns dict format.
        
        This method provides the new-style interface while invoke_model
        provides backward compatibility.
        """
        text, usage = self.invoke_model(
            model_id=model_id,
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return {
            'content': text,
            'usage': usage
        }
