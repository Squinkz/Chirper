import math
from numbers import Integral, Real
import random

import numpy as np

from . import ChirpKernels


class WaveTable:
    def __init__(self, sound):
        if not hasattr(sound, "samples") or not hasattr(sound, "channels"):
            raise TypeError("Expected a Sound object")

        samples = np.asarray(sound.samples, dtype = np.float64).reshape(-1)
        if sound.channels == 2:
            frames = samples.reshape(-1, 2)
            samples = (frames[:, 0] + frames[:, 1]) * 0.5
        elif sound.channels != 1:
            raise ValueError("Wave tables only support mono or stereo Sound objects")

        if len(samples) == 0:
            raise ValueError("Cannot create a wave table from an empty Sound")

        self.samples = samples.copy()
        self.samples.setflags(write = False)

    def GetValue(self, phase):
        position = (phase % 1.0) * len(self.samples)
        firstIndex = int(position) % len(self.samples)
        secondIndex = (firstIndex + 1) % len(self.samples)
        fraction = position - int(position)
        return self.samples[firstIndex] + ((self.samples[secondIndex] - self.samples[firstIndex]) * fraction)

    def GetValues(self, phases):
        positions = np.mod(phases, 1.0) * len(self.samples)
        firstIndices = positions.astype(np.int64) % len(self.samples)
        secondIndices = (firstIndices + 1) % len(self.samples)
        fractions = positions - firstIndices
        return self.samples[firstIndices] + ((self.samples[secondIndices] - self.samples[firstIndices]) * fractions)

    def __call__(self, time, frequency = 440.0):
        return self.GetValue(time * frequency)


class ChirpOscillator:
    WAVE_NAMES = (
        "Sine",
        "Pulse50",
        "Pulse25",
        "Pulse12",
        "Triangle",
        "Saw",
        "Pulse50AA",
        "Pulse25AA",
        "Pulse12AA",
        "TriangleAA",
        "SawAA",
        "Noise",
        "NoiseLP",
        "NoiseHP",
        "NoiseBP",
        "NoiseStep",
        "NoiseQuanta",
    )

    def __init__(self, sampleRate = 44100):
        if isinstance(sampleRate, bool) or not isinstance(sampleRate, Integral):
            raise TypeError("sampleRate must be an integer")
        if sampleRate <= 0:
            raise ValueError("sampleRate must be greater than zero")

        self.sampleRate = int(sampleRate)
        self.random = random.Random(0)
        self.ResetState()

    def ResetState(self):
        self.filterStates = {}
        self.stepNoiseValue = 0.0
        self.stepNoiseSampleIndex = -1
        self.quantaNoiseValue = 0.0
        self.quantaNoiseSampleIndex = -1

# -----------------------------------
# Wave Resolution
# -----------------------------------

    def GetWave(self, wave):
        if isinstance(wave, WaveTable):
            return wave
        if isinstance(wave, str):
            waveKey = wave.replace("_", "").replace("-", "").lower()
            for waveName in self.WAVE_NAMES:
                candidateKey = waveName.replace("_", "").replace("-", "").lower()
                if candidateKey == waveKey:
                    return getattr(self, waveName)

            raise ValueError("Unknown wave shape: " + wave)
        if callable(wave):
            return wave
        if hasattr(wave, "samples") and hasattr(wave, "channels"):
            return WaveTable(wave)

        raise TypeError("Expected a wave name, callable, or Sound")

    def GetWaveId(self, wave):
        waveFunction = getattr(wave, "__func__", wave)
        waveIds = {
            self.Sine.__func__: ChirpKernels.WAVE_SINE,
            self.Pulse50.__func__: ChirpKernels.WAVE_PULSE50,
            self.Pulse25.__func__: ChirpKernels.WAVE_PULSE25,
            self.Pulse12.__func__: ChirpKernels.WAVE_PULSE12,
            self.Triangle.__func__: ChirpKernels.WAVE_TRIANGLE,
            self.Saw.__func__: ChirpKernels.WAVE_SAW,
            self.Pulse50AA.__func__: ChirpKernels.WAVE_PULSE50_AA,
            self.Pulse25AA.__func__: ChirpKernels.WAVE_PULSE25_AA,
            self.Pulse12AA.__func__: ChirpKernels.WAVE_PULSE12_AA,
            self.SawAA.__func__: ChirpKernels.WAVE_SAW_AA,
            self.TriangleAA.__func__: ChirpKernels.WAVE_TRIANGLE_AA,
        }
        return waveIds.get(waveFunction)

    def IsNoiseWave(self, wave):
        waveFunction = getattr(wave, "__func__", wave)
        return waveFunction in (
            self.Noise.__func__,
            self.NoiseLP.__func__,
            self.NoiseHP.__func__,
            self.NoiseBP.__func__,
            self.NoiseStep.__func__,
            self.NoiseQuanta.__func__,
        )

# -----------------------------------
# Pitched Waves
# -----------------------------------

    def Sine(self, time, frequency = 440.0):
        return math.sin(2.0 * math.pi * frequency * time)

    def Phase(self, time, frequency = 440.0):
        return (time * frequency) % 1.0

    def Pulse50(self, time, frequency = 440.0):
        return 1.0 if self.Phase(time, frequency) < 0.5 else -1.0

    def Pulse25(self, time, frequency = 440.0):
        return 1.0 if self.Phase(time, frequency) < 0.25 else -1.0

    def Pulse12(self, time, frequency = 440.0):
        return 1.0 if self.Phase(time, frequency) < 0.125 else -1.0

    def Triangle(self, time, frequency = 440.0):
        phase = self.Phase(time, frequency)
        return 1.0 - (4.0 * abs(phase - 0.5))

    def Saw(self, time, frequency = 440.0):
        return (self.Phase(time, frequency) * 2.0) - 1.0

    def PolyBlep(self, phase, phaseIncrement):
        phaseIncrement = min(0.5, max(0.0, abs(phaseIncrement)))
        if phaseIncrement <= 0.0:
            return 0.0
        if phase < phaseIncrement:
            normalizedPhase = phase / phaseIncrement
            return normalizedPhase + normalizedPhase - (normalizedPhase * normalizedPhase) - 1.0
        if phase > 1.0 - phaseIncrement:
            normalizedPhase = (phase - 1.0) / phaseIncrement
            return (normalizedPhase * normalizedPhase) + normalizedPhase + normalizedPhase + 1.0

        return 0.0

    def GetPolyBlepValues(self, phases, phaseIncrement):
        phaseIncrement = min(0.5, max(0.0, abs(phaseIncrement)))
        values = np.zeros(len(phases), dtype = np.float64)
        if phaseIncrement <= 0.0:
            return values

        startMask = phases < phaseIncrement
        startPhases = phases[startMask] / phaseIncrement
        values[startMask] = startPhases + startPhases - (startPhases * startPhases) - 1.0

        endMask = phases > 1.0 - phaseIncrement
        endPhases = (phases[endMask] - 1.0) / phaseIncrement
        values[endMask] = (endPhases * endPhases) + endPhases + endPhases + 1.0
        return values

    def SawAA(self, time, frequency = 440.0):
        phase = self.Phase(time, frequency)
        phaseIncrement = abs(frequency) / self.sampleRate
        return ((phase * 2.0) - 1.0) - self.PolyBlep(phase, phaseIncrement)

    def GetAntiAliasedPulse(self, time, frequency, width):
        phase = self.Phase(time, frequency)
        phaseIncrement = abs(frequency) / self.sampleRate
        sample = 1.0 if phase < width else -1.0
        sample += self.PolyBlep(phase, phaseIncrement)
        sample -= self.PolyBlep((phase - width) % 1.0, phaseIncrement)
        return sample

    def Pulse50AA(self, time, frequency = 440.0):
        return self.GetAntiAliasedPulse(time, frequency, 0.5)

    def Pulse25AA(self, time, frequency = 440.0):
        return self.GetAntiAliasedPulse(time, frequency, 0.25)

    def Pulse12AA(self, time, frequency = 440.0):
        return self.GetAntiAliasedPulse(time, frequency, 0.125)

    def TriangleAA(self, time, frequency = 440.0):
        phase = self.Phase(time, frequency)
        phaseIncrement = abs(frequency) / self.sampleRate
        return ChirpKernels.GetTriangleValue(phase, phaseIncrement)

    def RenderBuiltIn(self, waveId, phases, phaseIncrement):
        normalizedPhases = np.mod(phases, 1.0)
        if waveId == ChirpKernels.WAVE_SINE:
            return np.sin(2.0 * math.pi * phases)
        if waveId == ChirpKernels.WAVE_PULSE50:
            return np.where(normalizedPhases < 0.5, 1.0, -1.0)
        if waveId == ChirpKernels.WAVE_PULSE25:
            return np.where(normalizedPhases < 0.25, 1.0, -1.0)
        if waveId == ChirpKernels.WAVE_PULSE12:
            return np.where(normalizedPhases < 0.125, 1.0, -1.0)
        if waveId == ChirpKernels.WAVE_TRIANGLE:
            return 1.0 - (4.0 * np.abs(normalizedPhases - 0.5))
        if waveId == ChirpKernels.WAVE_SAW:
            return (normalizedPhases * 2.0) - 1.0
        if waveId == ChirpKernels.WAVE_SAW_AA:
            return ((normalizedPhases * 2.0) - 1.0) - self.GetPolyBlepValues(normalizedPhases, phaseIncrement)
        if waveId in (
                ChirpKernels.WAVE_PULSE50_AA,
                ChirpKernels.WAVE_PULSE25_AA,
                ChirpKernels.WAVE_PULSE12_AA
                ):
            if waveId == ChirpKernels.WAVE_PULSE50_AA:
                width = 0.5
            elif waveId == ChirpKernels.WAVE_PULSE25_AA:
                width = 0.25
            else:
                width = 0.125

            samples = np.where(normalizedPhases < width, 1.0, -1.0)
            samples += self.GetPolyBlepValues(normalizedPhases, phaseIncrement)
            samples -= self.GetPolyBlepValues(np.mod(normalizedPhases - width, 1.0), phaseIncrement)
            return samples
        if waveId == ChirpKernels.WAVE_TRIANGLE_AA:
            if phaseIncrement == 0.0:
                lowerTableIndex = len(ChirpKernels.TRIANGLE_HARMONIC_LIMITS) - 1
                upperTableIndex = lowerTableIndex
                tableBlend = 0.0
            else:
                maximumHarmonic = 0.5 / abs(phaseIncrement)
                lowerTableIndex = 0
                upperTableIndex = 0
                for index, harmonicLimit in enumerate(ChirpKernels.TRIANGLE_HARMONIC_LIMITS[1:], start = 1):
                    if harmonicLimit <= maximumHarmonic:
                        lowerTableIndex = index
                        upperTableIndex = index
                    else:
                        upperTableIndex = index
                        break
                lowerLimit = ChirpKernels.TRIANGLE_HARMONIC_LIMITS[lowerTableIndex]
                upperLimit = ChirpKernels.TRIANGLE_HARMONIC_LIMITS[upperTableIndex]
                tableBlend = 0.0
                if upperLimit > lowerLimit:
                    tableBlend = max(
                        0.0,
                        min(1.0, (maximumHarmonic - lowerLimit) / (upperLimit - lowerLimit))
                    )

            tablePositions = normalizedPhases * ChirpKernels.TRIANGLE_TABLE_SIZE
            firstIndices = tablePositions.astype(np.int64) % ChirpKernels.TRIANGLE_TABLE_SIZE
            secondIndices = (firstIndices + 1) % ChirpKernels.TRIANGLE_TABLE_SIZE
            fractions = tablePositions - firstIndices
            lowerTable = ChirpKernels.TRIANGLE_TABLES[lowerTableIndex]
            lowerValues = lowerTable[firstIndices] + (
                (lowerTable[secondIndices] - lowerTable[firstIndices]) * fractions
            )
            if upperTableIndex == lowerTableIndex:
                return lowerValues

            upperTable = ChirpKernels.TRIANGLE_TABLES[upperTableIndex]
            upperValues = upperTable[firstIndices] + (
                (upperTable[secondIndices] - upperTable[firstIndices]) * fractions
            )
            return lowerValues + ((upperValues - lowerValues) * tableBlend)

        raise ValueError("Unknown built-in wave ID: " + str(waveId))

    def RenderWave(self, wave, frequency, frameCount, phaseDegrees = 0.0):
        wave = self.GetWave(wave)
        if isinstance(frameCount, bool) or not isinstance(frameCount, Integral):
            raise TypeError("frameCount must be an integer")
        if frameCount < 0:
            raise ValueError("frameCount must not be negative")
        if isinstance(frequency, bool) or not isinstance(frequency, Real):
            raise TypeError("frequency must be numeric")
        if isinstance(phaseDegrees, bool) or not isinstance(phaseDegrees, Real):
            raise TypeError("phaseDegrees must be numeric")

        frequency = float(frequency)
        phaseDegrees = float(phaseDegrees)
        if not math.isfinite(frequency):
            raise ValueError("frequency must be finite")
        if not math.isfinite(phaseDegrees):
            raise ValueError("phaseDegrees must be finite")
        frequency = max(0.0, frequency)
        if frameCount == 0:
            return np.empty(0, dtype = np.float64)

        phaseOffset = (phaseDegrees / 360.0) % 1.0
        phases = phaseOffset + ((np.arange(frameCount, dtype = np.float64) * frequency) / self.sampleRate)
        if isinstance(wave, WaveTable):
            return wave.GetValues(phases)

        waveId = self.GetWaveId(wave)
        if waveId is not None:
            return self.RenderBuiltIn(waveId, phases, frequency / self.sampleRate)

        if frequency > 0.0:
            times = (np.arange(frameCount, dtype = np.float64) / self.sampleRate) + (phaseOffset / frequency)
            return np.fromiter((wave(time, frequency) for time in times), dtype = np.float64, count = frameCount)

        return np.fromiter(
            (wave(phaseOffset, 1.0) for _ in range(frameCount)),
            dtype = np.float64,
            count = frameCount
        )

# -----------------------------------
# Noise Waves
# -----------------------------------

    def Noise(self, time, frequency = None):
        return (self.random.random() * 2.0) - 1.0

    def GetFilterCutoff(self, frequency, default = 1000.0):
        if frequency is None:
            return default

        nyquist = self.sampleRate * 0.5
        return max(1.0, min(nyquist * 0.95, frequency))

    def LowPassFilter(self, sample, cutoff, stateKey):
        cutoff = self.GetFilterCutoff(cutoff)
        alpha = 1.0 - math.exp((-2.0 * math.pi * cutoff) / self.sampleRate)
        previous = self.filterStates.get(stateKey, 0.0)
        current = previous + (alpha * (sample - previous))
        self.filterStates[stateKey] = current
        return current

    def HighPassFilter(self, sample, cutoff, stateKey):
        return sample - self.LowPassFilter(sample, cutoff, stateKey + ".lowPass")

    def BandPassFilter(self, sample, centerFreq, stateKey, bandwidth = 2.0):
        centerFreq = self.GetFilterCutoff(centerFreq)
        spread = math.sqrt(max(1.01, bandwidth))
        lowCutoff = self.GetFilterCutoff(centerFreq / spread)
        highCutoff = self.GetFilterCutoff(centerFreq * spread)
        if highCutoff < lowCutoff:
            lowCutoff, highCutoff = highCutoff, lowCutoff

        highPassed = self.HighPassFilter(sample, lowCutoff, stateKey + ".highPass")
        return self.LowPassFilter(highPassed, highCutoff, stateKey + ".lowPass")

    def NoiseLP(self, time, frequency = None):
        rawNoise = (self.random.random() * 2.0) - 1.0
        return self.LowPassFilter(rawNoise, self.GetFilterCutoff(frequency, 1000.0), "noise.lowPass")

    def NoiseHP(self, time, frequency = None):
        rawNoise = (self.random.random() * 2.0) - 1.0
        return self.HighPassFilter(rawNoise, self.GetFilterCutoff(frequency, 1000.0), "noise.highPass")

    def NoiseBP(self, time, frequency = None):
        rawNoise = (self.random.random() * 2.0) - 1.0
        return self.BandPassFilter(rawNoise, self.GetFilterCutoff(frequency, 1000.0), "noise.bandPass")

    def NoiseStep(self, time, frequency = 4000.0):
        clockRate = 4000.0 if frequency is None else max(1.0, frequency)
        samplesPerStep = max(1, int(self.sampleRate / clockRate))
        sampleIndex = int(round(time * self.sampleRate))

        if sampleIndex == 0 or (
            sampleIndex != self.stepNoiseSampleIndex and
            sampleIndex % samplesPerStep == 0
        ):
            firstSample = (self.random.random() * 2.0) - 1.0
            secondSample = (self.random.random() * 2.0) - 1.0
            self.stepNoiseValue = (firstSample + secondSample) * 0.5

        self.stepNoiseSampleIndex = sampleIndex
        return self.stepNoiseValue

    def NoiseQuanta(self, time, frequency = 4000.0):
        updateRate = 4000.0 if frequency is None else max(0.0, frequency)
        updateProbability = min(1.0, updateRate / self.sampleRate)
        sampleIndex = int(round(time * self.sampleRate))

        if sampleIndex != self.quantaNoiseSampleIndex and (
                sampleIndex == 0 or self.random.random() < updateProbability
                ):
            self.quantaNoiseValue = 1.0 if self.random.random() >= 0.5 else -1.0

        self.quantaNoiseSampleIndex = sampleIndex
        return self.quantaNoiseValue

# -----------------------------------
# Modulation
# -----------------------------------

    def GetLfoValue(self, wave, phase, phaseIncrement = None):
        if isinstance(wave, WaveTable):
            value = wave.GetValue(phase / (2.0 * math.pi))
            return max(-1.0, min(1.0, value))

        waveFunction = getattr(wave, "__func__", wave)
        if waveFunction == self.Sine.__func__:
            return math.sin(phase)

        normalizedPhase = (phase / (2.0 * math.pi)) % 1.0
        antiAliasedWaveIds = (
            ChirpKernels.WAVE_SAW_AA,
            ChirpKernels.WAVE_PULSE50_AA,
            ChirpKernels.WAVE_PULSE25_AA,
            ChirpKernels.WAVE_PULSE12_AA,
            ChirpKernels.WAVE_TRIANGLE_AA,
        )
        waveId = self.GetWaveId(wave)
        if waveId in antiAliasedWaveIds and phaseIncrement is not None:
            value = self.RenderBuiltIn(
                waveId,
                np.asarray([normalizedPhase], dtype = np.float64),
                abs(phaseIncrement) / (2.0 * math.pi)
            )[0]
        else:
            value = wave(normalizedPhase, 1.0)

        return max(-1.0, min(1.0, value))

    def GetMinimumPhase(self, wave, frequency = 0.0):
        wave = self.GetWave(wave)
        if isinstance(wave, WaveTable):
            minimumIndex = int(np.argmin(wave.samples))
            return (minimumIndex / len(wave.samples)) * (2.0 * math.pi)

        waveId = self.GetWaveId(wave)
        phaseIncrement = abs(float(frequency)) / self.sampleRate
        minimumPhases = {
            ChirpKernels.WAVE_SINE: 0.75,
            ChirpKernels.WAVE_PULSE50: 0.5,
            ChirpKernels.WAVE_PULSE25: 0.25,
            ChirpKernels.WAVE_PULSE12: 0.125,
            ChirpKernels.WAVE_TRIANGLE: 0.0,
            ChirpKernels.WAVE_SAW: 0.0,
            ChirpKernels.WAVE_PULSE50_AA: 0.5 + phaseIncrement,
            ChirpKernels.WAVE_PULSE25_AA: 0.25 + phaseIncrement,
            ChirpKernels.WAVE_PULSE12_AA: 0.125 + phaseIncrement,
            ChirpKernels.WAVE_SAW_AA: phaseIncrement,
            ChirpKernels.WAVE_TRIANGLE_AA: 0.0,
        }
        normalizedPhase = minimumPhases.get(waveId, 0.0) % 1.0
        return normalizedPhase * (2.0 * math.pi)


__all__ = [
    "ChirpOscillator",
    "WaveTable",
]
