"""
Azure Face API Manager for Doppelganger Finder
Replaces InsightFace with cloud-based face recognition
"""
import os
import logging
from typing import Dict, Any, List, Optional
from azure.cognitiveservices.vision.face import FaceClient
from azure.cognitiveservices.vision.face.models import TrainingStatusType, FaceAttributeType
from msrest.authentication import CognitiveServicesCredentials
from dotenv import load_dotenv
import time

load_dotenv()
logger = logging.getLogger(__name__)

class AzureFaceManager:
    def __init__(self):
        """Initialize Azure Face API client"""
        self.endpoint = os.getenv('AZURE_FACE_ENDPOINT', '').rstrip('/')  # Remove trailing slash
        self.api_key = os.getenv('AZURE_FACE_API_KEY')
        self.person_group_id = os.getenv('AZURE_FACE_PERSON_GROUP_ID', 'yearbook-faces')
        
        if not self.endpoint or not self.api_key:
            raise ValueError("Azure Face API credentials not configured in .env file")
        
        # Initialize Face API client
        self.face_client = FaceClient(
            self.endpoint,
            CognitiveServicesCredentials(self.api_key)
        )
        
        logger.info(f"✓ Azure Face API initialized: {self.endpoint}")
        
        # Initialize person group
        self._initialize_person_group()
    
    def _initialize_person_group(self) -> Dict[str, Any]:
        """Create or verify person group exists"""
        try:
            # Check if person group exists
            group = self.face_client.person_group.get(self.person_group_id)
            logger.info(f"✓ Person group '{self.person_group_id}' exists with {group.name}")
            return {'status': 'exists', 'name': group.name}
        
        except Exception as e:
            # Person group doesn't exist, create it
            try:
                self.face_client.person_group.create(
                    person_group_id=self.person_group_id,
                    name='Yearbook Faces Database',
                    recognition_model='recognition_04'
                )
                logger.info(f"✓ Created person group '{self.person_group_id}'")
                return {'status': 'created'}
            except Exception as create_error:
                logger.error(f"Failed to create person group: {create_error}")
                return {'status': 'error', 'message': str(create_error)}
    
    def detect_faces(self, image_data: bytes) -> Dict[str, Any]:
        """
        Detect faces in an image
        Returns face IDs, bounding boxes, and confidence scores
        """
        try:
            detected_faces = self.face_client.face.detect_with_stream(
                image=image_data,
                detection_model='detection_03',
                recognition_model='recognition_04',
                return_face_id=True,
                return_face_landmarks=True,
                return_face_attributes=[
                    FaceAttributeType.age,
                    FaceAttributeType.gender,
                    FaceAttributeType.smile,
                    FaceAttributeType.glasses
                ]
            )
            
            if not detected_faces:
                return {
                    'status': 'success',
                    'face_count': 0,
                    'faces': []
                }
            
            faces_data = []
            for face in detected_faces:
                face_rect = face.face_rectangle
                face_info = {
                    'face_id': face.face_id,
                    'bbox': {
                        'x': face_rect.left,
                        'y': face_rect.top,
                        'w': face_rect.width,
                        'h': face_rect.height
                    },
                    'confidence': 0.95,  # Azure doesn't return confidence, default to high
                    'landmarks': {
                        'left_eye': (face.face_landmarks.pupil_left.x, face.face_landmarks.pupil_left.y) if face.face_landmarks else None,
                        'right_eye': (face.face_landmarks.pupil_right.x, face.face_landmarks.pupil_right.y) if face.face_landmarks else None,
                        'nose': (face.face_landmarks.nose_tip.x, face.face_landmarks.nose_tip.y) if face.face_landmarks else None
                    } if face.face_landmarks else {},
                    'attributes': {
                        'age': face.face_attributes.age if face.face_attributes else None,
                        'gender': face.face_attributes.gender if face.face_attributes else None,
                        'smile': face.face_attributes.smile if face.face_attributes else None,
                        'glasses': face.face_attributes.glasses if face.face_attributes else None
                    } if face.face_attributes else {}
                }
                faces_data.append(face_info)
            
            logger.info(f"✓ Detected {len(faces_data)} faces")
            return {
                'status': 'success',
                'face_count': len(faces_data),
                'faces': faces_data
            }
        
        except Exception as e:
            logger.error(f"Face detection error: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'face_count': 0,
                'faces': []
            }
    
    def create_person(self, name: str, user_data: str = '') -> Dict[str, Any]:
        """Create a person in the person group"""
        try:
            person = self.face_client.person_group_person.create(
                person_group_id=self.person_group_id,
                name=name,
                user_data=user_data
            )
            
            logger.info(f"✓ Created person: {name} (ID: {person.person_id})")
            return {
                'status': 'success',
                'person_id': person.person_id,
                'name': name
            }
        
        except Exception as e:
            logger.error(f"Error creating person: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def add_face_to_person(self, person_id: str, image_data: bytes, target_face_rect: Optional[List[int]] = None) -> Dict[str, Any]:
        """Add a face image to a person"""
        try:
            # Add face to person
            persisted_face = self.face_client.person_group_person.add_face_from_stream(
                person_group_id=self.person_group_id,
                person_id=person_id,
                image=image_data,
                target_face=target_face_rect,
                detection_model='detection_03'
            )
            
            logger.info(f"✓ Added face to person {person_id}: {persisted_face.persisted_face_id}")
            return {
                'status': 'success',
                'persisted_face_id': persisted_face.persisted_face_id,
                'person_id': person_id
            }
        
        except Exception as e:
            logger.error(f"Error adding face to person: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def train_person_group(self) -> Dict[str, Any]:
        """Train the person group (required after adding faces)"""
        try:
            logger.info(f"Training person group '{self.person_group_id}'...")
            self.face_client.person_group.train(self.person_group_id)
            
            # Wait for training to complete
            while True:
                training_status = self.face_client.person_group.get_training_status(self.person_group_id)
                logger.info(f"Training status: {training_status.status}")
                
                if training_status.status == TrainingStatusType.succeeded:
                    logger.info("✓ Training completed successfully")
                    return {'status': 'success', 'message': 'Training completed'}
                
                elif training_status.status == TrainingStatusType.failed:
                    logger.error(f"Training failed: {training_status.message}")
                    return {'status': 'error', 'message': training_status.message}
                
                time.sleep(1)
        
        except Exception as e:
            logger.error(f"Training error: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def find_similar_faces(self, query_face_id: str, max_candidates: int = 100) -> Dict[str, Any]:
        """
        Find similar faces using face ID
        Uses identification to find matches in person group
        """
        try:
            # Use identify to find matching persons
            identify_results = self.face_client.face.identify(
                face_ids=[query_face_id],
                person_group_id=self.person_group_id,
                max_num_of_candidates_returned=max_candidates,
                confidence_threshold=0.5
            )
            
            if not identify_results or not identify_results[0].candidates:
                logger.info("No similar faces found")
                return {
                    'status': 'success',
                    'matches': [],
                    'match_count': 0
                }
            
            matches = []
            for candidate in identify_results[0].candidates:
                # Get person details
                person = self.face_client.person_group_person.get(
                    person_group_id=self.person_group_id,
                    person_id=candidate.person_id
                )
                
                match_data = {
                    'person_id': candidate.person_id,
                    'confidence': candidate.confidence,
                    'similarity_score': candidate.confidence,  # Use confidence as similarity
                    'name': person.name,
                    'user_data': person.user_data
                }
                matches.append(match_data)
            
            logger.info(f"✓ Found {len(matches)} similar faces")
            return {
                'status': 'success',
                'matches': matches,
                'match_count': len(matches)
            }
        
        except Exception as e:
            logger.error(f"Error finding similar faces: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_person_group_stats(self) -> Dict[str, Any]:
        """Get statistics about the person group"""
        try:
            group = self.face_client.person_group.get(self.person_group_id)
            persons = self.face_client.person_group_person.list(self.person_group_id)
            
            total_faces = sum(len(p.persisted_face_ids) for p in persons)
            
            return {
                'status': 'success',
                'person_group_id': self.person_group_id,
                'name': group.name,
                'total_persons': len(persons),
                'total_faces': total_faces,
                'recognition_model': group.recognition_model
            }
        
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'status': 'error', 'message': str(e)}


# Global instance
_azure_manager = None

def get_azure_face_manager() -> AzureFaceManager:
    """Get or create singleton Azure Face Manager instance"""
    global _azure_manager
    if _azure_manager is None:
        _azure_manager = AzureFaceManager()
    return _azure_manager
