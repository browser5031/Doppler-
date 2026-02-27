"""
Task Recovery System - Fix stuck scraping tasks
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

class TaskRecovery:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def find_stuck_tasks(self, timeout_minutes: int = 30) -> List[Dict]:
        """Find tasks that are stuck (processing for too long)"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
            
            # Find yearbooks stuck in 'processing' state
            query = {
                'scraping_status': 'processing',
                'started_at': {'$lt': cutoff_time.isoformat()}
            }
            
            stuck_tasks = await self.db.yearbooks.find(
                query,
                {'_id': 0, 'identifier': 1, 'title': 1, 'started_at': 1, 
                 'pages_processed': 1, 'faces_extracted': 1}
            ).to_list(None)
            
            logger.info(f"Found {len(stuck_tasks)} stuck tasks")
            return stuck_tasks
            
        except Exception as e:
            logger.error(f"Error finding stuck tasks: {str(e)}")
            return []
    
    async def find_queued_tasks(self) -> List[Dict]:
        """Find tasks stuck in queued state"""
        try:
            # Find yearbooks stuck in 'queued' state for more than 5 minutes
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=5)
            
            query = {
                'scraping_status': 'queued',
                'updated_at': {'$lt': cutoff_time.isoformat()}
            }
            
            queued_tasks = await self.db.yearbooks.find(
                query,
                {'_id': 0, 'identifier': 1, 'title': 1, 'updated_at': 1}
            ).to_list(None)
            
            logger.info(f"Found {len(queued_tasks)} queued tasks")
            return queued_tasks
            
        except Exception as e:
            logger.error(f"Error finding queued tasks: {str(e)}")
            return []
    
    async def reset_stuck_task(self, identifier: str) -> bool:
        """Reset a stuck task back to queued state"""
        try:
            result = await self.db.yearbooks.update_one(
                {'identifier': identifier},
                {'$set': {
                    'scraping_status': 'queued',
                    'updated_at': datetime.now(timezone.utc).isoformat(),
                    'error': None
                }}
            )
            
            if result.modified_count > 0:
                logger.info(f"Reset stuck task: {identifier}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error resetting task {identifier}: {str(e)}")
            return False
    
    async def mark_task_failed(self, identifier: str, error_msg: str) -> bool:
        """Mark a stuck task as failed"""
        try:
            result = await self.db.yearbooks.update_one(
                {'identifier': identifier},
                {'$set': {
                    'scraping_status': 'failed',
                    'updated_at': datetime.now(timezone.utc).isoformat(),
                    'error': error_msg
                }}
            )
            
            if result.modified_count > 0:
                logger.info(f"Marked task as failed: {identifier}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error marking task as failed {identifier}: {str(e)}")
            return False
    
    async def reset_all_stuck_tasks(self, timeout_minutes: int = 30) -> Dict:
        """Reset all stuck tasks"""
        try:
            stuck_tasks = await self.find_stuck_tasks(timeout_minutes)
            queued_tasks = await self.find_queued_tasks()
            
            reset_count = 0
            for task in stuck_tasks:
                if await self.reset_stuck_task(task['identifier']):
                    reset_count += 1
            
            for task in queued_tasks:
                if await self.reset_stuck_task(task['identifier']):
                    reset_count += 1
            
            return {
                'success': True,
                'stuck_found': len(stuck_tasks),
                'queued_found': len(queued_tasks),
                'reset_count': reset_count
            }
            
        except Exception as e:
            logger.error(f"Error resetting all stuck tasks: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_task_stats(self) -> Dict:
        """Get comprehensive task statistics"""
        try:
            total = await self.db.yearbooks.count_documents({})
            completed = await self.db.yearbooks.count_documents({'scraping_status': 'completed'})
            processing = await self.db.yearbooks.count_documents({'scraping_status': 'processing'})
            queued = await self.db.yearbooks.count_documents({'scraping_status': 'queued'})
            failed = await self.db.yearbooks.count_documents({'scraping_status': 'failed'})
            
            stuck_tasks = await self.find_stuck_tasks()
            queued_stuck = await self.find_queued_tasks()
            
            return {
                'total_yearbooks': total,
                'completed': completed,
                'processing': processing,
                'queued': queued,
                'failed': failed,
                'stuck_processing': len(stuck_tasks),
                'stuck_queued': len(queued_stuck),
                'total_faces': await self.db.faces.count_documents({})
            }
            
        except Exception as e:
            logger.error(f"Error getting task stats: {str(e)}")
            return {}
