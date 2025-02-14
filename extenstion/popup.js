document.addEventListener('DOMContentLoaded', function() {
    const transcribeBtn = document.getElementById('transcribeBtn');
    const statusElement = document.getElementById('status');
    const resultsElement = document.getElementById('results');
    const transcriptElement = document.getElementById('transcript');
    const quizElement = document.getElementById('quiz');

    function updateStatus(message) {
        statusElement.textContent = message;
    }

    function displayResults(transcript, quiz) {
        transcriptElement.textContent = transcript;
        
        quizElement.innerHTML = '';
        quiz.forEach((item, index) => {
            const li = document.createElement('li');
            li.innerHTML = `
                <strong>Question ${index + 1}:</strong> ${item.question}<br>
                <strong>Answer:</strong> ${item.answer}
            `;
            quizElement.appendChild(li);
        });
        
        resultsElement.style.display = 'block';
    }

    transcribeBtn.addEventListener('click', async () => {
        try {
            // First check if we're on a YouTube tab
            const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
            if (!tab.url || !tab.url.includes('youtube.com/watch')) {
                updateStatus('Please navigate to a YouTube video page first.');
                return;
            }

            // Get current video URL from content script
            const response = await chrome.tabs.sendMessage(tab.id, {action: "getVideoUrl"});
            
            if (!response || !response.videoUrl) {
                updateStatus('Could not detect YouTube video. Please refresh the page.');
                return;
            }

            updateStatus('Processing video...');
            transcribeBtn.disabled = true;

            // Send request to backend
            const result = await fetch('http://localhost:8000/transcribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ video_url: response.videoUrl })
            });

            const data = await result.json();
            
            if (data.status === 'success') {
                updateStatus('Done!');
                displayResults(data.transcript, data.quiz);
            } else {
                throw new Error(data.detail || 'Failed to process video');
            }
        } catch (error) {
            if (error.message.includes('Cannot establish connection')) {
                updateStatus('Please refresh the YouTube page and try again.');
            } else {
                updateStatus('Error: ' + error.message);
            }
        } finally {
            transcribeBtn.disabled = false;
        }
    });
});
