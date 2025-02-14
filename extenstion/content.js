chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === "getVideoUrl") {
        // Check if we're on a YouTube watch page
        if (window.location.href.includes('youtube.com/watch')) {
            // Get video ID from URL
            const urlParams = new URLSearchParams(window.location.search);
            const videoId = urlParams.get('v');
            
            if (videoId) {
                sendResponse({ 
                    videoUrl: `https://www.youtube.com/watch?v=${videoId}`,
                    status: true 
                });
                return true;
            }
        }
        sendResponse({ videoUrl: null, status: false });
    }
    return true;
});
