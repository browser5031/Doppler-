#!/usr/bin/env python3
"""
Test Face++ API directly (bypass InsightFace)
"""

import sys
sys.path.insert(0, '/app/backend')

import asyncio
from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

from scraper.facepp_service import get_facepp_service

async def test_facepp():
    print("=" * 60)
    print("Testing Face++ API Service")
    print("=" * 60)
    
    # Load test image
    with open('/tmp/test_face3.jpg', 'rb') as f:
        image_bytes = f.read()
    
    print(f"\n📸 Image size: {len(image_bytes)} bytes")
    
    # Get Face++ service
    service = get_facepp_service()
    
    if not service.enabled:
        print("❌ Face++ service not enabled!")
        return
    
    print("✅ Face++ service enabled\n")
    print("🔄 Detecting face and extracting embedding...")
    
    # Test detection
    embedding = service.detect_face_and_get_embedding(image_bytes)
    
    if embedding is not None:
        print(f"\n✅ SUCCESS!")
        print(f"   - Embedding shape: {embedding.shape}")
        print(f"   - Embedding type: {embedding.dtype}")
        print(f"   - Embedding norm: {(embedding ** 2).sum() ** 0.5:.4f}")
        print(f"   - Sample values: {embedding[:5]}")
        print(f"\n🎯 Face++ API is working correctly!")
    else:
        print("\n❌ No face detected or API error")

if __name__ == "__main__":
    asyncio.run(test_facepp())
