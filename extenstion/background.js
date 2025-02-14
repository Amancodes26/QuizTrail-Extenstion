let currentVideoUrl = null;

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (tab.url && tab.url.includes("youtube.com/watch")) {
        const urlParams = new URLSearchParams(new URL(tab.url).search);
        const videoId = urlParams.get('v');
        if (videoId) {
            currentVideoUrl = `https://www.youtube.com/watch?v=${videoId}`;
        }
    }
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "getVideoUrl") {
        // Query current active tab to get latest URL
        chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
            if (tabs[0] && tabs[0].url && tabs[0].url.includes("youtube.com/watch")) {
                const urlParams = new URLSearchParams(new URL(tabs[0].url).search);
                const videoId = urlParams.get('v');
                if (videoId) {
                    currentVideoUrl = `https://www.youtube.com/watch?v=${videoId}`;
                }
            }
            sendResponse({ videoUrl: currentVideoUrl });
        });
        return true;
    }
});
