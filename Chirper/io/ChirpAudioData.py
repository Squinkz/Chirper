import math
from numbers import Integral, Real

import numpy as np


SAMPLE_RATE = 44100
BITS_PER_SAMPLE = 16
PCM_BIT_DEPTHS = (8, 16, 24)


def ValidateChannels(channels):
    if isinstance(channels, bool) or not isinstance(channels, Integral) or channels not in (1, 2):
        raise ValueError("Unsupported channel count: " + str(channels))


def ValidateSamples(samples, channels):
    ValidateChannels(channels)
    samples = np.asarray(samples, dtype = np.float64).reshape(-1)
    if len(samples) % channels != 0:
        raise ValueError("Samples do not contain complete frames")
    if not np.all(np.isfinite(samples)):
        raise ValueError("Samples must contain only finite values")


def ValidatePcm(pcm, channels, bitsPerSample = BITS_PER_SAMPLE):
    if not isinstance(pcm, (bytes, bytearray, memoryview)):
        raise TypeError("PCM data must be bytes-like")

    ValidateChannels(channels)
    if (
            isinstance(bitsPerSample, bool)
            or not isinstance(bitsPerSample, Integral)
            or bitsPerSample not in PCM_BIT_DEPTHS
            ):
        raise ValueError("Unsupported bit depth: " + str(bitsPerSample))

    frameSize = channels * (bitsPerSample // 8)
    if len(pcm) % frameSize != 0:
        raise ValueError("PCM data does not contain complete sample frames")


def SamplesToPcm(samples, channels, bitsPerSample = BITS_PER_SAMPLE):
    if (
            isinstance(bitsPerSample, bool)
            or not isinstance(bitsPerSample, Integral)
            or bitsPerSample != 16
            ):
        raise ValueError("Sample encoding only supports 16-bit PCM")

    samples = np.asarray(samples, dtype = np.float64).reshape(-1)
    ValidateSamples(samples, channels)
    clipped = np.clip(samples, -1.0, 1.0)
    return np.rint(clipped * 32767.0).astype("<i2").tobytes()


def PcmToSamples(pcm, channels, bitsPerSample = BITS_PER_SAMPLE):
    ValidatePcm(pcm, channels, bitsPerSample)
    pcm = bytes(pcm)

    if bitsPerSample == 8:
        values = np.frombuffer(pcm, dtype = np.uint8).astype(np.float64)
        return (values - 128.0) / 128.0

    if bitsPerSample == 16:
        values = np.frombuffer(pcm, dtype = "<i2").astype(np.float64)
        return np.maximum(values / 32767.0, -1.0)

    sampleBytes = np.frombuffer(pcm, dtype = np.uint8).reshape(-1, 3).astype(np.int32)
    values = sampleBytes[:, 0] | (sampleBytes[:, 1] << 8) | (sampleBytes[:, 2] << 16)
    values[values >= 0x800000] -= 0x1000000
    return np.maximum(values.astype(np.float64) / 8388607.0, -1.0)


def GetSampleDuration(samples, channels, sampleRate = SAMPLE_RATE):
    ValidateChannels(channels)
    if isinstance(sampleRate, bool) or not isinstance(sampleRate, Integral) or sampleRate <= 0:
        raise ValueError("sampleRate must be a positive integer")
    if len(samples) % channels != 0:
        raise ValueError("Samples do not contain complete frames")

    return (len(samples) // channels) / sampleRate


def GetPcmDuration(pcm, channels, sampleRate = SAMPLE_RATE, bitsPerSample = BITS_PER_SAMPLE):
    ValidatePcm(pcm, channels, bitsPerSample)
    if isinstance(sampleRate, bool) or not isinstance(sampleRate, Integral) or sampleRate <= 0:
        raise ValueError("sampleRate must be a positive integer")

    bytesPerSample = bitsPerSample // 8
    frameSize = channels * bytesPerSample
    return (len(pcm) // frameSize) / sampleRate


def GetPanGains(pan):
    if isinstance(pan, bool) or not isinstance(pan, Real):
        raise TypeError("pan must be numeric")
    if not math.isfinite(pan):
        raise ValueError("pan must be finite")

    pan = max(-1.0, min(1.0, float(pan)))
    angle = (pan + 1.0) * (math.pi * 0.25)
    return math.cos(angle), math.sin(angle)


def ConvertChannels(samples, sourceChannels, targetChannels, pan = 0.0):
    ValidateChannels(sourceChannels)
    ValidateChannels(targetChannels)
    samples = np.asarray(samples, dtype = np.float64).reshape(-1)
    ValidateSamples(samples, sourceChannels)

    if sourceChannels == targetChannels:
        return samples.copy()
    if targetChannels == 1:
        frames = samples.reshape(-1, 2)
        return ((frames[:, 0] * 0.5) + (frames[:, 1] * 0.5)).copy()

    leftGain, rightGain = GetPanGains(pan)
    stereo = np.empty(len(samples) * 2, dtype = np.float64)
    stereo[0::2] = samples * leftGain
    stereo[1::2] = samples * rightGain
    return stereo


__all__ = [
    "ConvertChannels",
    "GetPcmDuration",
    "GetSampleDuration",
    "PcmToSamples",
    "SamplesToPcm",
    "ValidateChannels",
    "ValidatePcm",
    "ValidateSamples",
]
