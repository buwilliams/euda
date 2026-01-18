// Euno - Text-to-Speech Playback

// Track current audio instance to prevent overlapping playback
let currentTTSAudio = null;

/**
 * Play TTS audio from base64-encoded MP3 data.
 * Stops any currently playing audio before starting new playback.
 * @param {string} base64Audio - Base64-encoded audio data
 */
function playTTSAudio(base64Audio) {
    // Stop any currently playing audio
    if (currentTTSAudio) {
        currentTTSAudio.pause();
        currentTTSAudio.src = '';
        currentTTSAudio = null;
    }

    const audioData = 'data:audio/mpeg;base64,' + base64Audio;
    const audio = new Audio(audioData);
    currentTTSAudio = audio;

    audio.onerror = (e) => {
        console.error('TTS playback error:', e);
        currentTTSAudio = null;
    };

    audio.onended = () => {
        currentTTSAudio = null;
    };

    audio.play().catch(e => {
        console.error('TTS play failed:', e);
        currentTTSAudio = null;
    });
}
