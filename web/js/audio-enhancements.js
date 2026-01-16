// Audio Enhancements for Web - DSP processing using Web Audio API
// Matches Android implementation: bandpass filter, AGC, pre-emphasis, noise gate, click removal

class AudioEnhancementsProcessor extends AudioWorkletProcessor {
    constructor() {
        super();

        // Sample rate (will be set by AudioContext, typically 48000)
        this.sampleRate = sampleRate;

        // Bandpass filter state (80 Hz - 7000 Hz)
        this.initBandpassFilter();

        // AGC state
        this.agcCurrentGain = 1.0;
        this.agcTarget = 0.25; // Target RMS (25% of max)
        this.agcAttack = 0.001;
        this.agcRelease = 0.0001;
        this.agcMaxGain = 8.0;
        this.agcMinGain = 0.5;

        // Pre-emphasis state
        this.preEmphasisPrevSample = 0;
        this.preEmphasisCoeff = 0.97;

        // Noise gate state
        this.gateIsOpen = false;
        this.gateOpenThreshold = 0.02;  // Normalized (0-1)
        this.gateCloseThreshold = 0.01;
        this.gateFadeCounter = 0;
        this.gateAttackSamples = 10;
        this.gateReleaseSamples = 50;

        // Click removal state (median filter)
        this.clickWindowSize = 5;
        this.clickWindow = new Float32Array(this.clickWindowSize);
        this.clickWindowIndex = 0;
    }

    initBandpassFilter() {
        const lowCutoff = 80.0;
        const highCutoff = 7000.0;

        // High-pass filter coefficients (removes < 80 Hz)
        const omega_hp = 2.0 * Math.PI * lowCutoff / this.sampleRate;
        const sn_hp = Math.sin(omega_hp);
        const cs_hp = Math.cos(omega_hp);
        const alpha_hp = sn_hp / (2.0 * Math.sqrt(2.0));

        const hp_b0 = (1.0 + cs_hp) / 2.0;
        const hp_b1 = -(1.0 + cs_hp);
        const hp_b2 = (1.0 + cs_hp) / 2.0;
        const hp_a0 = 1.0 + alpha_hp;
        const hp_a1 = -2.0 * cs_hp;
        const hp_a2 = 1.0 - alpha_hp;

        this.hp_a0 = hp_b0 / hp_a0;
        this.hp_a1 = hp_b1 / hp_a0;
        this.hp_a2 = hp_b2 / hp_a0;
        this.hp_b1 = hp_a1 / hp_a0;
        this.hp_b2 = hp_a2 / hp_a0;

        // Low-pass filter coefficients (removes > 7000 Hz)
        const omega_lp = 2.0 * Math.PI * highCutoff / this.sampleRate;
        const sn_lp = Math.sin(omega_lp);
        const cs_lp = Math.cos(omega_lp);
        const alpha_lp = sn_lp / (2.0 * Math.sqrt(2.0));

        const lp_b0 = (1.0 - cs_lp) / 2.0;
        const lp_b1 = 1.0 - cs_lp;
        const lp_b2 = (1.0 - cs_lp) / 2.0;
        const lp_a0 = 1.0 + alpha_lp;
        const lp_a1 = -2.0 * cs_lp;
        const lp_a2 = 1.0 - alpha_lp;

        this.lp_a0 = lp_b0 / lp_a0;
        this.lp_a1 = lp_b1 / lp_a0;
        this.lp_a2 = lp_b2 / lp_a0;
        this.lp_b1 = lp_a1 / lp_a0;
        this.lp_b2 = lp_a2 / lp_a0;

        // Filter state
        this.hp_x1 = 0; this.hp_x2 = 0;
        this.hp_y1 = 0; this.hp_y2 = 0;
        this.lp_x1 = 0; this.lp_x2 = 0;
        this.lp_y1 = 0; this.lp_y2 = 0;
    }

    process(inputs, outputs) {
        const input = inputs[0];
        const output = outputs[0];

        if (!input || !input[0]) return true;

        const inputChannel = input[0];
        const outputChannel = output[0];
        const blockSize = inputChannel.length;

        // Process each sample
        for (let i = 0; i < blockSize; i++) {
            let sample = inputChannel[i];

            // 1. Bandpass filter (80 Hz - 7000 Hz)
            sample = this.applyBandpassFilter(sample);

            // 2. Click/pop removal
            sample = this.removeClick(sample);

            // 3. Noise gate
            const gateMultiplier = this.applyNoiseGate(sample);
            sample *= gateMultiplier;

            // 4. Pre-emphasis (if gate is open)
            if (gateMultiplier > 0.1) {
                sample = this.applyPreEmphasis(sample);
            }

            outputChannel[i] = sample;
        }

        // 5. AGC on the whole block (after other processing)
        this.applyAGC(outputChannel, blockSize);

        return true;
    }

    applyBandpassFilter(sample) {
        // High-pass filter
        const hp_y = this.hp_a0 * sample + this.hp_a1 * this.hp_x1 + this.hp_a2 * this.hp_x2
                    - this.hp_b1 * this.hp_y1 - this.hp_b2 * this.hp_y2;
        this.hp_x2 = this.hp_x1;
        this.hp_x1 = sample;
        this.hp_y2 = this.hp_y1;
        this.hp_y1 = hp_y;

        // Low-pass filter (creates bandpass)
        const lp_y = this.lp_a0 * hp_y + this.lp_a1 * this.lp_x1 + this.lp_a2 * this.lp_x2
                    - this.lp_b1 * this.lp_y1 - this.lp_b2 * this.lp_y2;
        this.lp_x2 = this.lp_x1;
        this.lp_x1 = hp_y;
        this.lp_y2 = this.lp_y1;
        this.lp_y1 = lp_y;

        return lp_y;
    }

    removeClick(sample) {
        // Add to circular buffer
        this.clickWindow[this.clickWindowIndex] = sample;
        this.clickWindowIndex = (this.clickWindowIndex + 1) % this.clickWindowSize;

        // Calculate median
        const sorted = Array.from(this.clickWindow).sort((a, b) => a - b);
        const median = sorted[Math.floor(this.clickWindowSize / 2)];

        // Detect spike
        const diff = Math.abs(sample - median);
        const threshold = 0.3; // Normalized

        return diff > threshold ? median : sample;
    }

    applyNoiseGate(sample) {
        const amplitude = Math.abs(sample);

        // Hysteresis
        const shouldBeOpen = this.gateIsOpen
            ? amplitude > this.gateCloseThreshold
            : amplitude > this.gateOpenThreshold;

        // Update gate state
        if (shouldBeOpen && !this.gateIsOpen) {
            this.gateIsOpen = true;
            this.gateFadeCounter = 0;
        } else if (!shouldBeOpen && this.gateIsOpen) {
            this.gateIsOpen = false;
            this.gateFadeCounter = this.gateReleaseSamples;
        }

        // Calculate fade multiplier
        let multiplier = 1.0;
        if (!this.gateIsOpen || this.gateFadeCounter > 0) {
            if (this.gateIsOpen) {
                // Fading in
                multiplier = Math.min(1.0, this.gateFadeCounter / this.gateAttackSamples);
                if (this.gateFadeCounter < this.gateAttackSamples) {
                    this.gateFadeCounter++;
                }
            } else {
                // Fading out or closed
                multiplier = this.gateFadeCounter > 0
                    ? this.gateFadeCounter / this.gateReleaseSamples
                    : 0.0;
                if (this.gateFadeCounter > 0) {
                    this.gateFadeCounter--;
                }
            }
        }

        return multiplier;
    }

    applyPreEmphasis(sample) {
        const emphasized = sample - this.preEmphasisCoeff * this.preEmphasisPrevSample;
        this.preEmphasisPrevSample = sample;
        return Math.max(-1.0, Math.min(1.0, emphasized));
    }

    applyAGC(buffer, length) {
        // Calculate RMS
        let sumSquares = 0;
        for (let i = 0; i < length; i++) {
            sumSquares += buffer[i] * buffer[i];
        }
        const rms = Math.sqrt(sumSquares / length);

        // Calculate desired gain
        const desiredGain = rms > 0 ? this.agcTarget / rms : 1.0;

        // Smooth gain changes
        if (desiredGain < this.agcCurrentGain) {
            // Attack
            this.agcCurrentGain += (desiredGain - this.agcCurrentGain) * this.agcAttack;
        } else {
            // Release
            this.agcCurrentGain += (desiredGain - this.agcCurrentGain) * this.agcRelease;
        }

        // Clamp gain
        this.agcCurrentGain = Math.max(this.agcMinGain,
                                       Math.min(this.agcMaxGain, this.agcCurrentGain));

        // Apply gain
        for (let i = 0; i < length; i++) {
            buffer[i] = Math.max(-1.0, Math.min(1.0, buffer[i] * this.agcCurrentGain));
        }
    }
}

registerProcessor('audio-enhancements-processor', AudioEnhancementsProcessor);
