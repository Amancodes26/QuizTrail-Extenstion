import requests
import json
import time
import logging
import os
import sys
import shutil
from dotenv import load_dotenv
import imageio_ffmpeg as ffmpeg

# Set up logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Use stdout for proper encoding
        logging.FileHandler('test.log', encoding='utf-8')  # Specify UTF-8 encoding
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_VIDEOS = [
    {
        "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # "Me at the zoo" (shortest YouTube video)
        "title": "Me at the zoo",
        "duration": 18
    }
]

def verify_ffmpeg():
    """Verify FFmpeg installation using imageio_ffmpeg"""
    try:
        ffmpeg_path = ffmpeg.get_ffmpeg_exe()
        logger.info(f"Found FFmpeg at: {ffmpeg_path}")
        
        # Test FFmpeg execution
        result = os.popen(f'"{ffmpeg_path}" -version').read()
        logger.info("FFmpeg verification:")
        logger.info(result.split('\n')[0])
        return True
        
    except Exception as e:
        logger.error(f"FFmpeg verification failed: {str(e)}")
        logger.error("\nPlease install FFmpeg:")
        logger.error("1. Run: pip install imageio-ffmpeg")
        logger.error("2. Or download from https://ffmpeg.org/download.html")
        return False

def test_server_health():
    """Test if the server is running and responding"""
    try:
        logger.info("Testing server health...")
        response = requests.get(f"{BASE_URL}/")
        assert response.status_code == 200
        assert response.json()["message"] == "API is working!"
        logger.info("Server health check passed!")  # Removed special character
        return True
    except Exception as e:
        logger.error(f"Server health check failed: {str(e)}")
        return False

def test_video_download(video_url):
    """Test video download functionality"""
    logger.info(f"\nTesting video download: {video_url}")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/transcribe",
            json={"video_url": video_url},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            timeout=300  # 5 minutes timeout
        )
        
        # Log response details
        logger.info(f"Response time: {time.time() - start_time:.2f} seconds")
        logger.info(f"Status Code: {response.status_code}")
        
        try:
            data = response.json()
            logger.info("Response content:")
            logger.info(json.dumps(data, indent=2))
            
            if response.status_code == 200:
                assert data["status"] == "success"
                assert "transcript" in data
                assert "quiz" in data
                assert len(data["quiz"]) > 0
                logger.info("Video processing test passed!")  # Removed special character
                return True
            else:
                logger.error(f"Test failed: {data.get('detail', 'Unknown error')}")
                return False
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("Request timed out after 5 minutes")
        return False
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        return False

def test_error_handling():
    """Test various error scenarios"""
    test_cases = [
        {
            "name": "Invalid URL format",
            "data": {"video_url": "not_a_url"},
            "expected_status": 400
        },
        {
            "name": "Empty URL",
            "data": {"video_url": ""},
            "expected_status": 400
        },
        {
            "name": "Non-YouTube URL",
            "data": {"video_url": "https://example.com"},
            "expected_status": 400
        }
    ]
    
    for test in test_cases:
        logger.info(f"\nTesting error case: {test['name']}")
        try:
            response = requests.post(
                f"{BASE_URL}/transcribe",
                json=test["data"],
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == test["expected_status"]
            logger.info(f"Error handling test passed! ({test['name']})")  # Removed special character
            
        except Exception as e:
            logger.error(f"Error handling test failed ({test['name']}): {str(e)}")

def run_all_tests():
    """Run all test cases"""
    logger.info("Starting test suite...")
    
    # Verify FFmpeg first
    if not verify_ffmpeg():
        logger.error("FFmpeg check failed, stopping tests")
        return
    
    # Test 1: Server Health
    if not test_server_health():
        logger.error("Server health check failed, stopping tests")
        return
    
    # Test 2: Error Handling
    test_error_handling()
    
    # Test 3: Video Processing
    success_count = 0
    for video in TEST_VIDEOS:
        if test_video_download(video["url"]):
            success_count += 1
        time.sleep(2)  # Add delay between tests
    
    # Summary
    logger.info("\nTest Summary:")
    logger.info(f"Total video tests: {len(TEST_VIDEOS)}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {len(TEST_VIDEOS) - success_count}")

if __name__ == "__main__":
    run_all_tests()
