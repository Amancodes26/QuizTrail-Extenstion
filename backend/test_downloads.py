import logging
import os
import time
from pytube import YouTube
import yt_dlp

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TEST_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"

def test_pytube():
    """Test PyTube download"""
    logger.info("\nTesting PyTube download...")
    try:
        yt = YouTube(TEST_URL)
        logger.info(f"Video title: {yt.title}")
        
        streams = yt.streams.filter(only_audio=True).order_by('abr').desc()
        if not streams:
            logger.error("No audio streams found")
            return False
            
        audio_stream = streams[0]
        logger.info(f"Selected stream: {audio_stream.abr}kbps")
        
        output_file = "pytube_test.mp4"
        audio_stream.download(filename=output_file)
        
        if os.path.exists(output_file):
            size = os.path.getsize(output_file)
            logger.info(f"Downloaded successfully: {size} bytes")
            os.remove(output_file)
            return True
    except Exception as e:
        logger.error(f"PyTube error: {str(e)}", exc_info=True)
        return False

def test_ytdlp():
    """Test yt-dlp download"""
    logger.info("\nTesting yt-dlp download...")
    try:
        output_path = f"ytdlp_test_{int(time.time())}.mp3"
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': output_path,
            'quiet': False,
            'verbose': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(TEST_URL, download=True)
            logger.info(f"Title: {info.get('title', 'Unknown')}")
            
            if os.path.exists(output_path):
                size = os.path.getsize(output_path)
                logger.info(f"Downloaded successfully: {size} bytes")
                os.remove(output_path)
                return True
            else:
                logger.error("File not created")
                return False
                
    except Exception as e:
        logger.error(f"yt-dlp error: {str(e)}", exc_info=True)
        return False

def main():
    logger.info("Starting download tests...")
    
    pytube_result = test_pytube()
    ytdlp_result = test_ytdlp()
    
    logger.info("\nTest Results:")
    logger.info(f"PyTube: {'Success' if pytube_result else 'Failed'}")
    logger.info(f"yt-dlp: {'Success' if ytdlp_result else 'Failed'}")

if __name__ == "__main__":
    main()
