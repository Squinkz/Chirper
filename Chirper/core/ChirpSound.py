import copy
from numbers import Integral

import numpy as np

from ..io import ChirpFile
from .ChirpConstants import Q
from .ChirpDSP import ChirpDSP
from .ChirpSynth import ChirpSynth


class Sound:
    SAMPLE_RATE = 44100
    BITS_PER_SAMPLE = 16
    CHANNELS = 2

    def __init__(
            self, data = None, channels = None, layered = True, *,
            pcm = None, samples = None, metadata = None
            ):
        if metadata is None:
            metadata = {}
        if not isinstance(metadata, dict):
            raise TypeError("metadata must be a dictionary")
        metadata = copy.deepcopy(metadata)

        if pcm is not None and samples is not None:
            raise ValueError("Provide pcm or samples, not both")
        if data is not None and (pcm is not None or samples is not None):
            raise ValueError("Provide data, pcm, or samples, not more than one")

        if pcm is not None:
            if not isinstance(pcm, (bytes, bytearray, memoryview)):
                raise TypeError("PCM data must be bytes-like")
            self._pcm = bytes(pcm)
            self._metadata = metadata
            self.sampleRate = self._metadata.get("sampleRate", self.SAMPLE_RATE)
            defaultChannels = self.CHANNELS if channels is None else channels
            metadataChannels = self._metadata.get("channels")
            if channels is not None and metadataChannels is not None and channels != metadataChannels:
                raise ValueError("channels disagrees with PCM metadata")
            self.channels = defaultChannels if metadataChannels is None else metadataChannels
            self.bitsPerSample = self._metadata.get("bitsPerSample", self.BITS_PER_SAMPLE)
            if (
                    isinstance(self.sampleRate, bool)
                    or not isinstance(self.sampleRate, Integral)
                    or self.sampleRate != self.SAMPLE_RATE
                    ):
                raise ValueError("Unsupported sample rate: " + str(self.sampleRate))
            if (
                    isinstance(self.bitsPerSample, bool)
                    or not isinstance(self.bitsPerSample, Integral)
                    or self.bitsPerSample != self.BITS_PER_SAMPLE
                    ):
                raise ValueError("Unsupported bit depth: " + str(self.bitsPerSample))
            ChirpFile.ValidatePcm(self._pcm, self.channels, self.bitsPerSample)
            dsp = ChirpDSP(channels = self.channels)
            self._samples = dsp.BytesToSamples(self._pcm)
            self._samples.setflags(write = False)
            self.duration = ChirpFile.GetPcmDuration(
                self._pcm, self.channels, self.sampleRate, self.bitsPerSample
            )
            self._metadata.update(
                self.MakeMetadata(self.duration, self.channels, self.sampleRate)
            )
            return

        metadataChannels = metadata.get("channels")
        metadataSampleRate = metadata.get("sampleRate", self.SAMPLE_RATE)
        if (
                isinstance(metadataSampleRate, bool)
                or not isinstance(metadataSampleRate, Integral)
                or metadataSampleRate != self.SAMPLE_RATE
                ):
            raise ValueError("Unsupported sample rate: " + str(metadataSampleRate))
        channels = self.CHANNELS if channels is None and metadataChannels is None else (
            metadataChannels if channels is None else channels
        )
        dsp = ChirpDSP(channels = channels)
        self.channels = channels
        self.sampleRate = self.SAMPLE_RATE
        self.bitsPerSample = self.BITS_PER_SAMPLE

        if samples is None:
            if not isinstance(layered, bool):
                raise TypeError("layered must be a boolean")
            if data is None:
                data = []

            renderSamples = getattr(data, "RenderSamples", None)
            if callable(renderSamples):
                samples = renderSamples(channels = channels)
            else:
                synthesizer = ChirpSynth(channels = channels)
                if layered:
                    layers = synthesizer.RenderLayers(data)
                    samples = np.empty(0, dtype = np.float64)
                    if layers:
                        samples = np.zeros(
                            max(len(layer) for layer in layers), dtype = np.float64
                        )
                    for layer in layers:
                        samples[:len(layer)] += layer
                else:
                    samples = synthesizer.RenderSamples(data)

        self._samples = np.asarray(samples, dtype = np.float64).reshape(-1).copy()
        if len(self._samples) % self.channels != 0:
            raise ValueError("Samples do not contain complete frames")
        if not np.all(np.isfinite(self._samples)):
            raise ValueError("Samples must contain only finite values")

        self._samples.setflags(write = False)
        self._pcm = None
        self.duration = dsp.GetSampleDuration(self._samples)
        self._metadata = metadata
        self._metadata.update(
            self.MakeMetadata(self.duration, self.channels, self.sampleRate)
        )

    @property
    def pcm(self):
        if self._pcm is None:
            dsp = ChirpDSP(channels = self.channels)
            self._pcm = dsp.SamplesToBytes(self._samples)

        return self._pcm

    @property
    def samples(self):
        return self._samples.copy()

    @property
    def metadata(self):
        return copy.deepcopy(self._metadata)

# -----------------------------------
# Creation
# -----------------------------------

    @classmethod
    def SetDefaults(cls, channels = None):
        if channels is not None:
            if isinstance(channels, bool) or not isinstance(channels, Integral) or channels not in (1, 2):
                raise ValueError("Sound only supports 1 or 2 channels")
            cls.CHANNELS = int(channels)

    def MakeMetadata(self, duration, channels, sampleRate = None):
        if sampleRate is None:
            sampleRate = self.SAMPLE_RATE

        return ChirpFile.MakePcmMetadata(
            duration, channels, sampleRate, self.BITS_PER_SAMPLE
        )

    @classmethod
    def Load(cls, path):
        data = ChirpFile.Load(path)
        return cls(
            samples = data.samples, channels = data.channels,
            metadata = data.metadata
        )

    @classmethod
    def LoadWav(cls, path):
        data = ChirpFile.ReadWav(path)
        return cls(
            samples = data.samples, channels = data.channels,
            metadata = data.metadata
        )

    def Save(self, path):
        return ChirpFile.Write(path, self._samples, self._metadata)

    def SaveWav(self, path):
        return ChirpFile.WriteWav(path, self.pcm, self._metadata)

    def CopyWithSamples(self, samples):
        return Sound(
            samples = samples, channels = self.channels,
            metadata = self._metadata
        )

# -----------------------------------
# Mix Controls
# -----------------------------------

    @classmethod
    def Mix(cls, sounds, channels = None, mixGain = 0.707):
        sounds = list(sounds)
        if len(sounds) == 0:
            raise ValueError("Cannot mix an empty sound list")

        first = sounds[0]
        channels = cls.CHANNELS if channels is None else channels
        if isinstance(channels, bool) or not isinstance(channels, Integral) or channels not in (1, 2):
            raise ValueError("Sound only supports 1 or 2 channels")
        channels = int(channels)

        sampleRate = first.sampleRate

        for sound in sounds:
            if sound.sampleRate != sampleRate:
                raise ValueError("Cannot mix sounds with different sample rates")

        dsp = ChirpDSP(channels = channels)
        sampleArrays = []
        for sound in sounds:
            if sound.channels == channels:
                sampleArrays.append(sound._samples)
            elif channels == 1:
                sourceDSP = ChirpDSP(channels = sound.channels)
                sampleArrays.append(sourceDSP.ApplySoundMono(sound._samples))
            else:
                sourceDSP = ChirpDSP(channels = sound.channels)
                sampleArrays.append(sourceDSP.ApplySoundStereo(sound._samples))

        samples = dsp.MixSamples(sampleArrays, mixGain)
        return cls(
            samples = samples, channels = channels,
            metadata = first.metadata
        )

    def Append(self, sound, crossfade = 0.0, easing = "equalPower"):
        if not isinstance(sound, Sound):
            raise TypeError("Append requires a Sound")
        if sound.sampleRate != self.sampleRate:
            raise ValueError("Cannot append sounds with different sample rates")

        channels = max(self.channels, sound.channels)
        firstSamples = self._samples
        secondSamples = sound._samples

        if self.channels != channels:
            firstSamples = ChirpDSP(channels = self.channels).ApplySoundStereo(firstSamples)
        if sound.channels != channels:
            secondSamples = ChirpDSP(channels = sound.channels).ApplySoundStereo(secondSamples)

        dsp = ChirpDSP(channels = channels)
        samples = dsp.ApplySoundAppend(firstSamples, secondSamples, crossfade, easing)
        return Sound(
            samples = samples, channels = channels,
            metadata = self.metadata
        )

    def Cut(self, duration, fade = 0.003):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundCut(self._samples, duration, fade)
        return self.CopyWithSamples(samples)

    def FadeIn(self, duration, easing = "linear"):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundFadeIn(self._samples, duration, easing)
        return self.CopyWithSamples(samples)

    def FadeOut(self, duration, easing = "linear"):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundFadeOut(self._samples, duration, easing)
        return self.CopyWithSamples(samples)

    def Reverse(self):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundReverse(self._samples)
        return self.CopyWithSamples(samples)

    def Invert(self):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundGain(self._samples, -1.0)
        return self.CopyWithSamples(samples)

    def Gain(self, amount):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundGain(self._samples, amount, 0.0)
        return self.CopyWithSamples(samples)

    def Debias(self):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundDebias(self._samples)
        return self.CopyWithSamples(samples)

    def Clip(self, limit = 1.0):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundClip(self._samples, limit)
        return self.CopyWithSamples(samples)

    def Normalize(self, headroom = 0.0):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.NormalizeSamples(self._samples, headroom)
        return self.CopyWithSamples(samples)

    def SoftClip(self, drive = 2.0, mix = 1.0):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundSoftClip(self._samples, drive, mix)
        return self.CopyWithSamples(samples)

    def Ring(self, freq, mix = 1.0, wave = "Sine"):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundRing(self._samples, freq, mix, wave)
        return self.CopyWithSamples(samples)

    def Chorus(
            self, rate = 0.8, depth = 0.003, delay = 0.015,
            voices = 2, feedback = 0.0, spread = 1.0, mix = 0.5, wave = "Sine"
            ):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundChorus(
            self._samples, rate, depth, delay, voices, feedback, spread, mix, wave
        )
        return self.CopyWithSamples(samples)

    def Phaser(
            self, rate = 0.5, minFreq = 300.0, maxFreq = 1600.0,
            stages = 6, feedback = 0.2, spread = 1.0, mix = 0.5, wave = "Sine"
            ):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundPhaser(
            self._samples, rate, minFreq, maxFreq, stages, feedback, spread, mix, wave
        )
        return self.CopyWithSamples(samples)

    def Pan(self, amount):
        dsp = ChirpDSP(channels = self.channels)
        if self.channels == 1:
            samples = dsp.ApplySoundStereo(self._samples, amount)
            return Sound(
                samples = samples, channels = 2,
                metadata = self.metadata
            )

        samples = dsp.ApplySoundPan(self._samples, amount)
        return self.CopyWithSamples(samples)

    def AutoPan(self, depth = 1.0, rate = 1.0, wave = "Sine", offset = 0.0):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundAutoPan(self._samples, depth, rate, wave, offset)
        return Sound(
            samples = samples, channels = 2,
            metadata = self.metadata
        )

    def Mono(self):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundMono(self._samples)
        return Sound(
            samples = samples, channels = 1,
            metadata = self.metadata
        )

    def Stereo(self):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundStereo(self._samples)
        return Sound(
            samples = samples, channels = 2,
            metadata = self.metadata
        )

# -----------------------------------
# EQ
# -----------------------------------

    def LowPass(self, freq, q = Q.MID):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundLowPass(self._samples, freq, q)
        return self.CopyWithSamples(samples)

    def HighPass(self, freq, q = Q.MID):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundHighPass(self._samples, freq, q)
        return self.CopyWithSamples(samples)

    def BandPass(self, freq, q = Q.MID):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundBandPass(self._samples, freq, q)
        return self.CopyWithSamples(samples)

    def Notch(self, freq, q = Q.MID):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundNotch(self._samples, freq, q)
        return self.CopyWithSamples(samples)

    def Peak(self, freq, db, q = Q.MID):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundPeak(self._samples, freq, db, q)
        return self.CopyWithSamples(samples)

    def LowShelf(self, freq, db, q = Q.MID):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundLowShelf(self._samples, freq, db, q)
        return self.CopyWithSamples(samples)

    def HighShelf(self, freq, db, q = Q.MID):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundHighShelf(self._samples, freq, db, q)
        return self.CopyWithSamples(samples)

    # Sweeps

    def LowPassSweep(self, startFreq, endFreq, q = Q.MID, easing = "linear"):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundLowPassSweep(self._samples, startFreq, endFreq, q, easing)
        return self.CopyWithSamples(samples)

    def HighPassSweep(self, startFreq, endFreq, q = Q.MID, easing = "linear"):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundHighPassSweep(self._samples, startFreq, endFreq, q, easing)
        return self.CopyWithSamples(samples)

    def BandPassSweep(self, startFreq, endFreq, q = Q.MID, easing = "linear"):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundBandPassSweep(self._samples, startFreq, endFreq, q, easing)
        return self.CopyWithSamples(samples)

    def NotchSweep(self, startFreq, endFreq, q = Q.MID, easing = "linear"):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundNotchSweep(self._samples, startFreq, endFreq, q, easing)
        return self.CopyWithSamples(samples)

    def PeakSweep(self, startFreq, endFreq, db, q = Q.MID, easing = "linear"):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundPeakSweep(self._samples, startFreq, endFreq, db, q, easing)
        return self.CopyWithSamples(samples)

    def LowShelfSweep(self, startFreq, endFreq, db, q = Q.MID, easing = "linear"):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundLowShelfSweep(self._samples, startFreq, endFreq, db, q, easing)
        return self.CopyWithSamples(samples)

    def HighShelfSweep(self, startFreq, endFreq, db, q = Q.MID, easing = "linear"):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundHighShelfSweep(self._samples, startFreq, endFreq, db, q, easing)
        return self.CopyWithSamples(samples)

# -----------------------------------
# Reverb / Delay
# -----------------------------------

    # Schroeder style reverb
    def Schroverb(self, wet = 0.35, decay = 0.72, roomSize = 1.0, tail = None):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundSchroverb(self._samples, wet, decay, roomSize, tail)
        return self.CopyWithSamples(samples)

    # A Freeverb style reverb implementation
    def Freeverb(self, wet = 0.35, decay = 0.84, damping = 0.5, width = 1.0, tail = None):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundFreeverb(self._samples, wet, decay, damping, width, tail)
        return self.CopyWithSamples(samples)

    # Rough emulation of the reverb on the Roland MT-32
    # source: https://github.com/munt/munt/blob/master/mt32emu/src/BReverbModel.cpp
    def MTVerb(self, wet = 0.35, decay = 0.72, mode = "room", tail = None):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundMTVerb(self._samples, wet, decay, mode, tail)
        return self.CopyWithSamples(samples)

    def Delay(self, delay = 0.25, decay = 0.5, count = None, extend = True):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundDelay(self._samples, (delay, decay, count, extend))
        return self.CopyWithSamples(samples)

    def PingPong(self, delay = 0.25, decay = 0.5, count = None, width = 1.0, extend = True):
        dsp = ChirpDSP(channels = self.channels)
        samples = dsp.ApplySoundPingPong(self._samples, (delay, decay, count, width, extend))
        return Sound(
            samples = samples, channels = 2,
            metadata = self.metadata
        )

__all__ = [
    "Sound",
]
