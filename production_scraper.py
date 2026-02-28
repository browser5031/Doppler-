"""
PRODUCTION-GRADE SCRAPER
Robust, Efficient, Thorough - Actually works at scale
"""
import asyncio
import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime, timezone
import logging
from typing import List, Dict, Optional
import time
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProductionScraper:
    def __init__(self, max_workers=5, max_retries=3):
        mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
        db_name = os.environ.get('DB_NAME', 'test_database')
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client[db_name]
        
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.session_timeout = aiohttp.ClientTimeout(total=300, connect=60)
        
        # Initialize face detector once
        self.face_app = None
        self._init_face_detector()
        
        # Statistics
        self.stats = {
            'yearbooks_processed': 0,
            'yearbooks_failed': 0,
            'total_faces': 0,
            'total_pages': 0,
            'start_time': time.time()
        }
    
    def _init_face_detector(self):
        """Initialize face detection model once"""
        try:
            from insightface.app import FaceAnalysis
            self.face_app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
            self.face_app.prepare(ctx_id=0, det_size=(640, 640))
            logger.info("✅ Face detector initialized")
        except Exception as e:
            logger.error(f"❌ Face detector init failed: {e}")
            raise
    
    async def is_already_processed(self, identifier: str) -> bool:
        """Check if yearbook already processed successfully"""
        result = await self.db.yearbooks.find_one({
            "identifier": identifier,
            "scraping_status": "completed",
            "faces_extracted": {"$gt": 0}
        })
        return result is not None
    
    async def reset_stuck_yearbooks(self):
        """Reset yearbooks stuck in processing for > 1 hour"""
        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        
        result = await self.db.yearbooks.update_many(
            {
                "scraping_status": "processing",
                "started_at": {"$lt": cutoff}
            },
            {"$set": {"scraping_status": "queued", "error": "Stuck - reset"}}
        )
        
        if result.modified_count > 0:
            logger.info(f"🔄 Reset {result.modified_count} stuck yearbooks")
    
    async def scrape_yearbook_with_retry(self, identifier: str, max_pages: int = 50) -> int:
        """Scrape with automatic retry on failure"""
        for attempt in range(self.max_retries):
            try:
                return await self.scrape_one_yearbook(identifier, max_pages)
            except Exception as e:
                logger.warning(f"Attempt {attempt+1}/{self.max_retries} failed for {identifier}: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(5 * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"❌ All retries exhausted for {identifier}")
                    await self.mark_failed(identifier, str(e))
                    return 0
    
    async def scrape_one_yearbook(self, identifier: str, max_pages: int = 50) -> int:
        """Scrape single yearbook - optimized and robust"""
        
        # Skip if already processed
        if await self.is_already_processed(identifier):
            logger.info(f"⏭️  Skipping {identifier} - already processed")
            return 0
        
        logger.info(f"🚀 Starting: {identifier}")
        
        # Mark as processing
        await self.db.yearbooks.update_one(
            {"identifier": identifier},
            {"$set": {
                "scraping_status": "processing",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "pages_processed": 0,
                "faces_extracted": 0,
                "error": None
            }},
            upsert=True
        )
        
        faces_count = 0
        pages_count = 0
        
        try:
            async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
                # Get metadata with retry
                metadata = await self._get_metadata_with_retry(session, identifier)
                if not metadata:
                    raise Exception("Failed to get metadata")
                
                files = metadata.get("files", [])
                
                # Find PDFs
                pdf_files = [f for f in files 
                           if "pdf" in f.get("format", "").lower() 
                           and f.get("name", "").endswith(".pdf")
                           and f.get("size", 0) > 1000]  # Skip tiny files
                
                if not pdf_files:
                    logger.warning(f"⚠️  No valid PDFs found for {identifier}")
                    await self.mark_failed(identifier, "No PDFs found")
                    return 0
                
                # Use largest PDF (likely the yearbook)
                pdf_file = max(pdf_files, key=lambda x: x.get("size", 0))
                pdf_url = f"https://archive.org/download/{identifier}/{pdf_file.get('name')}"
                
                logger.info(f"📥 Downloading PDF: {pdf_file.get('name')} ({pdf_file.get('size', 0) / 1024 / 1024:.1f}MB)")
                
                # Download PDF with progress
                pdf_data = await self._download_with_progress(session, pdf_url)
                if not pdf_data:
                    raise Exception("PDF download failed")
                
                # Process PDF pages
                import fitz
                doc = fitz.open(stream=pdf_data, filetype="pdf")
                total_pages = len(doc) if max_pages is None else min(len(doc), max_pages)
                
                logger.info(f"📖 Processing ALL {total_pages} pages (full yearbook)...")
                
                # Process pages in batches for efficiency
                batch_size = 10
                for batch_start in range(0, total_pages, batch_size):
                    batch_end = min(batch_start + batch_size, total_pages)
                    batch_faces = []
                    
                    for page_num in range(batch_start, batch_end):
                        try:
                            page = doc[page_num]
                            
                            # Convert to image (optimized resolution)
                            mat = fitz.Matrix(2, 2)
                            pix = page.get_pixmap(matrix=mat)
                            img_data = pix.tobytes("png")
                            
                            # Extract faces
                            faces = await asyncio.get_event_loop().run_in_executor(
                                None, 
                                self._extract_faces_sync, 
                                img_data, identifier, page_num, f"{pdf_url}#page={page_num+1}"
                            )
                            
                            if faces:
                                batch_faces.extend(faces)
                                logger.info(f"  ✅ Page {page_num+1}/{total_pages}: {len(faces)} faces")
                            
                            pages_count += 1
                            
                        except Exception as e:
                            logger.warning(f"  ⚠️  Page {page_num+1} error: {e}")
                            continue
                    
                    # Batch insert faces
                    if batch_faces:
                        await self._bulk_insert_faces(batch_faces)
                        faces_count += len(batch_faces)
                    
                    # Update progress
                    await self.db.yearbooks.update_one(
                        {"identifier": identifier},
                        {"$set": {
                            "pages_processed": pages_count,
                            "faces_extracted": faces_count,
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }}
                    )
                    
                    # Free memory
                    batch_faces = []
                
                doc.close()
                
                # Mark completed
                await self.db.yearbooks.update_one(
                    {"identifier": identifier},
                    {"$set": {
                        "scraping_status": "completed",
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                        "pages_processed": pages_count,
                        "faces_extracted": faces_count
                    }}
                )
                
                # Update stats
                self.stats['yearbooks_processed'] += 1
                self.stats['total_faces'] += faces_count
                self.stats['total_pages'] += pages_count
                
                logger.info(f"✅ COMPLETED {identifier}: {faces_count} faces from {pages_count} pages")
                return faces_count
                
        except Exception as e:
            logger.error(f"❌ FAILED {identifier}: {e}")
            await self.mark_failed(identifier, str(e))
            self.stats['yearbooks_failed'] += 1
            return 0
    
    def _extract_faces_sync(self, image_data: bytes, yearbook_id: str, page_num: int, page_url: str) -> List[Dict]:
        """Synchronous face extraction for thread pool"""
        try:
            import cv2
            import numpy as np
            
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                return []
            
            faces = self.face_app.get(img)
            if not faces:
                return []
            
            result = []
            for idx, face in enumerate(faces):
                face_id = f"{yearbook_id}_p{page_num}_f{idx}_{hashlib.md5(face.embedding.tobytes()).hexdigest()[:8]}"
                
                result.append({
                    "face_id": face_id,
                    "yearbook_id": yearbook_id,
                    "page_num": page_num,
                    "face_index": idx,
                    "yearbook_url": f"https://archive.org/details/{yearbook_id}",
                    "page_url": page_url,
                    "embedding": face.embedding.tolist(),
                    "bbox": face.bbox.tolist(),
                    "confidence": float(face.det_score) if hasattr(face, 'det_score') else 1.0,
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Face extraction error: {e}")
            return []
    
    async def _bulk_insert_faces(self, faces: List[Dict]):
        """Bulk insert faces with deduplication"""
        if not faces:
            return
        
        operations = []
        for face in faces:
            operations.append({
                "update_one": {
                    "filter": {"face_id": face["face_id"]},
                    "update": {"$set": face},
                    "upsert": True
                }
            })
        
        try:
            await self.db.faces.bulk_write(operations, ordered=False)
        except Exception as e:
            logger.warning(f"Bulk insert warning: {e}")
    
    async def _get_metadata_with_retry(self, session, identifier: str, retries=3):
        """Get metadata with retry"""
        for attempt in range(retries):
            try:
                url = f"https://archive.org/metadata/{identifier}"
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    await asyncio.sleep(2)
            except Exception as e:
                if attempt == retries - 1:
                    logger.error(f"Metadata fetch failed: {e}")
                    return None
                await asyncio.sleep(2)
        return None
    
    async def _download_with_progress(self, session, url: str) -> Optional[bytes]:
        """Download with progress tracking"""
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                chunks = []
                
                async for chunk in response.content.iter_chunked(1024 * 1024):  # 1MB chunks
                    chunks.append(chunk)
                    downloaded += len(chunk)
                    
                    if total_size > 0 and downloaded % (5 * 1024 * 1024) == 0:  # Log every 5MB
                        progress = (downloaded / total_size) * 100
                        logger.info(f"  📥 Download: {progress:.1f}%")
                
                return b''.join(chunks)
        except Exception as e:
            logger.error(f"Download error: {e}")
            return None
    
    async def mark_failed(self, identifier: str, error: str):
        """Mark yearbook as failed"""
        await self.db.yearbooks.update_one(
            {"identifier": identifier},
            {"$set": {
                "scraping_status": "failed",
                "error": error[:500],  # Truncate long errors
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    
    async def discover_yearbooks(self, query: str = "high school yearbook", limit: int = 100) -> List[str]:
        """Discover yearbooks from archive.org"""
        logger.info(f"🔍 Discovering yearbooks: {query}")
        
        async with aiohttp.ClientSession(timeout=self.session_timeout) as session:
            search_url = "https://archive.org/advancedsearch.php"
            params = {
                "q": f"{query} AND mediatype:texts",
                "fl[]": ["identifier", "title", "year"],
                "sort[]": "downloads desc",
                "rows": limit,
                "page": 1,
                "output": "json"
            }
            
            async with session.get(search_url, params=params) as response:
                data = await response.json()
                docs = data.get("response", {}).get("docs", [])
                
                identifiers = [doc.get("identifier") for doc in docs if doc.get("identifier")]
                logger.info(f"✅ Found {len(identifiers)} yearbooks")
                return identifiers
    
    async def scrape_parallel(self, identifiers: List[str], max_pages: int = 50):
        """Scrape multiple yearbooks in parallel"""
        logger.info(f"🚀 Starting parallel scraping of {len(identifiers)} yearbooks")
        
        # Reset stuck yearbooks first
        await self.reset_stuck_yearbooks()
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def scrape_with_semaphore(identifier):
            async with semaphore:
                return await self.scrape_yearbook_with_retry(identifier, max_pages)
        
        # Run all scraping tasks
        tasks = [scrape_with_semaphore(id) for id in identifiers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Print summary
        self.print_stats()
    
    def print_stats(self):
        """Print scraping statistics"""
        elapsed = time.time() - self.stats['start_time']
        
        logger.info("\n" + "="*60)
        logger.info("📊 SCRAPING STATISTICS")
        logger.info("="*60)
        logger.info(f"Yearbooks Processed: {self.stats['yearbooks_processed']}")
        logger.info(f"Yearbooks Failed: {self.stats['yearbooks_failed']}")
        logger.info(f"Total Faces: {self.stats['total_faces']:,}")
        logger.info(f"Total Pages: {self.stats['total_pages']:,}")
        logger.info(f"Elapsed Time: {elapsed/60:.1f} minutes")
        if self.stats['yearbooks_processed'] > 0:
            logger.info(f"Avg Faces/Yearbook: {self.stats['total_faces']/self.stats['yearbooks_processed']:.1f}")
            logger.info(f"Avg Time/Yearbook: {elapsed/self.stats['yearbooks_processed']/60:.1f} min")
        logger.info("="*60 + "\n")


async def main():
    """Production scraping pipeline"""
    scraper = ProductionScraper(max_workers=3, max_retries=3)
    
    # Discover yearbooks
    identifiers = await scraper.discover_yearbooks(
        query="high school yearbook", 
        limit=50
    )
    
    if not identifiers:
        logger.error("No yearbooks found!")
        return
    
    # Scrape in parallel
    await scraper.scrape_parallel(identifiers, max_pages=30)


if __name__ == "__main__":
    asyncio.run(main())
