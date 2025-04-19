class TypingTracker {
    constructor(sampleText, sessionId) {
        this.sampleText = sampleText;
        this.sessionId = sessionId;
        this.currentIndex = 0;
        this.startTime = null;
        this.lastKeystrokeTime = null;
        this.keystrokes = [];
        this.errors = 0;
        this.totalChars = 0;
    }

    start() {
        this.startTime = new Date();
        this.lastKeystrokeTime = this.startTime;
    }

    recordKeystroke(actualChar) {
        const now = new Date();
        const expectedChar = this.sampleText[this.currentIndex];
        const timeSincePrevious = this.lastKeystrokeTime ? now - this.lastKeystrokeTime : 0;

        const keystroke = {
            sessionId: this.sessionId,
            timestamp: now.toISOString(),
            expectedChar: expectedChar,
            actualChar: actualChar,
            timeSincePrevious: timeSincePrevious,
            isCorrect: expectedChar === actualChar
        };

        // Send keystroke data to server
        fetch('/record_keystroke', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(keystroke)
        });

        this.lastKeystrokeTime = now;
        this.currentIndex++;
        this.totalChars++;
        
        if (expectedChar !== actualChar) {
            this.errors++;
        }

        return keystroke.isCorrect;
    }

    getStats() {
        const endTime = new Date();
        const timeElapsed = (endTime - this.startTime) / 1000 / 60; // in minutes
        const wpm = Math.round((this.totalChars / 5) / timeElapsed); // standard WPM calculation
        const cpm = Math.round(this.totalChars / timeElapsed);
        const accuracy = ((this.totalChars - this.errors) / this.totalChars) * 100;

        return {
            wpm: wpm,
            cpm: cpm,
            expected_chars: this.sampleText.length,
            actual_chars: this.totalChars,
            errors: this.errors,
            accuracy: accuracy
        };
    }

    endSession() {
        const stats = this.getStats();
        
        // Send end session data to server
        fetch('/end_session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                sessionId: this.sessionId,
                stats: stats
            })
        });

        return stats;
    }
}
