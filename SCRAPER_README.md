# Doppelgänger Finder - Comprehensive Scraper System

## Overview
A complete yearbook scraping system that downloads PDFs from archive.org, extracts faces, generates embeddings, and enables face comparison across thousands of yearbook photos.

## Features

### 🔍 **Archive.org Integration**
- Search yearbooks by keyword, year range (2000-2015)
- Fetch complete metadata (title, creator, publisher, subjects, etc.)
- Direct PDF download links
- Support for all yearbook types (high school, college, university)

### 📄 **PDF Processing**
- Extract images from PDF pages using PyMuPDF
- Render pages as images for face detection
- Filter out small/decorative images
- Process PDFs with hundreds of pages

### 👤 **Face Detection & Recognition**
- DeepFace with Facenet512 model for accurate embeddings
- OpenCV face detection backend
- Extract face thumbnails with padding
- Generate 512-dimensional embeddings
- Store embeddings for fast similarity comparison

### 💾 **Database Storage**
- Store yearbook metadata (never actual PDFs)
- Save face embeddings and thumbnails as base64
- Link faces to original archive.org page URLs
- Comprehensive search filters (year, school, location)

### ⚙️ **Job Queue System**
- Background processing with priority queue
- Track scraping progress (pages processed, faces found)
- Status monitoring (queued, processing, completed, failed)
- Batch scraping support

### 🎨 **Admin Dashboard**
- Search archive.org directly from UI
- Start scraping jobs with one click
- Monitor real-time scraping status
- View extracted faces by yearbook
- Comprehensive filtering and search

## API Endpoints

### Scraper Management

#### Search Yearbooks
```bash
GET /api/scraper/search-yearbooks?query=yearbook&year_start=2000&year_end=2015&limit=50
```
Returns: List of yearbooks from archive.org

#### Get Yearbook Details
```bash
GET /api/scraper/yearbook/{identifier}
```
Returns: Complete metadata, PDF files, page count

#### Start Scraping
```bash
POST /api/scraper/start?identifier={id}&max_pages=10&priority=5
```
Creates scraping job and starts background processor

#### Batch Start
```bash
POST /api/scraper/batch-start
Body: ["identifier1", "identifier2", ...]
```
Creates multiple scraping jobs

#### Get Jobs
```bash
GET /api/scraper/jobs?status=processing&limit=20
```
Returns: List of scraping jobs with status

#### Get Status
```bash
GET /api/scraper/status
```
Returns: Current scraper status, job counts

### Data Access

#### Get Yearbooks
```bash
GET /api/yearbooks?skip=0&limit=20&status=completed
```
Returns: Yearbooks in database

#### Get Yearbook Faces
```bash
GET /api/yearbooks/{identifier}/faces?skip=0&limit=50
```
Returns: All faces extracted from a yearbook

#### Search Faces
```bash
GET /api/faces/search?year_start=2005&year_end=2010&school=Lincoln&limit=50
```
Returns: Faces matching filter criteria

## Data Models

### Yearbook
```json
{
  "identifier": "yearbook2005",
  "title": "Lincoln High School 2005",
  "year": 2005,
  "creator": "Lincoln High School",
  "publisher": "Yearbook Publishing Co.",
  "description": "Annual yearbook...",
  "subjects": ["yearbooks", "high school"],
  "archive_url": "https://archive.org/details/yearbook2005",
  "num_pages": 200,
  "faces_extracted": 342,
  "scraping_status": "completed",
  "created_at": "2025-01-27T12:00:00Z"
}
```

### Face
```json
{
  "face_id": "uuid",
  "embedding": [512 floats],
  "yearbook_id": "yearbook2005",
  "page_num": 42,
  "yearbook_url": "https://archive.org/details/yearbook2005",
  "page_url": "https://archive.org/details/yearbook2005/page/42",
  "thumbnail_url": "data:image/jpeg;base64,...",
  "name": null,
  "year": 2005,
  "school": "Lincoln High School",
  "location": "Lincoln, NE",
  "created_at": "2025-01-27T12:00:00Z"
}
```

### Scraping Job
```json
{
  "identifier": "yearbook2005",
  "status": "processing",
  "priority": 5,
  "created_at": "2025-01-27T12:00:00Z",
  "started_at": "2025-01-27T12:05:00Z",
  "faces_found": 120,
  "pages_processed": 42,
  "total_pages": 200,
  "error": null
}
```

## Search Capabilities

### Archive.org Search
- **Text search**: Keywords in title, description, creator
- **Year range**: Filter by publication year
- **Media type**: Automatically filtered to texts/PDFs
- **Sorting**: By downloads, date, relevance

### Face Search
- **Year range**: Find faces from specific years
- **School**: Search by school name (fuzzy match)
- **Location**: Filter by geographic location
- **Yearbook**: Get all faces from one yearbook
- **Pagination**: Skip/limit for large result sets

### Similarity Search
- Upload photo → Extract embedding → Compare with all faces
- Cosine similarity scoring
- Return top N matches (100-500)
- Sort by similarity percentage

## Usage Examples

### 1. Search for High School Yearbooks
```javascript
const response = await axios.get(`${API}/scraper/search-yearbooks`, {
  params: {
    query: 'high school yearbook',
    year_start: 2005,
    year_end: 2010,
    limit: 50
  }
});
```

### 2. Start Scraping a Yearbook
```javascript
await axios.post(`${API}/scraper/start`, null, {
  params: {
    identifier: 'yearbook2008',
    max_pages: 50,  // Limit to first 50 pages
    priority: 7
  }
});
```

### 3. Search Faces by School
```javascript
const response = await axios.get(`${API}/faces/search`, {
  params: {
    school: 'Lincoln High',
    year_start: 2000,
    year_end: 2015,
    limit: 100
  }
});
```

## Performance Considerations

### PDF Processing
- Large PDFs (500+ pages) can take 10-30 minutes
- Use `max_pages` parameter to limit processing
- Face detection averages 1-2 seconds per image

### Face Comparison
- Comparing against 10,000 faces: ~0.5 seconds
- Comparing against 100,000 faces: ~2-5 seconds
- MongoDB indexes on year, school for fast filtering

### Storage
- Embeddings: 512 floats × 4 bytes = 2KB per face
- Thumbnails (base64): ~15-30KB per face
- 100,000 faces ≈ 2-4GB storage

## Best Practices

1. **Start Small**: Use `max_pages=10` for testing
2. **Prioritize**: Use higher priority for important yearbooks
3. **Batch Process**: Use batch-start for multiple yearbooks
4. **Monitor**: Check `/scraper/status` regularly
5. **Filter**: Use year/location filters to narrow searches

## Troubleshomarks

### No Faces Detected
- Yearbook may have low-quality scans
- Images too small (< 100x100px)
- No portrait-style photos on pages

### Scraping Failed
- PDF download timeout (large files)
- Invalid PDF format
- Archive.org rate limiting

### Slow Performance
- Large PDF files (> 100MB)
- Many high-resolution images
- Processing all pages without limit

## Future Enhancements

1. **OCR Integration**: Extract names from yearbook captions
2. **Smart Pagination**: Detect student sections vs. other pages
3. **Duplicate Detection**: Skip duplicate faces
4. **Multi-threading**: Parallel page processing
5. **Resume Support**: Continue interrupted scraping jobs
6. **Advanced Filters**: Grade level, activities, sports
7. **Export**: Download faces as ZIP archive

## Architecture

```
┌─────────────────┐
│  Admin UI       │
│  (React)        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI        │
│  Server         │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌──────────┐
│Archive │ │ MongoDB  │
│Scraper │ │ Database │
└───┬────┘ └──────────┘
    │
    ▼
┌────────────┐
│    PDF     │
│ Processor  │
└─────┬──────┘
      │
      ▼
┌─────────────┐
│    Face     │
│  Processor  │
└─────────────┘
```

## MongoDB Collections

### `yearbooks`
- Stores yearbook metadata
- Index: identifier (unique)
- Index: year, scraping_status

### `faces`
- Stores face embeddings and metadata
- Index: yearbook_id, year
- Index: school (text), location (text)

### `scraping_jobs`
- Tracks scraping progress
- Index: status, priority, created_at

## Monitoring

Check scraping progress:
```bash
curl http://localhost:8001/api/scraper/status
```

View recent jobs:
```bash
curl http://localhost:8001/api/scraper/jobs?limit=5
```

Get yearbook details:
```bash
curl http://localhost:8001/api/yearbooks/{identifier}/faces
```
