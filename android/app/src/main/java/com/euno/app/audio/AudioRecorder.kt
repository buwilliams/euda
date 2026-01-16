package com.euno.app.audio

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log
import androidx.core.content.ContextCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

class AudioRecorder(private val context: Context) {

    companion object {
        private const val TAG = "AudioRecorder"
        private const val SAMPLE_RATE = 16000
        private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT

        // Voice Activity Detection (VAD) configuration - matches web app exactly
        // Volume thresholds (scaled for 16-bit PCM, web app uses 0-255 scale)
        private const val SILENCE_THRESHOLD = 400       // Below this amplitude = silence
        private const val MIN_SPEECH_VOLUME = 600       // Must exceed to count as real speech

        // Adaptive timeout bounds
        private const val MIN_TIMEOUT_MS = 800L         // Min silence before auto-stop (quick speakers)
        private const val BASE_TIMEOUT_MS = 1500L       // Default silence timeout
        private const val MAX_TIMEOUT_MS = 3000L        // Max silence timeout (thoughtful speakers)

        // Timing
        private const val MIN_SPEECH_DURATION_MS = 300L // Min recording before auto-stop allowed
        private const val MAX_RECORDING_MS = 120000L    // Max 2 minute recording

        // Pattern detection for adaptive timeout
        private const val SHORT_PAUSE_THRESHOLD_MS = 400L   // Pauses shorter = quick speaker
        private const val LONG_PAUSE_THRESHOLD_MS = 1000L   // Pauses longer = thoughtful speaker
        private const val RECENT_SPEECH_BONUS_MS = 500L     // Extra wait if speech was recent
        private const val RECENT_SPEECH_WINDOW_MS = 2000L   // "Recent" = within last 2 seconds
    }

    // Speech segment for pattern tracking
    private data class SpeechSegment(val type: String, val duration: Long)

    private var audioRecord: AudioRecord? = null
    @Volatile
    private var isRecording = false
    private var recordingThread: Thread? = null
    private val audioData = ByteArrayOutputStream()

    // VAD state
    private var onSilenceDetected: (() -> Unit)? = null
    private var recordingStartTime: Long = 0
    private var silenceStartTime: Long = 0
    private var hasSpeechStarted = false
    private var maxVolumeDetected = 0
    private var currentTimeout = BASE_TIMEOUT_MS

    // Adaptive VAD state
    private var wasSpeak = false
    private var speechStartTime: Long = 0
    private var lastSpeechTime: Long = 0
    private val speechSegments = mutableListOf<SpeechSegment>()

    // Audio filter for speech frequencies (80 Hz - 7000 Hz)
    private val audioFilter = AudioFilter(SAMPLE_RATE)

    // Audio enhancements (AGC, pre-emphasis, noise gate, click removal)
    private val audioEnhancements = AudioEnhancements()

    fun hasPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED
    }

    /**
     * Set callback for when VAD detects silence (auto-stop)
     */
    fun setOnSilenceDetected(callback: () -> Unit) {
        onSilenceDetected = callback
    }

    @SuppressLint("MissingPermission")
    fun startRecording(): Boolean {
        Log.d(TAG, "startRecording called, hasPermission=${hasPermission()}, isRecording=$isRecording")

        if (!hasPermission()) {
            Log.e(TAG, "No RECORD_AUDIO permission")
            return false
        }
        if (isRecording) {
            Log.w(TAG, "Already recording")
            return false
        }

        val bufferSize = AudioRecord.getMinBufferSize(
            SAMPLE_RATE,
            CHANNEL_CONFIG,
            AUDIO_FORMAT
        )
        Log.d(TAG, "Buffer size: $bufferSize")

        if (bufferSize == AudioRecord.ERROR || bufferSize == AudioRecord.ERROR_BAD_VALUE) {
            Log.e(TAG, "Invalid buffer size: $bufferSize")
            return false
        }

        return try {
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                bufferSize * 2
            )

            val state = audioRecord?.state
            Log.d(TAG, "AudioRecord state: $state (expected: ${AudioRecord.STATE_INITIALIZED})")

            if (state != AudioRecord.STATE_INITIALIZED) {
                Log.e(TAG, "AudioRecord not initialized, state: $state")
                audioRecord?.release()
                audioRecord = null
                return false
            }

            synchronized(audioData) {
                audioData.reset()
            }

            // Reset VAD state
            recordingStartTime = System.currentTimeMillis()
            silenceStartTime = 0
            hasSpeechStarted = false
            maxVolumeDetected = 0
            currentTimeout = BASE_TIMEOUT_MS

            // Reset adaptive VAD state
            wasSpeak = false
            speechStartTime = 0
            lastSpeechTime = 0
            speechSegments.clear()

            // Reset audio filter and enhancements
            audioFilter.reset()
            audioEnhancements.resetAll()

            isRecording = true
            audioRecord?.startRecording()
            Log.d(TAG, "AudioRecord.startRecording() called")

            recordingThread = Thread {
                Log.d(TAG, "Recording thread started with VAD")
                val buffer = ByteArray(bufferSize)
                var totalBytes = 0

                while (isRecording) {
                    val read = audioRecord?.read(buffer, 0, buffer.size) ?: 0
                    if (read > 0) {
                        // Audio processing pipeline (order matters!)
                        // 1. Bandpass filter - Remove out-of-band frequencies (80-7000 Hz)
                        audioFilter.filterBuffer(buffer, read)

                        // 2. Click/pop removal - Remove impulse noise before AGC
                        audioEnhancements.removeClicks(buffer, read)

                        // 3. Noise gate - Suppress background noise
                        val isGateClosed = audioEnhancements.applyNoiseGate(buffer, read)

                        // 4. Pre-emphasis - Boost high frequencies for clarity
                        if (!isGateClosed) {
                            audioEnhancements.applyPreEmphasis(buffer, read)
                        }

                        // 5. AGC - Normalize volume levels
                        if (!isGateClosed) {
                            audioEnhancements.applyAGC(buffer, read)
                        }

                        synchronized(audioData) {
                            audioData.write(buffer, 0, read)
                        }
                        totalBytes += read

                        // Process VAD on enhanced buffer
                        processVAD(buffer, read)
                    }
                }
                Log.d(TAG, "Recording thread ended, total bytes: $totalBytes, maxVolume: $maxVolumeDetected")
            }
            recordingThread?.start()

            Log.d(TAG, "Recording started successfully with VAD")
            true
        } catch (e: SecurityException) {
            Log.e(TAG, "SecurityException in startRecording", e)
            false
        } catch (e: Exception) {
            Log.e(TAG, "Exception in startRecording", e)
            false
        }
    }

    /**
     * Voice Activity Detection - analyzes audio buffer for speech/silence
     * Implements adaptive timeout based on speech patterns (matches web app)
     */
    private fun processVAD(buffer: ByteArray, length: Int) {
        if (!isRecording) return

        val now = System.currentTimeMillis()
        val recordingDuration = now - recordingStartTime

        // Max recording timeout
        if (recordingDuration >= MAX_RECORDING_MS) {
            Log.d(TAG, "VAD: Max recording time reached, auto-stopping")
            triggerSilenceCallback()
            return
        }

        // Calculate average amplitude from 16-bit PCM samples
        var sum = 0L
        val samples = length / 2  // 16-bit = 2 bytes per sample
        for (i in 0 until samples) {
            val sample = (buffer[i * 2].toInt() and 0xFF) or (buffer[i * 2 + 1].toInt() shl 8)
            val signedSample = if (sample > 32767) sample - 65536 else sample
            sum += abs(signedSample).toLong()
        }
        val avgAmplitude = if (samples > 0) (sum / samples).toInt() else 0

        // Track peak volume (used to filter accidental presses)
        if (avgAmplitude > maxVolumeDetected) {
            maxVolumeDetected = avgAmplitude
        }

        // isSpeaking = above silence threshold (detects any sound)
        // isRealSpeech = above minSpeechVolume (filters quiet noise/accidental presses)
        val isSpeaking = avgAmplitude > SILENCE_THRESHOLD
        val isRealSpeech = avgAmplitude > MIN_SPEECH_VOLUME

        if (isSpeaking) {
            // Speech detected
            if (!wasSpeak) {
                // Speech just started
                speechStartTime = now

                // Record the pause duration if we were in silence
                if (silenceStartTime != 0L && hasSpeechStarted) {
                    val pauseDuration = now - silenceStartTime
                    speechSegments.add(SpeechSegment("pause", pauseDuration))

                    // Adapt timeout based on observed pause patterns
                    adaptTimeout()
                }
            }

            // Only mark speech as started if volume exceeds minSpeechVolume
            if (isRealSpeech) {
                hasSpeechStarted = true
            }
            lastSpeechTime = now
            silenceStartTime = 0
            wasSpeak = true

        } else {
            // Silence detected
            if (wasSpeak && speechStartTime != 0L) {
                // Speech just ended - record speech duration
                val speechDuration = now - speechStartTime
                speechSegments.add(SpeechSegment("speech", speechDuration))
                speechStartTime = 0
            }

            wasSpeak = false

            if (hasSpeechStarted && recordingDuration > MIN_SPEECH_DURATION_MS) {
                // Start or continue silence timer
                if (silenceStartTime == 0L) {
                    silenceStartTime = now
                }

                // Calculate effective timeout with bonuses
                val effectiveTimeout = calculateEffectiveTimeout(now)
                val silenceDuration = now - silenceStartTime

                if (silenceDuration >= effectiveTimeout) {
                    Log.d(TAG, "VAD: Auto-stopping after ${silenceDuration}ms silence (timeout: ${effectiveTimeout}ms)")
                    triggerSilenceCallback()
                }
            }
        }
    }

    /**
     * Adapt timeout based on observed pause patterns (quick vs thoughtful speaker)
     */
    private fun adaptTimeout() {
        // Get recent pauses (last 5)
        val recentPauses = speechSegments
            .filter { it.type == "pause" }
            .takeLast(5)

        if (recentPauses.isEmpty()) {
            currentTimeout = BASE_TIMEOUT_MS
            return
        }

        // Calculate average pause duration
        val avgPause = recentPauses.map { it.duration }.average().toLong()

        currentTimeout = when {
            avgPause < SHORT_PAUSE_THRESHOLD_MS -> {
                // Quick speaker - shorter timeout
                MIN_TIMEOUT_MS
            }
            avgPause > LONG_PAUSE_THRESHOLD_MS -> {
                // Thoughtful speaker - longer timeout
                MAX_TIMEOUT_MS
            }
            else -> {
                // Normal speaker - interpolate between min and max
                val ratio = (avgPause - SHORT_PAUSE_THRESHOLD_MS).toFloat() /
                        (LONG_PAUSE_THRESHOLD_MS - SHORT_PAUSE_THRESHOLD_MS)
                (MIN_TIMEOUT_MS + ratio * (MAX_TIMEOUT_MS - MIN_TIMEOUT_MS)).toLong()
            }
        }

        // Clamp to bounds
        currentTimeout = max(MIN_TIMEOUT_MS, min(MAX_TIMEOUT_MS, currentTimeout))
    }

    /**
     * Calculate effective timeout with recent speech bonus
     */
    private fun calculateEffectiveTimeout(now: Long): Long {
        var timeout = currentTimeout

        // Add bonus time if speech was very recent (user might just be pausing)
        if (lastSpeechTime != 0L && (now - lastSpeechTime) < RECENT_SPEECH_WINDOW_MS) {
            // The more recent the speech, the more bonus time
            val recency = 1.0f - ((now - lastSpeechTime).toFloat() / RECENT_SPEECH_WINDOW_MS)
            timeout += (recency * RECENT_SPEECH_BONUS_MS).toLong()
        }

        return min(timeout, MAX_TIMEOUT_MS + RECENT_SPEECH_BONUS_MS)
    }

    private fun triggerSilenceCallback() {
        if (!isRecording) return
        onSilenceDetected?.invoke()
    }

    fun stopRecording(): ByteArray? {
        Log.d(TAG, "stopRecording called, isRecording=$isRecording")

        if (!isRecording) {
            Log.w(TAG, "Not recording")
            return null
        }

        isRecording = false

        try {
            recordingThread?.join(2000)
        } catch (e: InterruptedException) {
            Log.w(TAG, "Interrupted waiting for recording thread")
        }
        recordingThread = null

        try {
            audioRecord?.stop()
            Log.d(TAG, "AudioRecord stopped")
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping AudioRecord", e)
        }

        audioRecord?.release()
        audioRecord = null
        Log.d(TAG, "AudioRecord released")

        val pcmData: ByteArray
        synchronized(audioData) {
            pcmData = audioData.toByteArray()
        }

        Log.d(TAG, "PCM data size: ${pcmData.size}")

        if (pcmData.isEmpty()) {
            Log.e(TAG, "No audio data recorded")
            return null
        }

        // Convert PCM to WAV
        val wavData = pcmToWav(pcmData)
        Log.d(TAG, "WAV data size: ${wavData.size}")
        return wavData
    }

    fun isRecording(): Boolean = isRecording

    private fun pcmToWav(pcmData: ByteArray): ByteArray {
        val wavOutput = ByteArrayOutputStream()

        val totalDataLen = pcmData.size + 36
        val channels = 1
        val byteRate = SAMPLE_RATE * channels * 2

        // WAV header
        wavOutput.write("RIFF".toByteArray())
        wavOutput.write(intToBytes(totalDataLen))
        wavOutput.write("WAVE".toByteArray())
        wavOutput.write("fmt ".toByteArray())
        wavOutput.write(intToBytes(16)) // Subchunk1Size (16 for PCM)
        wavOutput.write(shortToBytes(1)) // AudioFormat (1 for PCM)
        wavOutput.write(shortToBytes(channels.toShort())) // NumChannels
        wavOutput.write(intToBytes(SAMPLE_RATE)) // SampleRate
        wavOutput.write(intToBytes(byteRate)) // ByteRate
        wavOutput.write(shortToBytes((channels * 2).toShort())) // BlockAlign
        wavOutput.write(shortToBytes(16)) // BitsPerSample
        wavOutput.write("data".toByteArray())
        wavOutput.write(intToBytes(pcmData.size))
        wavOutput.write(pcmData)

        return wavOutput.toByteArray()
    }

    private fun intToBytes(value: Int): ByteArray {
        return ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN).putInt(value).array()
    }

    private fun shortToBytes(value: Short): ByteArray {
        return ByteBuffer.allocate(2).order(ByteOrder.LITTLE_ENDIAN).putShort(value).array()
    }

    suspend fun saveToTempFile(): File? = withContext(Dispatchers.IO) {
        Log.d(TAG, "saveToTempFile called")
        val wavData = stopRecording()
        if (wavData == null) {
            Log.e(TAG, "stopRecording returned null")
            return@withContext null
        }

        try {
            val tempFile = File.createTempFile("recording", ".wav", context.cacheDir)
            FileOutputStream(tempFile).use { it.write(wavData) }
            Log.d(TAG, "Saved to temp file: ${tempFile.absolutePath}, size: ${tempFile.length()}")
            tempFile
        } catch (e: Exception) {
            Log.e(TAG, "Error saving temp file", e)
            null
        }
    }
}
