#!/usr/bin/env python3
"""Test Luxand.cloud API"""
import sys
sys.path.insert(0, '/app/backend')

from dotenv import load_dotenv
load_dotenv('/app/backend/.env')

from scraper.luxand_service import get_luxand_service

# Load test image
with open('/tmp/test_upload.jpg', 'rb') as f:
    image_bytes = f.read()

print("=" * 60)
print("Testing Luxand.cloud Face API")
print("=" * 60)

service = get_luxand_service()

if not service.enabled:
    print("❌ Luxand service not enabled!")
    sys.exit(1)

print("✅ Luxand service enabled\n")
print("🔄 Detecting face...")

embedding = service.detect_face_and_get_embedding(image_bytes)

if embedding is not None:
    print(f"\n✅ SUCCESS!")
    print(f"   - Embedding shape: {embedding.shape}")
    print(f"   - Embedding norm: {(embedding ** 2).sum() ** 0.5:.4f}")
    print(f"   - Sample values: {embedding[:5]}")
    print(f"\n🎯 Luxand.cloud is working!")
else:
    print("\n❌ Face detection failed")
    sys.exit(1)
