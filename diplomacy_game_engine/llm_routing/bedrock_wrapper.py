"""
Wrapper around existing BedrockClient to implement LLMClient interface.
"""

from typing import Dict, Any, Optional
from .llm_client import LLMClient
from diplomacy_game_engine.llm.bedrock_client import BedrockClient


class BedrockClientWrapper(LLMClient):
    """
    Wrapper around existing BedrockClient.
    
    This wrapper adapts the existing BedrockClient to the LLMClient interface,
    ensuring backward compatibility while enabling multi-provider support.
    """
    
    def __init__(
        self,
        model_id: str,
        region: str = "eu-west-1",
        profile_name: Optional[str] = None
    ):
        """
        Initialize Bedrock client wrapper.
        
        Args:
            model_id: Bedrock model ID (e.g., "eu.anthropic.claude-haiku-4-5-20251001-v1:0")
            region: AWS region
            profile_name: AWS profile name (optional)
        """
        self.model_id = model_id
        self.client = BedrockClient(region=region, profile_name=profile_name)
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Generate a response using Bedrock.
        
        Args:
            prompt: The user prompt/message
            system_prompt: Optional system prompt for context
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response
            
        Returns:
            Dict with 'content' and 'usage' keys
        """
        # Call existing BedrockClient
        response = self.client.generate(
            model_id=self.model_id,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Response is already in the correct format
        return response
    
    def get_model_id(self) -> str:
        """Get the Bedrock model ID."""
        return self.model_id
