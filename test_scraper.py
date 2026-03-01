#!/usr/bin/env python3
"""
Comprehensive scraper test - shows exactly what's working
"""
import sys
sys.path.insert(0, '/app/backend')

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from scraper.production_orchestrator import ProductionOrchestrator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_scraper():
    # Connect to MongoDB
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['test_database']
    
    # Initialize orchestrator
    orchestrator = ProductionOrchestrator(db, max_workers=2)
    
    # Test with a known good yearbook
    identifier = "011187-10.-std-e-yearbook-final"
    
    print(f"\n{'='*60}")
    print(f"TESTING SCRAPER WITH: {identifier}")
    print(f"{'='*60}\n")
    
    try:
        # Start scraping
        print("1. Starting scrape...")
        result = await orchestrator.start_scraping(
            identifier=identifier,
            options={'max_pages': 3}
        )
        print(f"   Result: {result}")
        
        # Wait for processing
        print("\n2. Waiting 30 seconds for processing...")
        await asyncio.sleep(30)
        
        # Check status
        print("\n3. Checking database...")
        yearbook = await db.yearbooks.find_one({'identifier': identifier}, {'_id': 0})
        if yearbook:
            print(f"   Status: {yearbook.get('scraping_status')}")
            print(f"   Faces: {yearbook.get('faces_extracted', 0)}")
            print(f"   Pages: {yearbook.get('pages_processed', 0)}/{yearbook.get('total_pages', '?')}")
            print(f"   Error: {yearbook.get('error', 'None')}")
        else:
            print("   ✗ Yearbook not found in database")
        
        # Check faces
        face_count = await db.faces.count_documents({'yearbook_id': identifier})
        print(f"\n4. Faces in database: {face_count}")
        
        if face_count > 0:
            sample_face = await db.faces.find_one({'yearbook_id': identifier}, {'_id': 0, 'embedding': 0})
            print(f"   Sample face: {sample_face}")
        
        print(f"\n{'='*60}")
        print(f"TEST COMPLETE")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_scraper())
