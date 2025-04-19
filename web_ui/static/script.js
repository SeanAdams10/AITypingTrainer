let isTestComplete = false;
let isCancelled = false;
let typingTracker = null;

function updateStats() {
    if (!typingTracker || isTestComplete || isCancelled) return;

    const stats = typingTracker.getStats();
    document.getElementById('wpm').textContent = stats.wpm;
    document.getElementById('cps').textContent = Math.round((stats.cpm / 60) * 10) / 10;
    document.getElementById('accuracy').textContent = stats.accuracy.toFixed(1);
}

function showStatusMessage(message, isSuccess = true) {
    const statusMessage = document.getElementById('status-message');
    statusMessage.textContent = message;
    statusMessage.style.display = 'block';
    statusMessage.className = 'status-message ' + (isSuccess ? 'success' : 'error');
}

function cancelTest() {
    if (isTestComplete || isCancelled) return;
    
    isCancelled = true;
    const typingInput = document.getElementById('typing-input');
    typingInput.disabled = true;
    document.getElementById('cancel-test').disabled = true;
    showStatusMessage('Test Cancelled', false);
}

function showFinalResults() {
    isTestComplete = true;
    const typingInput = document.getElementById('typing-input');
    typingInput.disabled = true;
    document.getElementById('cancel-test').disabled = true;

    const stats = typingTracker.endSession();

    // Show success message box
    alert(`Success - your typing speed is ${stats.wpm} WPM`);
    showStatusMessage(`Congratulations! You completed the test with ${stats.wpm} WPM`);

    // Update final results with clear explanations
    const resultsDiv = document.getElementById('results');
    document.getElementById('final-chars-expected').textContent = stats.expected_chars;
    document.getElementById('final-keypresses').textContent = stats.actual_chars;
    document.getElementById('final-wpm').textContent = stats.wpm;
    document.getElementById('final-cps').textContent = Math.round((stats.cpm / 60) * 10) / 10;
    document.getElementById('final-accuracy').textContent = stats.accuracy.toFixed(1);
    document.getElementById('final-errors').textContent = stats.errors;

    // Make sure the results div is visible
    resultsDiv.style.display = 'block';
    
    // Scroll to results
    resultsDiv.scrollIntoView({ behavior: 'smooth' });
}

document.addEventListener('DOMContentLoaded', function() {
    const sampleText = document.getElementById('sample-text').textContent;
    const typingInput = document.getElementById('typing-input');
    const cancelButton = document.getElementById('cancel-test');

    // Initialize the typing tracker
    typingTracker = new TypingTracker(sampleText, sessionId);

    cancelButton.addEventListener('click', cancelTest);

    // Add event listener for Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            cancelTest();
        }
    });

    function updateText() {
        const typed = typingInput.value;
        let html = '';
        
        for (let i = 0; i < sampleText.length; i++) {
            if (i < typed.length) {
                if (typed[i] === sampleText[i]) {
                    html += `<span class="correct">${sampleText[i]}</span>`;
                } else {
                    html += `<span class="incorrect">${sampleText[i]}</span>`;
                }
            } else {
                html += sampleText[i];
            }
        }
        
        document.getElementById('sample-text').innerHTML = html;

        // Check if test is complete
        if (typed.length === sampleText.length && !isTestComplete && !isCancelled) {
            showFinalResults();
        }
    }

    typingInput.addEventListener('input', function(e) {
        if (isTestComplete || isCancelled) return;

        if (!typingTracker.startTime) {
            typingTracker.start();
        }

        const typed = e.target.value;
        const lastChar = typed[typed.length - 1] || '';
        
        // Record the keystroke
        if (lastChar) {
            typingTracker.recordKeystroke(lastChar);
        }
        
        updateText();
        updateStats();
    });
});

// Update stats every second
setInterval(updateStats, 1000);
