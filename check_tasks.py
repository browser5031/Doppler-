#!/usr/bin/env python3
"""
CLI tool to check and fix stuck scraping tasks
Usage: python check_tasks.py
"""
import os
import sys
import asyncio
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Load environment
ROOT_DIR = Path(__file__).parent / 'backend'
load_dotenv(ROOT_DIR / '.env')

async def main():
    mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    db_name = os.environ.get('DB_NAME', 'test_database')
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print("=" * 60)
    print("DOPPELGANGER SCRAPER - TASK STATUS CHECK")
    print("=" * 60)
    print()
    
    # Get overall stats
    total_yearbooks = await db.yearbooks.count_documents({})
    total_faces = await db.faces.count_documents({})
    
    print(f"📚 Total Yearbooks: {total_yearbooks}")
    print(f"👤 Total Faces: {total_faces}")
    print()
    
    # Status breakdown
    print("STATUS BREAKDOWN:")
    print("-" * 60)
    
    completed = await db.yearbooks.count_documents({'scraping_status': 'completed'})
    processing = await db.yearbooks.count_documents({'scraping_status': 'processing'})
    queued = await db.yearbooks.count_documents({'scraping_status': 'queued'})
    failed = await db.yearbooks.count_documents({'scraping_status': 'failed'})
    
    print(f"✅ Completed:  {completed}")
    print(f"⚙️  Processing: {processing}")
    print(f"⏳ Queued:     {queued}")
    print(f"❌ Failed:     {failed}")
    print()
    
    # Find stuck tasks (processing for > 30 minutes)
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=30)
    stuck_processing = []
    
    async for yearbook in db.yearbooks.find({'scraping_status': 'processing'}):
        started_at = yearbook.get('started_at')
        if started_at:
            if isinstance(started_at, str):
                started_at = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
            if started_at < cutoff_time:
                stuck_processing.append(yearbook)
    
    # Find stuck queued tasks (queued for > 5 minutes)
    cutoff_queued = datetime.now(timezone.utc) - timedelta(minutes=5)
    stuck_queued = []
    
    async for yearbook in db.yearbooks.find({'scraping_status': 'queued'}):
        updated_at = yearbook.get('updated_at', yearbook.get('created_at'))
        if updated_at:
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            if updated_at < cutoff_queued:
                stuck_queued.append(yearbook)
    
    total_stuck = len(stuck_processing) + len(stuck_queued)
    
    if total_stuck > 0:
        print(f"⚠️  STUCK TASKS FOUND: {total_stuck}")
        print("=" * 60)
        
        if stuck_processing:
            print(f"\n🔴 Stuck in PROCESSING ({len(stuck_processing)} tasks):")
            print("-" * 60)
            for task in stuck_processing[:10]:  # Show first 10
                identifier = task.get('identifier', 'unknown')
                pages = task.get('pages_processed', 0)
                faces = task.get('faces_extracted', 0)
                started = task.get('started_at', 'unknown')
                print(f"  • {identifier}")
                print(f"    Pages: {pages}, Faces: {faces}, Started: {started}")
        
        if stuck_queued:
            print(f"\n🟡 Stuck in QUEUED ({len(stuck_queued)} tasks):")
            print("-" * 60)
            for task in stuck_queued[:10]:  # Show first 10
                identifier = task.get('identifier', 'unknown')
                updated = task.get('updated_at', task.get('created_at', 'unknown'))
                print(f"  • {identifier} (Last updated: {updated})")
        
        print("\n" + "=" * 60)
        print("TO FIX STUCK TASKS:")
        print("=" * 60)
        print("Option 1: Use the API endpoint:")
        print(f"  curl -X POST 'http://localhost:8001/api/recovery/reset-all-stuck'")
        print()
        print("Option 2: Run this script with --fix flag:")
        print(f"  python {sys.argv[0]} --fix")
        print()
        
        if '--fix' in sys.argv:
            print("🔧 FIXING STUCK TASKS...")
            print("-" * 60)
            
            fixed_count = 0
            for task in stuck_processing + stuck_queued:
                result = await db.yearbooks.update_one(
                    {'identifier': task['identifier']},
                    {'$set': {
                        'scraping_status': 'queued',
                        'updated_at': datetime.now(timezone.utc).isoformat(),
                        'error': None
                    }}
                )
                if result.modified_count > 0:
                    fixed_count += 1
                    print(f"  ✓ Reset: {task['identifier']}")
            
            print()
            print(f"✅ Fixed {fixed_count} stuck tasks!")
            print("   Tasks have been reset to 'queued' status.")
            print("   They will be processed again when you restart scraping.")
    else:
        print("✅ No stuck tasks found!")
        print("   All tasks are progressing normally.")
    
    print()
    print("=" * 60)
    
    client.close()

if __name__ == '__main__':
    asyncio.run(main())
