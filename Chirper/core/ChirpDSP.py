import math
from numbers import Integral, Real

import numpy as np

from ..io import ChirpAudioData
from . import ChirpKernels, Easing
from .ChirpOscillator import ChirpOscillator
from .ChirpTone import PerformanceFrequency


class ChirpDSP:
    SAMPLE_RATE = 44100
    BITS_PER_SAMPLE = 16
    MAX_AUTO_DELAY_TAIL_SECONDS = 30.0

    def __init__(self, channels = 2):
        if isinstance(channels, bool) or not isinstance(channels, Integral) or channels not in (1, 2):
            raise ValueError("ChirpDSP only supports 1 or 2 channels")

        self.channels = int(channels)
        self.oscillator = ChirpOscillator(sampleRate = self.SAMPLE_RATE)

    @staticmethod
    def ValidateNumber(value, name):
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(name + " must be numeric")
        value = float(value)
        if not math.isfinite(value):
            raise ValueError(name + " must be finite")
        return value

    @classmethod
    def ValidateInteger(cls, value, name):
        if isinstance(value, bool) or not isinstance(value, Integral):
            raise TypeError(name + " must be an integer")
        return int(value)

# -----------------------------------
# PCM Conversion
# -----------------------------------

    def SamplesToBytes(self, samples):
        return ChirpAudioData.SamplesToPcm(samples, self.channels)

    def BytesToSamples(self, sampleBytes):
        return ChirpAudioData.PcmToSamples(sampleBytes, self.channels)

    def PrepareSamples(self, soundData):
        if isinstance(soundData, (bytes, bytearray, memoryview)):
            samples = self.BytesToSamples(soundData)
            returnBytes = True
        else:
            samples = np.asarray(soundData, dtype = np.float64).reshape(-1)
            returnBytes = False

        if len(samples) % self.channels != 0:
            raise ValueError("Samples do not contain complete frames")
        if not np.all(np.isfinite(samples)):
            raise ValueError("Samples must contain only finite values")

        return samples.copy(), returnBytes

    def FinishSamples(self, samples, returnBytes):
        samples = np.asarray(samples, dtype = np.float64).reshape(-1)
        if not np.all(np.isfinite(samples)):
            raise ValueError("Samples must contain only finite values")

        if returnBytes:
            return self.SamplesToBytes(samples)

        return samples

    def CopySoundData(self, soundData):
        if isinstance(soundData, (bytes, bytearray, memoryview)):
            ChirpAudioData.ValidatePcm(soundData, self.channels, self.BITS_PER_SAMPLE)
            return bytes(soundData)

        samples = np.asarray(soundData, dtype = np.float64).reshape(-1)
        if len(samples) % self.channels != 0:
            raise ValueError("Samples do not contain complete frames")
        if not np.all(np.isfinite(samples)):
            raise ValueError("Samples must contain only finite values")

        return samples.copy()

    def GetSampleDuration(self, samples):
        ChirpAudioData.ValidateSamples(samples, self.channels)
        return ChirpAudioData.GetSampleDuration(
            samples, self.channels, self.SAMPLE_RATE
        )

    def GetEasingValues(
            self, count, easing = "linear", offset = 0, valueCount = None
        ):
        count = self.ValidateInteger(count, "count")
        if count <= 0:
            return np.empty(0, dtype = np.float64)

        offset = max(0, self.ValidateInteger(offset, "offset"))
        offset = min(count, offset)
        if valueCount is None:
            valueCount = count - offset
        else:
            valueCount = max(0, self.ValidateInteger(valueCount, "valueCount"))
            valueCount = min(valueCount, count - offset)
        if valueCount <= 0:
            return np.empty(0, dtype = np.float64)

        if count == 1:
            percentages = np.zeros(valueCount, dtype = np.float64)
        else:
            step = 1.0 / (count - 1)
            percentages = np.arange(
                offset, offset + valueCount, dtype = np.float64
            ) * step
            if offset + valueCount == count:
                percentages[-1] = 1.0
        if not callable(easing):
            easingKey = str(easing).replace("_", "").replace("-", "").lower()
            if easing is None or easingKey in ("linear", "lin"):
                return percentages

        easingFunction = Easing.Resolve(easing)
        return np.fromiter(
            (Easing.ApplyResolved(percent, easingFunction) for percent in percentages),
            dtype = np.float64,
            count = valueCount
        )

    def GetScopedFadeGains(
            self, frameCount, totalFrames, offsetFrames = 0,
            fadeInFrames = 0, fadeInEasing = "linear",
            fadeOutFrames = 0, fadeOutEasing = "linear"
            ):
        frameCount = max(0, self.ValidateInteger(frameCount, "frameCount"))
        totalFrames = max(0, self.ValidateInteger(totalFrames, "totalFrames"))
        offsetFrames = max(0, self.ValidateInteger(offsetFrames, "offsetFrames"))
        fadeInFrames = min(
            totalFrames, max(0, self.ValidateInteger(fadeInFrames, "fadeInFrames"))
        )
        fadeOutFrames = min(
            totalFrames, max(0, self.ValidateInteger(fadeOutFrames, "fadeOutFrames"))
        )
        gains = np.ones(frameCount, dtype = np.float64)
        sliceEnd = offsetFrames + frameCount

        fadeInEnd = min(sliceEnd, fadeInFrames)
        if offsetFrames < fadeInEnd:
            fadeInCount = fadeInEnd - offsetFrames
            gains[:fadeInCount] *= self.GetEasingValues(
                fadeInFrames, fadeInEasing, offsetFrames, fadeInCount
            )

        if fadeOutFrames > 0:
            fadeOutStart = totalFrames - fadeOutFrames
            fadeStart = max(offsetFrames, fadeOutStart)
            fadeEnd = min(sliceEnd, totalFrames)
            if fadeStart < fadeEnd:
                localStart = fadeStart - offsetFrames
                fadeCount = fadeEnd - fadeStart
                if fadeOutFrames == 1:
                    fadeOutGains = np.zeros(1, dtype = np.float64)
                else:
                    fadeOutGains = 1.0 - self.GetEasingValues(
                        fadeOutFrames, fadeOutEasing,
                        fadeStart - fadeOutStart, fadeCount
                    )
                gains[localStart:localStart + fadeCount] *= fadeOutGains

            if sliceEnd > totalFrames:
                tailStart = max(0, totalFrames - offsetFrames)
                gains[tailStart:] = 0.0

        return gains

    def GetModulationValues(self, wave, rate, frameCount, phaseOffsets):
        rate = self.ValidateNumber(rate, "rate")
        frameCount = self.ValidateInteger(frameCount, "frameCount")
        wave = self.oscillator.GetWave(wave)
        modulation = np.empty((len(phaseOffsets), frameCount), dtype = np.float64)

        for index, phaseDegrees in enumerate(phaseOffsets):
            values = self.oscillator.RenderWave(wave, rate, frameCount, phaseDegrees)
            modulation[index] = np.clip(values, -1.0, 1.0)

        return modulation

# -----------------------------------
# Mix Controls
# -----------------------------------

    def MixSamples(self, sampleArrays, mixGain = 0.707):
        mixGain = self.ValidateNumber(mixGain, "mixGain")
        sampleArrays = [np.asarray(samples, dtype = np.float64).reshape(-1) for samples in sampleArrays]
        if len(sampleArrays) == 0:
            raise ValueError("Cannot mix an empty sample list")
        if any(len(samples) % self.channels != 0 for samples in sampleArrays):
            raise ValueError("Samples do not contain complete frames")
        if any(not np.all(np.isfinite(samples)) for samples in sampleArrays):
            raise ValueError("Samples must contain only finite values")

        sampleCount = max(len(samples) for samples in sampleArrays)
        mixedSamples = np.zeros(sampleCount, dtype = np.float64)
        for samples in sampleArrays:
            mixedSamples[:len(samples)] += samples
        mixedSamples *= mixGain

        return mixedSamples

    def ApplySoundAppend(self, soundData, appendedData, crossfade = 0.0, easing = "equalPower"):
        crossfade = self.ValidateNumber(crossfade, "crossfade")

        if callable(easing):
            raise TypeError("Crossfade easing must be 'linear' or 'equalPower'")
        easingKey = str(easing).replace("_", "").replace("-", "").lower()
        if easingKey not in ("linear", "equalpower"):
            raise ValueError("Crossfade easing must be 'linear' or 'equalPower'")
        easing = easingKey

        firstSamples, returnBytes = self.PrepareSamples(soundData)
        secondSamples, _ = self.PrepareSamples(appendedData)

        firstFrames = len(firstSamples) // self.channels
        secondFrames = len(secondSamples) // self.channels
        crossfadeFrames = max(0, int(self.SAMPLE_RATE * crossfade))
        crossfadeFrames = min(crossfadeFrames, firstFrames, secondFrames)

        if crossfadeFrames == 0:
            return self.FinishSamples(
                np.concatenate((firstSamples, secondSamples)), returnBytes
            )

        if crossfadeFrames == 1:
            incomingGains = np.array([Easing.Apply(0.5, easing)], dtype = np.float64)
            outgoingGains = incomingGains.copy()
        else:
            incomingGains = self.GetEasingValues(crossfadeFrames, easing)
            outgoingGains = incomingGains[::-1]

        overlapSamples = crossfadeFrames * self.channels
        overlap = (
            firstSamples[-overlapSamples:] * np.repeat(outgoingGains, self.channels)
        ) + (
            secondSamples[:overlapSamples] * np.repeat(incomingGains, self.channels)
        )
        appended = np.concatenate((
            firstSamples[:-overlapSamples],
            overlap,
            secondSamples[overlapSamples:]
        ))
        return self.FinishSamples(appended, returnBytes)

    def ApplySoundGain(self, soundData, gain = 1.0, offset = 0.0):
        gain = self.ValidateNumber(gain, "gain")
        offset = self.ValidateNumber(offset, "offset")
        if gain == 1.0 and offset == 0.0:
            return self.CopySoundData(soundData)

        samples, returnBytes = self.PrepareSamples(soundData)
        samples = (samples * gain) + offset
        return self.FinishSamples(samples, returnBytes)

    def ApplySoundDebias(self, soundData):
        samples, returnBytes = self.PrepareSamples(soundData)
        if samples.size == 0:
            return self.FinishSamples(samples, returnBytes)

        frames = samples.reshape(-1, self.channels)
        frames -= np.mean(frames, axis = 0)
        return self.FinishSamples(samples, returnBytes)

    def ApplySoundClip(self, soundData, limit = 1.0):
        limit = self.ValidateNumber(limit, "limit")
        limit = max(0.0, limit)
        samples, returnBytes = self.PrepareSamples(soundData)
        samples = np.clip(samples, -limit, limit)
        return self.FinishSamples(samples, returnBytes)

    def ApplySoundSoftClip(self, soundData, drive = 2.0, mix = 1.0):
        drive = self.ValidateNumber(drive, "drive")
        mix = self.ValidateNumber(mix, "mix")
        drive = max(0.0001, drive)
        mix = max(0.0, min(1.0, mix))

        if mix == 0.0:
            return self.CopySoundData(soundData)

        normalizer = math.tanh(drive)
        samples, returnBytes = self.PrepareSamples(soundData)
        wet = np.tanh(samples * drive) / normalizer
        wet = np.clip(wet, -1.0, 1.0)
        mixed = (samples * (1.0 - mix)) + (wet * mix)
        return self.FinishSamples(mixed, returnBytes)

    def ApplySoundRing(self, soundData, freq, mix = 1.0, wave = "Sine"):
        freq = self.ValidateNumber(freq, "freq")
        mix = self.ValidateNumber(mix, "mix")
        freq = max(0.0, freq)
        mix = max(0.0, min(1.0, mix))

        if freq == 0.0 or mix == 0.0:
            return self.CopySoundData(soundData)

        samples, returnBytes = self.PrepareSamples(soundData)
        frameCount = len(samples) // self.channels
        carrier = self.oscillator.RenderWave(wave, freq, frameCount)
        carrier = np.repeat(carrier, self.channels)
        ringed = samples * ((1.0 - mix) + (carrier * mix))
        return self.FinishSamples(ringed, returnBytes)

    def ApplySoundChorus(
            self, soundData, rate = 0.8, depth = 0.003, delay = 0.015,
            voices = 2, feedback = 0.0, spread = 1.0, mix = 0.5, wave = "Sine"
            ):
        rate = self.ValidateNumber(rate, "rate")
        depth = self.ValidateNumber(depth, "depth")
        delay = self.ValidateNumber(delay, "delay")
        voices = self.ValidateInteger(voices, "voices")
        feedback = self.ValidateNumber(feedback, "feedback")
        spread = self.ValidateNumber(spread, "spread")
        mix = self.ValidateNumber(mix, "mix")
        rate = max(0.0, rate)
        delay = max(1.0 / self.SAMPLE_RATE, delay)
        depth = max(0.0, min(depth, delay - (1.0 / self.SAMPLE_RATE)))
        voices = max(1, voices)
        feedback = max(-0.95, min(0.95, feedback))
        spread = max(0.0, min(1.0, spread))
        mix = max(0.0, min(1.0, mix))

        if mix == 0.0:
            return self.CopySoundData(soundData)

        samples, returnBytes = self.PrepareSamples(soundData)
        frameCount = len(samples) // self.channels
        phaseOffsets = []
        for channel in range(self.channels):
            channelPhase = channel * 180.0 * spread
            for voiceIndex in range(voices):
                voicePhase = (voiceIndex / voices) * 180.0 * spread
                phaseOffsets.append(channelPhase + voicePhase)

        modulation = self.GetModulationValues(wave, rate, frameCount, phaseOffsets)
        modulation = modulation.reshape(self.channels, voices, frameCount)
        processor = ChirpKernels.CompiledChorus if ChirpKernels.NUMBA_ENABLED else ChirpKernels.ProcessChorus
        chorused = processor(
            samples,
            self.channels,
            modulation,
            delay * self.SAMPLE_RATE,
            depth * self.SAMPLE_RATE,
            feedback,
            mix
        )
        return self.FinishSamples(chorused, returnBytes)

    def ApplySoundPhaser(
            self, soundData, rate = 0.5, minFreq = 300.0, maxFreq = 1600.0,
            stages = 6, feedback = 0.2, spread = 1.0, mix = 0.5, wave = "Sine"
            ):
        rate = self.ValidateNumber(rate, "rate")
        minFreq = self.ValidateNumber(minFreq, "minFreq")
        maxFreq = self.ValidateNumber(maxFreq, "maxFreq")
        stages = self.ValidateInteger(stages, "stages")
        feedback = self.ValidateNumber(feedback, "feedback")
        spread = self.ValidateNumber(spread, "spread")
        mix = self.ValidateNumber(mix, "mix")
        rate = max(0.0, rate)
        minFreq = max(1.0, min(self.SAMPLE_RATE * 0.49, minFreq))
        maxFreq = max(1.0, min(self.SAMPLE_RATE * 0.49, maxFreq))
        if minFreq > maxFreq:
            minFreq, maxFreq = maxFreq, minFreq
        stages = max(1, stages)
        feedback = max(-0.95, min(0.95, feedback))
        spread = max(0.0, min(1.0, spread))
        mix = max(0.0, min(1.0, mix))

        if mix == 0.0:
            return self.CopySoundData(soundData)

        samples, returnBytes = self.PrepareSamples(soundData)
        frameCount = len(samples) // self.channels
        phaseOffsets = [channel * 180.0 * spread for channel in range(self.channels)]
        modulation = self.GetModulationValues(wave, rate, frameCount, phaseOffsets)
        processor = ChirpKernels.CompiledPhaser if ChirpKernels.NUMBA_ENABLED else ChirpKernels.ProcessPhaser
        phased = processor(
            samples,
            self.channels,
            modulation,
            minFreq,
            maxFreq,
            stages,
            feedback,
            mix,
            self.SAMPLE_RATE
        )
        return self.FinishSamples(phased, returnBytes)

    def ApplySoundCut(self, soundData, duration, fade = 0.003):
        duration = self.ValidateNumber(duration, "duration")
        fade = self.ValidateNumber(fade, "fade")
        duration = max(0.0, duration)
        fade = max(0.0, fade)
        samples, returnBytes = self.PrepareSamples(soundData)
        targetSamples = int(self.SAMPLE_RATE * duration) * self.channels
        targetSamples = min(len(samples), targetSamples)

        if targetSamples <= 0:
            return self.FinishSamples(np.empty(0, dtype = np.float64), returnBytes)

        cutSamples = samples[:targetSamples].copy()
        fadeSamples = min(int(self.SAMPLE_RATE * fade) * self.channels, len(cutSamples))
        fadeFrames = fadeSamples // self.channels

        if fadeFrames > 0:
            fadeStart = len(cutSamples) - (fadeFrames * self.channels)
            if fadeFrames == 1:
                gains = np.zeros(1, dtype = np.float64)
            else:
                gains = np.linspace(1.0, 0.0, fadeFrames, dtype = np.float64)
            cutSamples[fadeStart:] *= np.repeat(gains, self.channels)

        return self.FinishSamples(cutSamples, returnBytes)

    def ApplySoundFadeIn(self, soundData, duration, easing = "linear"):
        duration = self.ValidateNumber(duration, "duration")
        duration = max(0.0, duration)
        samples, returnBytes = self.PrepareSamples(soundData)
        fadeFrames = min(int(self.SAMPLE_RATE * duration), len(samples) // self.channels)

        if fadeFrames <= 0:
            return self.FinishSamples(samples, returnBytes)

        gains = self.GetEasingValues(fadeFrames, easing)
        samples[:fadeFrames * self.channels] *= np.repeat(gains, self.channels)
        return self.FinishSamples(samples, returnBytes)

    def ApplySoundFadeOut(self, soundData, duration, easing = "linear"):
        duration = self.ValidateNumber(duration, "duration")
        duration = max(0.0, duration)
        samples, returnBytes = self.PrepareSamples(soundData)
        totalFrames = len(samples) // self.channels
        fadeFrames = min(int(self.SAMPLE_RATE * duration), totalFrames)

        if fadeFrames <= 0:
            return self.FinishSamples(samples, returnBytes)

        fadeStart = (totalFrames - fadeFrames) * self.channels
        if fadeFrames == 1:
            gains = np.zeros(1, dtype = np.float64)
        else:
            gains = 1.0 - self.GetEasingValues(fadeFrames, easing)
        samples[fadeStart:] *= np.repeat(gains, self.channels)
        return self.FinishSamples(samples, returnBytes)

    def ApplySoundReverse(self, soundData):
        samples, returnBytes = self.PrepareSamples(soundData)
        frames = samples.reshape(-1, self.channels)
        reversedSamples = frames[::-1].reshape(-1).copy()
        return self.FinishSamples(reversedSamples, returnBytes)

    def GetPanGains(self, pan):
        return ChirpAudioData.GetPanGains(pan)

    def ApplySoundPan(self, soundData, pan):
        pan = self.ValidateNumber(pan, "pan")
        if self.channels == 1 or pan == 0.0:
            return self.CopySoundData(soundData)

        samples, returnBytes = self.PrepareSamples(soundData)
        pan = max(-1.0, min(1.0, pan))
        frames = samples.reshape(-1, 2)
        left = frames[:, 0].copy()
        right = frames[:, 1].copy()

        if pan > 0.0:
            leftGain, rightGain = self.GetPanGains(-1.0 + (pan * 2.0))
            frames[:, 0] = left * leftGain
            frames[:, 1] = (left * rightGain) + right
        else:
            leftGain, rightGain = self.GetPanGains(1.0 + (pan * 2.0))
            frames[:, 0] = left + (right * leftGain)
            frames[:, 1] = right * rightGain

        return self.FinishSamples(samples, returnBytes)

    def ApplySoundAutoPan(
            self, soundData, depth = 1.0, rate = 1.0, wave = "Sine",
            offset = 0.0, center = 0.0
            ):
        depth = self.ValidateNumber(depth, "depth")
        rate = self.ValidateNumber(rate, "rate")
        offset = self.ValidateNumber(offset, "offset")
        center = self.ValidateNumber(center, "center")
        depth = max(0.0, min(1.0, depth))
        rate = max(0.0, rate)
        center = max(-1.0, min(1.0, center))
        samples, returnBytes = self.PrepareSamples(soundData)
        frameCount = len(samples) // self.channels
        modulation = self.GetModulationValues(wave, rate, frameCount, [offset])[0]
        pan = np.clip(center + (modulation * depth), -1.0, 1.0)

        if self.channels == 1:
            angles = (pan + 1.0) * (math.pi * 0.25)
            stereo = np.empty(frameCount * 2, dtype = np.float64)
            stereo[0::2] = samples * np.cos(angles)
            stereo[1::2] = samples * np.sin(angles)
            return self.FinishSamples(stereo, returnBytes)

        frames = samples.reshape(-1, 2)
        left = frames[:, 0].copy()
        right = frames[:, 1].copy()
        rightward = pan > 0.0
        leftward = pan < 0.0

        rightAngles = pan[rightward] * (math.pi * 0.5)
        frames[rightward, 0] = left[rightward] * np.cos(rightAngles)
        frames[rightward, 1] = right[rightward] + (left[rightward] * np.sin(rightAngles))

        leftAngles = (pan[leftward] + 1.0) * (math.pi * 0.5)
        frames[leftward, 0] = left[leftward] + (right[leftward] * np.cos(leftAngles))
        frames[leftward, 1] = right[leftward] * np.sin(leftAngles)

        return self.FinishSamples(samples, returnBytes)

    def ApplySoundMono(self, soundData):
        if self.channels == 1:
            return self.CopySoundData(soundData)

        samples, returnBytes = self.PrepareSamples(soundData)
        mono = ChirpAudioData.ConvertChannels(samples, self.channels, 1)
        if returnBytes:
            return ChirpAudioData.SamplesToPcm(mono, 1)
        return mono

    def ApplySoundStereo(self, soundData, pan = 0.0):
        pan = self.ValidateNumber(pan, "pan")
        if self.channels == 2:
            return self.CopySoundData(soundData)

        samples, returnBytes = self.PrepareSamples(soundData)
        stereo = ChirpAudioData.ConvertChannels(
            samples, self.channels, 2, pan
        )
        if returnBytes:
            return ChirpAudioData.SamplesToPcm(stereo, 2)
        return stereo

    def NormalizeSamples(self, samples, headroom = 0.0):
        headroom = self.ValidateNumber(headroom, "headroom")
        samples = np.asarray(samples, dtype = np.float64).reshape(-1)
        if len(samples) % self.channels != 0:
            raise ValueError("Samples do not contain complete frames")
        if not np.all(np.isfinite(samples)):
            raise ValueError("Samples must contain only finite values")
        if samples.size == 0:
            return samples.copy()

        peak = float(np.max(np.abs(samples)))

        if peak <= 0.0:
            return samples.copy()

        headroom = max(0.0, headroom)
        targetPeak = 10.0 ** (-headroom / 20.0)
        gain = targetPeak / peak
        return samples * gain

# -----------------------------------
# EQ
# -----------------------------------

    def GetBiquadSetup(self, freq, q):
        freq = self.ValidateNumber(freq, "freq")
        q = self.ValidateNumber(q, "q")
        freq = max(1.0, min(self.SAMPLE_RATE * 0.499, freq))
        q = max(0.0001, q)
        omega = 2.0 * math.pi * freq / self.SAMPLE_RATE
        sinOmega = math.sin(omega)
        cosOmega = math.cos(omega)
        alpha = sinOmega / (2.0 * q)
        return cosOmega, alpha

    def NormalizeBiquad(self, b0, b1, b2, a0, a1, a2):
        coefficients = (b0, b1, b2, a0, a1, a2)
        if not all(math.isfinite(value) for value in coefficients) or abs(a0) < 0.0000001:
            raise ValueError("Invalid biquad coefficients")

        return b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0

    def _PreserveSilentFilterEnd(self, source, filtered):
        frameCount = len(source) // self.channels
        if frameCount == 0 or not np.all(source[-self.channels:] == 0.0):
            return filtered
        if np.all(filtered[-self.channels:] == 0.0):
            return filtered

        fadeFrames = min(int(self.SAMPLE_RATE * 0.003), frameCount)
        gains = np.zeros(1, dtype = np.float64) if fadeFrames == 1 else np.linspace(
            1.0, 0.0, fadeFrames, dtype = np.float64
        )
        filtered[-fadeFrames * self.channels:] *= np.repeat(gains, self.channels)
        return filtered

    def GetBiquadAmplitude(self, db):
        try:
            amplitude = 10.0 ** (db / 40.0)
        except OverflowError as error:
            raise ValueError("db produces invalid biquad coefficients") from error
        if not math.isfinite(amplitude) or amplitude <= 0.0:
            raise ValueError("db produces invalid biquad coefficients")
        return amplitude

    def ApplySoundLowPass(self, soundData, freq, q = 0.707):
        if isinstance(freq, PerformanceFrequency):
            return self._ApplySoundBiquadTrack(soundData, "lowPass", freq, q = q)
        cosOmega, alpha = self.GetBiquadSetup(freq, q)
        b0 = (1.0 - cosOmega) * 0.5
        b1 = 1.0 - cosOmega
        b2 = (1.0 - cosOmega) * 0.5
        a0 = 1.0 + alpha
        a1 = -2.0 * cosOmega
        a2 = 1.0 - alpha
        return self.ApplySoundBiquad(soundData, self.NormalizeBiquad(b0, b1, b2, a0, a1, a2))

    def ApplySoundHighPass(self, soundData, freq, q = 0.707):
        if isinstance(freq, PerformanceFrequency):
            return self._ApplySoundBiquadTrack(soundData, "highPass", freq, q = q)
        cosOmega, alpha = self.GetBiquadSetup(freq, q)
        b0 = (1.0 + cosOmega) * 0.5
        b1 = -(1.0 + cosOmega)
        b2 = (1.0 + cosOmega) * 0.5
        a0 = 1.0 + alpha
        a1 = -2.0 * cosOmega
        a2 = 1.0 - alpha
        return self.ApplySoundBiquad(soundData, self.NormalizeBiquad(b0, b1, b2, a0, a1, a2))

    def ApplySoundBandPass(self, soundData, freq, q = 0.707):
        if isinstance(freq, PerformanceFrequency):
            return self._ApplySoundBiquadTrack(soundData, "bandPass", freq, q = q)
        cosOmega, alpha = self.GetBiquadSetup(freq, q)
        b0 = alpha
        b1 = 0.0
        b2 = -alpha
        a0 = 1.0 + alpha
        a1 = -2.0 * cosOmega
        a2 = 1.0 - alpha
        return self.ApplySoundBiquad(soundData, self.NormalizeBiquad(b0, b1, b2, a0, a1, a2))

    def ApplySoundNotch(self, soundData, freq, q = 0.707):
        if isinstance(freq, PerformanceFrequency):
            return self._ApplySoundBiquadTrack(soundData, "notch", freq, q = q)
        cosOmega, alpha = self.GetBiquadSetup(freq, q)
        b0 = 1.0
        b1 = -2.0 * cosOmega
        b2 = 1.0
        a0 = 1.0 + alpha
        a1 = -2.0 * cosOmega
        a2 = 1.0 - alpha
        return self.ApplySoundBiquad(soundData, self.NormalizeBiquad(b0, b1, b2, a0, a1, a2))

    def ApplySoundPeak(self, soundData, freq, db, q = 0.707):
        if isinstance(freq, PerformanceFrequency):
            return self._ApplySoundBiquadTrack(
                soundData, "peak", freq, db = db, q = q
            )
        db = self.ValidateNumber(db, "db")
        cosOmega, alpha = self.GetBiquadSetup(freq, q)
        amp = self.GetBiquadAmplitude(db)
        b0 = 1.0 + (alpha * amp)
        b1 = -2.0 * cosOmega
        b2 = 1.0 - (alpha * amp)
        a0 = 1.0 + (alpha / amp)
        a1 = -2.0 * cosOmega
        a2 = 1.0 - (alpha / amp)
        return self.ApplySoundBiquad(soundData, self.NormalizeBiquad(b0, b1, b2, a0, a1, a2))

    def ApplySoundLowShelf(self, soundData, freq, db, q = 0.707):
        if isinstance(freq, PerformanceFrequency):
            return self._ApplySoundBiquadTrack(
                soundData, "lowShelf", freq, db = db, q = q
            )
        db = self.ValidateNumber(db, "db")
        cosOmega, alpha = self.GetBiquadSetup(freq, q)
        amp = self.GetBiquadAmplitude(db)
        beta = 2.0 * math.sqrt(amp) * alpha
        b0 = amp * ((amp + 1.0) - ((amp - 1.0) * cosOmega) + beta)
        b1 = 2.0 * amp * ((amp - 1.0) - ((amp + 1.0) * cosOmega))
        b2 = amp * ((amp + 1.0) - ((amp - 1.0) * cosOmega) - beta)
        a0 = (amp + 1.0) + ((amp - 1.0) * cosOmega) + beta
        a1 = -2.0 * ((amp - 1.0) + ((amp + 1.0) * cosOmega))
        a2 = (amp + 1.0) + ((amp - 1.0) * cosOmega) - beta
        return self.ApplySoundBiquad(soundData, self.NormalizeBiquad(b0, b1, b2, a0, a1, a2))

    def ApplySoundHighShelf(self, soundData, freq, db, q = 0.707):
        if isinstance(freq, PerformanceFrequency):
            return self._ApplySoundBiquadTrack(
                soundData, "highShelf", freq, db = db, q = q
            )
        db = self.ValidateNumber(db, "db")
        cosOmega, alpha = self.GetBiquadSetup(freq, q)
        amp = self.GetBiquadAmplitude(db)
        beta = 2.0 * math.sqrt(amp) * alpha
        b0 = amp * ((amp + 1.0) + ((amp - 1.0) * cosOmega) + beta)
        b1 = -2.0 * amp * ((amp - 1.0) + ((amp + 1.0) * cosOmega))
        b2 = amp * ((amp + 1.0) + ((amp - 1.0) * cosOmega) - beta)
        a0 = (amp + 1.0) - ((amp - 1.0) * cosOmega) + beta
        a1 = 2.0 * ((amp - 1.0) - ((amp + 1.0) * cosOmega))
        a2 = (amp + 1.0) - ((amp - 1.0) * cosOmega) - beta
        return self.ApplySoundBiquad(soundData, self.NormalizeBiquad(b0, b1, b2, a0, a1, a2))

    def ApplySoundLowPassSweep(self, soundData, startFreq, endFreq, q = 0.707, easing = "linear"):
        return self.ApplySoundBiquadSweep(soundData, "lowPass", startFreq, endFreq, 0.0, q, easing)

    def ApplySoundHighPassSweep(self, soundData, startFreq, endFreq, q = 0.707, easing = "linear"):
        return self.ApplySoundBiquadSweep(soundData, "highPass", startFreq, endFreq, 0.0, q, easing)

    def ApplySoundBandPassSweep(self, soundData, startFreq, endFreq, q = 0.707, easing = "linear"):
        return self.ApplySoundBiquadSweep(soundData, "bandPass", startFreq, endFreq, 0.0, q, easing)

    def ApplySoundNotchSweep(self, soundData, startFreq, endFreq, q = 0.707, easing = "linear"):
        return self.ApplySoundBiquadSweep(soundData, "notch", startFreq, endFreq, 0.0, q, easing)

    def ApplySoundPeakSweep(self, soundData, startFreq, endFreq, db, q = 0.707, easing = "linear"):
        return self.ApplySoundBiquadSweep(soundData, "peak", startFreq, endFreq, db, q, easing)

    def ApplySoundLowShelfSweep(self, soundData, startFreq, endFreq, db, q = 0.707, easing = "linear"):
        return self.ApplySoundBiquadSweep(soundData, "lowShelf", startFreq, endFreq, db, q, easing)

    def ApplySoundHighShelfSweep(self, soundData, startFreq, endFreq, db, q = 0.707, easing = "linear"):
        return self.ApplySoundBiquadSweep(soundData, "highShelf", startFreq, endFreq, db, q, easing)

    def _GetFilterFrequencyTrack(self, frequency, frameCount, name):
        if isinstance(frequency, PerformanceFrequency):
            frequencies = frequency.GetFrequencyTrack(
                frameCount, self.SAMPLE_RATE, self.oscillator
            )
        else:
            frequency = self.ValidateNumber(frequency, name)
            frequencies = np.full(frameCount, frequency, dtype = np.float64)

        if not np.all(np.isfinite(frequencies)):
            raise ValueError(name + " must produce only finite frequencies")
        if np.any(frequencies <= 0.0):
            raise ValueError(name + " must produce frequencies greater than zero")
        return frequencies

    def _SmoothFilterFrequencyTrack(self, frequencies):
        if len(frequencies) < 2:
            return frequencies

        smoothingFrames = max(1, int(self.SAMPLE_RATE * 0.001))
        smoothingAmount = 1.0 - math.exp(math.log(0.01) / smoothingFrames)
        smoothed = frequencies.copy()
        for frame in range(1, len(smoothed)):
            previous = smoothed[frame - 1]
            smoothed[frame] = previous * (
                (smoothed[frame] / previous) ** smoothingAmount
            )
        return smoothed

    def _GetTrackedBiquadCoefficients(self, filterType, freq, amp, q):
        cosOmega, alpha = self.GetBiquadSetup(freq, q)
        if filterType == "lowPass":
            coefficients = (
                (1.0 - cosOmega) * 0.5,
                1.0 - cosOmega,
                (1.0 - cosOmega) * 0.5,
                1.0 + alpha,
                -2.0 * cosOmega,
                1.0 - alpha
            )
        elif filterType == "highPass":
            coefficients = (
                (1.0 + cosOmega) * 0.5,
                -(1.0 + cosOmega),
                (1.0 + cosOmega) * 0.5,
                1.0 + alpha,
                -2.0 * cosOmega,
                1.0 - alpha
            )
        elif filterType == "bandPass":
            coefficients = (
                alpha, 0.0, -alpha,
                1.0 + alpha, -2.0 * cosOmega, 1.0 - alpha
            )
        elif filterType == "notch":
            coefficients = (
                1.0, -2.0 * cosOmega, 1.0,
                1.0 + alpha, -2.0 * cosOmega, 1.0 - alpha
            )
        elif filterType == "peak":
            coefficients = (
                1.0 + (alpha * amp),
                -2.0 * cosOmega,
                1.0 - (alpha * amp),
                1.0 + (alpha / amp),
                -2.0 * cosOmega,
                1.0 - (alpha / amp)
            )
        elif filterType == "lowShelf":
            beta = 2.0 * math.sqrt(amp) * alpha
            coefficients = (
                amp * ((amp + 1.0) - ((amp - 1.0) * cosOmega) + beta),
                2.0 * amp * ((amp - 1.0) - ((amp + 1.0) * cosOmega)),
                amp * ((amp + 1.0) - ((amp - 1.0) * cosOmega) - beta),
                (amp + 1.0) + ((amp - 1.0) * cosOmega) + beta,
                -2.0 * ((amp - 1.0) + ((amp + 1.0) * cosOmega)),
                (amp + 1.0) + ((amp - 1.0) * cosOmega) - beta
            )
        else:
            beta = 2.0 * math.sqrt(amp) * alpha
            coefficients = (
                amp * ((amp + 1.0) + ((amp - 1.0) * cosOmega) + beta),
                -2.0 * amp * ((amp - 1.0) + ((amp + 1.0) * cosOmega)),
                amp * ((amp + 1.0) + ((amp - 1.0) * cosOmega) - beta),
                (amp + 1.0) - ((amp - 1.0) * cosOmega) + beta,
                2.0 * ((amp - 1.0) - ((amp + 1.0) * cosOmega)),
                (amp + 1.0) - ((amp - 1.0) * cosOmega) - beta
            )
        return self.NormalizeBiquad(*coefficients)

    def _ApplySoundBiquadTrack(
            self, soundData, filterType, startFreq, endFreq = None,
            db = 0.0, q = 0.707, easing = "linear"
            ):
        filterTypes = (
            "lowPass", "highPass", "bandPass", "notch",
            "peak", "lowShelf", "highShelf"
        )
        if filterType not in filterTypes:
            raise ValueError("Unknown biquad track type: " + str(filterType))
        db = self.ValidateNumber(db, "db")
        q = max(0.0001, self.ValidateNumber(q, "q"))
        amp = self.GetBiquadAmplitude(db)
        samples, returnBytes = self.PrepareSamples(soundData)
        frameCount = len(samples) // self.channels
        startFrequencies = self._GetFilterFrequencyTrack(
            startFreq, frameCount, "startFreq"
        )
        frequencies = startFrequencies
        if endFreq is not None:
            endFrequencies = self._GetFilterFrequencyTrack(
                endFreq, frameCount, "endFreq"
            )
            progress = self.GetEasingValues(frameCount, easing)
            frequencies = startFrequencies * (
                (endFrequencies / startFrequencies) ** progress
            )

        frequencies = np.clip(
            frequencies, 1.0, self.SAMPLE_RATE * 0.499
        )
        frequencies = self._SmoothFilterFrequencyTrack(frequencies)

        if ChirpKernels.NUMBA_ENABLED:
            filtered = ChirpKernels.ApplyBiquadTrack(
                samples, frequencies, self.channels, self.SAMPLE_RATE,
                ChirpKernels.GetFilterTypeId(filterType), db, q
            )
        else:
            states = [[0.0, 0.0, 0.0, 0.0] for _ in range(self.channels)]
            filtered = np.empty(len(samples), dtype = np.float64)
            for frame, freq in enumerate(frequencies):
                coefficients = self._GetTrackedBiquadCoefficients(
                    filterType, freq, amp, q
                )
                for channel in range(self.channels):
                    sampleIndex = (frame * self.channels) + channel
                    filtered[sampleIndex] = self.ProcessBiquadSample(
                        samples[sampleIndex], coefficients, states[channel]
                    )

        filtered = self._PreserveSilentFilterEnd(samples, filtered)
        return self.FinishSamples(filtered, returnBytes)

    def ApplySoundBiquad(self, soundData, coefficients):
        samples, returnBytes = self.PrepareSamples(soundData)

        if ChirpKernels.NUMBA_ENABLED:
            filtered = ChirpKernels.ApplyBiquad(samples, np.asarray(coefficients, dtype = np.float64), self.channels)
        else:
            states = [[0.0, 0.0, 0.0, 0.0] for _ in range(self.channels)]
            filtered = np.empty(len(samples), dtype = np.float64)

            for i, sample in enumerate(samples):
                channel = i % self.channels
                filtered[i] = self.ProcessBiquadSample(sample, coefficients, states[channel])

        filtered = self._PreserveSilentFilterEnd(samples, filtered)
        return self.FinishSamples(filtered, returnBytes)

    def ApplySoundBiquadSweep(self, soundData, filterType, startFreq, endFreq, db = 0.0, q = 0.707, easing = "linear"):
        if (
                isinstance(startFreq, PerformanceFrequency)
                or isinstance(endFreq, PerformanceFrequency)
                ):
            return self._ApplySoundBiquadTrack(
                soundData, filterType, startFreq, endFreq, db, q, easing
            )
        startFreq = self.ValidateNumber(startFreq, "startFreq")
        endFreq = self.ValidateNumber(endFreq, "endFreq")
        db = self.ValidateNumber(db, "db")
        q = self.ValidateNumber(q, "q")
        startFreq = max(1.0, min(self.SAMPLE_RATE * 0.499, startFreq))
        endFreq = max(1.0, min(self.SAMPLE_RATE * 0.499, endFreq))
        filterTypes = ("lowPass", "highPass", "bandPass", "notch", "peak", "lowShelf", "highShelf")
        if filterType not in filterTypes:
            raise ValueError("Unknown biquad sweep type: " + str(filterType))
        easingFunction = Easing.Resolve(easing)
        amp = self.GetBiquadAmplitude(db) if filterType in ("peak", "lowShelf", "highShelf") else 1.0
        samples, returnBytes = self.PrepareSamples(soundData)
        frameCount = (len(samples) + self.channels - 1) // self.channels

        if ChirpKernels.NUMBA_ENABLED and Easing.IsBuiltIn(easing):
            filtered = ChirpKernels.ApplyBiquadSweep(
                samples, self.channels, self.SAMPLE_RATE,
                ChirpKernels.GetFilterTypeId(filterType),
                startFreq, endFreq, db, q, ChirpKernels.GetEasingId(easing)
                )
            filtered = self._PreserveSilentFilterEnd(samples, filtered)
            return self.FinishSamples(filtered, returnBytes)

        states = [[0.0, 0.0, 0.0, 0.0] for _ in range(self.channels)]
        filtered = np.empty(len(samples), dtype = np.float64)
        frameDivisor = max(1, frameCount - 1)
        frequencyRatio = endFreq / startFreq
        sqrtAmp = math.sqrt(amp)

        for frame in range(frameCount):
            percent = frame / frameDivisor
            percent = Easing.ApplyResolved(percent, easingFunction)
            freq = startFreq * (frequencyRatio ** percent)
            cosOmega, alpha = self.GetBiquadSetup(freq, q)

            if filterType == "lowPass":
                b0 = (1.0 - cosOmega) * 0.5
                b1 = 1.0 - cosOmega
                b2 = (1.0 - cosOmega) * 0.5
                a0 = 1.0 + alpha
                a1 = -2.0 * cosOmega
                a2 = 1.0 - alpha
            elif filterType == "highPass":
                b0 = (1.0 + cosOmega) * 0.5
                b1 = -(1.0 + cosOmega)
                b2 = (1.0 + cosOmega) * 0.5
                a0 = 1.0 + alpha
                a1 = -2.0 * cosOmega
                a2 = 1.0 - alpha
            elif filterType == "bandPass":
                b0 = alpha
                b1 = 0.0
                b2 = -alpha
                a0 = 1.0 + alpha
                a1 = -2.0 * cosOmega
                a2 = 1.0 - alpha
            elif filterType == "notch":
                b0 = 1.0
                b1 = -2.0 * cosOmega
                b2 = 1.0
                a0 = 1.0 + alpha
                a1 = -2.0 * cosOmega
                a2 = 1.0 - alpha
            elif filterType == "peak":
                b0 = 1.0 + (alpha * amp)
                b1 = -2.0 * cosOmega
                b2 = 1.0 - (alpha * amp)
                a0 = 1.0 + (alpha / amp)
                a1 = -2.0 * cosOmega
                a2 = 1.0 - (alpha / amp)
            elif filterType == "lowShelf":
                beta = 2.0 * sqrtAmp * alpha
                b0 = amp * ((amp + 1.0) - ((amp - 1.0) * cosOmega) + beta)
                b1 = 2.0 * amp * ((amp - 1.0) - ((amp + 1.0) * cosOmega))
                b2 = amp * ((amp + 1.0) - ((amp - 1.0) * cosOmega) - beta)
                a0 = (amp + 1.0) + ((amp - 1.0) * cosOmega) + beta
                a1 = -2.0 * ((amp - 1.0) + ((amp + 1.0) * cosOmega))
                a2 = (amp + 1.0) + ((amp - 1.0) * cosOmega) - beta
            elif filterType == "highShelf":
                beta = 2.0 * sqrtAmp * alpha
                b0 = amp * ((amp + 1.0) + ((amp - 1.0) * cosOmega) + beta)
                b1 = -2.0 * amp * ((amp - 1.0) + ((amp + 1.0) * cosOmega))
                b2 = amp * ((amp + 1.0) + ((amp - 1.0) * cosOmega) - beta)
                a0 = (amp + 1.0) - ((amp - 1.0) * cosOmega) + beta
                a1 = 2.0 * ((amp - 1.0) - ((amp + 1.0) * cosOmega))
                a2 = (amp + 1.0) - ((amp - 1.0) * cosOmega) - beta
            coefficients = self.NormalizeBiquad(b0, b1, b2, a0, a1, a2)
            for channel in range(self.channels):
                sampleIndex = (frame * self.channels) + channel
                if sampleIndex >= len(samples):
                    break
                filtered[sampleIndex] = self.ProcessBiquadSample(
                    samples[sampleIndex], coefficients, states[channel]
                )

        filtered = self._PreserveSilentFilterEnd(samples, filtered)
        return self.FinishSamples(filtered, returnBytes)

    def ProcessBiquadSample(self, sample, coefficients, state):
        b0, b1, b2, a1, a2 = coefficients
        x1, x2, y1, y2 = state
        output = (b0 * sample) + (b1 * x1) + (b2 * x2) - (a1 * y1) - (a2 * y2)

        state[1] = x1
        state[0] = sample
        state[3] = y1
        state[2] = output

        return output

# -----------------------------------
# Reverb / Delay
# -----------------------------------

    # Schroeder style reverb
    def ApplySoundSchroverb(self, soundData, wet = 0.35, decay = 0.72, roomSize = 1.0, tail = None):
        wet = self.ValidateNumber(wet, "wet")
        decay = self.ValidateNumber(decay, "decay")
        roomSize = self.ValidateNumber(roomSize, "roomSize")
        if tail is not None:
            tail = self.ValidateNumber(tail, "tail")
        wet = max(0.0, min(1.0, wet))
        if wet == 0.0:
            return self.CopySoundData(soundData)

        dry = 1.0 - wet
        decay = max(0.0, min(0.98, decay))
        roomSize = max(0.25, roomSize)
        if tail is not None:
            tail = max(0.0, tail)

        sourceSamples, returnBytes = self.PrepareSamples(soundData)
        combDelays = [0.0297, 0.0371, 0.0411, 0.0437]
        allPassDelays = [0.0050, 0.0017]
        if tail is None:
            combTail = self.GetReverbTailDuration(decay, max(combDelays) * roomSize)
            diffusionTail = sum(
                self.GetReverbTailDuration(0.7, delay * roomSize)
                for delay in allPassDelays
            )
            tailDuration = combTail + diffusionTail
        else:
            tailDuration = tail
        tailSamples = math.ceil(self.SAMPLE_RATE * tailDuration) * self.channels
        workingSamples = np.concatenate((sourceSamples, np.zeros(tailSamples, dtype = np.float64)))

        combOutputs = [self.FeedbackCombFilter(workingSamples, delay * roomSize, decay) for delay in combDelays]

        reverbed = np.mean(np.asarray(combOutputs), axis = 0)

        for delay in allPassDelays:
            reverbed = self.AllPassFilter(reverbed, delay * roomSize, 0.7)

        drySamples = np.zeros(len(reverbed), dtype = np.float64)
        drySamples[:len(sourceSamples)] = sourceSamples
        mixed = (drySamples * dry) + (np.asarray(reverbed) * wet)
        return self.FinishSamples(mixed, returnBytes)

    # A Freeverb style reverb implementation
    def ApplySoundFreeverb(self, soundData, wet = 0.35, decay = 0.84, damping = 0.5, width = 1.0, tail = None):
        wet = self.ValidateNumber(wet, "wet")
        decay = self.ValidateNumber(decay, "decay")
        damping = self.ValidateNumber(damping, "damping")
        width = self.ValidateNumber(width, "width")
        if tail is not None:
            tail = self.ValidateNumber(tail, "tail")
        wet = max(0.0, min(1.0, wet))
        if wet == 0.0:
            return self.CopySoundData(soundData)

        dry = 1.0 - wet
        decay = max(0.0, min(0.98, decay))
        damping = max(0.0, min(0.98, damping))
        width = max(0.0, min(1.0, width))
        if tail is not None:
            tail = max(0.0, tail)

        sourceSamples, returnBytes = self.PrepareSamples(soundData)
        sourceChannels = self.SplitChannels(sourceSamples)
        combDelays = [1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617]
        allPassDelays = [556, 441, 341, 225]
        stereoSpread = 23
        scale = self.SAMPLE_RATE / 44100.0
        longestSpread = stereoSpread if self.channels == 2 else 0
        longestCombDelay = ((max(combDelays) + longestSpread) * scale) / self.SAMPLE_RATE
        if tail is None:
            combTail = self.GetReverbTailDuration(decay, longestCombDelay)
            diffusionTail = sum(
                self.GetReverbTailDuration(
                    0.5,
                    ((delay + longestSpread) * scale) / self.SAMPLE_RATE
                )
                for delay in allPassDelays
            )
            tailDuration = combTail + diffusionTail
        else:
            tailDuration = tail
        tailFrames = math.ceil(self.SAMPLE_RATE * tailDuration)

        sourceChannels = [np.pad(channel, (0, tailFrames)) for channel in sourceChannels]

        if self.channels == 1:
            reverbed = self.FreeverbChannel(
                sourceChannels[0], combDelays, allPassDelays, 0, scale, decay, damping
            )
            mixedChannels = [(sourceChannels[0] * dry) + (reverbed * wet)]
        elif width == 0.0:
            monoSource = (sourceChannels[0] + sourceChannels[1]) * 0.5
            monoReverb = self.FreeverbChannel(monoSource, combDelays, allPassDelays, 0, scale, decay, damping)
            mixedChannels = [
                (sourceChannels[0] * dry) + (monoReverb * wet),
                (sourceChannels[1] * dry) + (monoReverb * wet)
            ]
        elif width == 1.0:
            reverbedChannels = [
                self.FreeverbChannel(
                    channelSamples, combDelays, allPassDelays,
                    stereoSpread if channelIndex == 1 else 0,
                    scale, decay, damping
                )
                for channelIndex, channelSamples in enumerate(sourceChannels)
            ]
            mixedChannels = [
                (sourceChannels[0] * dry) + (reverbedChannels[0] * wet),
                (sourceChannels[1] * dry) + (reverbedChannels[1] * wet)
            ]
        else:
            reverbedChannels = [
                self.FreeverbChannel(
                    channelSamples, combDelays, allPassDelays,
                    stereoSpread if channelIndex == 1 else 0,
                    scale, decay, damping
                )
                for channelIndex, channelSamples in enumerate(sourceChannels)
            ]
            monoSource = (sourceChannels[0] + sourceChannels[1]) * 0.5
            monoReverb = self.FreeverbChannel(monoSource, combDelays, allPassDelays, 0, scale, decay, damping)
            reverbLeft = ((monoReverb * (1.0 - width)) + (reverbedChannels[0] * width)) * wet
            reverbRight = ((monoReverb * (1.0 - width)) + (reverbedChannels[1] * width)) * wet
            mixedChannels = [
                (sourceChannels[0] * dry) + reverbLeft,
                (sourceChannels[1] * dry) + reverbRight
            ]

        mixed = self.JoinChannels(mixedChannels)

        return self.FinishSamples(mixed, returnBytes)

    # Rough emulation of the reverb unit on the Roland MT-32
    # source: https://github.com/munt/munt/blob/master/mt32emu/src/BReverbModel.cpp
    def ApplySoundMTVerb(self, soundData, wet = 0.35, decay = 0.72, mode = "room", tail = None):
        wet = self.ValidateNumber(wet, "wet")
        decay = self.ValidateNumber(decay, "decay")
        if tail is not None:
            tail = self.ValidateNumber(tail, "tail")
        wet = max(0.0, min(1.0, wet))
        if wet == 0.0:
            return self.CopySoundData(soundData)

        dry = 1.0 - wet
        decay = max(0.0, min(0.98, decay))
        settings = self.GetMTVerbSettings(mode)
        if tail is not None:
            tail = max(0.0, tail)

        sourceSamples, returnBytes = self.PrepareSamples(soundData)
        sourceChannels = self.SplitChannels(sourceSamples)
        sourceFrames = len(sourceChannels[0])
        if tail is None:
            entranceTail = settings["combs"][0] / self.SAMPLE_RATE
            entranceFactor = max(0.0, min(1.0, settings["combFactors"][0] / 256.0))
            if entranceFactor > 0.0:
                entranceTail += (
                    math.log(0.001) / math.log(entranceFactor)
                ) / self.SAMPLE_RATE
            diffusionTail = sum(
                self.GetReverbTailDuration(0.5, delay / self.SAMPLE_RATE)
                for delay in settings["allpasses"]
            )
            combTail = self.GetReverbTailDuration(
                decay, max(settings["combs"][1:]) / self.SAMPLE_RATE
            )
            outputTail = max(settings["outL"] + settings["outR"]) / self.SAMPLE_RATE
            tailDuration = entranceTail + diffusionTail + combTail + outputTail
        else:
            tailDuration = tail
        tailFrames = math.ceil(self.SAMPLE_RATE * tailDuration)
        workingFrames = sourceFrames + tailFrames
        monoInput = np.zeros(workingFrames, dtype = np.float64)
        monoInput[:sourceFrames] = np.mean(np.asarray(sourceChannels), axis = 0)

        diffused = self.MTEntranceFilter(monoInput, settings["combs"][0], settings["combFactors"][0], settings["lpfAmp"])

        for delay in settings["allpasses"]:
            diffused = self.AllPassFilterFrames(diffused, delay, 0.5)

        combOutputs = []
        for i, delay in enumerate(settings["combs"][1:]):
            combOutputs.append(
                self.MTCombFilter(diffused, delay, decay, settings["combFactors"][i + 1]))

        if ChirpKernels.NUMBA_ENABLED:
            mixedChannels = ChirpKernels.MixMTVerb(
                np.asarray(sourceChannels, dtype = np.float64),
                np.asarray(combOutputs, dtype = np.float64),
                np.asarray(settings["outL"], dtype = np.int64),
                np.asarray(settings["outR"], dtype = np.int64),
                sourceFrames,
                workingFrames,
                self.channels,
                dry,
                wet
            )
        else:
            mixedChannels = [[] for _ in range(self.channels)]
            for frame in range(workingFrames):
                reverbLeft = 0.0
                reverbRight = 0.0

                for combIndex, output in enumerate(combOutputs):
                    leftIndex = frame - settings["outL"][combIndex]
                    rightIndex = frame - settings["outR"][combIndex]
                    if leftIndex >= 0:
                        reverbLeft += output[leftIndex]
                    if rightIndex >= 0:
                        reverbRight += output[rightIndex]

                reverbLeft /= len(combOutputs)
                reverbRight /= len(combOutputs)

                if self.channels == 1:
                    drySample = sourceChannels[0][frame] if frame < sourceFrames else 0.0
                    wetSample = (reverbLeft + reverbRight) * 0.5
                    mixedChannels[0].append((drySample * dry) + (wetSample * wet))
                else:
                    dryLeft = sourceChannels[0][frame] if frame < sourceFrames else 0.0
                    dryRight = sourceChannels[1][frame] if frame < sourceFrames else 0.0
                    mixedChannels[0].append((dryLeft * dry) + (reverbLeft * wet))
                    mixedChannels[1].append((dryRight * dry) + (reverbRight * wet))

        return self.FinishSamples(self.JoinChannels(mixedChannels), returnBytes)

    def GetMTVerbSettings(self, mode):
        modeKey = str(mode).lower()
        modeAliases = {
            "0": "room",
            "room": "room",
            "1": "hall",
            "hall": "hall",
            "2": "plate",
            "plate": "plate",
        }

        if modeKey not in modeAliases:
            raise ValueError("Unknown MTVerb mode: " + str(mode))

        modes = {
            "room": {
                "allpasses": [994, 729, 78],
                "combs": [706, 2349, 2839, 3632],
                "outL": [2349, 141, 1960],
                "outR": [1174, 1570, 145],
                "combFactors": [0xA0, 0x60, 0x60, 0x60],
                "lpfAmp": 0x60,
            },
            "hall": {
                "allpasses": [1324, 809, 176],
                "combs": [962, 2619, 3545, 4519],
                "outL": [2618, 1760, 4518],
                "outR": [1300, 3532, 2274],
                "combFactors": [0x80, 0x60, 0x60, 0x60],
                "lpfAmp": 0x60,
            },
            "plate": {
                "allpasses": [969, 644, 157],
                "combs": [117, 2259, 2839, 3539],
                "outL": [2259, 718, 1769],
                "outR": [1136, 2128, 1],
                "combFactors": [0x00, 0x60, 0x60, 0x60],
                "lpfAmp": 0x80,
            },
        }

        return modes[modeAliases[modeKey]]

    def MTEntranceFilter(self, samples, delayFrames, factor, lpfAmp):
        delayFrames = self.ClampDelayFrames(delayFrames)
        factor = max(0.0, min(1.0, factor / 256.0))
        lpfAmp = max(0.0, min(1.0, lpfAmp / 256.0))

        if ChirpKernels.NUMBA_ENABLED:
            return ChirpKernels.MTEntranceFilter(np.asarray(samples, dtype = np.float64), delayFrames, factor, lpfAmp)

        samples = list(samples)
        buffer = [0.0] * delayFrames
        index = 0
        lpfState = 0.0
        output = []

        for sample in samples:
            delayed = buffer[index]
            lpfState = (delayed * (1.0 - factor)) + (lpfState * factor)
            output.append(lpfState * lpfAmp)
            buffer[index] = sample
            index = (index + 1) % delayFrames

        return output

    def MTCombFilter(self, samples, delayFrames, feedback, factor):
        delayFrames = self.ClampDelayFrames(delayFrames)
        factor = max(0.0, min(1.0, factor / 256.0))
        feedback = max(0.0, min(0.98, feedback))

        if ChirpKernels.NUMBA_ENABLED:
            return ChirpKernels.MTCombFilter(np.asarray(samples, dtype = np.float64), delayFrames, feedback, factor)

        samples = list(samples)
        buffer = [0.0] * delayFrames
        index = 0
        filterState = 0.0
        output = []

        for sample in samples:
            delayed = buffer[index]
            filterState = (delayed * (1.0 - factor)) + (filterState * factor)
            output.append(delayed)
            buffer[index] = sample + (filterState * feedback)
            index = (index + 1) % delayFrames

        return output

    def GetReverbTailDuration(self, decay, longestDelay, threshold = 0.001):
        if decay <= 0.0:
            return longestDelay

        decay = max(0.0001, min(0.98, decay))
        longestDelay = max(0.001, longestDelay)
        repeats = math.log(threshold) / math.log(decay)
        return max(longestDelay, longestDelay * repeats)

    def SplitChannels(self, samples):
        samples = np.asarray(samples, dtype = np.float64).reshape(-1)
        return [samples[channel::self.channels].copy() for channel in range(self.channels)]

    def JoinChannels(self, channels):

        channels = [np.asarray(channel, dtype = np.float64).reshape(-1) for channel in channels]
        frameCount = max(len(channel) for channel in channels)
        samples = np.zeros(frameCount * len(channels), dtype = np.float64)

        for channelIndex, channel in enumerate(channels):
            samples[channelIndex:len(channel) * len(channels):len(channels)] = channel

        return samples

    def FreeverbChannel(self, samples, combDelays, allPassDelays, spread, scale, decay, damping):
        reverbed = np.zeros(len(samples), dtype = np.float64)
        for delay in combDelays:
            reverbed += self.DampedFeedbackCombFilter(
                samples, int((delay + spread) * scale), decay, damping
            )
        reverbed /= len(combDelays)

        for delay in allPassDelays:
            reverbed = self.AllPassFilterFrames(reverbed, int((delay + spread) * scale), 0.5)

        return np.asarray(reverbed, dtype = np.float64)

    def ApplySoundDelay(self, soundData, delaySettings = None):
        if delaySettings is None:
            return self.CopySoundData(soundData)

        delay, decay, count, extend = delaySettings
        delay = self.ValidateNumber(delay, "delay")
        decay = self.ValidateNumber(decay, "decay")
        if count is not None:
            count = self.ValidateInteger(count, "count")
        if not isinstance(extend, bool):
            raise TypeError("extend must be a boolean")
        delay = max(0.0, delay)
        decay = max(0.0, min(0.999, decay))

        if delay <= 0.0 or decay <= 0.0:
            return self.CopySoundData(soundData)

        delaySamples = int(self.SAMPLE_RATE * delay) * self.channels
        if delaySamples <= 0:
            return self.CopySoundData(soundData)

        count = self.GetDelayCount(decay, count, delay)

        if count <= 0:
            return self.CopySoundData(soundData)

        sourceSamples, returnBytes = self.PrepareSamples(soundData)
        sampleCount = len(sourceSamples)
        if extend:
            sampleCount += delaySamples * count

        delayedSamples = np.zeros(sampleCount, dtype = np.float64)
        delayedSamples[:len(sourceSamples)] = sourceSamples

        echoGain = decay
        for repeat in range(1, count + 1):
            offset = delaySamples * repeat
            availableSamples = min(len(sourceSamples), len(delayedSamples) - offset)
            if availableSamples <= 0:
                break
            delayedSamples[offset:offset + availableSamples] += sourceSamples[:availableSamples] * echoGain
            echoGain *= decay

        return self.FinishSamples(delayedSamples, returnBytes)

    def ApplySoundPingPong(self, soundData, delaySettings = None):
        if delaySettings is None:
            return self.CopySoundData(soundData)

        delay, decay, count, width, extend = delaySettings
        delay = self.ValidateNumber(delay, "delay")
        decay = self.ValidateNumber(decay, "decay")
        if count is not None:
            count = self.ValidateInteger(count, "count")
        width = self.ValidateNumber(width, "width")
        if not isinstance(extend, bool):
            raise TypeError("extend must be a boolean")
        delay = max(0.0, delay)
        decay = max(0.0, min(0.999, decay))
        width = max(0.0, min(1.0, width))

        sourceSamples, returnBytes = self.PrepareSamples(soundData)
        sourceFrames = len(sourceSamples) // self.channels
        if self.channels == 1:
            leftGain, rightGain = self.GetPanGains(0.0)
            drySamples = np.empty(sourceFrames * 2, dtype = np.float64)
            drySamples[0::2] = sourceSamples * leftGain
            drySamples[1::2] = sourceSamples * rightGain
            monoSource = sourceSamples
        else:
            drySamples = sourceSamples
            stereoSource = sourceSamples.reshape(-1, 2)

        if delay <= 0.0 or decay <= 0.0:
            return self.FinishSamples(drySamples, returnBytes)

        delayFrames = int(self.SAMPLE_RATE * delay)
        if delayFrames <= 0:
            return self.FinishSamples(drySamples, returnBytes)

        count = self.GetDelayCount(decay, count, delay)

        if count <= 0:
            return self.FinishSamples(drySamples, returnBytes)

        targetFrames = sourceFrames
        if extend:
            targetFrames += delayFrames * count

        delayedSamples = np.zeros(targetFrames * 2, dtype = np.float64)
        delayedSamples[:len(drySamples)] = drySamples

        echoGain = decay
        for repeat in range(1, count + 1):
            offsetFrames = delayFrames * repeat
            availableFrames = min(sourceFrames, targetFrames - offsetFrames)
            if availableFrames <= 0:
                break

            targetStart = offsetFrames * 2
            targetEnd = (offsetFrames + availableFrames) * 2
            targetChannels = delayedSamples[targetStart:targetEnd].reshape(-1, 2)
            if self.channels == 1:
                pan = -width if repeat % 2 == 1 else width
                leftGain, rightGain = self.GetPanGains(pan)
                targetChannels[:, 0] += monoSource[:availableFrames] * echoGain * leftGain
                targetChannels[:, 1] += monoSource[:availableFrames] * echoGain * rightGain
            elif repeat % 2 == 1:
                source = stereoSource[:availableFrames]
                targetChannels[:, 0] += (
                    (source[:, 0] * (1.0 - width)) + (source[:, 1] * width)
                ) * echoGain
                targetChannels[:, 1] += (
                    (source[:, 1] * (1.0 - width)) + (source[:, 0] * width)
                ) * echoGain
            else:
                targetChannels += stereoSource[:availableFrames] * echoGain

            echoGain *= decay

        return self.FinishSamples(delayedSamples, returnBytes)

    def GetDelayCount(self, decay, count, delay = 0.25):
        if count is not None:
            return max(0, count)

        if decay < 0.01:
            return 0

        thresholdCount = max(1, math.floor(math.log(0.01) / math.log(decay)))
        tailLimit = max(1, math.floor(self.MAX_AUTO_DELAY_TAIL_SECONDS / max(delay, 1.0 / self.SAMPLE_RATE)))
        return min(thresholdCount, tailLimit)

    def GetDelaySampleCount(self, delay):
        return max(self.channels, int(self.SAMPLE_RATE * max(0.0, delay)) * self.channels)

    def ClampDelayFrames(self, delayFrames):
        return max(1, int(max(0, delayFrames)))

    def FeedbackCombFilter(self, samples, delay, feedback):
        delaySamples = self.GetDelaySampleCount(delay)
        feedback = max(0.0, min(0.98, feedback))

        if ChirpKernels.NUMBA_ENABLED:
            return ChirpKernels.FeedbackCombFilter(np.asarray(samples, dtype = np.float64), delaySamples, feedback)

        samples = list(samples)
        output = [0.0] * len(samples)

        for i, sample in enumerate(samples):
            delayed = output[i - delaySamples] if i >= delaySamples else 0.0
            output[i] = sample + (delayed * feedback)

        return output

    def DampedFeedbackCombFilter(self, samples, delayFrames, feedback, damping):
        delayFrames = self.ClampDelayFrames(delayFrames)
        feedback = max(0.0, min(0.98, feedback))
        damping = max(0.0, min(0.98, damping))

        if ChirpKernels.NUMBA_ENABLED:
            return ChirpKernels.DampedFeedbackCombFilter(
                np.asarray(samples, dtype = np.float64), delayFrames, feedback, damping)

        samples = list(samples)
        output = [0.0] * len(samples)
        filterState = 0.0

        for i, sample in enumerate(samples):
            delayed = output[i - delayFrames] if i >= delayFrames else 0.0
            filterState = (delayed * (1.0 - damping)) + (filterState * damping)
            output[i] = sample + (filterState * feedback)

        return output

    def AllPassFilter(self, samples, delay, feedback):
        delaySamples = self.GetDelaySampleCount(delay)
        return self.AllPassFilterFrames(samples, delaySamples, feedback)

    def AllPassFilterFrames(self, samples, delayFrames, feedback):
        delayFrames = self.ClampDelayFrames(delayFrames)
        feedback = max(0.0, min(0.98, feedback))

        if ChirpKernels.NUMBA_ENABLED:
            return ChirpKernels.AllPassFilter(np.asarray(samples, dtype = np.float64), delayFrames, feedback)

        samples = list(samples)
        output = [0.0] * len(samples)

        for i, sample in enumerate(samples):
            delayedInput = samples[i - delayFrames] if i >= delayFrames else 0.0
            delayedOutput = output[i - delayFrames] if i >= delayFrames else 0.0
            output[i] = (-feedback * sample) + delayedInput + (feedback * delayedOutput)

        return output



__all__ = [
    "ChirpDSP",
]
