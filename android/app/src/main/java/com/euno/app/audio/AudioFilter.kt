package com.euno.app.audio

import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Audio bandpass filter for isolating human speech frequencies.
 *
 * Implements a 2nd-order Butterworth bandpass filter optimized for speech.
 * Default range: 80 Hz - 7000 Hz (wideband speech)
 *
 * Benefits:
 * - Removes low-frequency rumble (< 80 Hz) from handling noise, wind, etc.
 * - Removes high-frequency hiss (> 7000 Hz) from electronic noise
 * - Improves transcription accuracy by focusing on speech content
 */
class AudioFilter(
    private val sampleRate: Int = 16000,
    private val lowCutoff: Double = 80.0,   // Hz - removes rumble/handling noise
    private val highCutoff: Double = 7000.0 // Hz - removes hiss
) {
    // Filter state for high-pass (removes low frequencies)
    private var hp_x1 = 0.0
    private var hp_x2 = 0.0
    private var hp_y1 = 0.0
    private var hp_y2 = 0.0

    // Filter state for low-pass (removes high frequencies)
    private var lp_x1 = 0.0
    private var lp_x2 = 0.0
    private var lp_y1 = 0.0
    private var lp_y2 = 0.0

    // High-pass filter coefficients (removes frequencies below lowCutoff)
    private val hp_a0: Double
    private val hp_a1: Double
    private val hp_a2: Double
    private val hp_b1: Double
    private val hp_b2: Double

    // Low-pass filter coefficients (removes frequencies above highCutoff)
    private val lp_a0: Double
    private val lp_a1: Double
    private val lp_a2: Double
    private val lp_b1: Double
    private val lp_b2: Double

    init {
        // Calculate high-pass filter coefficients (2nd order Butterworth)
        val omega_hp = 2.0 * PI * lowCutoff / sampleRate
        val sn_hp = sin(omega_hp)
        val cs_hp = cos(omega_hp)
        val alpha_hp = sn_hp / (2.0 * sqrt(2.0)) // Q = 1/sqrt(2) for Butterworth

        val hp_b0 = (1.0 + cs_hp) / 2.0
        val hp_b1_temp = -(1.0 + cs_hp)
        val hp_b2_temp = (1.0 + cs_hp) / 2.0
        val hp_a0_temp = 1.0 + alpha_hp
        val hp_a1_temp = -2.0 * cs_hp
        val hp_a2_temp = 1.0 - alpha_hp

        // Normalize
        hp_a0 = hp_b0 / hp_a0_temp
        hp_a1 = hp_b1_temp / hp_a0_temp
        hp_a2 = hp_b2_temp / hp_a0_temp
        hp_b1 = hp_a1_temp / hp_a0_temp
        hp_b2 = hp_a2_temp / hp_a0_temp

        // Calculate low-pass filter coefficients (2nd order Butterworth)
        val omega_lp = 2.0 * PI * highCutoff / sampleRate
        val sn_lp = sin(omega_lp)
        val cs_lp = cos(omega_lp)
        val alpha_lp = sn_lp / (2.0 * sqrt(2.0)) // Q = 1/sqrt(2) for Butterworth

        val lp_b0 = (1.0 - cs_lp) / 2.0
        val lp_b1_temp = 1.0 - cs_lp
        val lp_b2_temp = (1.0 - cs_lp) / 2.0
        val lp_a0_temp = 1.0 + alpha_lp
        val lp_a1_temp = -2.0 * cs_lp
        val lp_a2_temp = 1.0 - alpha_lp

        // Normalize
        lp_a0 = lp_b0 / lp_a0_temp
        lp_a1 = lp_b1_temp / lp_a0_temp
        lp_a2 = lp_b2_temp / lp_a0_temp
        lp_b1 = lp_a1_temp / lp_a0_temp
        lp_b2 = lp_a2_temp / lp_a0_temp
    }

    /**
     * Filter a 16-bit PCM audio buffer in-place.
     * Applies bandpass filter to isolate speech frequencies.
     *
     * @param buffer 16-bit PCM samples (little-endian)
     * @param length Number of bytes to process
     */
    fun filterBuffer(buffer: ByteArray, length: Int) {
        val samples = length / 2 // 16-bit = 2 bytes per sample

        for (i in 0 until samples) {
            // Read 16-bit sample (little-endian)
            val rawSample = (buffer[i * 2].toInt() and 0xFF) or (buffer[i * 2 + 1].toInt() shl 8)
            val sample = if (rawSample > 32767) rawSample - 65536 else rawSample

            // Convert to normalized double (-1.0 to 1.0)
            var x = sample.toDouble() / 32768.0

            // Apply high-pass filter (removes low frequencies)
            val hp_y = hp_a0 * x + hp_a1 * hp_x1 + hp_a2 * hp_x2 - hp_b1 * hp_y1 - hp_b2 * hp_y2
            hp_x2 = hp_x1
            hp_x1 = x
            hp_y2 = hp_y1
            hp_y1 = hp_y

            // Apply low-pass filter to high-pass output (creates bandpass)
            x = hp_y
            val lp_y = lp_a0 * x + lp_a1 * lp_x1 + lp_a2 * lp_x2 - lp_b1 * lp_y1 - lp_b2 * lp_y2
            lp_x2 = lp_x1
            lp_x1 = x
            lp_y2 = lp_y1
            lp_y1 = lp_y

            // Convert back to 16-bit PCM
            val filtered = (lp_y * 32768.0).toInt().coerceIn(-32768, 32767)
            val unsigned = if (filtered < 0) filtered + 65536 else filtered

            // Write back to buffer (little-endian)
            buffer[i * 2] = (unsigned and 0xFF).toByte()
            buffer[i * 2 + 1] = (unsigned shr 8).toByte()
        }
    }

    /**
     * Reset filter state (call when starting new recording)
     */
    fun reset() {
        hp_x1 = 0.0
        hp_x2 = 0.0
        hp_y1 = 0.0
        hp_y2 = 0.0
        lp_x1 = 0.0
        lp_x2 = 0.0
        lp_y1 = 0.0
        lp_y2 = 0.0
    }
}
