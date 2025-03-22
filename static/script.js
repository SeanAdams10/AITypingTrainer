let startTime = null;
let characterCount = 0;
let errorCount = 0;
let totalCharacters = 0;
let totalKeypresses = 0;
let isTestComplete = false;
let isCancelled = false;
let backspaceCount = 0;  // Track backspaces separately
let sampleText = '';  // Store sample text globally

function updateStats() {
    if (!startTime || isTestComplete || isCancelled) return;

    const currentTime = new Date();
    const elapsedTimeInSeconds = (currentTime - startTime) / 1000;
    const wordsPerMinute = Math.round((characterCount / 5) / (elapsedTimeInSeconds / 60));
    const charsPerSecond = Math.round((characterCount / elapsedTimeInSeconds) * 10) / 10;
    const errorPercentage = Math.round((errorCount / totalCharacters) * 100 * 10) / 10;

    document.getElementById('wpm').textContent = wordsPerMinute;
    document.getElementById('cps').textContent = charsPerSecond;
    document.getElementById('accuracy').textContent = (100 - errorPercentage).toFixed(1);
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

    const elapsedTimeInSeconds = (new Date() - startTime) / 1000;
    const wordsPerMinute = Math.round((characterCount / 5) / (elapsedTimeInSeconds / 60));
    const charsPerSecond = Math.round((characterCount / elapsedTimeInSeconds) * 10) / 10;
    const errorPercentage = Math.round((errorCount / totalCharacters) * 100 * 10) / 10;

    // Show success message box
    alert(`Success - your typing speed is ${wordsPerMinute} WPM`);
    showStatusMessage(`Congratulations! You completed the test with ${wordsPerMinute} WPM`);

    // Debug logs
    console.log('Showing final results:');
    console.log('Sample text length:', sampleText.length);
    console.log('Total keypresses:', totalKeypresses);
    console.log('WPM:', wordsPerMinute);
    console.log('CPS:', charsPerSecond);
    console.log('Error %:', errorPercentage);
    console.log('Error count:', errorCount);

    // Update final results with clear explanations
    const resultsDiv = document.getElementById('results');
    document.getElementById('final-chars-expected').textContent = sampleText.length;
    document.getElementById('final-keypresses').textContent = totalKeypresses;
    document.getElementById('final-wpm').textContent = wordsPerMinute;
    document.getElementById('final-cps').textContent = charsPerSecond;
    document.getElementById('final-accuracy').textContent = (100 - errorPercentage).toFixed(1);
    document.getElementById('final-errors').textContent = errorCount;

    // Make sure the results div is visible
    resultsDiv.style.display = 'block';
    
    // Scroll to results
    resultsDiv.scrollIntoView({ behavior: 'smooth' });
}

document.addEventListener('DOMContentLoaded', function() {
    sampleText = document.getElementById('sample-text').textContent;
    const typingInput = document.getElementById('typing-input');
    const cancelButton = document.getElementById('cancel-test');
    let currentPosition = 0;

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

        if (!startTime) {
            startTime = new Date();
        }

        const typed = e.target.value;
        
        // Track all keypresses, including backspaces
        totalKeypresses++;
        
        // Check if backspace was pressed
        if (typed.length < currentPosition) {
            backspaceCount++;
            // Character deleted
            characterCount--;
            totalCharacters--;
            if (typed.length < sampleText.length && 
                typed[typed.length - 1] !== sampleText[typed.length - 1]) {
                errorCount--;
            }
        } else {
            // New character typed
            characterCount++;
            totalCharacters++;
            if (typed[typed.length - 1] !== sampleText[typed.length - 1]) {
                errorCount++;
            }
        }
        
        currentPosition = typed.length;
        updateText();
        updateStats();
    });
});

// Update stats every second
setInterval(updateStats, 1000);
