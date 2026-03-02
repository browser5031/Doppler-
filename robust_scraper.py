#!/usr/bin/env python3
"""
Robust background scraper that actually works!
Runs continuously and collects faces from yearbooks
"""
import asyncio
import requests
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from PIL import Image
import io
import sys
import time
from datetime import datetime

sys.path.append('/app/backend')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize
client = AsyncIOMotorClient('mongodb://localhost:27017')
db = client['test_database']

# Import after path is set
from scraper.fast_face_detector import get_detector
from scraper.face_processor import FaceProcessor

async def scrape_yearbook_robust(identifier: str, max_pages: int = 100):
    """Robustly scrape a yearbook with proper error handling"""
    try:
        logger.info(f"🚀 Starting {identifier}")
        
        # Initialize detector and processor
        detector = get_detector()
        face_processor = FaceProcessor(db)
        
        # Mark as processing
        await db.yearbooks.update_one(
            {'identifier': identifier},
            {'$set': {
                'identifier': identifier,
                'scraping_status': 'processing',
                'started_at': datetime.utcnow().isoformat()
            }},
            upsert=True
        )
        
        faces_found = 0
        pages_processed = 0
        
        # Process pages
        for page_num in range(1, max_pages + 1):
            try:
                # Get page image
                filename = f"{page_num:04d}.jpg"
                url = f"https://archive.org/download/{identifier}/{filename}"
                
                resp = requests.get(url, timeout=15)
                if resp.status_code != 200 or len(resp.content) < 1000:
                    continue
                
                # Load and detect faces
                img = Image.open(io.BytesIO(resp.content))
                faces = detector.detect_faces(img)
                
                if faces:
                    logger.info(f"  📄 Page {page_num}: {len(faces)} faces")
                    
                    # Save faces
                    for face in faces:
                        embedding = face.get('embedding')
                        bbox = face.get('bbox', {})
                        
                        metadata = {
                            'yearbook_url': f"https://archive.org/details/{identifier}",
                            'page_url': f"https://archive.org/details/{identifier}/page/n{page_num}",
                            'x': int(bbox.get('x', 0)),
                            'y': int(bbox.get('y', 0)),
                            'w': int(bbox.get('w', bbox.get('width', 0))),
                            'h': int(bbox.get('h', bbox.get('height', 0))),
                            'confidence': face.get('confidence', 0.9)
                        }
                        
                        await face_processor.save_face(
                            embedding=embedding.tolist() if hasattr(embedding, 'tolist') else embedding,
                            yearbook_id=identifier,
                            page_num=page_num,
                            metadata=metadata
                        )
                        faces_found += 1
                
                pages_processed += 1
                
                # Progress update every 10 pages
                if pages_processed % 10 == 0:
                    await db.yearbooks.update_one(
                        {'identifier': identifier},
                        {'$set': {
                            'faces_extracted': faces_found,
                            'pages_processed': pages_processed
                        }}
                    )
                    logger.info(f"  ✅ Progress: {pages_processed} pages, {faces_found} faces")
                
            except Exception as e:
                logger.error(f"  ⚠️  Error on page {page_num}: {e}")
                continue
        
        # Mark complete
        await db.yearbooks.update_one(
            {'identifier': identifier},
            {'$set': {
                'scraping_status': 'completed',
                'faces_extracted': faces_found,
                'pages_processed': pages_processed,
                'completed_at': datetime.utcnow().isoformat()
            }}
        )
        
        logger.info(f"✅ {identifier}: {faces_found} faces from {pages_processed} pages\n")
        return {'faces': faces_found, 'pages': pages_processed}
        
    except Exception as e:
        logger.error(f"❌ Failed {identifier}: {e}")
        await db.yearbooks.update_one(
            {'identifier': identifier},
            {'$set': {'scraping_status': 'failed', 'error': str(e)}}
        )
        return {'faces': 0, 'pages': 0, 'error': str(e)}

async def main():
    """Main scraper loop"""
    yearbooks = [
        "0001_20191231",
        "0001_20191230",
        "0001_20191231_201912",
        "0003_20190906",
        "0006_20240809"
    ]
    
    logger.info("=" * 70)
    logger.info("🚀 ROBUST SCRAPER STARTING")
    logger.info("=" * 70)
    logger.info(f"Yearbooks to process: {len(yearbooks)}")
    logger.info(f"Pages per yearbook: 100")
    logger.info(f"Expected total faces: 5,000-7,500\n")
    
    for identifier in yearbooks:
        try:
            result = await scrape_yearbook_robust(identifier, max_pages=100)
            logger.info(f"✓ Result: {result}\n")
            
            # Brief pause between yearbooks
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"✗ Critical error with {identifier}: {e}\n")
            continue
    
    # Final stats
    total_faces = await db.faces.count_documents({})
    logger.info("=" * 70)
    logger.info("🎉 SCRAPER COMPLETED!")
    logger.info("=" * 70)
    logger.info(f"Total faces in database: {total_faces}")
    logger.info("=" * 70)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n\n⏹️  Scraper stopped by user")
    except Exception as e:
        logger.error(f"\n\n💥 Scraper crashed: {e}")
        import traceback
        traceback.print_exc()
