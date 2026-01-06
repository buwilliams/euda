// Euno - Voice Input (Speech-to-Text) with Voice Activity Detection

// ============== Voice Recording State ==============
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let recordingStartTime = null;
let audioStream = null;

// Maximum recording duration (2 minutes to stay well under 25MB limit)
const MAX_RECORDING_MS = 120000;
let recordingTimeout = null;

// ============== Voice Activity Detection (VAD) ==============
let audioContext = null;
let analyser = null;
let vadInterval = null;

// VAD Configuration
const VAD_CONFIG = {
    silenceThreshold: 15,      // Volume level below which is silence (0-255)
    silenceDurationMs: 4500,   // Auto-stop after this much silence (4.5 seconds)
    minSpeechDurationMs: 500,  // Minimum recording time before auto-stop kicks in
    checkIntervalMs: 100       // How often to check audio levels
};

let silenceStartTime = null;
let hasSpeechStarted = false;

// ============== Voice Recording Functions ==============

function toggleVoiceRecording() {
    if (isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
}

async function startRecording() {
    try {
        // Request microphone permission
        audioStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                sampleRate: 16000  // Optimal for speech recognition
            }
        });

        // Determine best supported format (webm preferred, mp4 fallback)
        const mimeType = getSupportedMimeType();

        mediaRecorder = new MediaRecorder(audioStream, {
            mimeType: mimeType,
            audioBitsPerSecond: 64000  // Keep file size reasonable
        });

        audioChunks = [];
        recordingStartTime = Date.now();
        silenceStartTime = null;
        hasSpeechStarted = false;

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = async () => {
            // Stop VAD monitoring
            stopVAD();

            // Stop all tracks to release microphone
            if (audioStream) {
                audioStream.getTracks().forEach(track => track.stop());
                audioStream = null;
            }

            if (audioChunks.length > 0) {
                const audioBlob = new Blob(audioChunks, { type: mimeType });
                await transcribeAudio(audioBlob);
            }

            clearRecordingTimeout();
        };

        mediaRecorder.onerror = (event) => {
            console.error('MediaRecorder error:', event.error);
            stopRecording();
            showVoiceError('Recording failed. Please try again.');
        };

        // Start recording with timeslice for chunked data
        mediaRecorder.start(1000);
        isRecording = true;
        updateVoiceUI();

        // Start Voice Activity Detection
        startVAD(audioStream);

        // Set maximum recording timeout
        recordingTimeout = setTimeout(() => {
            if (isRecording) {
                stopRecording();
            }
        }, MAX_RECORDING_MS);

    } catch (error) {
        console.error('Failed to start recording:', error);

        if (error.name === 'NotAllowedError') {
            showVoiceError('Microphone access denied. Please enable it in your browser settings.');
        } else if (error.name === 'NotFoundError') {
            showVoiceError('No microphone found. Please connect a microphone.');
        } else {
            showVoiceError('Could not access microphone. Please try again.');
        }
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
    }
    isRecording = false;
    updateVoiceUI();
    clearRecordingTimeout();
    stopVAD();
}

function clearRecordingTimeout() {
    if (recordingTimeout) {
        clearTimeout(recordingTimeout);
        recordingTimeout = null;
    }
}

// ============== Voice Activity Detection ==============

function startVAD(stream) {
    try {
        // Create audio context and analyser
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        analyser.smoothingTimeConstant = 0.5;

        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);

        const dataArray = new Uint8Array(analyser.frequencyBinCount);

        // Check audio levels periodically
        vadInterval = setInterval(() => {
            if (!isRecording) {
                stopVAD();
                return;
            }

            analyser.getByteFrequencyData(dataArray);

            // Calculate average volume
            const avgVolume = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;

            const now = Date.now();
            const recordingDuration = now - recordingStartTime;

            if (avgVolume > VAD_CONFIG.silenceThreshold) {
                // Speech detected
                hasSpeechStarted = true;
                silenceStartTime = null;
            } else if (hasSpeechStarted && recordingDuration > VAD_CONFIG.minSpeechDurationMs) {
                // Silence detected after speech started
                if (silenceStartTime === null) {
                    silenceStartTime = now;
                } else if (now - silenceStartTime >= VAD_CONFIG.silenceDurationMs) {
                    // Silence duration exceeded - auto-stop
                    console.log('VAD: Auto-stopping after silence');
                    stopRecording();
                }
            }
        }, VAD_CONFIG.checkIntervalMs);

    } catch (error) {
        console.error('Failed to start VAD:', error);
        // VAD is optional - recording still works without it
    }
}

function stopVAD() {
    if (vadInterval) {
        clearInterval(vadInterval);
        vadInterval = null;
    }

    if (audioContext && audioContext.state !== 'closed') {
        audioContext.close().catch(() => {});
        audioContext = null;
    }

    analyser = null;
    silenceStartTime = null;
    hasSpeechStarted = false;
}

function getSupportedMimeType() {
    // webm is best supported and works with OpenAI
    const types = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/mp4',
        'audio/ogg;codecs=opus'
    ];

    for (const type of types) {
        if (MediaRecorder.isTypeSupported(type)) {
            return type;
        }
    }

    // Fallback
    return 'audio/webm';
}

// ============== Transcription ==============

async function transcribeAudio(audioBlob) {
    // Show transcribing state
    setVoiceTranscribing(true);

    try {
        const formData = new FormData();

        // Determine file extension from mime type
        const ext = audioBlob.type.includes('mp4') ? 'm4a' : 'webm';
        formData.append('audio', audioBlob, `recording.${ext}`);

        const response = await fetch('/api/transcribe', {
            method: 'POST',
            body: formData,
            credentials: 'same-origin'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Transcription failed');
        }

        const data = await response.json();

        if (data.text && data.text.trim()) {
            // Auto-send transcribed text to chat
            autoSendTranscribedText(data.text.trim());
        } else {
            showVoiceError('No speech detected. Please try again.');
        }

    } catch (error) {
        console.error('Transcription error:', error);
        showVoiceError(error.message || 'Transcription failed. Please try again.');
    } finally {
        setVoiceTranscribing(false);
    }
}

function autoSendTranscribedText(text) {
    // Set the text in the input field
    const input = document.getElementById('context-input');
    input.value = text;

    // Trigger auto-resize
    input.dispatchEvent(new Event('input'));

    // Auto-send the message
    sendContextMessage();
}

// ============== UI Updates ==============

function updateVoiceUI() {
    const btn = document.getElementById('voice-btn');
    const icon = document.getElementById('voice-icon');

    if (!btn || !icon) return;

    if (isRecording) {
        btn.classList.add('recording');
        btn.title = 'Stop recording (or wait for auto-stop)';
        // Update icon to show recording state (filled circle/stop icon)
        icon.innerHTML = '<circle cx="12" cy="12" r="6" fill="currentColor"/>';
    } else {
        btn.classList.remove('recording');
        btn.title = 'Voice input';
        // Restore microphone icon
        icon.innerHTML = `
            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
            <line x1="12" y1="19" x2="12" y2="23"/>
            <line x1="8" y1="23" x2="16" y2="23"/>
        `;
    }
}

function setVoiceTranscribing(transcribing) {
    const btn = document.getElementById('voice-btn');

    if (!btn) return;

    if (transcribing) {
        btn.classList.add('transcribing');
        btn.disabled = true;
        btn.title = 'Transcribing...';
    } else {
        btn.classList.remove('transcribing');
        btn.disabled = false;
        btn.title = 'Voice input';
    }
}

function showVoiceError(message) {
    // Add error message to chat as system message
    if (typeof addInlineMessage === 'function') {
        addInlineMessage(message, 'friend');
    }
    if (typeof switchTab === 'function') {
        switchTab('chat');
    }
}

// ============== Feature Detection ==============

function isVoiceInputSupported() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder);
}

// Hide voice button if not supported
document.addEventListener('DOMContentLoaded', () => {
    if (!isVoiceInputSupported()) {
        const voiceBtn = document.getElementById('voice-btn');
        if (voiceBtn) {
            voiceBtn.style.display = 'none';
        }
    }
});
