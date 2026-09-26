#!/usr/bin/env python3
"""Test script to verify Hugging Face vision model availability."""
import os
import sys
import base64
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def test_hf_vision():
    """Test Hugging Face vision models with current API key."""
    try:
        from huggingface_hub import InferenceClient
    except ImportError:
        print("ERROR: huggingface_hub not installed. Run: pip install huggingface_hub")
        return False

    api_key = os.environ.get("HF_API_KEY", "")
    if not api_key:
        print("ERROR: HF_API_KEY not set in environment")
        return False

    print(f"Testing Hugging Face vision models with API key: {api_key[:10]}...")
    
    # Create a simple test image (1x1 red pixel)
    test_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
    
    # Vision models to test
    vision_models = [
        "microsoft/Phi-3.5-vision-instruct",
        "Qwen/Qwen2-VL-7B-Instruct",
        "meta-llama/Llama-3.2-11B-Vision-Instruct",
    ]
    
    for model_name in vision_models:
        print(f"\nTesting model: {model_name}")
        try:
            client = InferenceClient(
                provider="hf-inference",
                api_key=api_key
            )
            
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "What do you see in this image?"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{test_image_b64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=100,
                temperature=0.7
            )
            
            result = response.choices[0].message.content
            print(f"✓ SUCCESS: {model_name} works!")
            print(f"  Response: {result[:100]}...")
            return True
            
        except Exception as e:
            print(f"✗ FAILED: {model_name}")
            print(f"  Error: {str(e)}")
            continue
    
    print("\n❌ All vision models failed to work with hf-inference provider")
    print("The app will use fallback responses instead.")
    return False

if __name__ == "__main__":
    success = test_hf_vision()
    sys.exit(0 if success else 1)
