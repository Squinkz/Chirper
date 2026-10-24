import time
import weakref
from numbers import Integral

import numpy as np

from ..io import ChirpAudioData, ChirpFile
from .ChirpMixer import ChirpMixer
from .ChirpOutput import WinMMOutput


class ChirpPlayer:
    SAMPLE_RATE = 44100
    BITS_PER_SAMPLE = 16
    BLOCK_FRAMES = 1024

    def __init__(
            self, channels = 2, sampleRate = 44100,
            bitsPerSample = 16, voices = 16,
            volume = 1.0, enabled = True,
            blockFrames = BLOCK_FRAMES, outputFactory = None
            ):
        self.ValidateFormat(channels, sampleRate, bitsPerSample)

        self.enabled = enabled
        self.closed = False
        self.channels = channels
        self.sampleRate = sampleRate
        self.bitsPerSample = bitsPerSample
        self.voiceLimit = ChirpMixer.ValidateInteger(voices, "voices", 1)
        self.blockFrames = ChirpMixer.ValidateInteger(blockFrames, "blockFrames", 1)
        self.outputError = None
        self.mixer = ChirpMixer(
            channels = channels,
            voices = self.voiceLimit,
            volume = volume,
            blockFrames = self.blockFrames
        )
        if self.enabled:
            if outputFactory is None:
                outputFactory = WinMMOutput
            playerReference = weakref.ref(self)

            def HandleFailure(error):
                player = playerReference()
                if player is not None:
                    player.HandleOutputFailure(error)

            self.output = outputFactory(
                renderCallback = self.mixer.MixBlock,
                failureCallback = HandleFailure,
                channels = channels,
                sampleRate = sampleRate,
                bitsPerSample = bitsPerSample,
                blockFrames = self.blockFrames
            )
        else:
            self.output = None

# -----------------------------------
# Player Configuration
# -----------------------------------

    def ValidateFormat(self, channels, sampleRate, bitsPerSample):
        if isinstance(channels, bool) or not isinstance(channels, Integral) or channels not in (1, 2):
            raise ValueError("ChirpPlayer only supports 1 or 2 channels")
        sampleRate = ChirpMixer.ValidateInteger(sampleRate, "sampleRate")
        bitsPerSample = ChirpMixer.ValidateInteger(bitsPerSample, "bitsPerSample")
        if sampleRate != self.SAMPLE_RATE:
            raise ValueError("ChirpPlayer only supports 44100 Hz PCM")
        if bitsPerSample != self.BITS_PER_SAMPLE:
            raise ValueError("ChirpPlayer only supports 16-bit PCM")

    def Load(self, path):
        return ChirpFile.Load(path)

    def SetVolume(self, volume):
        self.mixer.SetVolume(volume)

    def HandleOutputFailure(self, error):
        self.outputError = error
        self.mixer.StopAll()

    def EnsureOutput(self):
        if self.closed:
            raise RuntimeError("ChirpPlayer is closed")
        if self.outputError is not None:
            raise self.outputError
        if self.output is not None:
            self.output.Start()

# -----------------------------------
# Playback
# -----------------------------------

    def Play(self, sound, volume = 1.0, blocking = False, voice = None):
        samples = self.GetPlaybackSamples(sound)
        if not self.enabled:
            return None

        handle = self.mixer.Play(samples, volume, voice)
        try:
            self.EnsureOutput()
        except Exception:
            handle.Stop()
            raise

        if blocking:
            handle.Wait()
            time.sleep(self.output.GetLatency())
            if self.outputError is not None:
                raise self.outputError

        return handle

    def PlayQueued(self, sound, volume = 1.0, voice = None):
        samples = self.GetPlaybackSamples(sound)
        if not self.enabled:
            return None

        handle = self.mixer.PlayQueued(samples, volume, voice)
        try:
            self.EnsureOutput()
        except Exception:
            handle.Stop()
            raise

        return handle

    def PlaySolo(self, sound, volume = 1.0, blocking = False):
        samples = self.GetPlaybackSamples(sound)
        if not self.enabled:
            return None

        handle = None
        try:
            handle = self.output.Flush(lambda: self.mixer.PlaySolo(samples, volume))
            self.EnsureOutput()
        except Exception:
            if handle is not None:
                handle.Stop()
            raise

        if blocking:
            handle.Wait()
            time.sleep(self.output.GetLatency())
            if self.outputError is not None:
                raise self.outputError

        return handle

# -----------------------------------
# Playback Data
# -----------------------------------

    def GetPlaybackSamples(self, sound):
        if (
                hasattr(sound, "_samples")
                and hasattr(sound, "channels")
                and hasattr(sound, "sampleRate")
                ):
            samples = np.asarray(sound._samples, dtype = np.float64).reshape(-1)
            channels = sound.channels
            sampleRate = sound.sampleRate
            bitsPerSample = self.BITS_PER_SAMPLE
        else:
            pcm, channels, sampleRate, bitsPerSample = self.GetPlaybackData(sound)
            samples = ChirpAudioData.PcmToSamples(
                pcm, channels, bitsPerSample
            )

        self.ValidateFormat(channels, sampleRate, bitsPerSample)
        if len(samples) % channels != 0:
            raise ValueError("PCM data does not contain complete sample frames")

        if channels != self.channels:
            samples = ChirpAudioData.ConvertChannels(
                samples, channels, self.channels
            )

        return samples

    def GetPlaybackData(self, sound):
        if isinstance(sound, (bytes, bytearray, memoryview)):
            pcm = bytes(sound)
            channels = self.channels
            sampleRate = self.sampleRate
            bitsPerSample = self.bitsPerSample
        elif (hasattr(sound, "pcm") and hasattr(sound, "metadata")):
            pcm = bytes(sound.pcm)
            channels = sound.channels
            sampleRate = sound.sampleRate
            bitsPerSample = sound.bitsPerSample
        else:
            raise TypeError("Expected bytes or Sound")

        bytesPerSample = bitsPerSample // 8
        frameSize = channels * bytesPerSample
        if (frameSize <= 0 or len(pcm) % frameSize != 0):
            raise ValueError("PCM data does not contain complete sample frames")

        return (pcm, channels, sampleRate, bitsPerSample)

# -----------------------------------
# Player Control
# -----------------------------------

    def GetStats(self):
        mixerStats = self.mixer.GetStats()
        if self.output is None:
            return {
                "blockFrames": self.blockFrames,
                "activeVoices": mixerStats["activeVoices"],
                "queuedVoices": mixerStats["queuedVoices"],
            }

        stats = self.output.GetStats()
        stats["activeVoices"] = mixerStats["activeVoices"]
        stats["queuedVoices"] = mixerStats["queuedVoices"]
        return stats

    def StopAll(self):
        self.mixer.StopAll()
        if self.output is not None:
            self.output.Flush()

    def Close(self):
        if self.closed:
            return

        self.mixer.StopAll()
        if self.output is not None:
            self.output.Close()
        self.closed = True

    def __del__(self):
        try:
            self.Close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exceptionType, exception, traceback):
        self.Close()


__all__ = [
    "ChirpPlayer",
]
