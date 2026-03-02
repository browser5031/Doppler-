"""
Complete FREE face recognition solution:
- Development: InsightFace (local ML)
- Production: Luxand (detect) + FaceNet-PyTorch (embed)
Cost: $0/month (500 free Luxand calls + lightweight FaceNet)
"""
import os
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from PIL import Image
import io

logger = logging.getLogger(__name__)

class HybridFaceRecognition:
    """
    Hybrid face recognition that works in both development and production
    - Development: Uses InsightFace (if available)
    - Production: Uses Luxand (FREE) + FaceNet-PyTorch (lightweight)
    """
    
    def __init__(self):
        self.mode = "unknown"
        self.insightface_detector = None
        self.facenet_model = None
        self.luxand_api_key = os.getenv('LUXAND_API_KEY', '')
        
        # Try to initialize InsightFace (development)
        try:
            from scraper.fast_face_detector import get_detector
            self.insightface_detector = get_detector()
            self.mode = "development"
            logger.info("✓ Using InsightFace (Development mode)")
        except Exception as e:
            logger.info(f"InsightFace not available: {e}")
        
        # If InsightFace not available, try FaceNet (production)
        if not self.insightface_detector:
            try:
                from facenet_pytorch import MTCNN, InceptionResnetV1
                self.mtcnn = MTCNN(keep_all=False, device='cpu')
                self.facenet_model = InceptionResnetV1(pretrained='vggface2').eval()
                self.mode = "production"
                logger.info("✓ Using FaceNet-PyTorch (Production mode)")
            except Exception as e:
                logger.warning(f"FaceNet not available: {e}")
                self.mode = "error"
    
    def detect_and_extract_embedding(self, image_bytes: bytes) -> Optional[Dict[str, Any]]:
        """
        Detect face and extract embedding
        Returns: {embedding: List[float], bbox: Dict[str, int], confidence: float}
        """
        try:
            # Reset BytesIO position if needed
            if isinstance(image_bytes, io.BytesIO):
                image_bytes.seek(0)
                img = Image.open(image_bytes)
            else:
                img = Image.open(io.BytesIO(image_bytes))
            
            # Try InsightFace first (development)
            if self.insightface_detector:
                return self._detect_with_insightface(img)
            
            # Fall back to FaceNet (production)
            elif self.facenet_model:
                return self._detect_with_facenet(img, image_bytes)
            
            else:
                logger.error("No face detection method available")
                return None
                
        except Exception as e:
            logger.error(f"Error in face detection: {e}")
            return None
    
    def _detect_with_insightface(self, img: Image.Image) -> Optional[Dict[str, Any]]:
        """Use InsightFace for detection and embedding"""
        try:
            faces = self.insightface_detector.detect_faces(img)
            
            if not faces or len(faces) == 0:
                return None
            
            # Get first/largest face
            face = faces[0]
            
            # Extract bbox from InsightFace result
            bbox = face.get('bbox', {})
            if not bbox or 'x' not in bbox:
                # Try facial_area format
                facial_area = face.get('facial_area', {})
                if facial_area:
                    bbox = {
                        'x': int(facial_area.get('x', 0)),
                        'y': int(facial_area.get('y', 0)),
                        'w': int(facial_area.get('w', 0)),
                        'h': int(facial_area.get('h', 0))
                    }
            
            return {
                'embedding': face.get('embedding', []),
                'bbox': bbox,
                'confidence': face.get('confidence', 0.95)
            }
            
        except Exception as e:
            logger.error(f"InsightFace detection error: {e}")
            return None
    
    def _detect_with_facenet(self, img: Image.Image, image_bytes: bytes) -> Optional[Dict[str, Any]]:
        """Use Luxand (detect) + FaceNet (embed) for production"""
        try:
            # Step 1: Detect face using Luxand (FREE 500/month)
            bbox = self._detect_with_luxand(image_bytes)
            
            if not bbox:
                # If Luxand fails or quota exceeded, try MTCNN
                bbox_mtcnn, _ = self.mtcnn.detect(img)
                if bbox_mtcnn is None:
                    return None
                bbox = {
                    'x': int(bbox_mtcnn[0][0]),
                    'y': int(bbox_mtcnn[0][1]),
                    'w': int(bbox_mtcnn[0][2] - bbox_mtcnn[0][0]),
                    'h': int(bbox_mtcnn[0][3] - bbox_mtcnn[0][1])
                }
            
            # Step 2: Crop face
            x, y, w, h = bbox['x'], bbox['y'], bbox['w'], bbox['h']
            face_crop = img.crop((x, y, x + w, y + h))
            
            # Step 3: Extract embedding using FaceNet
            face_crop = face_crop.resize((160, 160))
            face_tensor = self._pil_to_tensor(face_crop)
            
            with np.no_grad():
                embedding = self.facenet_model(face_tensor.unsqueeze(0))
                embedding = embedding.detach().cpu().numpy()[0]
            
            return {
                'embedding': embedding.tolist(),
                'bbox': bbox,
                'confidence': 0.9
            }
            
        except Exception as e:
            logger.error(f"FaceNet detection error: {e}")
            return None
    
    def _detect_with_luxand(self, image_bytes: bytes) -> Optional[Dict[str, int]]:
        """Detect face using Luxand Cloud API (FREE 500/month)"""
        if not self.luxand_api_key:
            return None
        
        try:
            import requests
            
            headers = {"token": self.luxand_api_key}
            files = {"photo": ("image.jpg", image_bytes, "image/jpeg")}
            
            response = requests.post(
                "https://api.luxand.cloud/photo/detect",
                headers=headers,
                files=files,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                faces = data.get('faces', [])
                
                if faces:
                    face = faces[0]  # Get first face
                    return {
                        'x': int(face.get('x', 0)),
                        'y': int(face.get('y', 0)),
                        'w': int(face.get('width', 0)),
                        'h': int(face.get('height', 0))
                    }
            else:
                logger.warning(f"Luxand API error: {response.status_code}")
            
            return None
            
        except Exception as e:
            logger.warning(f"Luxand detection failed: {e}")
            return None
    
    def _pil_to_tensor(self, img: Image.Image):
        """Convert PIL image to tensor for FaceNet"""
        import torch
        import torchvision.transforms as transforms
        
        transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
        ])
        
        return transform(img)
    
    def get_mode(self) -> str:
        """Get current operation mode"""
        return self.mode


# Singleton instance
_hybrid_recognizer = None

def get_hybrid_recognizer() -> HybridFaceRecognition:
    """Get or create hybrid recognizer instance"""
    global _hybrid_recognizer
    if _hybrid_recognizer is None:
        _hybrid_recognizer = HybridFaceRecognition()
    return _hybrid_recognizer
