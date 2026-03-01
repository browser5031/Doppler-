# HANDOFF NOTE - Yearbook Face Scraper Project

**Date:** March 1, 2026  
**Status:** Scraper partially fixed, Face cropping ready to implement  
**Credits Remaining:** ~60 minutes of 75 total

---

## 🎯 IMMEDIATE NEXT TASK: Implement Face Cropping (30-35 min)

### Current Problem:
- Thumbnails show full yearbook pages instead of cropped faces
- Users see same page image for multiple faces from that page
- Need to implement Option 2.5: Server-side face cropping

---

## 📊 CURRENT STATE

### Database:
- **Faces:** 313
- **Yearbooks:** 50 total
  - Processing: 1
  - Completed: 1  
  - Failed: 48
  - Queued: 0 (**PROBLEM: Should be 48!**)

### Services Running:
- ✅ Backend API (FastAPI) - port 8001
- ✅ Frontend (React) - port 3000
- ✅ MongoDB - localhost:27017
- ✅ Background worker - PID varies (check: `ps aux | grep background_worker`)
- ❌ Auto-scraper - NOT running (needs restart)

### Face Detection:
- Primary: InsightFace (local ML - working)
- Fallback: Luxand.cloud API (500 calls/month - configured)
- API Key stored in: `/app/backend/.env`

---

## ⚠️ CRITICAL ISSUES TO FIX

### Issue 1: Background Worker Not Picking Up Queued Yearbooks
**Status:** Still broken - 48 yearbooks showing as "failed" instead of "queued"

**Root Cause:** Worker reset them to queued but they immediately failed again

**Fix Needed:**
```bash
# Reset failed to queued again
python3 << 'EOF'
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def reset():
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.test_database
    await db.yearbooks.update_many(
        {'scraping_status': 'failed'},
        {'$set': {'scraping_status': 'queued'}}
    )
asyncio.run(reset())
EOF

# Restart worker
pkill -f background_worker
nohup python3 /app/background_worker.py > /var/log/background_worker.log 2>&1 &
```

**Check if working:**
```bash
# Should show increasing face count and decreasing queued count
curl http://localhost:8001/api/scraper/status
```

### Issue 2: Auto-scraper Not Running
**Fix:**
```bash
nohup python3 /app/auto_scraper.py > /var/log/auto_scraper.log 2>&1 &
```

---

## 🎨 FACE CROPPING IMPLEMENTATION PLAN

### Step 1: Update Face Processor to Store Bounding Boxes (5 min)

**File:** `/app/backend/scraper/face_processor.py`

**Current storage:**
```python
face_data = {
    'face_id': str(uuid.uuid4()),
    'embedding': embedding,
    'page_url': page_url,
    'yearbook_id': yearbook_id,
    'page_num': page_num
}
```

**Update to:**
```python
face_data = {
    'face_id': str(uuid.uuid4()),
    'embedding': embedding,
    'page_url': page_url,
    'yearbook_id': yearbook_id,
    'page_num': page_num,
    'bbox': {  # ADD THIS
        'x': int(metadata.get('x', 0)),
        'y': int(metadata.get('y', 0)),
        'w': int(metadata.get('w', 0)),
        'h': int(metadata.get('h', 0))
    }
}
```

**Location:** Around line 40-60 in `save_face()` method

---

### Step 2: Create Thumbnail Crop Endpoint (15 min)

**File:** `/app/backend/server.py`

**Add after existing endpoints (around line 500):**

```python
import os
from fastapi.responses import FileResponse, Response
from PIL import Image
import hashlib

# Create cache directory
CACHE_DIR = "/app/cache/thumbnails"
os.makedirs(CACHE_DIR, exist_ok=True)

@api_router.get("/thumbnail/{face_id}")
async def get_face_thumbnail(face_id: str):
    """
    Get cropped face thumbnail (Option 2.5 - PimEyes style)
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
            fallback_url = f"https://archive.org/services/img/{yearbook_id}/page/n{page_num}_thumb.jpg"
            
            # Redirect to archive.org
            return Response(status_code=302, headers={"Location": fallback_url})
        
        # Fetch page image from archive.org
        yearbook_id = face['yearbook_id']
        page_num = face['page_num']
        
        # Try different archive.org image URLs
        image_urls = [
            f"https://archive.org/download/{yearbook_id}/page/n{page_num}.jpg",
            f"https://archive.org/services/img/{yearbook_id}/page/n{page_num}",
        ]
        
        image_data = None
        for url in image_urls:
            try:
                import requests
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
```

**Add imports at top of file:**
```python
from fastapi.responses import FileResponse, Response  # Add to existing imports
```

---

### Step 3: Update Frontend to Use New Endpoint (5 min)

**File:** `/app/frontend/src/App.js`

**Find where thumbnails are displayed (around line 280):**

```javascript
// CURRENT:
{match.thumbnail_url && (
  <img
    src={match.thumbnail_url}  // Archive.org URL
    alt={`Match ${index + 1}`}
    className="w-full h-48 object-cover rounded-lg mb-3"
  />
)}

// CHANGE TO:
{match.face_id && (
  <img
    src={`${BACKEND_URL}/api/thumbnail/${match.face_id}`}  // Our crop endpoint
    alt={`Match ${index + 1}`}
    className="w-full h-48 object-cover rounded-lg mb-3"
    onError={(e) => {
      // Fallback to archive.org if crop fails
      e.target.src = match.thumbnail_url;
    }}
  />
)}
```

---

### Step 4: Update Existing Faces with Bbox (10 min)

**Problem:** Existing 313 faces don't have bbox data

**Solution:** Extract from face detection metadata if available

**Script to run:**
```python
# This needs to be created - check if face detection stores bbox
# InsightFace returns bbox in detection results
# Need to retroactively add bbox OR accept that old faces use page thumbnails
```

**Alternative:** Accept that existing faces show page thumbnails, only new faces get cropping

---

### Step 5: Test (5 min)

```bash
# Restart backend
sudo supervisorctl restart backend

# Test thumbnail endpoint
curl -I http://localhost:8001/api/thumbnail/<some-face-id>

# Test upload and see cropped results
curl -X POST -F "file=@test.jpg" -F "top_n=5" http://localhost:8001/api/upload-compare
```

---

## 🔧 TESTING COMMANDS

### Check Scraper Status:
```bash
curl http://localhost:8001/api/stats
curl http://localhost:8001/api/scraper/status
```

### Check Logs:
```bash
tail -f /var/log/background_worker.log
tail -f /var/log/auto_scraper.log  
tail -f /var/log/supervisor/backend.err.log
```

### Check Processes:
```bash
ps aux | grep -E "(background_worker|auto_scraper)"
sudo supervisorctl status
```

---

## 📁 KEY FILES

### Backend:
- `/app/backend/server.py` - Main API (632 lines)
- `/app/backend/scraper/face_processor.py` - Face storage logic
- `/app/backend/scraper/production_orchestrator.py` - Yearbook processing
- `/app/backend/scraper/fast_face_detector.py` - InsightFace wrapper
- `/app/backend/scraper/luxand_service.py` - Luxand API fallback
- `/app/backend/.env` - API keys

### Frontend:
- `/app/frontend/src/App.js` - Main React component with upload + admin

### Workers:
- `/app/background_worker.py` - Processes queued yearbooks
- `/app/auto_scraper.py` - Auto-discovers yearbooks every 30 min

### Config:
- `/app/backend/requirements.txt` - Python deps (with ML)
- `/app/backend/requirements-production.txt` - Lightweight (no ML)

---

## 💡 IMPORTANT NOTES

### Storage Optimization Done:
- ✅ Removed base64 thumbnails (saved 8GB for 1M faces)
- ✅ Using archive.org URLs (zero storage)
- ✅ Database: 4.3KB per face (down from 12KB)

### Face Detection Working:
- ✅ InsightFace for scraper (local)
- ✅ Luxand.cloud for user uploads (API)
- ✅ Smart filtering (portrait-only mode)

### Known Issues:
- ⚠️ Scraper keeps stopping (worker issue)
- ⚠️ Only 313 faces in 8+ hours (should be 1000s)
- ⚠️ 48 yearbooks stuck in failed status
- ⚠️ Page thumbnails instead of face crops

---

## 🎯 SUCCESS CRITERIA

### For Face Cropping:
- [ ] Users see actual cropped faces (not pages)
- [ ] Thumbnails cached for performance
- [ ] Fallback to page thumbnail if crop fails
- [ ] New faces store bbox automatically

### For Scraper:
- [ ] Face count increasing by 100s/hour
- [ ] No yearbooks stuck in "failed"
- [ ] Worker processing 3 yearbooks concurrently
- [ ] Auto-scraper queuing new yearbooks every 30 min

---

## 📞 IF THINGS BREAK

### Database Connection Issues:
```bash
# Check MongoDB
sudo systemctl status mongod
mongo mongodb://localhost:27017/test_database --eval "db.stats()"
```

### Backend Won't Start:
```bash
# Check error logs
tail -n 100 /var/log/supervisor/backend.err.log

# Check port
lsof -i :8001

# Restart
sudo supervisorctl restart backend
```

### Frontend Issues:
```bash
sudo supervisorctl restart frontend
tail -f /var/log/supervisor/frontend.err.log
```

---

## 🚀 DEPLOYMENT NOTES

**Current:** Development environment (has InsightFace ML)

**For Production Deployment:**
1. Use `/app/backend/requirements-production.txt`
2. Remove ML dependencies
3. Luxand API becomes primary face detector
4. Everything else works the same

---

## 💰 CREDIT BUDGET

- Used: ~15 min (scraper debugging)
- Remaining: ~60 min
- Face cropping estimate: 30-35 min
- Buffer: 25-30 min for testing/fixes

---

## ✅ QUICK START FOR NEXT SESSION

1. **Check scraper is running:**
   ```bash
   curl http://localhost:8001/api/stats
   ps aux | grep background_worker
   ```

2. **If not, restart everything:**
   ```bash
   sudo supervisorctl restart all
   pkill -f background_worker && nohup python3 /app/background_worker.py > /var/log/background_worker.log 2>&1 &
   nohup python3 /app/auto_scraper.py > /var/log/auto_scraper.log 2>&1 &
   ```

3. **Then implement face cropping** following steps above

4. **Test thoroughly** before finishing

---

## 📝 FINAL NOTES

- User is on phone, can't run commands
- Free tier (MongoDB 512MB, Luxand 500 calls/month)
- Target: 1M faces for good doppelganger matching
- Current rate: Too slow (need to fix scraper first!)
- User wants both scraper fix + face cropping done

**Priority: Get scraper collecting faces continuously, THEN add face cropping for better UX**

Good luck! 🚀
