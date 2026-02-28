#!/usr/bin/env python3
"""
SIMPLE SCRAPER - Just download and save image URLs first
Face detection can be done separately later in batches
"""
import sys
sys.path.insert(0, '/app/backend')

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from scraper.archive_scraper import ArchiveScraper
import uuid
from datetime import datetime, timezone

async def quick_scrape():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['test_database']
    scraper = ArchiveScraper(db)
    
    print("\n" + "="*70)
    print("QUICK SCRAPE - Just saving image URLs for now")
    print("="*70 + "\n")
    
    # Find a good yearbook
    identifier = "0001_20191231"
    
    print(f"1. Getting yearbook: {identifier}")
    yearbook_data = await scraper.get_yearbook_details(identifier)
    print(f"   Title: {yearbook_data['title']}")
    
    print(f"\n2. Getting image list...")
    images = await scraper.get_yearbook_images(identifier, max_images=20)
    print(f"   Found {len(images)} images")
    
    print(f"\n3. Saving placeholder faces (no detection yet)...")
    saved = 0
    for i, img_info in enumerate(images[:20]):
        # Save as a "face" with NO embedding yet
        face_data = {
            'face_id': str(uuid.uuid4()),
            'embedding': None,  # Will add later
            'yearbook_id': identifier,
            'page_num': i + 1,
            'yearbook_url': yearbook_data['archive_url'],
            'page_url': f"{yearbook_data['archive_url']}/page/{i+1}",
            'image_url': img_info['url'],  # Store the image URL
            'thumbnail_url': img_info['url'],  # Use same URL
            'name': None,
            'year': yearbook_data.get('year'),
            'school': yearbook_data.get('title'),
            'needs_processing': True,  # Flag for later face detection
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        await db.faces.insert_one(face_data)
        saved += 1
        if saved % 5 == 0:
            print(f"   Saved {saved} image URLs...")
    
    print(f"\n✓ Saved {saved} images!")
    print(f"\nTotal faces in DB now: {await db.faces.count_documents({})}")
    print("\n" + "="*70)
    print("DONE! You can now see images in the results page")
    print("Face detection can be run separately later")
    print("="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(quick_scrape())
