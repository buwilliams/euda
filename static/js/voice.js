// Euno - Voice Input (Speech-to-Text) with Adaptive Voice Activity Detection

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

// Industry-standard VAD Configuration
const VAD_CONFIG = {
    // Volume thresholds (0-255 scale)
    silenceThreshold: 15,       // Below this = silence
    minSpeechVolume: 18,        // Must exceed this to count as real speech (filters noise/accidental presses)

    // Adaptive timeout bounds (industry standard for dictation/transcription)
    minTimeoutMs: 800,       // Minimum silence before auto-stop (quick speakers)
    baseTimeoutMs: 1500,     // Default silence timeout (standard)
    maxTimeoutMs: 3000,      // Maximum silence timeout (thoughtful speakers)

    // Timing
    minSpeechDurationMs: 300,  // Minimum speech before allowing auto-stop
    checkIntervalMs: 50,       // Audio level check frequency (50ms = responsive)

    // Pattern detection
    shortPauseThresholdMs: 400,   // Pauses shorter than this = quick speaker
    longPauseThresholdMs: 1000,   // Pauses longer than this = thoughtful speaker
    recentSpeechBonusMs: 500,     // Extra wait time if speech was recent
    recentSpeechWindowMs: 2000    // "Recent" = within last 2 seconds
};

// VAD State
let silenceStartTime = null;
let hasSpeechStarted = false;
let lastSpeechTime = null;
let speechSegments = [];        // Track speech/silence patterns
let currentTimeout = VAD_CONFIG.baseTimeoutMs;
let maxVolumeDetected = 0;      // Track peak volume to filter accidental presses

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

        // Reset VAD state
        silenceStartTime = null;
        hasSpeechStarted = false;
        lastSpeechTime = null;
        speechSegments = [];
        currentTimeout = VAD_CONFIG.baseTimeoutMs;
        maxVolumeDetected = 0;

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

            // Check if we detected real speech (filters accidental mic presses)
            if (maxVolumeDetected < VAD_CONFIG.minSpeechVolume) {
                console.log(`VAD: Skipping transcription - max volume ${maxVolumeDetected} below threshold ${VAD_CONFIG.minSpeechVolume}`);
                showVoiceError('No speech detected. Please try again.');
                clearRecordingTimeout();
                return;
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

// ============== Adaptive Voice Activity Detection ==============

function startVAD(stream) {
    try {
        // Create audio context and analyser
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        analyser.smoothingTimeConstant = 0.3;  // More responsive

        const source = audioContext.createMediaStreamSource(stream);
        source.connect(analyser);

        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        let wasSpeak = false;
        let speechStartTime = null;

        // Check audio levels periodically
        vadInterval = setInterval(() => {
            if (!isRecording) {
                stopVAD();
                return;
            }

            analyser.getByteFrequencyData(dataArray);

            // Calculate average volume
            const avgVolume = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;

            // Track peak volume (used to filter accidental presses)
            if (avgVolume > maxVolumeDetected) {
                maxVolumeDetected = avgVolume;
            }

            // isSpeaking = above silence threshold (detects any sound)
            // isRealSpeech = above minSpeechVolume (filters quiet noise/accidental presses)
            const isSpeaking = avgVolume > VAD_CONFIG.silenceThreshold;
            const isRealSpeech = avgVolume > VAD_CONFIG.minSpeechVolume;

            const now = Date.now();
            const recordingDuration = now - recordingStartTime;

            if (isSpeaking) {
                // Speech detected
                if (!wasSpeak) {
                    // Speech just started
                    speechStartTime = now;

                    // Record the pause duration if we were in silence
                    if (silenceStartTime !== null && hasSpeechStarted) {
                        const pauseDuration = now - silenceStartTime;
                        speechSegments.push({ type: 'pause', duration: pauseDuration });

                        // Adapt timeout based on observed pause patterns
                        adaptTimeout();
                    }
                }

                // Only mark speech as started if volume exceeds minSpeechVolume
                // This filters out quiet noise and accidental mic presses
                if (isRealSpeech) {
                    hasSpeechStarted = true;
                }
                lastSpeechTime = now;
                silenceStartTime = null;
                wasSpeak = true;

            } else {
                // Silence detected
                if (wasSpeak && speechStartTime) {
                    // Speech just ended - record speech duration
                    const speechDuration = now - speechStartTime;
                    speechSegments.push({ type: 'speech', duration: speechDuration });
                    speechStartTime = null;
                }

                wasSpeak = false;

                if (hasSpeechStarted && recordingDuration > VAD_CONFIG.minSpeechDurationMs) {
                    // Start or continue silence timer
                    if (silenceStartTime === null) {
                        silenceStartTime = now;
                    }

                    // Calculate effective timeout with bonuses
                    const effectiveTimeout = calculateEffectiveTimeout(now);
                    const silenceDuration = now - silenceStartTime;

                    if (silenceDuration >= effectiveTimeout) {
                        // Silence duration exceeded - auto-stop
                        console.log(`VAD: Auto-stopping after ${silenceDuration}ms silence (timeout: ${effectiveTimeout}ms)`);
                        stopRecording();
                    }
                }
            }
        }, VAD_CONFIG.checkIntervalMs);

    } catch (error) {
        console.error('Failed to start VAD:', error);
        // VAD is optional - recording still works without it
    }
}

function adaptTimeout() {
    // Get recent pauses (last 5)
    const recentPauses = speechSegments
        .filter(s => s.type === 'pause')
        .slice(-5);

    if (recentPauses.length === 0) {
        currentTimeout = VAD_CONFIG.baseTimeoutMs;
        return;
    }

    // Calculate average pause duration
    const avgPause = recentPauses.reduce((sum, p) => sum + p.duration, 0) / recentPauses.length;

    if (avgPause < VAD_CONFIG.shortPauseThresholdMs) {
        // Quick speaker - shorter timeout
        currentTimeout = VAD_CONFIG.minTimeoutMs;
    } else if (avgPause > VAD_CONFIG.longPauseThresholdMs) {
        // Thoughtful speaker - longer timeout
        currentTimeout = VAD_CONFIG.maxTimeoutMs;
    } else {
        // Normal speaker - interpolate between min and max
        const ratio = (avgPause - VAD_CONFIG.shortPauseThresholdMs) /
                      (VAD_CONFIG.longPauseThresholdMs - VAD_CONFIG.shortPauseThresholdMs);
        currentTimeout = VAD_CONFIG.minTimeoutMs +
                        ratio * (VAD_CONFIG.maxTimeoutMs - VAD_CONFIG.minTimeoutMs);
    }

    // Clamp to bounds
    currentTimeout = Math.max(VAD_CONFIG.minTimeoutMs,
                     Math.min(VAD_CONFIG.maxTimeoutMs, currentTimeout));
}

function calculateEffectiveTimeout(now) {
    let timeout = currentTimeout;

    // Add bonus time if speech was very recent (user might just be pausing)
    if (lastSpeechTime && (now - lastSpeechTime) < VAD_CONFIG.recentSpeechWindowMs) {
        // The more recent the speech, the more bonus time
        const recency = 1 - ((now - lastSpeechTime) / VAD_CONFIG.recentSpeechWindowMs);
        timeout += recency * VAD_CONFIG.recentSpeechBonusMs;
    }

    return Math.min(timeout, VAD_CONFIG.maxTimeoutMs + VAD_CONFIG.recentSpeechBonusMs);
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
    lastSpeechTime = null;
    speechSegments = [];
    currentTimeout = VAD_CONFIG.baseTimeoutMs;
    // Note: maxVolumeDetected is intentionally NOT reset here
    // It's checked in onstop handler after VAD stops
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

