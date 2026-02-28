#!/usr/bin/env python3
"""
Test RapidAPI Face Analyzer directly
"""

import sys
sys.path.insert(0, '/app/backend')

import asyncio
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

from scraper.rapidapi_service import get_rapidapi_service

async def test_rapidapi():
    print("=" * 60)
    print("Testing RapidAPI Face Analyzer Service")
    print("=" * 60)
    
    # Load test image
    with open('/tmp/test_face3.jpg', 'rb') as f:
        image_bytes = f.read()
    
    print(f"\n📸 Image size: {len(image_bytes)} bytes")
    
    # Get RapidAPI service
    service = get_rapidapi_service()
    
    if not service.enabled:
        print("❌ RapidAPI service not enabled!")
        return
    
    print("✅ RapidAPI service enabled\n")
    print("🔄 Detecting face and extracting embedding...")
    
    # Test detection
    embedding = service.detect_face_and_get_embedding(image_bytes)
    
    if embedding is not None:
        print(f"\n✅ SUCCESS!")
        print(f"   - Embedding shape: {embedding.shape}")
        print(f"   - Embedding type: {embedding.dtype}")
        print(f"   - Embedding norm: {(embedding ** 2).sum() ** 0.5:.4f}")
        print(f"   - Sample values: {embedding[:5]}")
        print(f"\n🎯 RapidAPI Face Analyzer is working correctly!")
    else:
        print("\n❌ No face detected or API error")

if __name__ == "__main__":
    asyncio.run(test_rapidapi())
