#!/usr/bin/env python3
"""Direct synchronous test of PDF processing"""
import sys
sys.path.insert(0, '/app/backend')

from scraper.pdf_processor import PDFProcessor
from scraper.face_processor import FaceProcessor
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

async def test_direct():
    print("\n" + "="*60)
    print("DIRECT PDF PROCESSING TEST")
    print("="*60 + "\n")
    
    # Download a small PDF manually
    import urllib.request
    pdf_url = "https://archive.org/download/1909_20200501/1909.pdf"
    pdf_path = "/tmp/test_yearbook.pdf"
    
    print("1. Downloading PDF...")
    urllib.request.urlretrieve(pdf_url, pdf_path)
    print(f"   ✓ Downloaded to {pdf_path}")
    
    # Process PDF
    processor = PDFProcessor()
    
    print("\n2. Getting PDF info...")
    info = processor.get_pdf_info(pdf_path)
    print(f"   Pages: {info['num_pages']}")
    
    print("\n3. Extracting images (first 3 pages)...")
    images = processor.extract_images_from_pdf(pdf_path, page_limit=3)
    print(f"   ✓ Extracted {len(images)} images")
    
    if images:
        print("\n4. Detecting faces...")
        for i, img_data in enumerate(images[:2]):
            print(f"   Image {i+1}: {img_data['width']}x{img_data['height']}")
            faces = processor.detect_faces_in_image(img_data['image'])
            print(f"     Found {len(faces)} faces")
            
            if faces:
                print("     ✓✓✓ FACE DETECTED! ✓✓✓")
                # Save to database
                client = AsyncIOMotorClient('mongodb://localhost:27017')
                db = client['test_database']
                face_proc = FaceProcessor(db)
                
                for face in faces:
                    thumbnail = processor.extract_face_thumbnail(img_data['image'], face)
                    face_id = await face_proc.save_face(
                        embedding=face['embedding'],
                        yearbook_id='test_direct',
                        page_num=img_data['page_num'],
                        face_thumbnail=thumbnail,
                        metadata={'yearbook_url': 'test', 'page_url': 'test', 'year': 1909, 'school': 'Test'}
                    )
                    print(f"     Saved face: {face_id}")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(test_direct())
