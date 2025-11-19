"""
LLM routing module for multi-provider support.

This module provides an abstraction layer for routing LLM calls to different providers
(AWS Bedrock, OpenRouter, etc.) based on model ID format.
"""

from .llm_client import LLMClient
from .bedrock_wrapper import BedrockClientWrapper
from .openrouter_client import OpenRouterClient
from .client_factory import LLMClientFactory

__all__ = [
    'LLMClient',
    'BedrockClientWrapper',
    'OpenRouterClient',
    'LLMClientFactory'
]
