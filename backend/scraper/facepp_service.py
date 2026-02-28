"""
Face++ API Service for Face Detection and Embedding Generation
Fallback service when InsightFace ML is unavailable (production deployment)
"""

import requests
import logging
import os
import numpy as np
from typing import Optional, List
from PIL import Image
from io import BytesIO

logger = logging.getLogger(__name__)

class FacePlusPlusService:
    """Service for Face++ API interactions"""
    
    def __init__(self):
        """Initialize Face++ service with API credentials"""
        self.api_key = os.environ.get('FACE_PLUS_API_KEY')
        self.api_secret = os.environ.get('FACE_PLUS_API_SECRET')
        self.api_endpoint = os.environ.get(
            'FACE_PLUS_API_ENDPOINT',
            'https://api-us.faceplusplus.com/facepp/v3'
        )
        self.timeout = 30
        
        if not self.api_key or not self.api_secret:
            logger.warning("Face++ credentials not configured")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("✅ Face++ service initialized")
    
    def detect_face_and_get_embedding(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """
        Detect face and extract embedding using Face++ API
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            512-dimensional face embedding (compatible with InsightFace format)
            or None if no face detected
        """
        
        if not self.enabled:
            logger.error("Face++ service not enabled - missing credentials")
            return None
        
        try:
            # Validate image
            image = Image.open(BytesIO(image_bytes))
            if image.size[0] < 10 or image.size[1] < 10:
                logger.warning("Image dimensions too small")
                return None
            
            # Call Face++ detect API
            url = f"{self.api_endpoint}/detect"
            params = {
                "api_key": self.api_key,
                "api_secret": self.api_secret,
                "return_landmark": 2,  # 106 landmarks
                "return_attributes": "gender,age,emotion"
            }
            
            files = {"image_file": image_bytes}
            
            response = requests.post(
                url,
                data=params,
                files=files,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                error_data = response.json()
                logger.error(f"Face++ API error: {error_data.get('error_message')}")
                return None
            
            result = response.json()
            faces = result.get('faces', [])
            
            if not faces:
                logger.info("No faces detected by Face++ API")
                return None
            
            # Get first face
            face = faces[0]
            logger.info(f"Face++ detected face with {face.get('confidence', 0):.2f} confidence")
            
            # Generate embedding from landmarks
            # Face++ returns 106 landmarks - we'll create a 512-dim embedding
            embedding = self._generate_embedding_from_landmarks(face)
            
            return embedding
            
        except requests.exceptions.Timeout:
            logger.error("Face++ API request timeout")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Face++ API request failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Face++ processing error: {str(e)}")
            return None
    
    def _generate_embedding_from_landmarks(self, face_data: dict) -> np.ndarray:
        """
        Generate 512-dimensional embedding from Face++ landmarks
        
        This creates a pseudo-embedding compatible with InsightFace format
        by encoding geometric features from facial landmarks.
        
        Args:
            face_data: Face data from Face++ API
            
        Returns:
            512-dimensional normalized embedding
        """
        
        # Get landmark data
        landmarks = face_data.get('landmark', {})
        
        # Extract key facial features
        features = []
        
        # Process each landmark point (x, y coordinates)
        landmark_keys = [
            'left_eye_left_corner', 'left_eye_right_corner',
            'right_eye_left_corner', 'right_eye_right_corner',
            'nose_tip', 'mouth_left_corner', 'mouth_right_corner',
            'left_eyebrow_left_corner', 'left_eyebrow_right_corner',
            'right_eyebrow_left_corner', 'right_eyebrow_right_corner',
            'contour_left1', 'contour_left2', 'contour_left3',
            'contour_right1', 'contour_right2', 'contour_right3',
            'contour_chin'
        ]
        
        for key in landmark_keys:
            if key in landmarks:
                features.append(float(landmarks[key]['x']))
                features.append(float(landmarks[key]['y']))
        
        # Add face rectangle features
        rect = face_data.get('face_rectangle', {})
        features.extend([
            float(rect.get('top', 0)),
            float(rect.get('left', 0)),
            float(rect.get('width', 100)),
            float(rect.get('height', 100))
        ])
        
        # Add attributes as features
        attributes = face_data.get('attributes', {})
        
        # Gender (encoded as 0 or 1)
        gender = attributes.get('gender', {})
        features.append(1.0 if gender.get('value') == 'Male' else 0.0)
        
        # Age (normalized to 0-1 range)
        age = attributes.get('age', {}).get('value', 30)
        features.append(float(age) / 100.0)
        
        # Emotion scores
        emotion = attributes.get('emotion', {})
        for emotion_type in ['happiness', 'neutral', 'sadness', 'anger', 'surprise', 'disgust', 'fear']:
            features.append(float(emotion.get(emotion_type, 0)) / 100.0)
        
        # Pad to 512 dimensions with derived features
        while len(features) < 512:
            # Use combinations of existing features
            if len(features) > 10:
                # Create derived features using combinations
                idx1 = len(features) % (len(features) - 1)
                idx2 = (len(features) + 1) % (len(features) - 1)
                derived = (features[idx1] + features[idx2]) / 2.0
                features.append(derived)
            else:
                features.append(0.0)
        
        # Convert to numpy array and normalize
        embedding = np.array(features[:512], dtype=np.float32)
        
        # L2 normalization (same as InsightFace)
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        logger.debug(f"Generated 512-dim embedding from Face++ landmarks")
        return embedding


# Global instance
_facepp_service: Optional[FacePlusPlusService] = None

def get_facepp_service() -> FacePlusPlusService:
    """Get or create Face++ service singleton"""
    global _facepp_service
    if _facepp_service is None:
        _facepp_service = FacePlusPlusService()
    return _facepp_service
