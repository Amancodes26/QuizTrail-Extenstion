import logging
from pytube import YouTube
from pytube.exceptions import *

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_youtube_download(url):
    try:
        logger.info(f"Testing URL: {url}")
        
        # Initialize YouTube
        logger.info("Initializing YouTube object...")
        yt = YouTube(url)
        
        # Check availability
        logger.info("Checking video availability...")
        yt.check_availability()
        
        # Print video details
        logger.info(f"Title: {yt.title}")
        logger.info(f"Length: {yt.length} seconds")
        logger.info(f"Views: {yt.views}")
        
        # Get audio streams
        logger.info("\nFetching audio streams...")
        audio_streams = yt.streams.filter(only_audio=True).order_by('abr').desc()
        
        if not audio_streams:
            logger.error("No audio streams found!")
            return
            
        # Print available audio streams
        logger.info("\nAvailable audio streams:")
        for i, stream in enumerate(audio_streams):
            logger.info(f"{i+1}. itag: {stream.itag}, abr: {stream.abr}, mime_type: {stream.mime_type}")
        
        # Try downloading the best audio stream
        best_audio = audio_streams[0]
        logger.info(f"\nAttempting to download best audio stream (itag: {best_audio.itag})")
        output_file = best_audio.download(filename="test_audio.mp4")
        logger.info(f"Download successful! File saved as: {output_file}")
        
    except VideoPrivate:
        logger.error("This video is private!")
    except VideoUnavailable:
        logger.error("This video is unavailable!")
    except AgeRestrictedError:
        logger.error("This video is age restricted!")
    except LiveStreamError:
        logger.error("This video is a live stream!")
    except RegexMatchError:
        logger.error("Invalid YouTube URL!")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)

if __name__ == "__main__":
    # Test with a few different videos
    test_videos = [
        "https://www.youtube.com/watch?v=IsM4bnJ-8Gw",  # Original test video
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Known working video
        "https://youtu.be/dQw4w9WgXcQ"                  # Short URL format
    ]
    
    for video_url in test_videos:
        logger.info("\n" + "="*50)
        test_youtube_download(video_url)
        logger.info("="*50 + "\n")
