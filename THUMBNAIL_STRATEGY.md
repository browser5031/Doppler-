# Thumbnail Strategy for Free Tier (PimEyes-Style)

## Recommended: Server-Side Crop + Cache

### Why This Approach:
1. Shows ACTUAL faces (not full pages)
2. Zero database storage
3. Works on free tier
4. Good user experience
5. Scales well

### How It Works:

**Step 1: Store Bounding Box (4 numbers)**
```javascript
{
  face_id: "abc123",
  embedding: [512 floats],  // 4KB
  page_url: "https://archive.org/...",
  bbox: {x: 100, y: 200, w: 80, h: 100}  // 16 bytes!
}
```

**Step 2: Generate Thumbnail URL**
```javascript
thumbnail_url: "/api/thumbnail/{face_id}"
// Or with params:
thumbnail_url: "/api/crop?yearbook={id}&page={num}&x={x}&y={y}&w={w}&h={h}"
```

**Step 3: Backend Endpoint**
```python
@app.get("/api/thumbnail/{face_id}")
async def get_thumbnail(face_id: str):
    # 1. Get face data from DB (has bbox)
    # 2. Check cache first (Redis or file)
    # 3. If not cached:
    #    - Fetch page image from archive.org
    #    - Crop to bbox
    #    - Resize to 200x200
    #    - Cache for 7 days
    # 4. Return image
```

**Step 4: Frontend**
```javascript
<img src={`${BACKEND_URL}/api/thumbnail/${match.face_id}`} />
```

### Storage Impact:

**Per Face:**
- Embedding: 4KB
- Bounding box: 16 bytes (4 integers)
- Metadata: ~500 bytes
- **Total: ~4.5KB**

**For 1M faces:**
- Database: 4.5GB
- Cache (7 days, 30% active): ~250MB
- **Total: ~5GB** (vs 12GB with base64!)

### Performance:

**First Load:**
- Fetch from archive.org: ~200ms
- Crop & resize: ~50ms
- Cache & return: ~10ms
- **Total: ~260ms** (acceptable)

**Cached (subsequent):**
- Return from cache: ~5ms
- **Fast!**

### Free Tier Compatible:

✅ MongoDB: ~128K faces (512MB limit)
✅ Disk cache: ~250MB for active thumbnails
✅ Archive.org: Free bandwidth
✅ No image storage in DB
✅ Luxand: 500 calls/month (for uploads)

### Scaling Path:

**To 1M faces:**
1. Start: Free tier (128K faces)
2. Scale: Paid MongoDB M10 ($60/mo, 10GB)
3. Cache: Redis or file system
4. CDN: CloudFlare free tier for cached images

**Why better than alternatives:**
- Option 1 (Archive thumbs): Shows page, not face ❌
- Option 3 (Placeholder): Still need image source ❌
- This option: Shows face, fast, scalable ✅
