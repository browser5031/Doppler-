#!/usr/bin/env python3
"""Real-time progress monitor - watch scraping live"""
import time
from pymongo import MongoClient
import os

def clear_screen():
    os.system('clear' if os.name != 'nt' else 'cls')

db = MongoClient('mongodb://localhost:27017')['test_database']

print("🔴 LIVE PROGRESS MONITOR - Updates every 3 seconds")
print("Press Ctrl+C to stop\n")

try:
    while True:
        clear_screen()
        print("="*70)
        print("🔴 LIVE SCRAPING PROGRESS")
        print("="*70 + "\n")
        
        # Total stats
        total_faces = db.faces.count_documents({})
        total_yearbooks = db.yearbooks.count_documents({})
        processing = db.yearbooks.count_documents({'scraping_status': 'processing'})
        completed = db.yearbooks.count_documents({'scraping_status': 'completed'})
        queued = db.yearbooks.count_documents({'scraping_status': 'queued'})
        
        print(f"📊 OVERALL STATUS:")
        print(f"   💾 Total Faces: {total_faces}")
        print(f"   📚 Total Yearbooks: {total_yearbooks}")
        print(f"   🟢 Completed: {completed}")
        print(f"   🔵 Processing: {processing}")
        print(f"   ⚪ Queued: {queued}")
        print()
        
        # Show processing jobs with progress
        if processing > 0:
            print("🔵 CURRENTLY PROCESSING:")
            jobs = list(db.yearbooks.find(
                {'scraping_status': 'processing'},
                {'_id': 0, 'identifier': 1, 'faces_extracted': 1, 'pages_processed': 1, 'total_pages': 1, 'progress_percent': 1}
            ).limit(5))
            
            for job in jobs:
                name = job['identifier'][:35]
                faces = job.get('faces_extracted', 0)
                pages = job.get('pages_processed', 0)
                total = job.get('total_pages', '?')
                progress = job.get('progress_percent', 0)
                
                bar_length = 20
                filled = int(bar_length * progress / 100)
                bar = '█' * filled + '░' * (bar_length - filled)
                
                print(f"   {name}")
                print(f"   [{bar}] {progress}%  |  {faces} faces  |  {pages}/{total} pages")
                print()
        
        print(f"\n⏱️  Updated: {time.strftime('%H:%M:%S')}")
        print("="*70)
        
        time.sleep(3)
        
except KeyboardInterrupt:
    print("\n\n✓ Monitor stopped")
