import requests
import sys
import json
import io
from datetime import datetime
from PIL import Image
import numpy as np

class DoppelgangerAPITester:
    def __init__(self, base_url="https://twin-detector-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, passed, details=""):
        """Log test result"""
        self.tests_run += 1
        if passed:
            self.tests_passed += 1
        
        result = {
            "test": name,
            "status": "PASS" if passed else "FAIL",
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status_emoji = "✅" if passed else "❌"
        print(f"{status_emoji} {name}")
        if details:
            print(f"   {details}")

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.api_base}{endpoint}"
        headers = {}
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, data=data, headers=headers, timeout=60)
                elif data:
                    headers['Content-Type'] = 'application/json'
                    response = requests.post(url, json=data, headers=headers, timeout=30)
                else:
                    response = requests.post(url, headers=headers, timeout=30)

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}"
            
            if success and response.content:
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and len(str(response_data)) < 200:
                        details += f" | Response: {response_data}"
                    else:
                        details += f" | Response length: {len(str(response_data))} chars"
                except:
                    details += f" | Response length: {len(response.text)} chars"
            
            self.log_test(name, success, details)
            return success, response.json() if success and response.content else {}

        except Exception as e:
            self.log_test(name, False, f"Error: {str(e)}")
            return False, {}

    def create_test_image(self, format='JPEG'):
        """Create a simple test image with a face-like pattern"""
        # Create a 400x400 image with a simple face pattern
        img = Image.new('RGB', (400, 400), color='white')
        pixels = img.load()
        
        # Draw a simple face pattern
        for x in range(400):
            for y in range(400):
                # Face circle
                center_x, center_y = 200, 200
                distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
                
                if distance < 150:  # Face
                    pixels[x, y] = (220, 200, 180)  # Skin color
                    
                    # Eyes
                    if ((x - 170) ** 2 + (y - 170) ** 2) ** 0.5 < 20:  # Left eye
                        pixels[x, y] = (0, 0, 0)
                    if ((x - 230) ** 2 + (y - 170) ** 2) ** 0.5 < 20:  # Right eye
                        pixels[x, y] = (0, 0, 0)
                    
                    # Mouth
                    if ((x - 200) ** 2 + (y - 250) ** 2) ** 0.5 < 25:  # Mouth
                        pixels[x, y] = (100, 50, 50)
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format=format)
        img_byte_arr.seek(0)
        return img_byte_arr

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test("API Root", "GET", "/", 200)

    def test_stats_endpoint(self):
        """Test stats endpoint"""
        success, response = self.run_test("Get Stats", "GET", "/stats", 200)
        
        if success and response:
            # Validate stats response structure
            required_fields = ['total_faces', 'by_year']
            if all(field in response for field in required_fields):
                self.log_test("Stats Response Structure", True, f"Fields: {list(response.keys())}")
            else:
                self.log_test("Stats Response Structure", False, f"Missing fields. Got: {list(response.keys())}")
        
        return success

    def test_seed_database(self):
        """Test database seeding"""
        success, response = self.run_test("Seed Database", "POST", "/seed-database", 200)
        
        if success and response:
            if 'message' in response and 'count' in response:
                self.log_test("Seed Response Structure", True, f"Message: {response.get('message', '')}")
            else:
                self.log_test("Seed Response Structure", False, f"Unexpected response: {response}")
        
        return success

    def test_upload_compare_valid_image(self):
        """Test face comparison with valid image"""
        test_image = self.create_test_image('JPEG')
        files = {'file': ('test_face.jpg', test_image, 'image/jpeg')}
        
        success, response = self.run_test(
            "Upload Compare - Valid Image", 
            "POST", 
            "/upload-compare?top_n=10", 
            200, 
            files=files
        )
        
        if success and response:
            # Validate response structure
            required_fields = ['total_faces_compared', 'results', 'processing_time']
            if all(field in response for field in required_fields):
                self.log_test(
                    "Upload Response Structure", 
                    True, 
                    f"Compared: {response.get('total_faces_compared', 0)}, Results: {len(response.get('results', []))}"
                )
                
                # Check result structure if there are results
                if response.get('results'):
                    first_result = response['results'][0]
                    result_fields = ['face_id', 'similarity_score', 'yearbook_url', 'page_url']
                    if all(field in first_result for field in result_fields):
                        self.log_test("Result Item Structure", True, f"Similarity: {first_result.get('similarity_score', 0):.1f}%")
                    else:
                        self.log_test("Result Item Structure", False, f"Missing fields in result: {list(first_result.keys())}")
                else:
                    self.log_test("Results Available", False, "No results returned")
            else:
                self.log_test("Upload Response Structure", False, f"Missing fields. Got: {list(response.keys())}")
        
        return success

    def test_upload_compare_invalid_file(self):
        """Test face comparison with invalid file"""
        # Create a text file instead of image
        text_content = b"This is not an image file"
        files = {'file': ('test.txt', io.BytesIO(text_content), 'text/plain')}
        
        success, response = self.run_test(
            "Upload Compare - Invalid File", 
            "POST", 
            "/upload-compare", 
            400, 
            files=files
        )
        
        return success

    def test_upload_compare_no_face(self):
        """Test face comparison with image containing no face"""
        # Create a solid color image with no face
        img = Image.new('RGB', (200, 200), color='blue')
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_byte_arr.seek(0)
        
        files = {'file': ('no_face.jpg', img_byte_arr, 'image/jpeg')}
        
        success, response = self.run_test(
            "Upload Compare - No Face", 
            "POST", 
            "/upload-compare", 
            400, 
            files=files
        )
        
        return success

    def test_upload_compare_different_formats(self):
        """Test different image formats"""
        formats = ['PNG', 'JPEG']
        
        for format_name in formats:
            test_image = self.create_test_image(format_name)
            mime_type = f'image/{format_name.lower()}'
            files = {'file': (f'test.{format_name.lower()}', test_image, mime_type)}
            
            success, _ = self.run_test(
                f"Upload Compare - {format_name}", 
                "POST", 
                "/upload-compare?top_n=5", 
                200, 
                files=files
            )

    def run_all_tests(self):
        """Run all API tests"""
        print("🧪 Starting Doppelganger API Tests...")
        print(f"🌐 Testing against: {self.base_url}")
        print("=" * 60)

        # Test basic endpoints first
        self.test_root_endpoint()
        self.test_stats_endpoint()
        self.test_seed_database()
        
        # Test upload functionality
        self.test_upload_compare_valid_image()
        self.test_upload_compare_different_formats()
        
        # Test error cases
        self.test_upload_compare_invalid_file()
        self.test_upload_compare_no_face()

        # Print summary
        print("=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print("⚠️  Some tests failed!")
            return 1

def main():
    tester = DoppelgangerAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())