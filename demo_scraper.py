#!/usr/bin/env python3
"""
Quick Demo - Start scraping 10 yearbooks right now!
This will give you ~500 faces in about 5-10 minutes
"""
import asyncio
import aiohttp
import sys
from datetime import datetime

API = 'http://localhost:8001/api'

async def quick_demo():
    print("\n" + "="*60)
    print("🎯 QUICK DEMO - Let's Get Your First 500 Faces!")
    print("="*60 + "\n")
    
    print("This will:")
    print("  ✅ Discover 10 yearbooks from archive.org")
    print("  ✅ Start scraping them (first 30 pages each)")
    print("  ✅ Extract faces automatically")
    print("  ✅ Show you real-time progress")
    print("\n⏱️  Estimated time: 5-10 minutes\n")
    
    input("Press Enter to start...")
    
    print("\n🔍 Discovering yearbooks...")
    async with aiohttp.ClientSession() as session:
        # Discover yearbooks
        async with session.get(f'{API}/scraper/search-yearbooks', 
                              params={'query': 'high school yearbook', 
                                     'year_start': 2010, 
                                     'year_end': 2015, 
                                     'limit': 10}) as response:
            data = await response.json()
            yearbooks = data.get('results', [])
            print(f"✅ Found {len(yearbooks)} yearbooks!\n")
            
            if not yearbooks:
                print("❌ No yearbooks found. Try different years or search terms.")
                return
            
            # Show what we found
            print("📚 Yearbooks to scrape:")
            for i, yb in enumerate(yearbooks[:10], 1):
                print(f"   {i}. {yb.get('title', 'Unknown')} ({yb.get('year', 'N/A')})")
            
            print(f"\n🚀 Starting scraping...")
            
            # Start scraping each one
            started = 0
            for yb in yearbooks[:10]:
                identifier = yb.get('identifier')
                try:
                    async with session.post(f'{API}/scraper/start',
                                          params={'identifier': identifier, 
                                                 'max_pages': 30, 
                                                 'priority': 5}) as resp:
                        if resp.status == 200:
                            started += 1
                            print(f"   ✅ Started: {yb.get('title', identifier)[:50]}")
                        await asyncio.sleep(0.5)  # Small delay between requests
                except Exception as e:
                    print(f"   ⚠️  Skipped: {identifier} ({str(e)[:50]})")
            
            print(f"\n✅ Started scraping {started} yearbooks!")
            print("\n" + "="*60)
            print("📊 MONITORING PROGRESS")
            print("="*60 + "\n")
            print("Checking progress every 10 seconds...")
            print("Press Ctrl+C to stop monitoring (scraping will continue)\n")
            
            # Monitor progress
            try:
                last_faces = 0
                for i in range(60):  # Monitor for 10 minutes
                    await asyncio.sleep(10)
                    
                    async with session.get(f'{API}/recovery/stats') as resp:
                        stats = await resp.json()
                        total_faces = stats.get('total_faces', 0)
                        processing = stats.get('processing', 0)
                        completed = stats.get('completed', 0)
                        
                        faces_gained = total_faces - last_faces
                        last_faces = total_faces
                        
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                              f"👤 {total_faces:,} faces | "
                              f"⚙️  {processing} processing | "
                              f"✅ {completed} done | "
                              f"📈 +{faces_gained} new")
                        
                        if processing == 0 and completed >= started:
                            print("\n🎉 All yearbooks completed!")
                            break
                
                print("\n" + "="*60)
                print("✅ DEMO COMPLETE!")
                print("="*60)
                
                # Final stats
                async with session.get(f'{API}/recovery/stats') as resp:
                    stats = await resp.json()
                    print(f"\n📊 Final Stats:")
                    print(f"   Total Faces: {stats.get('total_faces', 0):,}")
                    print(f"   Yearbooks Completed: {stats.get('completed', 0)}")
                    print(f"   Yearbooks in Database: {stats.get('total_yearbooks', 0)}")
                
                print("\n🎯 Ready for more?")
                print("   Run: ./start_scraping.sh")
                print("   Visit: your-app-url/admin")
                print("\n💚 Your doppelganger finder is ready to use!\n")
                
            except KeyboardInterrupt:
                print("\n\n⚠️  Monitoring stopped (scraping continues in background)")
                print("   Check progress: python /app/check_tasks.py")
                print("   Or visit: your-app-url/admin\n")

if __name__ == '__main__':
    try:
        asyncio.run(quick_demo())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
