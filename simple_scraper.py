#!/usr/bin/env python3
"""
Simple reliable scraper using archive.org page service API
"""
import asyncio
import requests
from motor.motor_asyncio import AsyncIOMotorClient
from PIL import Image
import io
import logging
from datetime import datetime, timezone
import sys
sys.path.append('/app/backend')
from scraper.fast_face_detector import get_detector
from scraper.face_processor import FaceProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize
client = AsyncIOMotorClient('mongodb://localhost:27017')
db = client['test_database']
face_processor = FaceProcessor(db)
face_detector = get_detector()

async def scrape_yearbook(identifier: str, max_pages: int = 50):
    """Scrape a yearbook using archive.org page service"""
    logger.info(f"Starting {identifier}")
    
    # Mark as processing
    await db.yearbooks.update_one(
        {'identifier': identifier},
        {'$set': {
            'identifier': identifier,
            'scraping_status': 'processing',
            'started_at': datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    faces_found = 0
    pages_processed = 0
    
    # Try pages 0-max_pages
    for page_num in range(max_pages):
        try:
            # Get page image from archive.org
            url = f"https://archive.org/services/img/{identifier}/page/n{page_num}"
            resp = requests.get(url, timeout=15, allow_redirects=True)
            
            if resp.status_code != 200 or len(resp.content) < 1000:
                continue
            
            # Load image
            img = Image.open(io.BytesIO(resp.content))
            
            # Detect faces
            faces = face_detector.detect_faces(img)
            
            # Log all faces detected (even low confidence)
            if faces:
                logger.info(f"  Page {page_num}: Found {len(faces)} faces (conf: {[f.get('confidence', 0) for f in faces[:3]]})")
                
                # Save each face
                for face in faces:
                    embedding = face.get('embedding')
                    bbox = face.get('bbox', {})
                    
                    metadata = {
                        'yearbook_url': f"https://archive.org/details/{identifier}",
                        'page_url': f"https://archive.org/details/{identifier}/page/n{page_num}",
                        'x': bbox.get('x', 0),
                        'y': bbox.get('y', 0),
                        'w': bbox.get('width', 0),
                        'h': bbox.get('height', 0),
                        'confidence': face.get('confidence', 0)
                    }
                    
                    await face_processor.save_face(
                        embedding=embedding.tolist() if hasattr(embedding, 'tolist') else embedding,
                        yearbook_id=identifier,
                        page_num=page_num,
                        metadata=metadata
                    )
                    faces_found += 1
            
            pages_processed += 1
            
            # Update progress every 5 pages
            if pages_processed % 5 == 0:
                await db.yearbooks.update_one(
                    {'identifier': identifier},
                    {'$set': {
                        'faces_extracted': faces_found,
                        'pages_processed': pages_processed,
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    }}
                )
                logger.info(f"  Progress: {pages_processed} pages, {faces_found} faces")
                
        except Exception as e:
            logger.error(f"  Error on page {page_num}: {e}")
            continue
    
    # Mark as completed
    await db.yearbooks.update_one(
        {'identifier': identifier},
        {'$set': {
            'scraping_status': 'completed',
            'faces_extracted': faces_found,
            'pages_processed': pages_processed,
            'total_pages': pages_processed,
            'completed_at': datetime.now(timezone.utc).isoformat()
        }}
    )
    
    logger.info(f"✓ {identifier}: {faces_found} faces from {pages_processed} pages")
    return {'faces': faces_found, 'pages': pages_processed}

async def main():
    """Scrape multiple yearbooks"""
    yearbooks = [
        "0001_20191231",
        "0001_20191230", 
        "0001_20191231_201912",
        "0003_20190906",
        "0006_20240809"
    ]
    
    logger.info(f"Starting scraper for {len(yearbooks)} yearbooks")
    
    for identifier in yearbooks:
        try:
            result = await scrape_yearbook(identifier, max_pages=30)
            logger.info(f"✓ Completed {identifier}: {result}")
        except Exception as e:
            logger.error(f"✗ Failed {identifier}: {e}")
    
    # Final stats
    total_faces = await db.faces.count_documents({})
    logger.info(f"\n=== FINAL STATS ===")
    logger.info(f"Total faces in database: {total_faces}")

if __name__ == "__main__":
    asyncio.run(main())
