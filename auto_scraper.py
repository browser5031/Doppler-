#!/usr/bin/env python3
"""
AUTO-SCRAPER - Get to 1 Million Faces FAST!
This script continuously discovers and scrapes yearbooks from archive.org
"""
import os
import sys
import asyncio
import aiohttp
from pathlib import Path
from dotenv import load_dotenv
import logging
from datetime import datetime

# Setup
ROOT_DIR = Path(__file__).parent / 'backend'
load_dotenv(ROOT_DIR / '.env')

BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8001')
API = f"{BACKEND_URL}/api"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AutoScraper:
    def __init__(self):
        self.session = None
        self.total_discovered = 0
        self.total_started = 0
        self.target_faces = 1_000_000
        
    async def get_stats(self):
        """Get current scraping statistics"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API}/recovery/stats") as response:
                    if response.status == 200:
                        return await response.json()
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
        return {}
    
    async def discover_yearbooks(self, year_start=1950, year_end=2024, limit=200):
        """Discover yearbooks from archive.org"""
        try:
            logger.info(f"🔍 Discovering yearbooks ({year_start}-{year_end})...")
            
            params = {
                'query': 'yearbook',
                'year_start': year_start,
                'year_end': year_end,
                'limit': limit
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API}/scraper/search-yearbooks", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        yearbooks = data.get('results', [])
                        self.total_discovered += len(yearbooks)
                        logger.info(f"✅ Found {len(yearbooks)} yearbooks!")
                        return yearbooks
        except Exception as e:
            logger.error(f"Error discovering yearbooks: {e}")
        return []
    
    async def start_scraping(self, identifier, max_pages=50):
        """Start scraping a single yearbook"""
        try:
            params = {
                'identifier': identifier,
                'max_pages': max_pages,
                'priority': 5
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{API}/scraper/start", params=params) as response:
                    if response.status == 200:
                        self.total_started += 1
                        return True
                    else:
                        logger.warning(f"Failed to start {identifier}: {response.status}")
        except Exception as e:
            logger.debug(f"Error starting {identifier}: {e}")
        return False
    
    async def batch_scrape(self, yearbooks, max_pages=50):
        """Start scraping multiple yearbooks"""
        logger.info(f"🚀 Starting batch scrape of {len(yearbooks)} yearbooks...")
        
        tasks = []
        for yb in yearbooks:
            identifier = yb.get('identifier')
            if identifier:
                tasks.append(self.start_scraping(identifier, max_pages))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful = sum(1 for r in results if r is True)
        
        logger.info(f"✅ Started {successful}/{len(yearbooks)} yearbooks")
        return successful
    
    async def reset_stuck_tasks(self):
        """Reset any stuck tasks"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{API}/recovery/reset-all-stuck") as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('reset_count', 0) > 0:
                            logger.info(f"🔧 Reset {data['reset_count']} stuck tasks")
                        return True
        except Exception as e:
            logger.error(f"Error resetting stuck tasks: {e}")
        return False
    
    async def run_cycle(self, year_start, year_end, max_pages_per_book=50, batch_size=200):
        """Run one discovery and scraping cycle"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🎯 CYCLE START - Target: {self.target_faces:,} faces")
        logger.info(f"{'='*60}\n")
        
        # Get current stats
        stats = await self.get_stats()
        current_faces = stats.get('total_faces', 0)
        logger.info(f"📊 Current Progress: {current_faces:,} / {self.target_faces:,} faces ({current_faces/self.target_faces*100:.1f}%)")
        
        if current_faces >= self.target_faces:
            logger.info(f"🎉 TARGET REACHED! {current_faces:,} faces collected!")
            return True
        
        # Reset any stuck tasks
        await self.reset_stuck_tasks()
        
        # Discover yearbooks
        yearbooks = await self.discover_yearbooks(year_start, year_end, batch_size)
        
        if not yearbooks:
            logger.warning("⚠️  No yearbooks found in this range")
            return False
        
        # Start scraping
        await self.batch_scrape(yearbooks, max_pages_per_book)
        
        # Show updated stats
        stats = await self.get_stats()
        logger.info(f"\n📈 Stats:")
        logger.info(f"  Total Yearbooks: {stats.get('total_yearbooks', 0)}")
        logger.info(f"  Processing: {stats.get('processing', 0)}")
        logger.info(f"  Queued: {stats.get('queued', 0)}")
        logger.info(f"  Completed: {stats.get('completed', 0)}")
        logger.info(f"  Total Faces: {stats.get('total_faces', 0):,}")
        
        return False
    
    async def run_continuous(self, cycles=10, delay_between_cycles=60):
        """Run multiple cycles to reach 1M faces"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 AUTO-SCRAPER STARTING!")
        logger.info(f"🎯 Target: {self.target_faces:,} faces")
        logger.info(f"⏱️  Running {cycles} cycles")
        logger.info(f"{'='*60}\n")
        
        # Year ranges to search (working backwards for better photos)
        year_ranges = [
            (2010, 2024),
            (2000, 2009),
            (1990, 1999),
            (1980, 1989),
            (1970, 1979),
            (1960, 1969),
            (1950, 1959),
        ]
        
        for cycle in range(cycles):
            logger.info(f"\n🔄 CYCLE {cycle + 1}/{cycles}")
            
            # Rotate through year ranges
            year_range = year_ranges[cycle % len(year_ranges)]
            
            target_reached = await self.run_cycle(
                year_start=year_range[0],
                year_end=year_range[1],
                max_pages_per_book=50,  # Limit pages per book for speed
                batch_size=200  # Process 200 yearbooks per cycle
            )
            
            if target_reached:
                logger.info(f"\n🎉🎉🎉 TARGET REACHED! 🎉🎉🎉")
                break
            
            if cycle < cycles - 1:
                logger.info(f"\n⏳ Waiting {delay_between_cycles}s before next cycle...")
                await asyncio.sleep(delay_between_cycles)
        
        # Final stats
        stats = await self.get_stats()
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 FINAL STATS")
        logger.info(f"{'='*60}")
        logger.info(f"Total Faces: {stats.get('total_faces', 0):,}")
        logger.info(f"Total Yearbooks: {stats.get('total_yearbooks', 0)}")
        logger.info(f"Completed: {stats.get('completed', 0)}")
        logger.info(f"Discovered: {self.total_discovered}")
        logger.info(f"Started: {self.total_started}")
        logger.info(f"{'='*60}\n")

async def main():
    scraper = AutoScraper()
    
    # Parse arguments
    cycles = 20  # Default: 20 cycles
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        cycles = int(sys.argv[1])
    
    await scraper.run_continuous(cycles=cycles, delay_between_cycles=30)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Scraper stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
