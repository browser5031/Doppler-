"""
Mobile API endpoints - Optimized for Android app
"""
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta, timezone
import jwt
from passlib.hash import bcrypt
import uuid

mobile_router = APIRouter(prefix="/api/mobile")

# JWT settings
SECRET_KEY = "your-secret-key-change-in-production"  # Change this!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30 * 24 * 60  # 30 days

# Models
class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    username: str

class FavoriteCreate(BaseModel):
    face_id: str

class MobileStats(BaseModel):
    total_faces: int
    total_yearbooks: int
    user_favorites: int

# Helper functions
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None

async def get_current_user(token: str):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return payload

# Auth endpoints
@mobile_router.post("/auth/register", response_model=Token)
async def register(user: UserCreate, db=None):
    """Register a new user"""
    from server import db as database
    
    # Check if user exists
    existing = await database.users.find_one({"username": user.username})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Hash password
    hashed_password = bcrypt.hash(user.password)
    
    # Create user
    user_id = str(uuid.uuid4())
    user_doc = {
        "user_id": user_id,
        "username": user.username,
        "email": user.email,
        "password": hashed_password,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "favorites": []
    }
    
    await database.users.insert_one(user_doc)
    
    # Create token
    access_token = create_access_token({"user_id": user_id, "username": user.username})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user_id,
        username=user.username
    )

@mobile_router.post("/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    """Login user"""
    from server import db
    
    # Find user
    user = await db.users.find_one({"username": credentials.username})
    if not user or not bcrypt.verify(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Create token
    access_token = create_access_token({
        "user_id": user["user_id"],
        "username": user["username"]
    })
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_id=user["user_id"],
        username=user["username"]
    )

# Face comparison - mobile optimized (smaller response)
@mobile_router.post("/compare")
async def mobile_compare(
    file: UploadFile = File(...),
    limit: int = 50,  # Reduced for mobile
    token: str = None
):
    """Mobile-optimized face comparison"""
    from server import extract_face_embedding, db
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    
    # Verify token if provided
    user = None
    if token:
        user = await get_current_user(token)
    
    contents = await file.read()
    
    # Extract embedding
    user_embedding = extract_face_embedding(contents)
    if user_embedding is None:
        raise HTTPException(status_code=400, detail="No face detected")
    
    # Get all faces
    faces_cursor = db.faces.find({}, {"_id": 0, "face_id": 1, "embedding": 1, 
                                       "yearbook_url": 1, "page_url": 1, 
                                       "thumbnail_url": 1, "year": 1, "school": 1})
    all_faces = await faces_cursor.to_list(None)
    
    if not all_faces:
        raise HTTPException(status_code=404, detail="No faces in database yet")
    
    # Calculate similarities
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
                "year": face.get("year"),
                "school": face.get("school"),
                "yearbook_url": face["yearbook_url"],
                "page_url": face["page_url"],
                "thumbnail_url": face.get("thumbnail_url"),
                "similarity_score": float(similarity * 100)
            })
    
    # Sort and return top matches
    similarities.sort(key=lambda x: x["similarity_score"], reverse=True)
    
    return {
        "total_compared": len(all_faces),
        "results": similarities[:limit]
    }

# Favorites
@mobile_router.post("/favorites")
async def add_favorite(favorite: FavoriteCreate, token: str):
    """Add face to favorites"""
    from server import db
    
    user = await get_current_user(token)
    user_id = user["user_id"]
    
    # Add to favorites
    await db.users.update_one(
        {"user_id": user_id},
        {"$addToSet": {"favorites": favorite.face_id}}
    )
    
    return {"success": True, "message": "Added to favorites"}

@mobile_router.delete("/favorites/{face_id}")
async def remove_favorite(face_id: str, token: str):
    """Remove from favorites"""
    from server import db
    
    user = await get_current_user(token)
    user_id = user["user_id"]
    
    await db.users.update_one(
        {"user_id": user_id},
        {"$pull": {"favorites": face_id}}
    )
    
    return {"success": True, "message": "Removed from favorites"}

@mobile_router.get("/favorites")
async def get_favorites(token: str):
    """Get user's favorite faces"""
    from server import db
    
    user = await get_current_user(token)
    user_id = user["user_id"]
    
    # Get user with favorites
    user_doc = await db.users.find_one({"user_id": user_id})
    favorite_ids = user_doc.get("favorites", [])
    
    if not favorite_ids:
        return {"favorites": []}
    
    # Get face details
    faces = await db.faces.find(
        {"face_id": {"$in": favorite_ids}},
        {"_id": 0}
    ).to_list(None)
    
    return {"favorites": faces}

# Stats - mobile optimized
@mobile_router.get("/stats")
async def get_mobile_stats(token: Optional[str] = None):
    """Get app statistics"""
    from server import db
    
    total_faces = await db.faces.count_documents({})
    total_yearbooks = await db.yearbooks.count_documents({})
    
    user_favorites = 0
    if token:
        try:
            user = await get_current_user(token)
            user_doc = await db.users.find_one({"user_id": user["user_id"]})
            user_favorites = len(user_doc.get("favorites", []))
        except:
            pass
    
    return {
        "total_faces": total_faces,
        "total_yearbooks": total_yearbooks,
        "user_favorites": user_favorites
    }

# Admin endpoints for mobile
@mobile_router.get("/admin/scraper-status")
async def mobile_scraper_status(token: str):
    """Get scraper status (admin only)"""
    from server import db
    
    user = await get_current_user(token)
    
    total_yearbooks = await db.yearbooks.count_documents({})
    total_faces = await db.faces.count_documents({})
    processing = await db.yearbooks.count_documents({'scraping_status': 'processing'})
    completed = await db.yearbooks.count_documents({'scraping_status': 'completed'})
    queued = await db.yearbooks.count_documents({'scraping_status': 'queued'})
    failed = await db.yearbooks.count_documents({'scraping_status': 'failed'})
    
    return {
        "total_yearbooks": total_yearbooks,
        "total_faces": total_faces,
        "processing": processing,
        "completed": completed,
        "queued": queued,
        "failed": failed
    }

@mobile_router.post("/admin/start-scraping")
async def mobile_start_scraping(identifier: str, max_pages: int = 50, token: str = None):
    """Start scraping a yearbook (admin)"""
    from server import orchestrator
    
    if token:
        user = await get_current_user(token)
    
    result = await orchestrator.start_scraping(identifier, {'max_pages': max_pages})
    return result

@mobile_router.post("/admin/auto-discover")
async def mobile_auto_discover(limit: int = 100, token: str = None):
    """Auto-discover and start scraping (admin)"""
    from server import archive_scraper, orchestrator
    
    if token:
        user = await get_current_user(token)
    
    # Discover yearbooks
    yearbooks = await archive_scraper.search_yearbooks(
        query="high school yearbook",
        year_start=2000,
        year_end=2015,
        limit=limit
    )
    
    if not yearbooks:
        return {'message': 'No yearbooks found', 'started': 0}
    
    # Start scraping all
    identifiers = [yb['identifier'] for yb in yearbooks]
    result = await orchestrator.batch_scrape(identifiers, max_pages=50)
    
    return {
        'message': f'Started scraping {len(identifiers)} yearbooks',
        'total_yearbooks': len(identifiers),
        'details': result
    }
