"""
Factory for creating appropriate LLM client based on model ID.
"""

from typing import Dict, Any, Optional
from .llm_client import LLMClient
from .bedrock_wrapper import BedrockClientWrapper
from .openrouter_client import OpenRouterClient
import logging

logger = logging.getLogger(__name__)


class LLMClientFactory:
    """
    Factory for creating appropriate LLM client based on model ID format.
    
    Automatically detects whether a model ID is for AWS Bedrock or OpenRouter
    and returns the appropriate client implementation.
    """
    
    # Bedrock model ID prefixes (region codes)
    BEDROCK_PREFIXES = [
        'eu.',      # Europe regions
        'us.',      # US regions
        'ap-',      # Asia Pacific regions
        'ca-',      # Canada regions
        'me-',      # Middle East regions
        'sa-',      # South America regions
        'af-',      # Africa regions
    ]
    
    @staticmethod
    def create_client(
        model_id: str,
        aws_region: Optional[str] = None,
        aws_profile: Optional[str] = None,
        openrouter_api_key: Optional[str] = None
    ) -> LLMClient:
        """
        Create appropriate LLM client based on model ID format.
        
        Args:
            model_id: Model identifier
            aws_region: AWS region for Bedrock (default: "eu-west-1")
            aws_profile: AWS profile name for Bedrock (optional)
            openrouter_api_key: OpenRouter API key (required for OpenRouter models)
            
        Returns:
            LLMClient instance (BedrockClientWrapper or OpenRouterClient)
            
        Raises:
            ValueError: If OpenRouter model is specified but no API key provided
            
        Examples:
            # Bedrock model
            client = LLMClientFactory.create_client(
                "eu.anthropic.claude-haiku-4-5-20251001-v1:0",
                aws_region="eu-west-1"
            )
            
            # OpenRouter model
            client = LLMClientFactory.create_client(
                "anthropic/claude-4.5-sonnet",
                openrouter_api_key="sk-or-..."
            )
        """
        if LLMClientFactory.is_bedrock_model(model_id):
            logger.info(f"Creating Bedrock client for model: {model_id}")
            return BedrockClientWrapper(
                model_id=model_id,
                region=aws_region or "eu-west-1",
                profile_name=aws_profile
            )
        else:
            logger.info(f"Creating OpenRouter client for model: {model_id}")
            if not openrouter_api_key:
                raise ValueError(
                    f"OpenRouter API key required for model: {model_id}\n"
                    "Set OPENROUTER_API_KEY in your .env file"
                )
            return OpenRouterClient(
                model_id=model_id,
                api_key=openrouter_api_key
            )
    
    @staticmethod
    def is_bedrock_model(model_id: str) -> bool:
        """
        Check if model ID is for AWS Bedrock.
        
        Bedrock model IDs start with region codes like:
        - eu.anthropic.claude-haiku-4-5-20251001-v1:0
        - us.anthropic.claude-sonnet-4-5-20250929-v1:0
        
        Args:
            model_id: Model identifier to check
            
        Returns:
            True if model is for Bedrock, False for OpenRouter
        """
        return any(
            model_id.startswith(prefix)
            for prefix in LLMClientFactory.BEDROCK_PREFIXES
        )
    
    @staticmethod
    def get_provider_name(model_id: str) -> str:
        """
        Get the provider name for a model ID.
        
        Args:
            model_id: Model identifier
            
        Returns:
            "bedrock" or "openrouter"
        """
        return "bedrock" if LLMClientFactory.is_bedrock_model(model_id) else "openrouter"
