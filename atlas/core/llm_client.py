"""
LLM Client utility for ATLAS.

This module provides a unified interface for various LLM providers,
handling API key management, client initialization, and error handling.
"""

import os
from typing import Any, Dict, Optional, Union
from atlas.core import get_config, AtlasError


class LLMClientError(AtlasError):
    """LLM client specific errors."""
    pass


class LLMClient:
    """Unified LLM client for multiple providers."""
    
    def __init__(self, config=None):
        """Initialize LLM client with configuration.
        
        Args:
            config: Optional LLMConfig object. If None, loads from global config.
        """
        if config is None:
            config = get_config().llm
        
        self.config = config
        self._client = None
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate LLM configuration."""
        if self.config.provider == "openai":
            if not self.config.api_key:
                raise LLMClientError(
                    "OpenAI API key is required. Set ATLAS_LLM_API_KEY or OPENAI_API_KEY environment variable."
                )
        
        elif self.config.provider == "azure":
            if not all([self.config.api_key, self.config.azure_endpoint, self.config.azure_deployment_name]):
                raise LLMClientError(
                    "Azure OpenAI requires api_key, azure_endpoint, and azure_deployment_name. "
                    "Set the appropriate ATLAS_LLM_* or AZURE_OPENAI_* environment variables."
                )
        
        elif self.config.provider == "anthropic":
            if not self.config.api_key:
                raise LLMClientError(
                    "Anthropic API key is required. Set ATLAS_LLM_API_KEY environment variable."
                )
        
        elif self.config.provider == "local":
            if not self.config.local_model_path and not self.config.api_base_url:
                raise LLMClientError(
                    "Local provider requires either local_model_path or api_base_url."
                )
    
    def get_client(self):
        """Get the appropriate LLM client instance."""
        if self._client is not None:
            return self._client
        
        try:
            if self.config.provider == "openai":
                self._client = self._create_openai_client()
            elif self.config.provider == "azure":
                self._client = self._create_azure_client()
            elif self.config.provider == "anthropic":
                self._client = self._create_anthropic_client()
            elif self.config.provider == "local":
                self._client = self._create_local_client()
            else:
                raise LLMClientError(f"Unsupported LLM provider: {self.config.provider}")
        
        except ImportError as e:
            raise LLMClientError(
                f"Required package for {self.config.provider} is not installed: {e}"
            )
        except Exception as e:
            raise LLMClientError(f"Failed to create LLM client: {e}")
        
        return self._client
    
    def _create_openai_client(self):
        """Create OpenAI client."""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package is required for OpenAI provider")
        
        client_kwargs = {
            "api_key": self.config.api_key,
            "timeout": self.config.timeout,
        }
        
        if self.config.api_base_url:
            client_kwargs["base_url"] = self.config.api_base_url
        
        return OpenAI(**client_kwargs)
    
    def _create_azure_client(self):
        """Create Azure OpenAI client."""
        try:
            from openai import AzureOpenAI
        except ImportError:
            raise ImportError("openai package is required for Azure OpenAI provider")
        
        return AzureOpenAI(
            api_key=self.config.api_key,
            azure_endpoint=self.config.azure_endpoint,
            api_version=self.config.azure_api_version,
            timeout=self.config.timeout,
        )
    
    def _create_anthropic_client(self):
        """Create Anthropic client."""
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError("anthropic package is required for Anthropic provider")
        
        client_kwargs = {
            "api_key": self.config.api_key,
            "timeout": self.config.timeout,
        }
        
        if self.config.api_base_url:
            client_kwargs["base_url"] = self.config.api_base_url
        
        return Anthropic(**client_kwargs)
    
    def _create_local_client(self):
        """Create local model client (OpenAI-compatible API)."""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package is required for local provider")
        
        base_url = self.config.api_base_url or f"http://localhost:{self.config.local_api_port}/v1"
        
        return OpenAI(
            api_key="not-needed",  # Local models usually don't need API keys
            base_url=base_url,
            timeout=self.config.timeout,
        )
    
    def create_completion(self, messages: list, **kwargs) -> Dict[str, Any]:
        """Create a chat completion using the configured LLM.
        
        Args:
            messages: List of message dictionaries
            **kwargs: Additional parameters for the completion
            
        Returns:
            Dictionary containing the completion response
        """
        client = self.get_client()
        
        # Set default parameters
        completion_kwargs = {
            "model": self._get_model_name(),
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
        }
        
        # Add provider-specific parameters
        completion_kwargs.update(kwargs)
        
        try:
            if self.config.provider == "anthropic":
                # Anthropic has a different API structure
                response = client.messages.create(**completion_kwargs)
                return self._format_anthropic_response(response)
            else:
                # OpenAI-compatible API
                response = client.chat.completions.create(**completion_kwargs)
                return self._format_openai_response(response)
        
        except Exception as e:
            raise LLMClientError(f"Failed to create completion: {e}")
    
    def _get_model_name(self) -> str:
        """Get the model name for API calls."""
        if self.config.provider == "azure":
            return self.config.azure_deployment_name
        return self.config.model_name
    
    def _format_openai_response(self, response) -> Dict[str, Any]:
        """Format OpenAI response to standard format."""
        return {
            "content": response.choices[0].message.content,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            "model": response.model,
            "provider": self.config.provider,
        }
    
    def _format_anthropic_response(self, response) -> Dict[str, Any]:
        """Format Anthropic response to standard format."""
        return {
            "content": response.content[0].text,
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            "model": response.model,
            "provider": self.config.provider,
        }


# Global LLM client instance
_llm_client: Optional[LLMClient] = None


def get_llm_client(config=None) -> LLMClient:
    """Get or create global LLM client instance."""
    global _llm_client
    if _llm_client is None or config is not None:
        _llm_client = LLMClient(config)
    return _llm_client


def create_completion(messages: list, **kwargs) -> Dict[str, Any]:
    """Convenience function to create a completion using the global LLM client."""
    return get_llm_client().create_completion(messages, **kwargs)
