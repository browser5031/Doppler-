import os
import uuid
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
import base64
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

class FaceProcessor:
    def __init__(self, db):
        self.db = db
    
    async def save_face(
        self,
        embedding: List[float],
        yearbook_id: str,
        page_num: int,
        face_thumbnail: bytes = None,
        metadata: Dict = None
    ) -> Optional[str]:
        """
        Save detected face to database
        """
        try:
            face_data = {
                'face_id': str(uuid.uuid4()),
                'embedding': embedding,
                'yearbook_id': yearbook_id,
                'page_num': page_num,
                'yearbook_url': metadata.get('yearbook_url', ''),
                'page_url': metadata.get('page_url', ''),
                'name': metadata.get('name'),
                'year': metadata.get('year'),
                'school': metadata.get('school', ''),
                'location': metadata.get('location', ''),
                'grade': metadata.get('grade', ''),
                'additional_info': metadata.get('additional_info', {}),
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Store face bounding box for future cropping (Option 2.5)
            if face_thumbnail:
                face_data['has_thumbnail'] = True
                # Store bbox if available in metadata
                if 'bbox' in metadata:
                    face_data['bbox'] = metadata['bbox']
            else:
                face_data['has_thumbnail'] = False
            
            # Generate archive.org thumbnail URL (Option 1 - simple & free)
            # Extract page number from page_url for accuracy
            page_number = page_num
            if face_data.get('page_url') and '/page/' in face_data['page_url']:
                try:
                    # Extract actual page number from page_url
                    # Format: https://archive.org/details/{id}/page/{num}
                    page_number = face_data['page_url'].split('/page/')[-1]
                except:
                    page_number = page_num
            
            # Archive.org thumbnail formats
            # Format 1: Thumbnail with 'n' prefix
            face_data['thumbnail_url'] = f"https://archive.org/services/img/{yearbook_id}/page/n{page_number}_thumb.jpg"
            
            # Store alternate formats as backup
            face_data['thumbnail_url_full'] = f"https://archive.org/download/{yearbook_id}/page/n{page_number}.jpg"
            
            await self.db.faces.insert_one(face_data)
            logger.info(f"Saved face {face_data['face_id']} from {yearbook_id} page {page_num}")
            
            return face_data['face_id']
            
        except Exception as e:
            logger.error(f"Error saving face: {str(e)}")
            return None
    
    async def update_yearbook_face_count(self, yearbook_id: str) -> None:
        """
        Update the face count for a yearbook
        """
        try:
            count = await self.db.faces.count_documents({'yearbook_id': yearbook_id})
            await self.db.yearbooks.update_one(
                {'identifier': yearbook_id},
                {'$set': {'faces_extracted': count}}
            )
        except Exception as e:
            logger.error(f"Error updating face count: {str(e)}")
    
    async def get_faces_by_yearbook(self, yearbook_id: str, skip: int = 0, limit: int = 50) -> List[Dict]:
        """
        Get all faces from a specific yearbook
        """
        try:
            cursor = self.db.faces.find(
                {'yearbook_id': yearbook_id},
                {'_id': 0, 'embedding': 0}  # Exclude embedding for performance
            ).skip(skip).limit(limit)
            
            faces = await cursor.to_list(length=limit)
            return faces
            
        except Exception as e:
            logger.error(f"Error getting faces by yearbook: {str(e)}")
            return []
    
    async def search_faces(
        self,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None,
        school: Optional[str] = None,
        location: Optional[str] = None,
        yearbook_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Dict:
        """
        Search faces with comprehensive filters
        """
        try:
            # Build query
            query = {}
            
            if year_start or year_end:
                query['year'] = {}
                if year_start:
                    query['year']['$gte'] = year_start
                if year_end:
                    query['year']['$lte'] = year_end
            
            if school:
                query['school'] = {'$regex': school, '$options': 'i'}
            
            if location:
                query['location'] = {'$regex': location, '$options': 'i'}
            
            if yearbook_id:
                query['yearbook_id'] = yearbook_id
            
            # Get total count
            total = await self.db.faces.count_documents(query)
            
            # Get faces
            cursor = self.db.faces.find(
                query,
                {'_id': 0, 'embedding': 0, 'thumbnail_base64': 0}
            ).skip(skip).limit(limit).sort('created_at', -1)
            
            faces = await cursor.to_list(length=limit)
            
            return {
                'total': total,
                'skip': skip,
                'limit': limit,
                'faces': faces
            }
            
        except Exception as e:
            logger.error(f"Error searching faces: {str(e)}")
            return {'total': 0, 'skip': 0, 'limit': 0, 'faces': []}