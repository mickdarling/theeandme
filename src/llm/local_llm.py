"""
Local LLM integration supporting Ollama and LM Studio.

This module provides a unified interface for communicating with local LLM services,
handling model loading, inference, and error recovery.
"""

import json
import logging
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional, AsyncGenerator
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class LLMService(Enum):
    """Supported LLM services."""
    OLLAMA = "ollama"
    LM_STUDIO = "lmstudio"


@dataclass
class LLMResponse:
    """Response from LLM inference."""
    content: str
    model: str
    tokens_generated: Optional[int] = None
    inference_time: Optional[float] = None
    error: Optional[str] = None


class LocalLLM:
    """Local LLM interface supporting multiple backends."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize LLM client."""
        self.config = config
        self.service = LLMService(config.get('service', 'ollama'))
        self.base_url = config.get('base_url', self._get_default_url())
        self.model = config.get('model', 'llama3.1:8b')
        self.fallback_models = config.get('fallback_models', [])
        self.timeout = config.get('timeout', 30)
        self.session = None
        
        logger.info(f"Initialized {self.service.value} client at {self.base_url}")
        
    def _get_default_url(self) -> str:
        """Get default URL for the service."""
        if self.service == LLMService.OLLAMA:
            return "http://localhost:11434"
        elif self.service == LLMService.LM_STUDIO:
            return "http://localhost:1234"
        return "http://localhost:11434"
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()
    
    async def initialize(self):
        """Initialize the LLM client."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        
        # Test connection and model availability
        is_healthy = await self.health_check()
        if not is_healthy:
            logger.warning(f"LLM service at {self.base_url} is not responding")
        
    async def shutdown(self):
        """Shutdown the LLM client."""
        if self.session:
            await self.session.close()
    
    async def health_check(self) -> bool:
        """Check if the LLM service is healthy."""
        try:
            if self.service == LLMService.OLLAMA:
                async with self.session.get(f"{self.base_url}/api/version") as response:
                    return response.status == 200
            elif self.service == LLMService.LM_STUDIO:
                async with self.session.get(f"{self.base_url}/v1/models") as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
        
    async def list_models(self) -> List[str]:
        """List available models."""
        try:
            if self.service == LLMService.OLLAMA:
                async with self.session.get(f"{self.base_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        return [model['name'] for model in data.get('models', [])]
            elif self.service == LLMService.LM_STUDIO:
                async with self.session.get(f"{self.base_url}/v1/models") as response:
                    if response.status == 200:
                        data = await response.json()
                        return [model['id'] for model in data.get('data', [])]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
        return []
    
    async def generate_response(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """Generate a response from the LLM."""
        model = model or self.model
        
        try:
            if self.service == LLMService.OLLAMA:
                return await self._ollama_generate(prompt, model, system_prompt)
            elif self.service == LLMService.LM_STUDIO:
                return await self._lmstudio_generate(prompt, model, system_prompt)
        except Exception as e:
            logger.error(f"Generation failed with model {model}: {e}")
            
            # Try fallback models
            for fallback_model in self.fallback_models:
                try:
                    logger.info(f"Trying fallback model: {fallback_model}")
                    if self.service == LLMService.OLLAMA:
                        return await self._ollama_generate(prompt, fallback_model, system_prompt)
                    elif self.service == LLMService.LM_STUDIO:
                        return await self._lmstudio_generate(prompt, fallback_model, system_prompt)
                except Exception as fallback_e:
                    logger.error(f"Fallback model {fallback_model} also failed: {fallback_e}")
                    continue
            
            return LLMResponse(
                content="",
                model=model,
                error=f"All models failed. Last error: {str(e)}"
            )
    
    async def _ollama_generate(
        self, 
        prompt: str, 
        model: str,
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """Generate response using Ollama API."""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        async with self.session.post(
            f"{self.base_url}/api/generate",
            json=payload
        ) as response:
            if response.status == 200:
                data = await response.json()
                return LLMResponse(
                    content=data.get("response", ""),
                    model=model,
                    tokens_generated=data.get("eval_count"),
                    inference_time=data.get("total_duration", 0) / 1e9  # Convert ns to seconds
                )
            else:
                error_text = await response.text()
                raise Exception(f"Ollama API error {response.status}: {error_text}")
    
    async def _lmstudio_generate(
        self, 
        prompt: str, 
        model: str,
        system_prompt: Optional[str] = None
    ) -> LLMResponse:
        """Generate response using LM Studio OpenAI-compatible API."""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "temperature": self.config.get("temperature", 0.7),
            "max_tokens": self.config.get("max_tokens", 1000)
        }
        
        async with self.session.post(
            f"{self.base_url}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json=payload
        ) as response:
            if response.status == 200:
                data = await response.json()
                choice = data["choices"][0]
                return LLMResponse(
                    content=choice["message"]["content"],
                    model=model,
                    tokens_generated=data.get("usage", {}).get("completion_tokens"),
                    inference_time=None  # LM Studio doesn't provide timing info
                )
            else:
                error_text = await response.text()
                raise Exception(f"LM Studio API error {response.status}: {error_text}")
    
    async def stream_response(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response from LLM (for future use with real-time responses)."""
        model = model or self.model
        
        if self.service == LLMService.OLLAMA:
            async for chunk in self._ollama_stream(prompt, model, system_prompt):
                yield chunk
        elif self.service == LLMService.LM_STUDIO:
            async for chunk in self._lmstudio_stream(prompt, model, system_prompt):
                yield chunk
    
    async def _ollama_stream(
        self, 
        prompt: str, 
        model: str,
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response from Ollama."""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        async with self.session.post(
            f"{self.base_url}/api/generate",
            json=payload
        ) as response:
            async for line in response.content:
                try:
                    data = json.loads(line)
                    if "response" in data:
                        yield data["response"]
                except json.JSONDecodeError:
                    continue
    
    async def _lmstudio_stream(
        self, 
        prompt: str, 
        model: str,
        system_prompt: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response from LM Studio."""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": self.config.get("temperature", 0.7),
            "max_tokens": self.config.get("max_tokens", 1000)
        }
        
        async with self.session.post(
            f"{self.base_url}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json=payload
        ) as response:
            async for line in response.content:
                if line.startswith(b"data: "):
                    try:
                        data = json.loads(line[6:])
                        if data.get("choices") and data["choices"][0].get("delta", {}).get("content"):
                            yield data["choices"][0]["delta"]["content"]
                    except json.JSONDecodeError:
                        continue