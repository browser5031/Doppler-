import os
import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime, timezone
from scraper.archive_scraper import ArchiveScraper
from scraper.pdf_processor import PDFProcessor
from scraper.face_processor import FaceProcessor

logger = logging.getLogger(__name__)

class ScraperOrchestrator:
    def __init__(self, db):
        self.db = db
        self.archive_scraper = ArchiveScraper(db)
        self.pdf_processor = PDFProcessor()
        self.face_processor = FaceProcessor(db)
        self.is_running = False
        self.current_job = None
        
    async def process_yearbook(self, identifier: str, options: Dict = None) -> Dict:
        """
        Complete pipeline: Download PDF -> Extract images -> Detect faces -> Save to DB
        """
        options = options or {}
        max_pages = options.get('max_pages', None)
        
        try:
            logger.info(f"Starting to process yearbook: {identifier}")
            
            # Get yearbook details
            yearbook_data = await self.archive_scraper.get_yearbook_details(identifier)
            if not yearbook_data:
                return {'success': False, 'error': 'Could not fetch yearbook details'}
            
            # Save yearbook to DB
            await self.archive_scraper.save_yearbook_to_db(yearbook_data)
            
            # Update status
            await self.db.yearbooks.update_one(
                {'identifier': identifier},
                {'$set': {'scraping_status': 'downloading'}}
            )
            
            # Get PDF download URL
            pdf_url = await self.archive_scraper.get_pdf_download_url(identifier)
            if not pdf_url:
                await self.db.yearbooks.update_one(
                    {'identifier': identifier},
                    {'$set': {'scraping_status': 'error', 'error': 'No PDF found'}}
                )
                return {'success': False, 'error': 'No PDF file found for this yearbook'}
            
            # Download PDF
            pdf_path = f"/tmp/yearbook_processing/{identifier}.pdf"
            logger.info(f"Downloading PDF from {pdf_url}")
            
            download_success = await self.pdf_processor.download_pdf(pdf_url, pdf_path)
            if not download_success:
                await self.db.yearbooks.update_one(
                    {'identifier': identifier},
                    {'$set': {'scraping_status': 'error', 'error': 'Failed to download PDF'}}
                )
                return {'success': False, 'error': 'Failed to download PDF'}
            
            # Get PDF info
            pdf_info = self.pdf_processor.get_pdf_info(pdf_path)
            total_pages = pdf_info.get('num_pages', 0)
            
            await self.db.yearbooks.update_one(
                {'identifier': identifier},
                {'$set': {
                    'scraping_status': 'processing',
                    'total_pages': total_pages
                }}
            )
            
            # Extract images from PDF
            logger.info(f"Extracting images from PDF ({total_pages} pages)")
            images = self.pdf_processor.extract_images_from_pdf(pdf_path, page_limit=max_pages)
            
            logger.info(f"Extracted {len(images)} images, detecting faces...")
            
            faces_found = 0
            pages_processed = set()
            
            # Process each image
            for img_data in images:
                page_num = img_data['page_num']
                pages_processed.add(page_num)
                
                # Detect faces
                faces = self.pdf_processor.detect_faces_in_image(img_data['image'])
                
                # Save each face
                for face in faces:
                    # Extract face thumbnail
                    thumbnail = self.pdf_processor.extract_face_thumbnail(
                        img_data['image'],
                        face
                    )
                    
                    # Prepare metadata
                    metadata = {
                        'yearbook_url': yearbook_data['archive_url'],
                        'page_url': f"{yearbook_data['archive_url']}/page/{page_num}",
                        'year': yearbook_data.get('year'),
                        'school': yearbook_data.get('title', ''),
                        'location': yearbook_data.get('publisher', '')
                    }
                    
                    # Save to database
                    face_id = await self.face_processor.save_face(
                        embedding=face['embedding'],
                        yearbook_id=identifier,
                        page_num=page_num,
                        face_thumbnail=thumbnail,
                        metadata=metadata
                    )
                    
                    if face_id:
                        faces_found += 1
                
                # Update progress
                await self.db.yearbooks.update_one(
                    {'identifier': identifier},
                    {'$set': {
                        'pages_processed': len(pages_processed),
                        'faces_extracted': faces_found
                    }}
                )
            
            # Clean up
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            
            # Update final status
            await self.db.yearbooks.update_one(
                {'identifier': identifier},
                {'$set': {
                    'scraping_status': 'completed',
                    'completed_at': datetime.now(timezone.utc).isoformat(),
                    'faces_extracted': faces_found,
                    'pages_processed': len(pages_processed)
                }}
            )
            
            logger.info(f"Completed processing {identifier}: {faces_found} faces from {len(pages_processed)} pages")
            
            return {
                'success': True,
                'faces_found': faces_found,
                'pages_processed': len(pages_processed),
                'total_pages': total_pages
            }
            
        except Exception as e:
            logger.error(f"Error processing yearbook {identifier}: {str(e)}")
            
            await self.db.yearbooks.update_one(
                {'identifier': identifier},
                {'$set': {
                    'scraping_status': 'error',
                    'error': str(e)
                }}
            )
            
            return {'success': False, 'error': str(e)}
    
    async def process_job_queue(self):
        """
        Process scraping jobs from queue
        """
        self.is_running = True
        
        while self.is_running:
            try:
                # Get next queued job
                job = await self.db.scraping_jobs.find_one_and_update(
                    {'status': 'queued'},
                    {'$set': {
                        'status': 'processing',
                        'started_at': datetime.now(timezone.utc).isoformat()
                    }},
                    sort=[('priority', -1), ('created_at', 1)]
                )
                
                if job:
                    self.current_job = job
                    identifier = job['identifier']
                    options = job.get('options', {})
                    
                    logger.info(f"Processing job for yearbook: {identifier}")
                    result = await self.process_yearbook(identifier, options)
                    
                    # Update job status
                    await self.db.scraping_jobs.update_one(
                        {'_id': job['_id']},
                        {'$set': {
                            'status': 'completed' if result['success'] else 'failed',
                            'completed_at': datetime.now(timezone.utc).isoformat(),
                            'faces_found': result.get('faces_found', 0),
                            'pages_processed': result.get('pages_processed', 0),
                            'error': result.get('error')
                        }}
                    )
                    
                    self.current_job = None
                else:
                    # No jobs in queue, wait
                    await asyncio.sleep(5)
                    
            except Exception as e:
                logger.error(f"Error in job queue processor: {str(e)}")
                await asyncio.sleep(5)
    
    def stop(self):
        """Stop the orchestrator"""
        self.is_running = False