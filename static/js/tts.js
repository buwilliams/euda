// Euno - Text-to-Speech Playback

/**
 * Play TTS audio from base64-encoded MP3 data.
 * Simple playback without stop controls per user preference.
 * @param {string} base64Audio - Base64-encoded audio data
 */
function playTTSAudio(base64Audio) {
    const audioData = 'data:audio/mpeg;base64,' + base64Audio;
    const audio = new Audio(audioData);

    audio.onerror = (e) => {
        console.error('TTS playback error:', e);
    };

    audio.play().catch(e => {
        console.error('TTS play failed:', e);
    });
}
