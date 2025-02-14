import logging
import os
from main import download_audio, get_ffmpeg_path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_download():
    # Test video URL (short video)
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    
    # Check FFmpeg
    ffmpeg_path = get_ffmpeg_path()
    logger.info(f"FFmpeg path: {ffmpeg_path}")
    
    try:
        # Try downloading
        logger.info(f"Attempting to download: {test_url}")
        output_path = download_audio(test_url)
        
        # Verify file
        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            logger.info(f"Download successful! File size: {size} bytes")
            logger.info(f"File path: {output_path}")
            
            # Clean up
            os.remove(output_path)
            logger.info("File cleaned up")
        else:
            logger.error("File not found after download")
            
    except Exception as e:
        logger.error(f"Download failed: {str(e)}", exc_info=True)

if __name__ == "__main__":
    test_download()
