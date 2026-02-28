from fastapi import FastAPI, APIRouter, File, UploadFile, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import numpy as np
from PIL import Image
import io
import base64
import traceback
# Removed sklearn dependency - using numpy instead
import asyncio
from scraper.archive_scraper import ArchiveScraper
from scraper.robust_orchestrator import RobustOrchestrator
from scraper.face_processor import FaceProcessor
try:
    from scraper.fast_face_detector import get_detector
    ML_ENABLED = True
except Exception as e:
    logger.warning(f"ML models not available: {e}. Face detection disabled.")
    ML_ENABLED = False
    get_detector = None

# Import Face++ service as fallback
from scraper.facepp_service import get_facepp_service
FACEPP_ENABLED = False

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize scraper components (optional if ML not available)
archive_scraper = ArchiveScraper(db)
orchestrator = RobustOrchestrator(db, max_workers=6)
face_processor = FaceProcessor(db)

# Initialize face detector only if ML is enabled
if ML_ENABLED:
    try:
        face_detector = get_detector()
        logger.info("✅ InsightFace initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️ Could not initialize face detector: {e}")
        face_detector = None
        ML_ENABLED = False
else:
    face_detector = None
    logger.warning("⚠️ Running in API-only mode (no local ML)")

def cosine_similarity_np(a: np.ndarray, b: np.ndarray) -> float:
    """
    Calculate cosine similarity using numpy (lightweight replacement for sklearn)
    """
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

class FaceEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    face_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: Optional[str] = None
    year: Optional[int] = None
    school: Optional[str] = None
    yearbook_url: str
    page_url: str
    thumbnail_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SimilarityResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    face_id: str
    name: Optional[str] = None
    year: Optional[int] = None
    school: Optional[str] = None
    yearbook_url: str
    page_url: str
    thumbnail_url: Optional[str] = None
    similarity_score: float

class ComparisonResponse(BaseModel):
    total_faces_compared: int
    results: List[SimilarityResult]
    processing_time: float

def extract_face_embedding(image_bytes: bytes) -> Optional[np.ndarray]:
    """Extract face embedding using InsightFace - FAST (if available)"""
    if not ML_ENABLED or face_detector is None:
        logger.warning("ML not available - cannot extract embedding from upload")
        return None
    
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        # Use global InsightFace detector
        faces = face_detector.detect_faces(img)
        
        if faces and len(faces) > 0:
            # Return first face embedding
            return np.array(faces[0]["embedding"])
        return None
    except Exception as e:
        logger.error(f"Error extracting face embedding: {str(e)}")
        return None

@api_router.get("/")
async def root():
    return {"message": "Doppelganger Finder API"}

@api_router.post("/upload-compare", response_model=ComparisonResponse)
async def upload_and_compare(
    file: UploadFile = File(...),
    top_n: int = Query(default=100, ge=1, le=500, description="Number of top matches to return (1-500)")
):
    start_time = datetime.now()
    
    try:
        contents = await file.read()
        
        user_embedding = extract_face_embedding(contents)
        if user_embedding is None:
            if not ML_ENABLED:
                raise HTTPException(
                    status_code=503,
                    detail="Face detection service unavailable. This deployment does not support local ML processing."
                )
            raise HTTPException(
                status_code=400,
                detail="No face detected in the uploaded image. Please upload a clear photo with a visible face."
            )
        
        # FIXED: Use batched processing instead of loading all faces at once
        # This prevents memory exhaustion with large databases
        total_count = await db.faces.count_documents({})
        
        if total_count == 0:
            raise HTTPException(
                status_code=404,
                detail="No faces in database yet. Please check back later."
            )
        
        logger.info(f"Comparing against {total_count} faces in database using batched processing")
        
        similarities = []
        batch_size = 1000  # Process 1000 faces at a time
        
        # Process faces in batches to avoid memory issues
        for skip in range(0, total_count, batch_size):
            batch_faces = await db.faces.find(
                {}, 
                {"_id": 0, "face_id": 1, "name": 1, "year": 1, "school": 1, 
                 "yearbook_url": 1, "page_url": 1, "thumbnail_url": 1, "embedding": 1}
            ).skip(skip).limit(batch_size).to_list(batch_size)
            
            for face in batch_faces:
                if "embedding" in face and face["embedding"]:
                    try:
                        db_embedding = np.array(face["embedding"])
                        
                        # Use numpy-based cosine similarity (no sklearn)
                        similarity = cosine_similarity_np(user_embedding, db_embedding)
                        
                        similarities.append({
                            "face_id": face["face_id"],
                            "name": face.get("name"),
                            "year": int(face.get("year")) if face.get("year") and str(face.get("year")).isdigit() else None,
                            "school": face.get("school"),
                            "yearbook_url": face["yearbook_url"],
                            "page_url": face["page_url"],
                            "thumbnail_url": face.get("thumbnail_url"),
                            "similarity_score": float(similarity * 100)
                        })
                    except Exception as e:
                        logger.debug(f"Error processing face {face.get('face_id')}: {e}")
                        continue
            
            logger.debug(f"Processed batch {skip//batch_size + 1}: {len(batch_faces)} faces")
        
        # Sort all similarities and get top N
        similarities.sort(key=lambda x: x["similarity_score"], reverse=True)
        top_results = similarities[:top_n]
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        logger.info(f"Comparison complete: {len(similarities)} valid comparisons, returning top {len(top_results)} in {processing_time:.2f}s")
        
        return ComparisonResponse(
            total_faces_compared=len(similarities),
            results=[SimilarityResult(**r) for r in top_results],
            processing_time=processing_time
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upload_and_compare: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred during face comparison: {str(e)}"
        )

@api_router.post("/seed-database")
async def seed_database():
    try:
        count = await db.faces.count_documents({})
        if count > 0:
            return {"message": f"Database already has {count} faces"}
        
        sample_faces = [
            {
                "face_id": str(uuid.uuid4()),
                "name": "John Smith",
                "year": 2005,
                "school": "Lincoln High School",
                "yearbook_url": "https://archive.org/details/yearbook2005",
                "page_url": "https://archive.org/details/yearbook2005/page/42",
                "thumbnail_url": "https://images.unsplash.com/photo-1542850083-aff0f80c1646?w=400",
                "embedding": np.random.randn(512).tolist(),
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "face_id": str(uuid.uuid4()),
                "name": "Emily Johnson",
                "year": 2007,
                "school": "Washington University",
                "yearbook_url": "https://archive.org/details/yearbook2007",
                "page_url": "https://archive.org/details/yearbook2007/page/128",
                "thumbnail_url": "https://images.unsplash.com/photo-1728585255188-6c8de5aeb275?w=400",
                "embedding": np.random.randn(512).tolist(),
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "face_id": str(uuid.uuid4()),
                "name": "Michael Brown",
                "year": 2010,
                "school": "Jefferson College",
                "yearbook_url": "https://archive.org/details/yearbook2010",
                "page_url": "https://archive.org/details/yearbook2010/page/89",
                "thumbnail_url": "https://images.unsplash.com/photo-1542850083-aff0f80c1646?w=400",
                "embedding": np.random.randn(512).tolist(),
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "face_id": str(uuid.uuid4()),
                "name": "Sarah Davis",
                "year": 2012,
                "school": "Roosevelt High School",
                "yearbook_url": "https://archive.org/details/yearbook2012",
                "page_url": "https://archive.org/details/yearbook2012/page/156",
                "thumbnail_url": "https://images.unsplash.com/photo-1728585255188-6c8de5aeb275?w=400",
                "embedding": np.random.randn(512).tolist(),
                "created_at": datetime.now(timezone.utc).isoformat()
            },
            {
                "face_id": str(uuid.uuid4()),
                "name": "David Wilson",
                "year": 2013,
                "school": "Madison University",
                "yearbook_url": "https://archive.org/details/yearbook2013",
                "page_url": "https://archive.org/details/yearbook2013/page/203",
                "thumbnail_url": "https://images.unsplash.com/photo-1542850083-aff0f80c1646?w=400",
                "embedding": np.random.randn(512).tolist(),
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        ]
        
        result = await db.faces.insert_many(sample_faces)
        return {
            "message": f"Successfully seeded {len(result.inserted_ids)} sample faces",
            "count": len(result.inserted_ids)
        }
        
    except Exception as e:
        logger.error(f"Error seeding database: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/stats")
async def get_stats():
    try:
        total_faces = await db.faces.count_documents({})
        total_yearbooks = await db.yearbooks.count_documents({})
        
        pipeline = [
            {"$group": {
                "_id": "$year",
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        years = await db.faces.aggregate(pipeline).to_list(None)
        
        return {
            "total_faces": total_faces,
            "total_yearbooks": total_yearbooks,
            "by_year": years
        }
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============== SCRAPER ENDPOINTS ==============

@api_router.get("/scraper/search-yearbooks")
async def search_yearbooks(
    query: str = Query(default="yearbook", description="Search query"),
    year_start: int = Query(default=2000, description="Start year"),
    year_end: int = Query(default=2015, description="End year"),
    limit: int = Query(default=50, ge=1, le=200)
):
    """Search for yearbooks on archive.org"""
    try:
        results = await archive_scraper.search_yearbooks(
            query=query,
            year_start=year_start,
            year_end=year_end,
            limit=limit
        )
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error searching yearbooks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/scraper/yearbook/{identifier}")
async def get_yearbook_details(identifier: str):
    """Get detailed information about a specific yearbook"""
    try:
        details = await archive_scraper.get_yearbook_details(identifier)
        if not details:
            raise HTTPException(status_code=404, detail="Yearbook not found")
        
        # Also check for available file formats
        pdf_info = await archive_scraper.get_pdf_download_url(identifier)
        details['available_format'] = pdf_info
        
        return details
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting yearbook details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/scraper/debug/{identifier}")
async def debug_yearbook_files(identifier: str):
    """Debug endpoint to see all available files for a yearbook"""
    try:
        import internetarchive as ia
        item = ia.get_item(identifier)
        
        files = []
        for f in item.files:
            files.append({
                'name': f['name'],
                'format': f.get('format', 'unknown'),
                'size': f.get('size', 0),
            })
        
        return {
            'identifier': identifier,
            'total_files': len(files),
            'files': files[:50],  # First 50 files
            'has_pdf': any('.pdf' in f['name'] for f in files),
            'has_djvu': any('.djvu' in f['name'] for f in files),
            'formats': list(set(f.get('format', 'unknown') for f in item.files))
        }
    except Exception as e:
        logger.error(f"Error debugging files: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/scraper/start")
async def start_scraping(
    background_tasks: BackgroundTasks,
    identifier: str = Query(..., description="Archive.org identifier"),
    max_pages: Optional[int] = Query(default=None, description="Limit pages to process"),
    priority: int = Query(default=5, ge=1, le=10)
):
    """Start scraping a yearbook - FAST"""
    try:
        result = await orchestrator.start_scraping(
            identifier=identifier,
            options={'max_pages': max_pages, 'priority': priority}
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to start scraping'))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting scraping: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/scraper/batch-start")
async def start_batch_scraping(
    background_tasks: BackgroundTasks,
    identifiers: List[str],
    max_pages: Optional[int] = Query(default=None)
):
    """Start scraping multiple yearbooks in parallel"""
    try:
        result = await orchestrator.batch_scrape(identifiers, max_pages=max_pages)
        return result
        
    except Exception as e:
        logger.error(f"Error starting batch scraping: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/scraper/auto-discover")
async def auto_discover_and_scrape(
    query: str = Query(default="yearbook"),
    year_start: int = Query(default=2000),
    year_end: int = Query(default=2015),
    limit: int = Query(default=100),
    max_pages_per_book: Optional[int] = Query(default=50)
):
    """Auto-discover yearbooks and start scraping all - FAST TRACK TO 1M FACES"""
    try:
        # Search for yearbooks
        yearbooks = await archive_scraper.search_yearbooks(
            query=query,
            year_start=year_start,
            year_end=year_end,
            limit=limit
        )
        
        if not yearbooks:
            return {'message': 'No yearbooks found', 'started': 0}
        
        # Start scraping all
        identifiers = [yb['identifier'] for yb in yearbooks]
        result = await orchestrator.batch_scrape(identifiers, max_pages=max_pages_per_book)
        
        return {
            'message': f'Started scraping {len(identifiers)} yearbooks',
            'total_yearbooks': len(identifiers),
            'details': result
        }
        
    except Exception as e:
        logger.error(f"Error in auto-discover: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/scraper/progress")
async def get_scraping_progress(
    status: Optional[str] = Query(default=None),
    skip: int = Query(default=0),
    limit: int = Query(default=20)
):
    """Get yearbook scraping progress"""
    try:
        query = {}
        if status:
            query['scraping_status'] = status
        
        cursor = db.yearbooks.find(
            query,
            {'_id': 0, 'identifier': 1, 'title': 1, 'year': 1, 'scraping_status': 1, 
             'faces_extracted': 1, 'pages_processed': 1, 'total_pages': 1, 'error': 1}
        ).skip(skip).limit(limit).sort('updated_at', -1)
        
        yearbooks = await cursor.to_list(length=limit)
        total = await db.yearbooks.count_documents(query)
        
        return {
            "yearbooks": yearbooks,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error getting progress: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/scraper/status")
async def get_scraper_status():
    """Get current scraper status"""
    try:
        total_yearbooks = await db.yearbooks.count_documents({})
        total_faces = await db.faces.count_documents({})
        processing = await db.yearbooks.count_documents({'scraping_status': 'processing'})
        completed = await db.yearbooks.count_documents({'scraping_status': 'completed'})
        failed = await db.yearbooks.count_documents({'scraping_status': 'failed'})
        queued = await db.yearbooks.count_documents({'scraping_status': 'queued'})
        
        return {
            "total_yearbooks": total_yearbooks,
            "total_faces": total_faces,
            "processing": processing,
            "completed": completed,
            "failed": failed,
            "queued": queued,
            "current_jobs": list(orchestrator.current_jobs.keys())
        }
    except Exception as e:
        logger.error(f"Error getting scraper status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/yearbooks")
async def get_yearbooks(
    skip: int = Query(default=0),
    limit: int = Query(default=20),
    status: Optional[str] = Query(default=None)
):
    """Get list of yearbooks in database"""
    try:
        query = {}
        if status:
            query['scraping_status'] = status
        
        cursor = db.yearbooks.find(query, {'_id': 0}).skip(skip).limit(limit).sort('created_at', -1)
        yearbooks = await cursor.to_list(length=limit)
        total = await db.yearbooks.count_documents(query)
        
        return {
            "yearbooks": yearbooks,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error getting yearbooks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/yearbooks/{identifier}/faces")
async def get_yearbook_faces(
    identifier: str,
    skip: int = Query(default=0),
    limit: int = Query(default=50)
):
    """Get faces from a specific yearbook"""
    try:
        faces = await face_processor.get_faces_by_yearbook(identifier, skip, limit)
        total = await db.faces.count_documents({'yearbook_id': identifier})
        
        return {
            "faces": faces,
            "total": total,
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error getting yearbook faces: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/faces/search")
async def search_all_faces(
    year_start: Optional[int] = Query(default=None),
    year_end: Optional[int] = Query(default=None),
    school: Optional[str] = Query(default=None),
    location: Optional[str] = Query(default=None),
    yearbook_id: Optional[str] = Query(default=None),
    skip: int = Query(default=0),
    limit: int = Query(default=50)
):
    """Search faces with filters"""
    try:
        result = await face_processor.search_faces(
            year_start=year_start,
            year_end=year_end,
            school=school,
            location=location,
            yearbook_id=yearbook_id,
            skip=skip,
            limit=limit
        )
        return result
    except Exception as e:
        logger.error(f"Error searching faces: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()