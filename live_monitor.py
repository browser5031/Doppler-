#!/usr/bin/env python3
"""
Real-Time Scraper Monitor - Watch faces being collected LIVE!
"""
import asyncio
import aiohttp
import sys
import os
from datetime import datetime
from time import time

API = 'http://localhost:8001/api'

class LiveMonitor:
    def __init__(self):
        self.last_faces = 0
        self.last_yearbooks = 0
        self.start_time = time()
        self.faces_per_second = 0
        
    def clear_screen(self):
        os.system('clear' if os.name != 'nt' else 'cls')
    
    def format_time(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
    
    def draw_progress_bar(self, current, target, width=50):
        if target == 0:
            percentage = 0
        else:
            percentage = min(100, (current / target) * 100)
        
        filled = int(width * percentage / 100)
        bar = '█' * filled + '░' * (width - filled)
        return f"[{bar}] {percentage:.1f}%"
    
    async def get_stats(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{API}/recovery/stats', timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as e:
            return None
        return {}
    
    async def get_recent_jobs(self, limit=5):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'{API}/scraper/progress?limit={limit}', timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('yearbooks', [])
        except Exception as e:
            return []
        return []
    
    def display_dashboard(self, stats, jobs):
        self.clear_screen()
        
        elapsed = time() - self.start_time
        total_faces = stats.get('total_faces', 0)
        total_yearbooks = stats.get('total_yearbooks', 0)
        processing = stats.get('processing', 0)
        completed = stats.get('completed', 0)
        queued = stats.get('queued', 0)
        failed = stats.get('failed', 0)
        stuck_processing = stats.get('stuck_processing', 0)
        stuck_queued = stats.get('stuck_queued', 0)
        
        # Calculate rates
        faces_gained = total_faces - self.last_faces
        yearbooks_gained = total_yearbooks - self.last_yearbooks
        
        if elapsed > 0:
            self.faces_per_second = total_faces / elapsed
        
        self.last_faces = total_faces
        self.last_yearbooks = total_yearbooks
        
        # Header
        print("╔" + "═" * 78 + "╗")
        print("║" + " " * 20 + "🚀 DOPPELGANGER LIVE SCRAPER MONITOR 🚀" + " " * 19 + "║")
        print("╚" + "═" * 78 + "╝")
        print()
        
        # Main Stats
        print("┌─ 📊 MAIN STATISTICS " + "─" * 56 + "┐")
        print(f"│  👤 Total Faces:          {total_faces:>10,}  {'+' + str(faces_gained) if faces_gained > 0 else '':>10} │")
        print(f"│  📚 Total Yearbooks:      {total_yearbooks:>10,}  {'+' + str(yearbooks_gained) if yearbooks_gained > 0 else '':>10} │")
        print(f"│  ⏱️  Runtime:              {self.format_time(elapsed):>10}                   │")
        print(f"│  📈 Faces/Second:         {self.faces_per_second:>10.2f}                   │")
        print("└" + "─" * 78 + "┘")
        print()
        
        # Progress to 1M
        target = 1_000_000
        print("┌─ 🎯 PROGRESS TO 1 MILLION FACES " + "─" * 43 + "┐")
        print(f"│  {self.draw_progress_bar(total_faces, target, 70)} │")
        print(f"│  {total_faces:,} / {target:,} faces                                          │")
        if self.faces_per_second > 0:
            remaining = (target - total_faces) / self.faces_per_second
            print(f"│  ⏳ ETA: {self.format_time(remaining):>10}                                             │")
        print("└" + "─" * 78 + "┘")
        print()
        
        # Task Status
        print("┌─ ⚙️  TASK STATUS " + "─" * 60 + "┐")
        print(f"│  ✅ Completed:            {completed:>10}                               │")
        print(f"│  ⚙️  Processing:          {processing:>10}                               │")
        print(f"│  ⏳ Queued:               {queued:>10}                               │")
        print(f"│  ❌ Failed:               {failed:>10}                               │")
        
        if stuck_processing > 0 or stuck_queued > 0:
            print(f"│  ⚠️  Stuck:                {stuck_processing + stuck_queued:>10}  (Run: python check_tasks.py --fix) │")
        print("└" + "─" * 78 + "┘")
        print()
        
        # Recent Jobs
        if jobs:
            print("┌─ 📋 RECENT JOBS " + "─" * 60 + "┐")
            for i, job in enumerate(jobs[:5], 1):
                title = (job.get('title', 'Unknown')[:45] + '...') if len(job.get('title', 'Unknown')) > 45 else job.get('title', 'Unknown')
                status = job.get('scraping_status', 'unknown')
                faces = job.get('faces_extracted', 0)
                pages = job.get('pages_processed', 0)
                
                status_icon = {
                    'completed': '✅',
                    'processing': '⚙️',
                    'queued': '⏳',
                    'failed': '❌'
                }.get(status, '❓')
                
                print(f"│ {i}. {status_icon} {title:<48} │")
                print(f"│    Status: {status:<10} | Faces: {faces:<5} | Pages: {pages:<5}           │")
            print("└" + "─" * 78 + "┘")
        else:
            print("┌─ 📋 RECENT JOBS " + "─" * 60 + "┐")
            print("│  No jobs yet. Start scraping to see progress here!                      │")
            print("└" + "─" * 78 + "┘")
        
        print()
        print("🔄 Updating every 2 seconds... Press Ctrl+C to stop monitoring")
        print()
        
    async def run(self):
        print("Starting live monitor...")
        print("Fetching initial data...\n")
        
        try:
            while True:
                stats = await self.get_stats()
                jobs = await self.get_recent_jobs(5)
                
                if stats:
                    self.display_dashboard(stats, jobs)
                else:
                    print("⚠️  Unable to connect to backend. Retrying...")
                
                await asyncio.sleep(2)
                
        except KeyboardInterrupt:
            self.clear_screen()
            print("\n" + "="*80)
            print("📊 FINAL STATISTICS")
            print("="*80)
            
            stats = await self.get_stats()
            if stats:
                elapsed = time() - self.start_time
                print(f"\n  Total Runtime:     {self.format_time(elapsed)}")
                print(f"  Total Faces:       {stats.get('total_faces', 0):,}")
                print(f"  Total Yearbooks:   {stats.get('total_yearbooks', 0):,}")
                print(f"  Completed:         {stats.get('completed', 0)}")
                print(f"  Average Rate:      {self.faces_per_second:.2f} faces/second")
            
            print("\n✅ Monitor stopped. Scraping continues in background.")
            print("\n📍 Check status anytime:")
            print("   • CLI: python /app/check_tasks.py")
            print("   • Web: Visit /admin in your browser")
            print("   • Monitor: python /app/live_monitor.py")
            print()

async def main():
    monitor = LiveMonitor()
    await monitor.run()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
