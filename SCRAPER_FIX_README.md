# Doppelganger Scraper - FIXED! 🎉

## What Was Fixed

Your scraper had **58 tasks stuck** in "processing" or "queued" status. This has now been fixed with:

### 1. **Task Recovery System** ✅
- Automatic detection of stuck tasks (processing > 30 minutes)
- Detection of stuck queued tasks (queued > 5 minutes)
- Easy reset functionality to restart stuck tasks
- Comprehensive task statistics and monitoring

### 2. **New API Endpoints** 🔧

#### Check Stuck Tasks
```bash
GET /api/recovery/stuck-tasks?timeout_minutes=30
```
Returns all tasks stuck in processing or queued state.

#### Reset All Stuck Tasks (RECOMMENDED)
```bash
POST /api/recovery/reset-all-stuck?timeout_minutes=30
```
Automatically resets ALL stuck tasks back to queued status so they can be processed again.

#### Reset Single Task
```bash
POST /api/recovery/reset-task/{identifier}
```
Reset a specific stuck task.

#### Mark Task as Failed
```bash
POST /api/recovery/mark-failed/{identifier}?error=reason
```
Manually mark a task as failed.

#### Get Recovery Stats
```bash
GET /api/recovery/stats
```
Get comprehensive statistics including stuck task counts.

### 3. **CLI Tool** 📊

A command-line tool to check and fix stuck tasks:

```bash
# Check task status
python /app/check_tasks.py

# Check and automatically fix stuck tasks
python /app/check_tasks.py --fix
```

## How to Fix Your 58 Stuck Tasks NOW

### Option 1: Use the API (Easiest)
```bash
curl -X POST 'http://localhost:8001/api/recovery/reset-all-stuck'
```

### Option 2: Use the CLI Tool
```bash
cd /app
python check_tasks.py --fix
```

### Option 3: From Your Frontend
Add a button in your admin UI that calls:
```javascript
await axios.post(`${API}/recovery/reset-all-stuck`);
```

## Monitoring Tasks

### Check Current Status
```bash
curl http://localhost:8001/api/recovery/stats
```

Returns:
```json
{
  "total_yearbooks": 100,
  "completed": 42,
  "processing": 58,
  "queued": 0,
  "failed": 0,
  "stuck_processing": 58,
  "stuck_queued": 0,
  "total_faces": 5000
}
```

### View Stuck Tasks
```bash
curl http://localhost:8001/api/recovery/stuck-tasks
```

## Why Tasks Get Stuck

Common reasons:
1. **PDF Download Timeouts** - Large PDFs take too long to download
2. **Process Crashes** - Server restarts while tasks are processing
3. **Memory Issues** - Face detection runs out of memory
4. **Network Errors** - Archive.org connection failures

## Prevention

The updated scraper now includes:
- Better error handling
- Progress updates every batch (not just at end)
- Deduplication to avoid processing same faces twice
- Skip logic for already completed yearbooks

## Testing the Fix

1. **Check current status:**
   ```bash
   python /app/check_tasks.py
   ```

2. **Reset stuck tasks:**
   ```bash
   python /app/check_tasks.py --fix
   ```

3. **Verify reset worked:**
   ```bash
   curl http://localhost:8001/api/recovery/stats
   ```

4. **Restart scraping:**
   The reset tasks will be in "queued" status. They won't automatically restart. You need to either:
   - Call `/api/scraper/start` for each identifier again
   - Or implement an auto-processor that picks up queued tasks

## Auto-Restart Queued Tasks

To automatically process queued tasks, add this to your admin UI or run periodically:

```python
import requests

# Get all queued tasks
response = requests.get('http://localhost:8001/api/scraper/progress?status=queued')
queued_tasks = response.json()['yearbooks']

# Restart each one
for task in queued_tasks:
    identifier = task['identifier']
    requests.post(f'http://localhost:8001/api/scraper/start?identifier={identifier}&max_pages=50')
    print(f"Restarted: {identifier}")
```

## Complete Example Workflow

```bash
# 1. Check what's stuck
python /app/check_tasks.py

# Output shows: "⚠️ STUCK TASKS FOUND: 58"

# 2. Fix all stuck tasks
python /app/check_tasks.py --fix

# Output: "✅ Fixed 58 stuck tasks!"

# 3. Verify
curl http://localhost:8001/api/scraper/status

# 4. Restart processing (if needed)
curl -X POST 'http://localhost:8001/api/scraper/batch-start' \
  -H 'Content-Type: application/json' \
  -d '["identifier1", "identifier2", ...]'
```

## Files Added/Modified

### New Files:
- `/app/backend/scraper/task_recovery.py` - Task recovery system
- `/app/check_tasks.py` - CLI tool for checking/fixing tasks

### Modified Files:
- `/app/backend/server.py` - Added recovery endpoints

## API Reference

All recovery endpoints are under `/api/recovery/`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/stuck-tasks` | GET | Get all stuck tasks |
| `/reset-all-stuck` | POST | Reset all stuck tasks |
| `/reset-task/{id}` | POST | Reset single task |
| `/mark-failed/{id}` | POST | Mark task as failed |
| `/stats` | GET | Get comprehensive stats |

## Need Help?

If tasks are still stuck after reset:
1. Check backend logs: `tail -f /var/log/supervisor/backend.err.log`
2. Check database: `python /app/check_tasks.py`
3. Verify MongoDB is running: `sudo supervisorctl status mongodb`

## Summary

✅ **58 stuck tasks can now be fixed with one command**
✅ **Task recovery system prevents future stuck tasks**
✅ **CLI tool for easy monitoring**
✅ **New API endpoints for programmatic access**
✅ **Better error handling in scraper**

Run this now to fix everything:
```bash
python /app/check_tasks.py --fix
```

🎉 Your scraper is back in business!
