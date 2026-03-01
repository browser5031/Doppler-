import os
import io
import logging
from typing import List, Dict, Tuple, Optional
import fitz  # PyMuPDF
from PIL import Image
import numpy as np
import asyncio
import aiohttp

logger = logging.getLogger(__name__)

class PDFProcessor:
    def __init__(self, temp_dir: str = "/tmp/yearbook_processing"):
        self.temp_dir = temp_dir
        os.makedirs(temp_dir, exist_ok=True)
        
    async def download_pdf(self, url: str, save_path: str) -> bool:
        """
        Download PDF from URL
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=300)) as response:
                    if response.status == 200:
                        with open(save_path, 'wb') as f:
                            f.write(await response.read())
                        return True
            return False
        except Exception as e:
            logger.error(f"Error downloading PDF: {str(e)}")
            return False
    
    def extract_images_from_pdf(self, pdf_path: str, page_limit: int = None) -> List[Dict]:
        """
        Extract all images from PDF pages
        Returns list of {page_num, image_data, image_index}
        """
        try:
            doc = fitz.open(pdf_path)
            images = []
            
            total_pages = len(doc) if page_limit is None else min(len(doc), page_limit)
            
            for page_num in range(total_pages):
                page = doc[page_num]
                image_list = page.get_images(full=True)
                
                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        # Convert to PIL Image
                        image = Image.open(io.BytesIO(image_bytes))
                        
                        # Filter out very small images (likely logos/decorations)
                        if image.width >= 100 and image.height >= 100:
                            images.append({
                                'page_num': page_num + 1,
                                'image_index': img_index,
                                'image': image,
                                'width': image.width,
                                'height': image.height,
                                'format': base_image["ext"]
                            })
                    except Exception as e:
                        logger.warning(f"Could not extract image {img_index} from page {page_num}: {str(e)}")
                        continue
            
            doc.close()
            logger.info(f"Extracted {len(images)} images from {total_pages} pages")
            return images
            
        except Exception as e:
            logger.error(f"Error extracting images from PDF: {str(e)}")
            return []
    
    def render_page_as_image(self, pdf_path: str, page_num: int, dpi: int = 150) -> Optional[Image.Image]:
        """
        Render a PDF page as an image
        """
        try:
            doc = fitz.open(pdf_path)
            page = doc[page_num]
            
            # Render page to pixmap
            mat = fitz.Matrix(dpi/72, dpi/72)
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            doc.close()
            return img
            
        except Exception as e:
            logger.error(f"Error rendering page {page_num}: {str(e)}")
            return None
    
    def detect_faces_in_image(self, image: Image.Image, min_confidence: float = 0.25) -> List[Dict]:
        """
        Detect faces in an image using InsightFace (FAST!)
        """
        try:
            from scraper.fast_face_detector import get_detector
            
            detector = get_detector()
            faces = detector.detect_faces(image)
            
            # Filter by confidence
            results = [f for f in faces if f.get('confidence', 1.0) >= min_confidence]
            
            logger.info(f"Detected {len(results)} faces (confidence >= {min_confidence})")
            return results
            
        except Exception as e:
            logger.debug(f"No faces detected in image: {str(e)}")
            return []
    
    def extract_face_thumbnail(self, image: Image.Image, face_data: Dict, padding: int = 20) -> Optional[bytes]:
        """
        Extract and save face thumbnail
        """
        try:
            x = max(0, face_data['x'] - padding)
            y = max(0, face_data['y'] - padding)
            w = face_data['w'] + (2 * padding)
            h = face_data['h'] + (2 * padding)
            
            # Crop face
            face_img = image.crop((x, y, x + w, y + h))
            
            # Resize to standard size
            face_img = face_img.resize((200, 200), Image.LANCZOS)
            
            # Convert to bytes
            img_byte_arr = io.BytesIO()
            face_img.save(img_byte_arr, format='JPEG', quality=85)
            img_byte_arr.seek(0)
            
            return img_byte_arr.getvalue()
            
        except Exception as e:
            logger.error(f"Error extracting face thumbnail: {str(e)}")
            return None
    
    def get_pdf_info(self, pdf_path: str) -> Dict:
        """
        Get PDF metadata
        """
        try:
            doc = fitz.open(pdf_path)
            metadata = doc.metadata
            
            info = {
                'num_pages': len(doc),
                'title': metadata.get('title', ''),
                'author': metadata.get('author', ''),
                'subject': metadata.get('subject', ''),
                'creator': metadata.get('creator', ''),
                'producer': metadata.get('producer', ''),
                'creation_date': metadata.get('creationDate', ''),
                'modification_date': metadata.get('modDate', '')
            }
            
            doc.close()
            return info
            
        except Exception as e:
            logger.error(f"Error getting PDF info: {str(e)}")
            return {}