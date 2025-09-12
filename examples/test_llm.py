#!/usr/bin/env python3
"""
Test script for LLM integration.

This script tests the connection to LM Studio or Ollama and verifies
that models are available and responding correctly.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from llm.local_llm import LocalLLM, LLMService


async def test_lm_studio():
    """Test LM Studio integration."""
    print("🧪 Testing LM Studio Integration")
    print("=" * 50)
    
    # LM Studio configuration
    config = {
        "service": "lmstudio",
        "base_url": "http://localhost:1234",
        "model": "llama-3.2-3b-instruct",  # Common LM Studio model
        "temperature": 0.7,
        "max_tokens": 100
    }
    
    async with LocalLLM(config) as llm:
        # Health check
        print("1. Health Check...")
        is_healthy = await llm.health_check()
        print(f"   Status: {'✅ Healthy' if is_healthy else '❌ Not responding'}")
        
        if not is_healthy:
            print("\n⚠️  LM Studio not responding. Make sure:")
            print("   - LM Studio is running")
            print("   - Local server is started (LM Studio → Local Server)")
            print("   - A model is loaded")
            return
        
        # List models
        print("\n2. Available Models...")
        models = await llm.list_models()
        if models:
            for model in models[:5]:  # Show first 5 models
                print(f"   📦 {model}")
            if len(models) > 5:
                print(f"   ... and {len(models) - 5} more models")
        else:
            print("   ⚠️  No models found")
        
        # Test generation
        print("\n3. Test Generation...")
        test_prompt = "Hello! Can you briefly explain what you are in one sentence?"
        
        response = await llm.generate_response(test_prompt)
        
        if response.error:
            print(f"   ❌ Error: {response.error}")
        else:
            print(f"   Model: {response.model}")
            print(f"   Response: {response.content}")
            if response.tokens_generated:
                print(f"   Tokens: {response.tokens_generated}")
            if response.inference_time:
                print(f"   Time: {response.inference_time:.2f}s")


async def test_ollama():
    """Test Ollama integration."""
    print("🧪 Testing Ollama Integration")
    print("=" * 50)
    
    # Ollama configuration
    config = {
        "service": "ollama", 
        "base_url": "http://localhost:11434",
        "model": "llama3.1:8b",
        "fallback_models": ["llama3.1:8b-q4_0", "mistral:7b"]
    }
    
    async with LocalLLM(config) as llm:
        # Health check
        print("1. Health Check...")
        is_healthy = await llm.health_check()
        print(f"   Status: {'✅ Healthy' if is_healthy else '❌ Not responding'}")
        
        if not is_healthy:
            print("\n⚠️  Ollama not responding. Install with:")
            print("   curl -fsSL https://ollama.com/install.sh | sh")
            print("   ollama pull llama3.1:8b")
            return
        
        # List models
        print("\n2. Available Models...")
        models = await llm.list_models()
        if models:
            for model in models:
                print(f"   📦 {model}")
        else:
            print("   ⚠️  No models found. Run: ollama pull llama3.1:8b")
        
        # Test generation
        print("\n3. Test Generation...")
        test_prompt = "Hello! Can you briefly explain what you are in one sentence?"
        
        response = await llm.generate_response(test_prompt)
        
        if response.error:
            print(f"   ❌ Error: {response.error}")
        else:
            print(f"   Model: {response.model}")
            print(f"   Response: {response.content}")
            if response.tokens_generated:
                print(f"   Tokens: {response.tokens_generated}")
            if response.inference_time:
                print(f"   Time: {response.inference_time:.2f}s")


async def main():
    """Main test function."""
    print("🤖 The E and Me - LLM Integration Test")
    print("=" * 60)
    
    # Test LM Studio (since it's installed)
    await test_lm_studio()
    
    print("\n" + "=" * 60)
    
    # Test Ollama (if available)
    await test_ollama()
    
    print("\n✅ LLM integration tests complete!")


if __name__ == "__main__":
    asyncio.run(main())