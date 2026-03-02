# Doppler Face Scraper - Production Deployment Guide

## ⚠️ IMPORTANT: Production Mode

This application has TWO modes:

### 1. Development Mode (Current Sandbox)
- ✅ Full ML capabilities (InsightFace face detection)
- ✅ Active scraping from Archive.org
- ✅ Real-time face comparison with uploaded photos
- **Requirements:** 4GB+ RAM, Local MongoDB

### 2. Production Mode (Emergent Deployment)
- ⚠️ ML features DISABLED (memory constraints)
- ⚠️ Scraping endpoints return 503 errors
- ✅ Can display existing faces from database
- ✅ Upload endpoint returns sample results
- **Requirements:** 1GB RAM, Atlas MongoDB

## Production Deployment Configuration

### Environment Variables Required:
```bash
PRODUCTION_MODE=true          # Disables ML features
MONGO_URL=<atlas-connection-string>
DB_NAME=doppler_production
CORS_ORIGINS=*
REACT_APP_BACKEND_URL=https://your-app.emergent.host
```

### What Works in Production:
- ✅ View existing faces in database
- ✅ Browse yearbooks
- ✅ Admin dashboard (shows scraped data)
- ✅ API endpoints for face retrieval
- ✅ Thumbnail cropping (fetches from archive.org)

### What Doesn't Work in Production:
- ❌ Upload photo for face comparison (returns mock data)
- ❌ Scraping new yearbooks (needs development environment)
- ❌ Real-time face detection

## Recommended Architecture

### For Production Use:

**Option 1: Hybrid Setup (Recommended)**
1. **Production (Emergent):** Frontend + Read-only API
   - Displays pre-scraped faces
   - Provides search/browse interface
   - Uses thumbnails from archive.org

2. **Development (Sandbox):** Scraping Service
   - Runs scraper to collect faces
   - Stores results in Atlas MongoDB
   - Production reads from same database

**Option 2: External ML API**
- Replace InsightFace with AWS Rekognition/Google Vision AI
- Lightweight backend processes API responses
- Fully deployable to Emergent

**Option 3: Full ML Platform**
- Deploy to AWS ECS/Fargate with 4GB+ memory
- Keep all ML features
- Not compatible with Emergent

## Database Setup

### Data Migration:
The scraper in development will populate MongoDB Atlas:
```bash
# In development environment:
python3 /app/simple_scraper.py  # Scrapes faces → Atlas DB

# Production deployment:
# Reads same Atlas DB, displays faces
```

### Collections:
- `faces` - Face embeddings, bboxes, metadata
- `yearbooks` - Scraping progress, status

## Files for Production

### Use This Requirements File:
```
/app/backend/requirements-production.txt
```
(Excludes InsightFace, scikit-learn, opencv)

### Production Server Check:
The server auto-detects production mode and disables ML features when:
- `PRODUCTION_MODE=true` environment variable is set
- OR InsightFace imports fail

## Health Check

Production deployment requires `/health` endpoint:
```bash
curl https://your-app.emergent.host/health
# Response: {"status": "healthy", "database": "connected"}
```

## Deployment Checklist

Before deploying to production:

- [ ] Set `PRODUCTION_MODE=true` in environment
- [ ] Configure Atlas MongoDB connection string
- [ ] Update `REACT_APP_BACKEND_URL` to production URL
- [ ] Ensure faces are pre-scraped in development
- [ ] Test `/health` endpoint
- [ ] Verify thumbnails load from archive.org
- [ ] Accept that upload/scraping won't work (by design)

## Post-Deployment

### To Add More Faces:
1. Use development environment with ML
2. Run scraper: `python3 /app/simple_scraper.py`
3. Faces automatically available in production (shared Atlas DB)

### Monitoring:
```bash
# Check face count
curl https://your-app.emergent.host/api/stats

# View yearbooks
curl https://your-app.emergent.host/api/yearbooks?limit=10
```

## Support

For questions about:
- **Deployment:** Contact Emergent support
- **ML Features:** Consider external APIs (AWS Rekognition, Google Vision AI)
- **Scraping:** Use development environment

---

**Current Status:** ✅ Configured for production with ML gracefully disabled
