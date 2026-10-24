from collections import deque
import math
from numbers import Integral, Real
import threading

import numpy as np


class ChirpVoiceHandle:
    def __init__(self, mixer, voiceId, doneEvent):
        self.mixer = mixer
        self.voiceId = voiceId
        self.doneEvent = doneEvent

    def Stop(self):
        self.mixer.StopVoice(self.voiceId)

    def Wait(self, timeout = None):
        return self.doneEvent.wait(timeout)

    def IsPlaying(self):
        return self.mixer.IsVoicePlaying(self.voiceId)


class ChirpVoice:
    def __init__(self, voiceId, voiceIndex, samples, volume, startOrder):
        self.voiceId = voiceId
        self.voiceIndex = voiceIndex
        self.samples = samples
        self.volume = volume
        self.startOrder = startOrder
        self.sampleIndex = 0
        self.doneEvent = threading.Event()
        self.handle = None


class ChirpMixer:
    MAX_QUEUED_VOICES = 256

    def __init__(self, channels = 2, voices = 16, volume = 1.0, blockFrames = 1024):
        if isinstance(channels, bool) or not isinstance(channels, Integral) or channels not in (1, 2):
            raise ValueError("ChirpMixer only supports 1 or 2 channels")

        self.channels = int(channels)
        self.voiceLimit = self.ValidateInteger(voices, "voices", 1)
        self.blockFrames = self.ValidateInteger(blockFrames, "blockFrames", 1)
        self.blockSamples = self.blockFrames * self.channels
        self.voiceSlots = [None] * self.voiceLimit
        self.voiceQueues = [deque() for _ in range(self.voiceLimit)]
        self.activeVoices = []
        self.nextVoiceId = 1
        self.nextStartOrder = 1
        self.lock = threading.RLock()
        self.scratchBuffer = np.empty(self.blockSamples, dtype = np.float64)
        self.SetVolume(volume)

# -----------------------------------
# Mixer Configuration
# -----------------------------------

    @staticmethod
    def ValidateNumber(value, name):
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(name + " must be numeric")
        value = float(value)
        if not math.isfinite(value):
            raise ValueError(name + " must be finite")
        return value

    @staticmethod
    def ValidateInteger(value, name, minimum = None):
        if isinstance(value, bool) or not isinstance(value, Integral):
            raise TypeError(name + " must be an integer")
        value = int(value)
        if minimum is not None and value < minimum:
            raise ValueError(name + " must be at least " + str(minimum))
        return value

    def SetVolume(self, volume):
        volume = self.ValidateNumber(volume, "volume")
        with self.lock:
            self.volume = max(0.0, min(1.0, volume)) ** 2.0

    def ValidateSamples(self, samples):
        samples = np.array(samples, dtype = np.float64, copy = True, order = "C").reshape(-1)
        if len(samples) % self.channels != 0:
            raise ValueError("Samples do not contain complete frames")
        if not np.all(np.isfinite(samples)):
            raise ValueError("Samples must contain only finite values")

        return samples

# -----------------------------------
# Voice Management
# -----------------------------------

    def GetVoiceIndex(self, voice):
        if voice is None:
            return None

        voiceIndex = self.ValidateInteger(voice, "voice")
        if (voiceIndex < 0 or voiceIndex >= self.voiceLimit):
            raise ValueError("Voice must be between 0 and " + str(self.voiceLimit - 1))

        return voiceIndex

    def GetFreeVoiceIndex(self):
        for voiceIndex, activeVoice in enumerate(self.voiceSlots):
            if activeVoice is None:
                return voiceIndex

        return None

    def CreateVoice(self, voiceIndex, samples, volume):
        voiceId = self.nextVoiceId
        self.nextVoiceId += 1
        startOrder = self.nextStartOrder
        self.nextStartOrder += 1
        voice = ChirpVoice(voiceId, voiceIndex, samples, max(0.0, min(1.0, volume)) ** 2.0, startOrder)
        voice.handle = ChirpVoiceHandle(self, voiceId, voice.doneEvent)
        return voice

    def StartVoice(self, voice):
        if len(voice.samples) == 0:
            voice.doneEvent.set()
            return

        self.voiceSlots[voice.voiceIndex] = voice
        self.activeVoices.append(voice)

    def CompleteVoice(self, voice):
        voiceIndex = voice.voiceIndex
        if self.voiceSlots[voiceIndex] is voice:
            self.voiceSlots[voiceIndex] = None
        if voice in self.activeVoices:
            self.activeVoices.remove(voice)

        voice.doneEvent.set()

    def ClearQueues(self):
        for queuedVoices in self.voiceQueues:
            while queuedVoices:
                queuedVoices.popleft().doneEvent.set()

# -----------------------------------
# Playback
# -----------------------------------

    def Play(self, samples, volume = 1.0, voice = None):
        samples = self.ValidateSamples(samples)
        volume = self.ValidateNumber(volume, "volume")
        voiceIndex = self.GetVoiceIndex(voice)

        with self.lock:
            if len(samples) == 0:
                if voiceIndex is None:
                    voiceIndex = 0
                newVoice = self.CreateVoice(voiceIndex, samples, volume)
                self.StartVoice(newVoice)
                return newVoice.handle

            if voiceIndex is None:
                voiceIndex = self.GetFreeVoiceIndex()
                if voiceIndex is None:
                    oldestVoice = min(self.activeVoices, key = lambda activeVoice: (activeVoice.startOrder))
                    voiceIndex = oldestVoice.voiceIndex
                    self.CompleteVoice(oldestVoice)
            else:
                activeVoice = self.voiceSlots[voiceIndex]
                if activeVoice is not None:
                    self.CompleteVoice(activeVoice)

            newVoice = self.CreateVoice(voiceIndex, samples, volume)
            self.StartVoice(newVoice)
            return newVoice.handle

    def PlayQueued(self, samples, volume = 1.0, voice = None):
        samples = self.ValidateSamples(samples)
        volume = self.ValidateNumber(volume, "volume")
        voiceIndex = self.GetVoiceIndex(voice)

        with self.lock:
            if voiceIndex is None:
                voiceIndex = self.GetFreeVoiceIndex()
                if voiceIndex is None:
                    voiceIndex = 0

            if (self.voiceSlots[voiceIndex] is None and not self.voiceQueues[voiceIndex]):
                newVoice = self.CreateVoice(voiceIndex, samples, volume)
                self.StartVoice(newVoice)
            else:
                if len(self.voiceQueues[voiceIndex]) >= self.MAX_QUEUED_VOICES:
                    raise OverflowError("Voice queue is full")
                newVoice = self.CreateVoice(voiceIndex, samples, volume)
                self.voiceQueues[voiceIndex].append(newVoice)

            return newVoice.handle

    def PlaySolo(self, samples, volume = 1.0):
        samples = self.ValidateSamples(samples)
        volume = self.ValidateNumber(volume, "volume")

        with self.lock:
            self.ClearQueues()
            for activeVoice in list(self.activeVoices):
                self.CompleteVoice(activeVoice)

            newVoice = self.CreateVoice(0, samples, volume)
            self.StartVoice(newVoice)
            return newVoice.handle

# -----------------------------------
# Mixing
# -----------------------------------

    def MixBlock(self, output = None):
        if output is None:
            output = np.zeros(self.blockSamples, dtype = np.float64)
        else:
            output = np.asarray(output)
            if output.dtype != np.float64:
                raise TypeError("Output buffer must use float64 samples")
            if not output.flags.c_contiguous or not output.flags.writeable:
                raise ValueError("Output buffer must be writable and contiguous")
            output = output.reshape(-1)
            if len(output) != self.blockSamples:
                raise ValueError("Output buffer has the wrong size")
            output.fill(0.0)

        with self.lock:
            for voiceIndex in range(self.voiceLimit):
                blockSampleIndex = 0

                while blockSampleIndex < self.blockSamples:
                    while self.voiceSlots[voiceIndex] is None and self.voiceQueues[voiceIndex]:
                        self.StartVoice(self.voiceQueues[voiceIndex].popleft())
                    activeVoice = self.voiceSlots[voiceIndex]
                    if activeVoice is None:
                        break

                    remainingSamples = (len(activeVoice.samples) - activeVoice.sampleIndex)
                    mixedSampleCount = min(remainingSamples, self.blockSamples - blockSampleIndex)
                    sourceEnd = (activeVoice.sampleIndex + mixedSampleCount)
                    targetEnd = (blockSampleIndex + mixedSampleCount)
                    np.multiply(
                        activeVoice.samples[activeVoice.sampleIndex:sourceEnd],
                        activeVoice.volume,
                        out = self.scratchBuffer[:mixedSampleCount]
                    )
                    with np.errstate(over = "ignore", invalid = "ignore"):
                        output[blockSampleIndex:targetEnd] += self.scratchBuffer[:mixedSampleCount]
                    activeVoice.sampleIndex = sourceEnd
                    blockSampleIndex = targetEnd

                    if (activeVoice.sampleIndex >= len(activeVoice.samples)):
                        self.CompleteVoice(activeVoice)

            maximum = np.finfo(np.float64).max
            np.nan_to_num(output, copy = False, nan = 0.0, posinf = maximum, neginf = -maximum)
            output *= self.volume

        return output

# -----------------------------------
# Playback Control
# -----------------------------------

    def StopVoice(self, voiceId):
        with self.lock:
            for activeVoice in list(self.activeVoices):
                if activeVoice.voiceId == voiceId:
                    self.CompleteVoice(activeVoice)
                    return True

            for queuedVoices in self.voiceQueues:
                for queuedVoice in list(queuedVoices):
                    if queuedVoice.voiceId == voiceId:
                        queuedVoices.remove(queuedVoice)
                        queuedVoice.doneEvent.set()
                        return True

        return False

    def IsVoicePlaying(self, voiceId):
        with self.lock:
            for activeVoice in self.activeVoices:
                if activeVoice.voiceId == voiceId:
                    return True

            for queuedVoices in self.voiceQueues:
                for queuedVoice in queuedVoices:
                    if queuedVoice.voiceId == voiceId:
                        return True

        return False

    def StopAll(self):
        with self.lock:
            self.ClearQueues()
            for activeVoice in list(self.activeVoices):
                self.CompleteVoice(activeVoice)

    def GetStats(self):
        with self.lock:
            return {
                "activeVoices": len(self.activeVoices),
                "queuedVoices": sum(len(queue) for queue in self.voiceQueues),
            }


__all__ = [
    "ChirpMixer",
    "ChirpVoiceHandle",
]
