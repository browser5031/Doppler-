"""
FIXED SCRAPER - Actually works!
No background tasks, no reload issues, just works.
"""
import asyncio
import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime, timezone
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FixedScraper:
    def __init__(self):
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        db_name = os.environ.get('DB_NAME', 'test_database')
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client[db_name]
        
    async def scrape_one_yearbook(self, identifier, max_pages=30):
        """Scrape ONE yearbook completely - synchronously, no background tasks"""
        logger.info(f"🚀 Starting: {identifier}")
        
        # Mark as processing
        await self.db.yearbooks.update_one(
            {"identifier": identifier},
            {"$set": {
                "scraping_status": "processing",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "pages_processed": 0,
                "faces_extracted": 0
            }},
            upsert=True
        )
        
        faces_count = 0
        pages_count = 0
        
        try:
            # Get yearbook metadata from archive.org
            async with aiohttp.ClientSession() as session:
                url = f"https://archive.org/metadata/{identifier}"
                async with session.get(url) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to get metadata: {response.status}")
                    
                    metadata = await response.json()
                    files = metadata.get("files", [])
                    
                    # Find PDF or image files
                    image_files = [f for f in files if f.get("format") in ["JPEG", "PNG", "Image Container PDF"]]
                    
                    logger.info(f"📄 Found {len(image_files)} image files")
                    
                    # Process each image
                    for i, file_info in enumerate(image_files[:max_pages]):
                        if i >= max_pages:
                            break
                            
                        filename = file_info.get("name", "")
                        image_url = f"https://archive.org/download/{identifier}/{filename}"
                        
                        try:
                            # Download image
                            async with session.get(image_url) as img_response:
                                if img_response.status == 200:
                                    image_data = await img_response.read()
                                    
                                    # Extract faces from image
                                    faces = await self.extract_faces_from_image(image_data, identifier, i, image_url)
                                    
                                    if faces:
                                        faces_count += len(faces)
                                        logger.info(f"  ✅ Page {i+1}: Found {len(faces)} faces")
                                    
                                    pages_count += 1
                                    
                                    # Update progress IMMEDIATELY
                                    await self.db.yearbooks.update_one(
                                        {"identifier": identifier},
                                        {"$set": {
                                            "pages_processed": pages_count,
                                            "faces_extracted": faces_count,
                                            "updated_at": datetime.now(timezone.utc).isoformat()
                                        }}
                                    )
                                    
                        except Exception as e:
                            logger.warning(f"  ⚠️ Page {i+1} failed: {e}")
                            continue
            
            # Mark as completed
            await self.db.yearbooks.update_one(
                {"identifier": identifier},
                {"$set": {
                    "scraping_status": "completed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "pages_processed": pages_count,
                    "faces_extracted": faces_count
                }}
            )
            
            logger.info(f"✅ COMPLETED {identifier}: {faces_count} faces from {pages_count} pages")
            return faces_count
            
        except Exception as e:
            logger.error(f"❌ FAILED {identifier}: {e}")
            await self.db.yearbooks.update_one(
                {"identifier": identifier},
                {"$set": {
                    "scraping_status": "failed",
                    "error": str(e),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            return 0
    
    async def extract_faces_from_image(self, image_data, yearbook_id, page_num, image_url):
        """Extract faces from image and save to database"""
        try:
            import cv2
            import numpy as np
            from insightface.app import FaceAnalysis
            
            # Initialize face detector (cached)
            if not hasattr(self, 'face_app'):
                self.face_app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
                self.face_app.prepare(ctx_id=0, det_size=(640, 640))
            
            # Convert image
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return []
            
            # Detect faces
            faces = self.face_app.get(img)
            
            if not faces:
                return []
            
            # Save each face
            saved_faces = []
            for idx, face in enumerate(faces):
                face_id = f"{yearbook_id}_p{page_num}_f{idx}"
                
                face_doc = {
                    "face_id": face_id,
                    "yearbook_id": yearbook_id,
                    "page_num": page_num,
                    "face_index": idx,
                    "yearbook_url": f"https://archive.org/details/{yearbook_id}",
                    "page_url": image_url,
                    "embedding": face.embedding.tolist(),
                    "bbox": face.bbox.tolist(),
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                
                await self.db.faces.update_one(
                    {"face_id": face_id},
                    {"$set": face_doc},
                    upsert=True
                )
                
                saved_faces.append(face_id)
            
            return saved_faces
            
        except Exception as e:
            logger.error(f"Face extraction error: {e}")
            return []
    
    async def discover_and_scrape(self, query="yearbook", limit=20, max_pages=30):
        """Discover yearbooks and scrape them one by one"""
        logger.info(f"🔍 Discovering yearbooks: {query}")
        
        async with aiohttp.ClientSession() as session:
            # Search archive.org
            search_url = "https://archive.org/advancedsearch.php"
            params = {
                "q": query,
                "output": "json",
                "rows": limit,
                "page": 1
            }
            
            async with session.get(search_url, params=params) as response:
                data = await response.json()
                docs = data.get("response", {}).get("docs", [])
                
                logger.info(f"✅ Found {len(docs)} yearbooks")
                
                total_faces = 0
                for doc in docs:
                    identifier = doc.get("identifier")
                    if identifier:
                        faces = await self.scrape_one_yearbook(identifier, max_pages)
                        total_faces += faces
                
                logger.info(f"🎉 DONE! Total faces: {total_faces}")
                return total_faces

async def main():
    """Test the fixed scraper"""
    scraper = FixedScraper()
    
    # Test with ONE yearbook first
    logger.info("=" * 60)
    logger.info("TESTING FIXED SCRAPER")
    logger.info("=" * 60)
    
    # Test yearbook
    test_id = "yearbook1970unse"
    faces = await scraper.scrape_one_yearbook(test_id, max_pages=10)
    
    logger.info("=" * 60)
    logger.info(f"TEST COMPLETE: {faces} faces extracted")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
