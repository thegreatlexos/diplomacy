"""
AWS Bedrock client for invoking foundation models.
"""

import json
import boto3
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class BedrockClient:
    """Client for interacting with AWS Bedrock foundation models."""
    
    def __init__(self, region: str = "eu-west-1", profile_name: Optional[str] = None):
        """
        Initialize Bedrock client.
        
        Args:
            region: AWS region for Bedrock service
            profile_name: AWS profile name (optional, uses default if not specified)
        """
        self.region = region
        self.profile_name = profile_name
        
        # Create session with profile if specified
        if profile_name:
            session = boto3.Session(profile_name=profile_name)
            self.client = session.client('bedrock-runtime', region_name=region)
            logger.debug(f"BedrockClient: {region} (profile: {profile_name})")
        else:
            self.client = boto3.client('bedrock-runtime', region_name=region)
            logger.debug(f"BedrockClient: {region}")
    
    def generate(
        self,
        model_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate a response (unified interface).
        
        Args:
            model_id: The model identifier
            prompt: The user prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            
        Returns:
            Dict with 'content' and 'usage' keys
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
    
    def invoke_model(
        self,
        model_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> tuple[str, Dict[str, int]]:
        """
        Invoke a Bedrock foundation model.
        
        Args:
            model_id: The model identifier (e.g., "anthropic.claude-3-sonnet-20240229-v1:0")
            prompt: The user prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
            
        Returns:
            Tuple of (response_text, token_usage_dict)
            token_usage_dict contains: {"input_tokens": int, "output_tokens": int, "total_tokens": int}
            
        Raises:
            Exception: If the API call fails
        """
        try:
            # Check for SSO authentication errors early
            from botocore.exceptions import UnauthorizedSSOTokenError, NoCredentialsError
            
            # Determine the request format based on model provider
            if "anthropic" in model_id.lower() or "claude" in model_id.lower():
                body = self._build_anthropic_request(
                    prompt, system_prompt, max_tokens, temperature
                )
            elif "mistral" in model_id.lower():
                body = self._build_mistral_request(
                    prompt, system_prompt, max_tokens, temperature
                )
            elif "meta" in model_id.lower() or "llama" in model_id.lower():
                body = self._build_meta_request(
                    prompt, system_prompt, max_tokens, temperature
                )
            elif "amazon" in model_id.lower() or "nova" in model_id.lower():
                body = self._build_amazon_request(
                    prompt, system_prompt, max_tokens, temperature
                )
            else:
                # Default to a generic format
                body = self._build_generic_request(
                    prompt, system_prompt, max_tokens, temperature
                )
            
            logger.debug(f"Invoking: {model_id}")
            logger.debug(f"Request body: {json.dumps(body, indent=2)}")
            
            response = self.client.invoke_model(
                modelId=model_id,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            logger.debug(f"Response body: {json.dumps(response_body, indent=2)}")
            
            # Extract text based on response format
            text = self._extract_response_text(response_body, model_id)
            
            # Extract token usage
            token_usage = self._extract_token_usage(response_body, model_id)
            
            logger.debug(f"Response received: {len(text)} chars, {token_usage['total_tokens']} tokens")
            
            return text, token_usage
            
        except Exception as e:
            from botocore.exceptions import UnauthorizedSSOTokenError, NoCredentialsError
            
            # Check for SSO authentication errors
            if isinstance(e, UnauthorizedSSOTokenError):
                error_msg = (
                    f"\n{'='*60}\n"
                    f"❌ AWS SSO SESSION EXPIRED\n"
                    f"{'='*60}\n"
                    f"Your AWS SSO session has expired.\n"
                    f"Please run: aws sso login --profile {self.profile_name or 'default'}\n"
                    f"{'='*60}\n"
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg) from e
            elif isinstance(e, NoCredentialsError):
                error_msg = (
                    f"\n{'='*60}\n"
                    f"❌ AWS CREDENTIALS NOT FOUND\n"
                    f"{'='*60}\n"
                    f"No AWS credentials configured.\n"
                    f"Please run: aws sso login --profile {self.profile_name or 'default'}\n"
                    f"{'='*60}\n"
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg) from e
            else:
                logger.error(f"Error invoking model {model_id}: {str(e)}")
                raise
    
    def _build_anthropic_request(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Build request body for Anthropic Claude models."""
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        if system_prompt:
            body["system"] = system_prompt
        
        return body
    
    def _build_mistral_request(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Build request body for Mistral models."""
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        return {
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
    
    def _build_meta_request(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Build request body for Meta Llama models."""
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        return {
            "prompt": full_prompt,
            "max_gen_len": max_tokens,
            "temperature": temperature
        }
    
    def _build_amazon_request(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Build request body for Amazon Nova models."""
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": [{"text": system_prompt}]
            })
        
        messages.append({
            "role": "user",
            "content": [{"text": prompt}]
        })
        
        return {
            "messages": messages,
            "inferenceConfig": {
                "max_new_tokens": max_tokens,
                "temperature": temperature
            }
        }
    
    def _build_generic_request(
        self,
        prompt: str,
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Build generic request body."""
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        return {
            "prompt": full_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
    
    def _extract_response_text(self, response_body: Dict[str, Any], model_id: str) -> str:
        """Extract text from response body based on model format."""
        
        # Anthropic Claude format
        if "content" in response_body:
            if isinstance(response_body["content"], list):
                return response_body["content"][0].get("text", "")
            return response_body["content"]
        
        # Mistral format
        if "outputs" in response_body:
            if isinstance(response_body["outputs"], list):
                return response_body["outputs"][0].get("text", "")
        
        # Meta Llama format
        if "generation" in response_body:
            return response_body["generation"]
        
        # Amazon Nova format
        if "output" in response_body:
            output = response_body["output"]
            if "message" in output:
                message = output["message"]
                if "content" in message and isinstance(message["content"], list):
                    return message["content"][0].get("text", "")
        
        # Generic fallback
        if "text" in response_body:
            return response_body["text"]
        
        if "completion" in response_body:
            return response_body["completion"]
        
        logger.warning(f"Unknown response format for model {model_id}")
        return str(response_body)
    
    def _extract_token_usage(self, response_body: Dict[str, Any], model_id: str) -> Dict[str, int]:
        """Extract token usage from response body."""
        
        # Anthropic Claude format
        if "usage" in response_body:
            usage = response_body["usage"]
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            if input_tokens > 0 or output_tokens > 0:
                return {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens
                }
        
        # Amazon Nova format (different key names)
        if "usage" in response_body:
            usage = response_body["usage"]
            input_tokens = usage.get("inputTokens", 0)
            output_tokens = usage.get("outputTokens", 0)
            if input_tokens > 0 or output_tokens > 0:
                return {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens
                }
        
        # Mistral format
        if "outputs" in response_body and isinstance(response_body["outputs"], list):
            if len(response_body["outputs"]) > 0:
                output = response_body["outputs"][0]
                if "token_count" in output:
                    # Mistral may only provide output tokens
                    output_tokens = output["token_count"]
                    return {
                        "input_tokens": 0,  # Not provided
                        "output_tokens": output_tokens,
                        "total_tokens": output_tokens
                    }
        
        # Fallback: estimate based on character count
        logger.warning(f"Could not extract token usage for model {model_id}, estimating from text length")
        
        # Extract text to estimate tokens
        text = self._extract_response_text(response_body, model_id)
        
        # Rough estimate: ~4 characters per token (average for English text)
        estimated_output_tokens = len(text) // 4
        
        return {
            "input_tokens": 0,  # Can't estimate input without prompt
            "output_tokens": estimated_output_tokens,
            "total_tokens": estimated_output_tokens,
            "estimated": True  # Flag to indicate this is an estimate
        }
