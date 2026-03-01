#!/usr/bin/env python3
"""
Background Worker - Continuously processes queued yearbooks
This should run as a service to ensure continuous processing
"""

import asyncio
import sys
import logging
from datetime import datetime

sys.path.insert(0, '/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from scraper.production_orchestrator import ProductionOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BackgroundWorker:
    def __init__(self, db, max_concurrent=3):
        self.db = db
        self.orchestrator = ProductionOrchestrator(db, max_workers=6)
        self.max_concurrent = max_concurrent
        self.running = True
        
    async def process_queue(self):
        """Continuously process queued yearbooks"""
        logger.info(f"🚀 Background worker started (max {self.max_concurrent} concurrent)")
        
        while self.running:
            try:
                # Get currently processing count
                processing_count = await self.db.yearbooks.count_documents({
                    'scraping_status': 'processing'
                })
                
                # Get queued yearbooks
                queued_count = await self.db.yearbooks.count_documents({
                    'scraping_status': 'queued'
                })
                
                logger.info(f"📊 Status: {processing_count} processing, {queued_count} queued")
                
                # Process yearbooks up to max_concurrent
                slots_available = self.max_concurrent - processing_count
                
                if slots_available > 0 and queued_count > 0:
                    # Get yearbooks to process
                    yearbooks = await self.db.yearbooks.find({
                        'scraping_status': 'queued'
                    }).limit(slots_available).to_list(slots_available)
                    
                    # Process each yearbook
                    tasks = []
                    for yb in yearbooks:
                        logger.info(f"⚙️  Starting: {yb['identifier']}")
                        task = asyncio.create_task(
                            self.process_one(yb['identifier'])
                        )
                        tasks.append(task)
                    
                    # Wait a bit before checking again
                    await asyncio.sleep(5)
                else:
                    # Nothing to do, wait longer
                    await asyncio.sleep(10)
                    
            except Exception as e:
                logger.error(f"❌ Worker error: {e}")
                await asyncio.sleep(30)
    
    async def process_one(self, identifier: str):
        """Process a single yearbook"""
        try:
            logger.info(f"🔄 Processing {identifier}")
            
            # Process the yearbook (no max_pages = process all)
            await self.orchestrator.process_yearbook(
                identifier,
                max_pages=None  # Process ALL pages
            )
            
            logger.info(f"✅ Completed {identifier}")
            
        except Exception as e:
            logger.error(f"❌ Error processing {identifier}: {e}")
            # Mark as failed
            await self.db.yearbooks.update_one(
                {'identifier': identifier},
                {
                    '$set': {
                        'scraping_status': 'failed',
                        'error_message': str(e)
                    }
                }
            )
    
    def stop(self):
        """Stop the worker"""
        logger.info("🛑 Stopping worker...")
        self.running = False

async def main():
    """Main worker loop"""
    # Connect to database
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.test_database
    
    # Create worker
    worker = BackgroundWorker(db, max_concurrent=3)
    
    try:
        # Run worker
        await worker.process_queue()
    except KeyboardInterrupt:
        logger.info("⏹️  Received stop signal")
        worker.stop()
    except Exception as e:
        logger.error(f"💥 Worker crashed: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Worker stopped")
