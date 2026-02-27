"""
Robust orchestrator - production grade with retry, deduplication, and optimization
"""
import sys
sys.path.insert(0, '/app/backend')

from scraper.production_orchestrator import ProductionOrchestrator
import logging
import hashlib
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class RobustOrchestrator(ProductionOrchestrator):
    """Enhanced orchestrator with robustness improvements"""
    
    def __init__(self, db, max_workers=6):
        super().__init__(db, max_workers)
        self.stats = {
            'start_time': datetime.now(timezone.utc),
            'total_processed': 0,
            'total_faces': 0,
            'total_errors': 0
        }
    
    async def detect_and_save_faces(self, identifier: str, yearbook_data: dict, img_data: dict) -> dict:
        """Enhanced with deduplication"""
        try:
            page_num = img_data['page_num']
            faces = self.pdf_processor.detect_faces_in_image(img_data['image'])
            
            saved = 0
            duplicates = 0
            
            for face in faces:
                # Create hash for deduplication
                embedding_str = str(face['embedding'][:50])
                embedding_hash = hashlib.md5(embedding_str.encode()).hexdigest()
                
                # Check for duplicate
                existing = await self.db.faces.find_one({'embedding_hash': embedding_hash})
                if existing:
                    duplicates += 1
                    continue
                
                thumbnail = self.pdf_processor.extract_face_thumbnail(img_data['image'], face)
                
                metadata = {
                    'yearbook_url': yearbook_data['archive_url'],
                    'page_url': f"{yearbook_data['archive_url']}/page/{page_num}",
                    'year': yearbook_data.get('year'),
                    'school': yearbook_data.get('title', ''),
                    'location': yearbook_data.get('publisher', ''),
                    'confidence': face.get('confidence', 1.0)
                }
                
                face_id = await self.face_processor.save_face(
                    embedding=face['embedding'],
                    yearbook_id=identifier,
                    page_num=page_num,
                    face_thumbnail=thumbnail,
                    metadata=metadata
                )
                
                if face_id:
                    await self.db.faces.update_one(
                        {'face_id': face_id},
                        {'$set': {'embedding_hash': embedding_hash}}
                    )
                    saved += 1
            
            return {'faces_count': saved, 'page_num': page_num, 'duplicates': duplicates}
            
        except Exception as e:
            logger.debug(f"No faces in page {img_data.get('page_num')}: {str(e)}")
            return {'faces_count': 0, 'page_num': img_data.get('page_num'), 'duplicates': 0}
    
    async def start_scraping(self, identifier: str, options: dict = None):
        """Enhanced with skip logic"""
        options = options or {}
        
        # Check if already completed
        existing = await self.db.yearbooks.find_one({'identifier': identifier})
        if existing:
            if existing.get('scraping_status') == 'completed' and existing.get('faces_extracted', 0) > 0:
                return {
                    'success': True,
                    'message': f'Already completed with {existing.get("faces_extracted")} faces',
                    'identifier': identifier,
                    'skipped': True
                }
        
        return await super().start_scraping(identifier, options)
