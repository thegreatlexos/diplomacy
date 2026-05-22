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

        # Adjust max_tokens for reasoning/thinking models that need headroom
        reasoning_models = ["gpt-5-mini", "gpt-5.5", "deepseek-v4-pro", "deepseek-v4-flash", "claude-opus"]
        if any(m in self.model_id.lower() for m in reasoning_models):
            max_tokens = max(max_tokens, 8000)
            logger.debug(f"Increased max_tokens to {max_tokens} for reasoning model {self.model_id}")

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
            
            # Extract content and usage with debug logging
            logger.debug(f"OpenRouter response structure: {type(response)}")
            logger.debug(f"Response choices: {hasattr(response, 'choices')} - {len(response.choices) if hasattr(response, 'choices') and response.choices else 0}")

            if hasattr(response, 'choices') and response.choices:
                choice = response.choices[0]
                logger.debug(f"First choice finish_reason: {getattr(choice, 'finish_reason', 'unknown')}")
                if hasattr(choice, 'message'):
                    message = choice.message

                    # Try content first, then reasoning field (for OpenAI reasoning models)
                    content = getattr(message, 'content', None)
                    reasoning = getattr(message, 'reasoning', None)

                    logger.debug(f"Content available: {content is not None}")
                    logger.debug(f"Reasoning available: {reasoning is not None}")

                    if content is None and reasoning is not None:
                        logger.info("Using reasoning field as content (OpenAI reasoning model)")
                        # Extract orders from reasoning field for GPT-5-mini
                        extracted_orders = self._extract_orders_from_reasoning(reasoning)
                        if extracted_orders:
                            logger.info("Extracted orders from reasoning field")
                            content = extracted_orders
                        else:
                            logger.warning("No orders found in reasoning field, returning empty content")
                            logger.debug(f"Failed reasoning text sample: {reasoning[:500]}...")
                            # Write full reasoning to debug file for analysis
                            import os
                            from datetime import datetime
                            debug_file = "/tmp/gpt5_mini_failed_reasoning.txt"
                            try:
                                with open(debug_file, "w") as f:
                                    f.write("=== GPT-5-mini Failed Reasoning Response ===\n")
                                    f.write(f"Timestamp: {datetime.now()}\n")
                                    f.write(f"Full reasoning text:\n{reasoning}\n")
                                logger.info(f"Full reasoning text saved to {debug_file}")
                            except Exception as e:
                                logger.warning(f"Could not save debug file: {e}")
                            content = ""  # Return empty instead of raw reasoning

                    logger.debug(f"Final content: {content[:100] if content else None}... (type: {type(content)})")
                else:
                    logger.error("Choice has no message attribute")
                    content = None
            else:
                logger.error("Response has no choices or choices is empty")
                content = None

            if content is None:
                # Check if this was a token limit issue
                if (hasattr(response, 'choices') and response.choices and
                    hasattr(response.choices[0], 'finish_reason') and
                    response.choices[0].finish_reason == 'length'):
                    logger.warning("Response truncated due to token limit, treating as empty content")
                    content = ""  # Return empty content for clean auto-hold
                else:
                    logger.error(f"Content is None! Full response: {response}")
                    raise RuntimeError("OpenRouter returned None content")

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

            # Check for specific JSON parsing errors (truncated responses)
            if "EOF while parsing" in str(e) or "Expecting" in str(e):
                logger.warning(f"JSON parsing error detected, likely truncated response: {e}")
                error_msg = f"OpenRouter response truncated or malformed: {e}"

            if hasattr(e, 'response'):
                try:
                    error_msg += f"\nResponse: {e.response.text}"
                except Exception:
                    pass
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def get_model_id(self) -> str:
        """Get the OpenRouter model ID."""
        return self.model_id

    def _extract_orders_from_reasoning(self, reasoning_text: str) -> str:
        """Extract orders from GPT-5-mini reasoning field text."""
        if not reasoning_text:
            return ""

        import re

        # Look for orders block patterns in reasoning text
        patterns = [
            r'```\s*orders[:\s]*\n(.*?)```',           # ```orders\n...\n```
            r'```orders[:\s]*\n(.*?)\n```',            # ```orders:...\n```
            r'```\s*orders[:\s]*\n(.*?)\n```',         # ``` orders...\n```
            r'```\s*\n([FA].*?)```',                   # ```\nF/A orders\n```
            r'Final orders?[:\s]*\n(.*?)(?:\n\n|\Z)', # Final orders: ...
            r'My orders?[:\s]*\n(.*?)(?:\n\n|\Z)',    # My orders: ...
        ]

        for pattern in patterns:
            match = re.search(pattern, reasoning_text, re.DOTALL | re.IGNORECASE)
            if match:
                orders = match.group(1).strip()
                if orders and ('F ' in orders or 'A ' in orders):
                    return orders

        # Enhanced fallback: look for F/A unit patterns anywhere
        unit_patterns = [
            r'([FA])\s+([A-Za-z]{3})\s*[-–—→]\s*([A-Za-z]{3})',  # F Lon - ENG
            r'([FA])\s+([A-Za-z]{3})\s+to\s+([A-Za-z]{3})',      # F Lon to ENG
            r'([FA])\s+([A-Za-z]{3})\s*:\s*([A-Za-z]{3})',       # F Lon: ENG
        ]

        orders = []
        for pattern in unit_patterns:
            matches = re.findall(pattern, reasoning_text, re.IGNORECASE)
            for match in matches:
                unit_type, from_loc, to_loc = match
                orders.append(f"{unit_type.upper()} {from_loc.title()} - {to_loc.title()}")

        if orders:
            return "\n".join(orders)

        return ""
