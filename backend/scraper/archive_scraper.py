import os
import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone
import internetarchive as ia
import aiohttp
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING

logger = logging.getLogger(__name__)

class ArchiveScraper:
    def __init__(self, db):
        self.db = db
        self.session = None
        
    async def search_yearbooks(self, 
                              query: str = "yearbook",
                              year_start: int = 2000,
                              year_end: int = 2015,
                              limit: int = 100) -> List[Dict]:
        """
        Search archive.org for yearbooks with comprehensive filtering
        """
        try:
            search_query = f'{query} AND mediatype:texts AND year:[{year_start} TO {year_end}]'
            
            # Search archive.org
            search = ia.search_items(search_query, 
                                   fields=['identifier', 'title', 'year', 'subject', 
                                          'creator', 'publisher', 'description', 'date',
                                          'collection', 'downloads', 'item_size'])
            
            results = []
            for i, item in enumerate(search):
                if i >= limit:
                    break
                    
                results.append({
                    'identifier': item.get('identifier'),
                    'title': item.get('title', ''),
                    'year': item.get('year', ''),
                    'date': item.get('date', ''),
                    'creator': item.get('creator', ''),
                    'publisher': item.get('publisher', ''),
                    'description': item.get('description', ''),
                    'subjects': item.get('subject', []),
                    'collection': item.get('collection', []),
                    'downloads': item.get('downloads', 0),
                    'size': item.get('item_size', 0)
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching yearbooks: {str(e)}")
            return []
    
    async def get_yearbook_details(self, identifier: str) -> Optional[Dict]:
        """
        Get detailed metadata for a specific yearbook
        """
        try:
            item = ia.get_item(identifier)
            metadata = item.metadata
            
            # Get PDF file info
            pdf_files = [f for f in item.files if f['name'].endswith('.pdf')]
            
            return {
                'identifier': identifier,
                'title': metadata.get('title', ''),
                'year': metadata.get('year', ''),
                'date': metadata.get('date', ''),
                'creator': metadata.get('creator', ''),
                'publisher': metadata.get('publisher', ''),
                'description': metadata.get('description', ''),
                'subjects': metadata.get('subject', []) if isinstance(metadata.get('subject'), list) else [metadata.get('subject', '')],
                'language': metadata.get('language', ''),
                'scanner': metadata.get('scanner', ''),
                'sponsor': metadata.get('sponsor', ''),
                'contributor': metadata.get('contributor', ''),
                'collection': metadata.get('collection', []),
                'pdf_files': pdf_files,
                'num_pages': metadata.get('imagecount', 0),
                'archive_url': f'https://archive.org/details/{identifier}',
                'download_url': f'https://archive.org/download/{identifier}',
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Error getting yearbook details for {identifier}: {str(e)}")
            return None
    
    async def save_yearbook_to_db(self, yearbook_data: Dict) -> str:
        """
        Save yearbook metadata to database
        """
        try:
            # Check if already exists
            existing = await self.db.yearbooks.find_one(
                {'identifier': yearbook_data['identifier']},
                {'_id': 0}
            )
            
            if existing:
                return existing['identifier']
            
            # Add timestamps
            yearbook_data['created_at'] = datetime.now(timezone.utc).isoformat()
            yearbook_data['scraping_status'] = 'pending'
            yearbook_data['faces_extracted'] = 0
            
            await self.db.yearbooks.insert_one(yearbook_data)
            logger.info(f"Saved yearbook: {yearbook_data['identifier']}")
            
            return yearbook_data['identifier']
            
        except Exception as e:
            logger.error(f"Error saving yearbook to DB: {str(e)}")
            return None
    
    async def get_pdf_download_url(self, identifier: str) -> Optional[str]:
        """
        Get direct download URL for yearbook PDF
        """
        try:
            item = ia.get_item(identifier)
            pdf_files = [f for f in item.files if f['name'].endswith('.pdf')]
            
            if pdf_files:
                pdf_file = pdf_files[0]['name']
                return f"https://archive.org/download/{identifier}/{pdf_file}"
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting PDF URL: {str(e)}")
            return None
    
    async def create_scraping_job(self, 
                                 identifier: str,
                                 priority: int = 5,
                                 options: Dict = None) -> str:
        """
        Create a scraping job for a yearbook
        """
        try:
            job = {
                'identifier': identifier,
                'status': 'queued',
                'priority': priority,
                'options': options or {},
                'created_at': datetime.now(timezone.utc).isoformat(),
                'started_at': None,
                'completed_at': None,
                'faces_found': 0,
                'pages_processed': 0,
                'total_pages': 0,
                'error': None
            }
            
            result = await self.db.scraping_jobs.insert_one(job)
            job_id = str(result.inserted_id)
            
            logger.info(f"Created scraping job {job_id} for {identifier}")
            return job_id
            
        except Exception as e:
            logger.error(f"Error creating scraping job: {str(e)}")
            return None