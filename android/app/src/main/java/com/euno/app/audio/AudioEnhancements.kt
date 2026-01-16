package com.euno.app.audio

import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

/**
 * Additional audio enhancements for improved speech quality.
 * Includes AGC, pre-emphasis, noise gate, and click removal.
 *
 * Processing pipeline:
 * 1. Click/pop removal - Remove impulse noise
 * 2. Noise gate - Suppress background noise
 * 3. Pre-emphasis - Boost high frequencies for clarity
 * 4. AGC - Normalize volume levels
 */
class AudioEnhancements {

    // ==================== Automatic Gain Control (AGC) ====================

    /**
     * Automatic Gain Control - normalizes audio volume for consistent levels.
     *
     * Adapts to speaker volume and microphone distance, ensuring:
     * - Quiet speakers are boosted
     * - Loud speakers don't clip
     * - Consistent transcription accuracy
     *
     * @param buffer 16-bit PCM buffer to process in-place
     * @param length Number of bytes to process
     */
    private var agcTarget = 8000.0       // Target RMS level (~25% of max)
    private var agcCurrentGain = 1.0     // Current gain multiplier
    private val agcAttack = 0.001        // How fast to reduce gain (prevent clipping)
    private val agcRelease = 0.0001      // How fast to increase gain (smooth)
    private val agcMaxGain = 8.0         // Maximum amplification
    private val agcMinGain = 0.5         // Minimum amplification

    fun applyAGC(buffer: ByteArray, length: Int) {
        val samples = length / 2

        // Calculate RMS (root mean square) for this buffer
        var sumSquares = 0.0
        for (i in 0 until samples) {
            val rawSample = (buffer[i * 2].toInt() and 0xFF) or (buffer[i * 2 + 1].toInt() shl 8)
            val sample = if (rawSample > 32767) rawSample - 65536 else rawSample
            sumSquares += sample * sample
        }
        val rms = if (samples > 0) kotlin.math.sqrt(sumSquares / samples) else 0.0

        // Calculate desired gain to reach target RMS
        val desiredGain = if (rms > 0) agcTarget / rms else 1.0

        // Smooth gain changes (attack/release)
        agcCurrentGain = if (desiredGain < agcCurrentGain) {
            // Reduce gain quickly (attack) to prevent clipping
            agcCurrentGain + (desiredGain - agcCurrentGain) * agcAttack
        } else {
            // Increase gain slowly (release) for smooth transitions
            agcCurrentGain + (desiredGain - agcCurrentGain) * agcRelease
        }

        // Clamp gain to safe range
        agcCurrentGain = agcCurrentGain.coerceIn(agcMinGain, agcMaxGain)

        // Apply gain to buffer
        for (i in 0 until samples) {
            val rawSample = (buffer[i * 2].toInt() and 0xFF) or (buffer[i * 2 + 1].toInt() shl 8)
            val sample = if (rawSample > 32767) rawSample - 65536 else rawSample

            // Apply gain with soft clipping
            val amplified = (sample * agcCurrentGain).toInt()
            val clipped = amplified.coerceIn(-32768, 32767)
            val unsigned = if (clipped < 0) clipped + 65536 else clipped

            buffer[i * 2] = (unsigned and 0xFF).toByte()
            buffer[i * 2 + 1] = (unsigned shr 8).toByte()
        }
    }

    fun resetAGC() {
        agcCurrentGain = 1.0
    }


    // ==================== Pre-emphasis Filter ====================

    /**
     * Pre-emphasis filter - boosts high frequencies for better consonant clarity.
     *
     * Standard in telephony (ITU-T G.711). Improves recognition of:
     * - Consonants (s, t, k, p, f, etc.)
     * - Word boundaries
     * - Overall speech intelligibility
     *
     * Uses coefficient of 0.97 (industry standard)
     */
    private var preEmphasisPrevSample = 0

    fun applyPreEmphasis(buffer: ByteArray, length: Int, coefficient: Double = 0.97) {
        val samples = length / 2

        for (i in 0 until samples) {
            val rawSample = (buffer[i * 2].toInt() and 0xFF) or (buffer[i * 2 + 1].toInt() shl 8)
            val sample = if (rawSample > 32767) rawSample - 65536 else rawSample

            // y[n] = x[n] - α * x[n-1]
            val emphasized = sample - (coefficient * preEmphasisPrevSample).toInt()
            preEmphasisPrevSample = sample

            // Clamp to 16-bit range
            val clipped = emphasized.coerceIn(-32768, 32767)
            val unsigned = if (clipped < 0) clipped + 65536 else clipped

            buffer[i * 2] = (unsigned and 0xFF).toByte()
            buffer[i * 2 + 1] = (unsigned shr 8).toByte()
        }
    }

    fun resetPreEmphasis() {
        preEmphasisPrevSample = 0
    }


    // ==================== Noise Gate ====================

    /**
     * Noise Gate - aggressively suppresses audio below threshold.
     *
     * More aggressive than VAD - completely zeros out quiet sections:
     * - Breathing between words
     * - Constant background hum
     * - Keyboard typing
     * - Air conditioning
     *
     * Uses hysteresis (different open/close thresholds) to prevent flutter.
     */
    private var gateIsOpen = false
    private val gateOpenThreshold = 600    // Must exceed to open gate
    private val gateCloseThreshold = 300   // Must fall below to close gate
    private val gateAttackSamples = 10     // Samples to fade in
    private val gateReleaseSamples = 50    // Samples to fade out
    private var gateFadeCounter = 0

    fun applyNoiseGate(buffer: ByteArray, length: Int): Boolean {
        val samples = length / 2

        // Calculate average amplitude
        var sum = 0L
        for (i in 0 until samples) {
            val rawSample = (buffer[i * 2].toInt() and 0xFF) or (buffer[i * 2 + 1].toInt() shl 8)
            val sample = if (rawSample > 32767) rawSample - 65536 else rawSample
            sum += abs(sample).toLong()
        }
        val avgAmplitude = if (samples > 0) (sum / samples).toInt() else 0

        // Hysteresis: different thresholds for opening vs closing
        val shouldBeOpen = if (gateIsOpen) {
            avgAmplitude > gateCloseThreshold  // Stay open until below close threshold
        } else {
            avgAmplitude > gateOpenThreshold   // Must exceed open threshold to open
        }

        // Update gate state with fade in/out
        if (shouldBeOpen && !gateIsOpen) {
            // Opening gate - fade in
            gateIsOpen = true
            gateFadeCounter = 0
        } else if (!shouldBeOpen && gateIsOpen) {
            // Closing gate - fade out
            gateIsOpen = false
            gateFadeCounter = gateReleaseSamples
        }

        // Apply gate with fade
        var shouldZeroBuffer = false
        if (!gateIsOpen || gateFadeCounter > 0) {
            val fadeMultiplier = if (gateIsOpen) {
                // Fading in (attack)
                min(1.0, gateFadeCounter.toDouble() / gateAttackSamples)
            } else {
                // Fading out (release) or fully closed
                if (gateFadeCounter > 0) {
                    gateFadeCounter.toDouble() / gateReleaseSamples
                } else {
                    0.0 // Fully closed, zero the buffer
                }
            }

            if (fadeMultiplier == 0.0) {
                shouldZeroBuffer = true
            } else {
                // Apply fade
                for (i in 0 until samples) {
                    val rawSample = (buffer[i * 2].toInt() and 0xFF) or (buffer[i * 2 + 1].toInt() shl 8)
                    val sample = if (rawSample > 32767) rawSample - 65536 else rawSample

                    val faded = (sample * fadeMultiplier).toInt()
                    val unsigned = if (faded < 0) faded + 65536 else faded

                    buffer[i * 2] = (unsigned and 0xFF).toByte()
                    buffer[i * 2 + 1] = (unsigned shr 8).toByte()
                }
            }

            // Update fade counter
            if (gateIsOpen && gateFadeCounter < gateAttackSamples) {
                gateFadeCounter++
            } else if (!gateIsOpen && gateFadeCounter > 0) {
                gateFadeCounter--
            }
        }

        return shouldZeroBuffer
    }

    fun resetNoiseGate() {
        gateIsOpen = false
        gateFadeCounter = 0
    }


    // ==================== Click/Pop Removal (Median Filter) ====================

    /**
     * Median filter - removes impulse noise (clicks, pops, taps).
     *
     * Detects sudden amplitude spikes and replaces with median of neighbors.
     * Effective for:
     * - Phone taps/touches
     * - Mouth clicks
     * - Pocket rustling
     * - Key jingles
     */
    private val clickWindowSize = 5  // Samples to look at (must be odd)
    private val clickWindow = IntArray(clickWindowSize)
    private var clickWindowIndex = 0

    fun removeClicks(buffer: ByteArray, length: Int) {
        val samples = length / 2

        for (i in 0 until samples) {
            val rawSample = (buffer[i * 2].toInt() and 0xFF) or (buffer[i * 2 + 1].toInt() shl 8)
            val sample = if (rawSample > 32767) rawSample - 65536 else rawSample

            // Add to circular buffer
            clickWindow[clickWindowIndex] = sample
            clickWindowIndex = (clickWindowIndex + 1) % clickWindowSize

            // Calculate median of window
            val sorted = clickWindow.sorted()
            val median = sorted[clickWindowSize / 2]

            // Detect spike: if current sample is very different from median
            val diff = abs(sample - median)
            val threshold = 5000  // Spike threshold

            val output = if (diff > threshold) {
                // Likely a click/pop - use median instead
                median
            } else {
                // Normal audio - pass through
                sample
            }

            val unsigned = if (output < 0) output + 65536 else output
            buffer[i * 2] = (unsigned and 0xFF).toByte()
            buffer[i * 2 + 1] = (unsigned shr 8).toByte()
        }
    }

    fun resetClickRemoval() {
        clickWindow.fill(0)
        clickWindowIndex = 0
    }


    // ==================== Master Reset ====================

    /**
     * Reset all enhancement states (call when starting new recording)
     */
    fun resetAll() {
        resetAGC()
        resetPreEmphasis()
        resetNoiseGate()
        resetClickRemoval()
    }
}
