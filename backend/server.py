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
from deepface import DeepFace
from PIL import Image
import io
import base64
import traceback
from sklearn.metrics.pairwise import cosine_similarity
import asyncio
from scraper.archive_scraper import ArchiveScraper
from scraper.orchestrator import ScraperOrchestrator
from scraper.face_processor import FaceProcessor

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

def extract_face_embedding(image_bytes: bytes, model_name: str = "Facenet512") -> Optional[np.ndarray]:
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img_array = np.array(img)
        
        embedding_objs = DeepFace.represent(
            img_path=img_array,
            model_name=model_name,
            enforce_detection=True,
            detector_backend="opencv"
        )
        
        if embedding_objs and len(embedding_objs) > 0:
            return np.array(embedding_objs[0]["embedding"])
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
    top_n: int = 100
):
    start_time = datetime.now()
    
    try:
        contents = await file.read()
        
        user_embedding = extract_face_embedding(contents)
        if user_embedding is None:
            raise HTTPException(
                status_code=400,
                detail="No face detected in the uploaded image. Please upload a clear photo with a visible face."
            )
        
        faces_cursor = db.faces.find({}, {"_id": 0})
        all_faces = await faces_cursor.to_list(None)
        
        if not all_faces:
            raise HTTPException(
                status_code=404,
                detail="No faces in database yet. Please check back later."
            )
        
        similarities = []
        for face in all_faces:
            if "embedding" in face and face["embedding"]:
                db_embedding = np.array(face["embedding"])
                similarity = cosine_similarity(
                    user_embedding.reshape(1, -1),
                    db_embedding.reshape(1, -1)
                )[0][0]
                
                similarities.append({
                    "face_id": face["face_id"],
                    "name": face.get("name"),
                    "year": face.get("year"),
                    "school": face.get("school"),
                    "yearbook_url": face["yearbook_url"],
                    "page_url": face["page_url"],
                    "thumbnail_url": face.get("thumbnail_url"),
                    "similarity_score": float(similarity * 100)
                })
        
        similarities.sort(key=lambda x: x["similarity_score"], reverse=True)
        top_results = similarities[:top_n]
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return ComparisonResponse(
            total_faces_compared=len(all_faces),
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
            "by_year": years
        }
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
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