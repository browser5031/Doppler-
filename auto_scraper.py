#!/usr/bin/env python3
"""
Auto-scraper: Continuously scrapes yearbooks to build database
Runs in background, auto-discovers and processes yearbooks
"""
import asyncio
import requests
import time
from datetime import datetime

API_URL = "http://localhost:8001/api"

async def auto_scrape_loop():
    print("\n" + "="*70)
    print("🚀 AUTO-SCRAPER STARTED - Building Database Automatically")
    print("="*70 + "\n")
    
    batch_num = 1
    total_started = 0
    
    while True:
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Starting batch #{batch_num}...")
            
            # Auto-discover and scrape yearbooks
            response = requests.post(
                f"{API_URL}/scraper/auto-discover",
                params={
                    'query': 'high school yearbook',
                    'year_start': 2005,
                    'year_end': 2015,
                    'limit': 50,  # 50 yearbooks per batch
                    'max_pages_per_book': 25  # 25 pages each
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                started = data.get('total_yearbooks', 0)
                total_started += started
                print(f"✓ Batch #{batch_num}: Started {started} yearbooks")
                print(f"  Total queued so far: {total_started} yearbooks")
            else:
                print(f"✗ Batch #{batch_num} failed: {response.status_code}")
            
            # Check status
            status_resp = requests.get(f"{API_URL}/scraper/status", timeout=10)
            if status_resp.status_code == 200:
                status = status_resp.json()
                print(f"\n📊 Current Status:")
                print(f"  • Total faces: {status.get('total_faces', 0)}")
                print(f"  • Processing: {status.get('processing', 0)}")
                print(f"  • Queued: {status.get('queued', 0)}")
                print(f"  • Completed: {status.get('completed', 0)}")
            
            batch_num += 1
            
            # Wait 30 minutes before next batch
            print(f"\n⏳ Waiting 30 minutes before next batch...")
            print(f"   (Scraper is working in background)")
            await asyncio.sleep(1800)  # 30 minutes
            
        except Exception as e:
            print(f"\n✗ Error in batch #{batch_num}: {e}")
            print(f"   Retrying in 5 minutes...")
            await asyncio.sleep(300)

if __name__ == "__main__":
    try:
        asyncio.run(auto_scrape_loop())
    except KeyboardInterrupt:
        print("\n\n🛑 Auto-scraper stopped by user")
    except Exception as e:
        print(f"\n\n✗ Auto-scraper crashed: {e}")
