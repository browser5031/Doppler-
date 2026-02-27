# PRODUCTION SCRAPER - Optimized for 500K-1M faces

import os
import asyncio
import logging
import io
import aiohttp
from typing import Dict, Optional, List
from datetime import datetime, timezone
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing
from scraper.archive_scraper import ArchiveScraper
from scraper.pdf_processor import PDFProcessor
from scraper.face_processor import FaceProcessor

logger = logging.getLogger(__name__)

class ProductionOrchestrator:
    def __init__(self, db, max_workers=4):
        self.db = db
        self.archive_scraper = ArchiveScraper(db)
        self.pdf_processor = PDFProcessor()
        self.face_processor = FaceProcessor(db)
        self.is_running = False
        self.current_jobs = {}
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
    async def start_scraping(self, identifier: str, options: Dict = None) -> Dict:
        """Start scraping immediately in background"""
        options = options or {}
        
        try:
            # Check if already processing
            existing = await self.db.yearbooks.find_one({'identifier': identifier})
            if existing and existing.get('scraping_status') == 'processing':
                return {'success': False, 'error': 'Already processing this yearbook'}
            
            # Get yearbook details
            yearbook_data = await self.archive_scraper.get_yearbook_details(identifier)
            if not yearbook_data:
                return {'success': False, 'error': 'Yearbook not found on archive.org'}
            
            # Save/update in database
            await self.db.yearbooks.update_one(
                {'identifier': identifier},
                {'$set': {
                    **yearbook_data,
                    'scraping_status': 'queued',
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }},
                upsert=True
            )
            
            # Start processing in background
            asyncio.create_task(self.process_yearbook(identifier, yearbook_data, options))
            
            return {
                'success': True,
                'message': f'Started scraping {identifier}',
                'identifier': identifier
            }
            
        except Exception as e:
            logger.error(f"Error starting scraping: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def process_yearbook(self, identifier: str, yearbook_data: Dict, options: Dict) -> Dict:
        """Main processing pipeline - optimized for speed"""
        try:
            await self.db.yearbooks.update_one(
                {'identifier': identifier},
                {'$set': {'scraping_status': 'processing', 'started_at': datetime.now(timezone.utc).isoformat()}}
            )
            
            # Get format info
            format_info = await self.archive_scraper.get_pdf_download_url(identifier)
            if not format_info:
                raise Exception('No compatible format found')
            
            file_format = format_info['format']
            logger.info(f"Processing {identifier} - Format: {file_format}")
            
            # Process based on format
            if file_format == 'images':
                result = await self.process_image_yearbook_fast(identifier, yearbook_data, options)
            else:
                result = await self.process_pdf_yearbook_fast(identifier, yearbook_data, format_info, options)
            
            # Update status
            if result['success']:
                await self.db.yearbooks.update_one(
                    {'identifier': identifier},
                    {'$set': {
                        'scraping_status': 'completed',
                        'completed_at': datetime.now(timezone.utc).isoformat(),
                        'faces_extracted': result['faces_found'],
                        'pages_processed': result['pages_processed']
                    }}
                )
            else:
                await self.db.yearbooks.update_one(
                    {'identifier': identifier},
                    {'$set': {'scraping_status': 'failed', 'error': result.get('error')}}
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing {identifier}: {str(e)}")
            await self.db.yearbooks.update_one(
                {'identifier': identifier},
                {'$set': {'scraping_status': 'failed', 'error': str(e)}}
            )
            return {'success': False, 'error': str(e)}
    
    async def process_pdf_yearbook_fast(self, identifier: str, yearbook_data: Dict, format_info: Dict, options: Dict) -> Dict:
        """Fast PDF processing with parallel face detection"""
        max_pages = options.get('max_pages')
        pdf_url = format_info['url']
        
        try:
            pdf_path = f"/tmp/yearbook_processing/{identifier}.pdf"
            logger.info(f"Downloading PDF: {pdf_url}")
            
            if not await self.pdf_processor.download_pdf(pdf_url, pdf_path):
                return {'success': False, 'error': 'Failed to download PDF'}
            
            # Get PDF info
            pdf_info = self.pdf_processor.get_pdf_info(pdf_path)
            total_pages = pdf_info.get('num_pages', 0)
            logger.info(f"PDF has {total_pages} pages")
            
            # Extract images
            images = self.pdf_processor.extract_images_from_pdf(pdf_path, page_limit=max_pages)
            logger.info(f"Extracted {len(images)} images")
            
            # Process faces in parallel
            result = await self.process_images_parallel(identifier, yearbook_data, images)
            
            # Cleanup
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in PDF processing: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def process_image_yearbook_fast(self, identifier: str, yearbook_data: Dict, options: Dict) -> Dict:
        """Fast image-based yearbook processing"""
        max_images = options.get('max_pages')
        
        try:
            # Get image URLs
            image_urls = await self.archive_scraper.get_yearbook_images(identifier, max_images=max_images)
            if not image_urls:
                return {'success': False, 'error': 'No images found'}
            
            logger.info(f"Processing {len(image_urls)} images from {identifier}")
            
            # Download images in parallel
            images = await self.download_images_parallel(image_urls)
            logger.info(f"Downloaded {len(images)} images")
            
            # Process faces
            result = await self.process_images_parallel(identifier, yearbook_data, images)
            return result
            
        except Exception as e:
            logger.error(f"Error in image processing: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def download_images_parallel(self, image_urls: List[Dict], max_concurrent=10) -> List[Dict]:
        """Download multiple images in parallel"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def download_one(img_info, idx):
            async with semaphore:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(img_info['url'], timeout=aiohttp.ClientTimeout(total=30)) as response:
                            if response.status == 200:
                                img_bytes = await response.read()
                                img = Image.open(io.BytesIO(img_bytes))
                                return {
                                    'page_num': idx + 1,
                                    'image': img,
                                    'width': img.width,
                                    'height': img.height
                                }
                            else:
                                logger.warning(f"Failed to download {img_info['url']}: HTTP {response.status}")
                except Exception as e:
                    logger.warning(f"Failed to download {img_info['url']}: {str(e)}")
                return None
        
        tasks = [download_one(img_info, idx) for idx, img_info in enumerate(image_urls)]
        results = await asyncio.gather(*tasks)
        successful = [r for r in results if r is not None]
        logger.info(f"Successfully downloaded {len(successful)}/{len(image_urls)} images")
        return successful
    
    async def process_images_parallel(self, identifier: str, yearbook_data: Dict, images: List[Dict]) -> Dict:
        """Process images for faces in parallel - MAXIMUM SPEED"""
        try:
            faces_found = 0
            processed_pages = set()
            
            # Process in batches
            batch_size = 10
            for i in range(0, len(images), batch_size):
                batch = images[i:i+batch_size]
                
                # Detect faces in parallel
                face_results = await asyncio.gather(
                    *[self.detect_and_save_faces(identifier, yearbook_data, img_data) 
                      for img_data in batch],
                    return_exceptions=True
                )
                
                # Count results
                for result in face_results:
                    if isinstance(result, dict):
                        faces_found += result.get('faces_count', 0)
                        if result.get('page_num'):
                            processed_pages.add(result['page_num'])
                
                # Update progress every batch
                await self.db.yearbooks.update_one(
                    {'identifier': identifier},
                    {'$set': {
                        'pages_processed': len(processed_pages),
                        'faces_extracted': faces_found
                    }}
                )
                
                logger.info(f"{identifier}: Processed {len(processed_pages)} pages, found {faces_found} faces")
            
            return {
                'success': True,
                'faces_found': faces_found,
                'pages_processed': len(processed_pages),
                'total_pages': len(images)
            }
            
        except Exception as e:
            logger.error(f"Error processing images: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def detect_and_save_faces(self, identifier: str, yearbook_data: Dict, img_data: Dict) -> Dict:
        """Detect and save faces from a single image"""
        try:
            page_num = img_data['page_num']
            
            # Detect faces
            faces = self.pdf_processor.detect_faces_in_image(img_data['image'])
            
            # Save each face
            for face in faces:
                thumbnail = self.pdf_processor.extract_face_thumbnail(img_data['image'], face)
                
                metadata = {
                    'yearbook_url': yearbook_data['archive_url'],
                    'page_url': f"{yearbook_data['archive_url']}/page/{page_num}",
                    'year': yearbook_data.get('year'),
                    'school': yearbook_data.get('title', ''),
                    'location': yearbook_data.get('publisher', '')
                }
                
                await self.face_processor.save_face(
                    embedding=face['embedding'],
                    yearbook_id=identifier,
                    page_num=page_num,
                    face_thumbnail=thumbnail,
                    metadata=metadata
                )
            
            return {'faces_count': len(faces), 'page_num': page_num}
            
        except Exception as e:
            logger.debug(f"No faces in page {img_data.get('page_num')}: {str(e)}")
            return {'faces_count': 0, 'page_num': img_data.get('page_num')}
    
    async def batch_scrape(self, identifiers: List[str], max_pages: int = None) -> Dict:
        """Scrape multiple yearbooks in parallel"""
        logger.info(f"Starting batch scrape of {len(identifiers)} yearbooks")
        
        results = []
        for identifier in identifiers:
            result = await self.start_scraping(identifier, {'max_pages': max_pages})
            results.append({'identifier': identifier, 'result': result})
        
        return {
            'total': len(identifiers),
            'results': results
        }
    
    def stop(self):
        """Stop the orchestrator"""
        self.is_running = False
        self.executor.shutdown(wait=False)