from fastapi import FastAPI, APIRouter, File, UploadFile, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, Response
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
from sklearn.metrics.pairwise import cosine_similarity
import asyncio
from scraper.archive_scraper import ArchiveScraper
from scraper.robust_orchestrator import RobustOrchestrator
from scraper.face_processor import FaceProcessor
from scraper.fast_face_detector import get_detector

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

# Initialize production-ready face comparison (NO ML models needed!)
from production_face_comparison import ProductionFaceComparison
face_comparer = ProductionFaceComparison()
USE_PRODUCTION_MODE = True
logger.info("✓ Production face comparison initialized (lightweight, no ML)")

# Initialize scraper components
archive_scraper = ArchiveScraper(db)
face_processor = FaceProcessor(db)

# Check if InsightFace is available for scraping (development only)
try:
    from scraper.robust_orchestrator import RobustOrchestrator
    from scraper.fast_face_detector import get_detector
    orchestrator = RobustOrchestrator(db, max_workers=6)
    face_detector = get_detector()
    logger.info("✓ InsightFace available for scraping (Development mode)")
except ImportError as e:
    logger.info("InsightFace not available - scraping disabled in production")
    orchestrator = None
    face_detector = None

# Create cache directory for thumbnails
CACHE_DIR = "/app/cache/thumbnails"
os.makedirs(CACHE_DIR, exist_ok=True)

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
    """Extract face embedding using InsightFace - FAST"""
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

@app.get("/health")
async def health_check():
    """Health check endpoint for deployment"""
    try:
        # Check MongoDB connection
        await db.command('ping')
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@api_router.post("/upload-compare", response_model=ComparisonResponse)
async def upload_and_compare(
    file: UploadFile = File(...),
    top_n: int = 100
):
    """Upload face and find similar faces using Azure Face API"""
    start_time = datetime.now()
    
    if not USE_AZURE or not azure_face:
        raise HTTPException(status_code=503, detail="Face recognition service not available")
    
    try:
        # Read uploaded image
        contents = await file.read()
        from io import BytesIO
        image_stream = BytesIO(contents)
        
        # Detect face in uploaded image using Azure
        detect_result = azure_face.detect_faces(image_stream)
        
        if detect_result['status'] != 'success' or detect_result['face_count'] == 0:
            raise HTTPException(
                status_code=400,
                detail="No face detected in uploaded image. Please upload a clear photo with a visible face."
            )
        
        # Get the first detected face ID
        query_face_id = detect_result['faces'][0]['face_id']
        logger.info(f"Detected face ID: {query_face_id}")
        
        # Find similar faces in our database using Azure
        search_result = azure_face.find_similar_faces(query_face_id, max_candidates=top_n)
        
        if search_result['status'] != 'success':
            raise HTTPException(status_code=500, detail=f"Face search failed: {search_result.get('message')}")
        
        # Get face details from MongoDB for each match
        results = []
        for match in search_result['matches']:
            # The person_id in Azure corresponds to face_id in our MongoDB
            face_doc = await db.faces.find_one({'face_id': match['person_id']})
            
            if face_doc:
                results.append(SimilarityResult(
                    face_id=face_doc.get('face_id', ''),
                    name=face_doc.get('name'),
                    year=face_doc.get('year'),
                    school=face_doc.get('school'),
                    yearbook_url=face_doc.get('yearbook_url', ''),
                    page_url=face_doc.get('page_url', ''),
                    thumbnail_url=face_doc.get('thumbnail_url'),
                    similarity_score=match['similarity_score']
                ))
        
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"✓ Found {len(results)} similar faces in {processing_time:.2f}s")
        
        return ComparisonResponse(
            total_faces_compared=await db.faces.count_documents({}),
            results=results[:top_n],
            processing_time=processing_time
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in upload-compare: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
    """Start scraping a yearbook"""
    if PRODUCTION_MODE or not orchestrator:
        raise HTTPException(status_code=503, detail="Scraping not available in production mode. Use development environment for scraping.")
    
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

@api_router.get("/thumbnail/{face_id}")
async def get_face_thumbnail(face_id: str):
    """
    Get cropped face thumbnail (PimEyes style)
    Fetches page from archive.org, crops to face bbox, caches result
    """
    try:
        # Check cache first
        cache_path = os.path.join(CACHE_DIR, f"{face_id}.jpg")
        if os.path.exists(cache_path):
            return FileResponse(cache_path, media_type="image/jpeg")
        
        # Get face data from database
        face = await db.faces.find_one({'face_id': face_id})
        if not face:
            raise HTTPException(status_code=404, detail="Face not found")
        
        # Check if bbox exists
        bbox = face.get('bbox')
        if not bbox or not all(k in bbox for k in ['x', 'y', 'w', 'h']):
            # No bbox - return archive.org page thumbnail as fallback
            yearbook_id = face.get('yearbook_id')
            page_num = face.get('page_num')
            if yearbook_id and page_num is not None:
                fallback_url = f"https://archive.org/services/img/{yearbook_id}/page/n{page_num}_thumb.jpg"
                return Response(status_code=302, headers={"Location": fallback_url})
            raise HTTPException(status_code=404, detail="No thumbnail available")
        
        # Fetch page image from archive.org
        yearbook_id = face['yearbook_id']
        page_num = face['page_num']
        
        # Try different archive.org image URLs
        image_urls = [
            f"https://archive.org/download/{yearbook_id}/page/n{page_num}.jpg",
            f"https://archive.org/services/img/{yearbook_id}/page/n{page_num}",
        ]
        
        import requests
        image_data = None
        for url in image_urls:
            try:
                resp = requests.get(url, timeout=10, allow_redirects=True)
                if resp.status_code == 200:
                    image_data = resp.content
                    break
            except:
                continue
        
        if not image_data:
            raise HTTPException(status_code=404, detail="Could not fetch page image")
        
        # Open image and crop to face
        from io import BytesIO
        img = Image.open(BytesIO(image_data))
        
        # Extract bbox
        x, y, w, h = bbox['x'], bbox['y'], bbox['w'], bbox['h']
        
        # Crop with some padding (10%)
        padding = int(max(w, h) * 0.1)
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(img.width, x + w + padding)
        y2 = min(img.height, y + h + padding)
        
        face_img = img.crop((x1, y1, x2, y2))
        
        # Resize to standard thumbnail size
        face_img.thumbnail((200, 200), Image.Resampling.LANCZOS)
        
        # Save to cache
        face_img.save(cache_path, "JPEG", quality=85)
        
        return FileResponse(cache_path, media_type="image/jpeg")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating thumbnail for {face_id}: {e}")
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