import copy
import json
import math
from numbers import Integral
import os
import struct
import tempfile
import wave
from pathlib import Path

import numpy as np

from .ChirpAudioData import (
    GetPcmDuration,
    GetSampleDuration,
    PcmToSamples,
    SamplesToPcm,
    ValidatePcm,
    ValidateSamples,
)


MAGIC = b"CHIRP2"
FORMAT = "float32-le"
SAMPLE_RATE = 44100
BITS_PER_SAMPLE = 16
PCM_FORMATS = {
    8: "pcm_u8",
    16: "pcm_s16le",
    24: "pcm_s24le",
}
MAX_METADATA_BYTES = 65536


class ChirpFileData:
    def __init__(self, samples, metadata):
        self._metadata = copy.deepcopy(metadata)
        ValidateMetadata(self._metadata)
        self.sampleRate = self._metadata["sampleRate"]
        self.channels = self._metadata["channels"]
        self._samples = np.asarray(samples, dtype = np.float64).reshape(-1).copy()
        ValidateSamples(self._samples, self.channels)
        expectedFrames = round(self._metadata["duration"] * self.sampleRate)
        actualFrames = len(self._samples) // self.channels
        if actualFrames != expectedFrames:
            raise ValueError("Chirp sample payload does not match its declared duration")
        self._samples.setflags(write = False)
        self.duration = GetSampleDuration(self._samples, self.channels, self.sampleRate)
        self._metadata.update(MakeMetadata(self.duration, self.channels, self.sampleRate))
        self.sampleFormat = self._metadata["sampleFormat"]

    @property
    def samples(self):
        return self._samples.copy()

    @property
    def metadata(self):
        return copy.deepcopy(self._metadata)


class PcmFileData:
    def __init__(self, pcm, metadata):
        if not isinstance(pcm, (bytes, bytearray, memoryview)):
            raise TypeError("PCM data must be bytes-like")
        self.pcm = bytes(pcm)
        self._metadata = copy.deepcopy(metadata)
        ValidatePcmMetadata(self._metadata)
        self.sampleRate = self._metadata["sampleRate"]
        self.channels = self._metadata["channels"]
        self.bitsPerSample = self._metadata["bitsPerSample"]
        ValidatePcm(self.pcm, self.channels, self.bitsPerSample)
        expectedFrames = round(self._metadata["duration"] * self.sampleRate)
        actualFrames = len(self.pcm) // (self.channels * (self.bitsPerSample // 8))
        if actualFrames != expectedFrames:
            raise ValueError("PCM payload does not match its declared duration")
        self._samples = PcmToSamples(
            self.pcm, self.channels, self.bitsPerSample
        )
        ValidateSamples(self._samples, self.channels)
        self._samples.setflags(write = False)
        self.duration = GetPcmDuration(
            self.pcm, self.channels, self.sampleRate, self.bitsPerSample
        )
        self._metadata.update(
            MakePcmMetadata(
                self.duration, self.channels, self.sampleRate, self.bitsPerSample
            )
        )
        self.sampleFormat = self._metadata["format"]

    @property
    def samples(self):
        return self._samples.copy()

    @property
    def metadata(self):
        return copy.deepcopy(self._metadata)


def GetChirpPath(path):
    path = Path(path)
    if path.suffix.lower() == ".chirp":
        return path
    if path.suffix:
        return path.with_suffix(".chirp")
    return Path(str(path) + ".chirp")


def GetWavPath(path):
    path = Path(path)
    if path.suffix.lower() == ".wav":
        return path
    if path.suffix:
        return path.with_suffix(".wav")
    return Path(str(path) + ".wav")


def MakeMetadata(duration, channels, sampleRate = SAMPLE_RATE):
    return {
        "sampleRate": sampleRate,
        "channels": channels,
        "sampleFormat": FORMAT,
        "duration": duration,
    }


def MakePcmMetadata(
        duration, channels, sampleRate = SAMPLE_RATE,
        bitsPerSample = BITS_PER_SAMPLE
        ):
    if (
            isinstance(bitsPerSample, bool)
            or not isinstance(bitsPerSample, Integral)
            or bitsPerSample not in PCM_FORMATS
            ):
        raise ValueError("Unsupported bit depth: " + str(bitsPerSample))

    return {
        "sampleRate": sampleRate,
        "channels": channels,
        "bitsPerSample": bitsPerSample,
        "duration": duration,
        "format": PCM_FORMATS[bitsPerSample],
    }


def ValidateMetadata(metadata):
    if not isinstance(metadata, dict):
        raise ValueError("Chirp metadata must be a JSON object")

    if metadata.get("sampleFormat") != FORMAT:
        raise ValueError("Unsupported chirp sample format: " + str(metadata.get("sampleFormat")))

    ValidateCommonMetadata(metadata)


def ValidatePcmMetadata(metadata):
    if not isinstance(metadata, dict):
        raise ValueError("PCM metadata must be a dictionary")

    bitsPerSample = metadata.get("bitsPerSample")
    if (
            isinstance(bitsPerSample, bool)
            or not isinstance(bitsPerSample, Integral)
            or bitsPerSample not in PCM_FORMATS
            ):
        raise ValueError("Unsupported bit depth: " + str(bitsPerSample))

    if metadata.get("format") != PCM_FORMATS[bitsPerSample]:
        raise ValueError("Unsupported PCM format: " + str(metadata.get("format")))

    ValidateCommonMetadata(metadata)


def ValidateCommonMetadata(metadata):
    sampleRate = metadata.get("sampleRate")
    if (
            isinstance(sampleRate, bool)
            or not isinstance(sampleRate, Integral)
            or sampleRate != SAMPLE_RATE
            ):
        raise ValueError("Unsupported sample rate: " + str(metadata.get("sampleRate")))

    channels = metadata.get("channels")
    if isinstance(channels, bool) or not isinstance(channels, Integral) or channels not in (1, 2):
        raise ValueError("Unsupported channel count: " + str(metadata.get("channels")))

    duration = metadata.get("duration")
    if (
            isinstance(duration, bool)
            or not isinstance(duration, (int, float))
            or not math.isfinite(duration)
            or duration < 0.0
            ):
        raise ValueError("Invalid duration: " + str(duration))


def RejectJsonConstant(value):
    raise ValueError("Invalid JSON constant: " + value)


def Read(path):
    path = GetChirpPath(path)

    with open(path, "rb") as file:
        magic = file.read(len(MAGIC))
        if magic != MAGIC:
            raise ValueError("Not a chirp file: " + str(path))

        metadataLengthBytes = file.read(4)
        if len(metadataLengthBytes) != 4:
            raise ValueError("Chirp file is missing its metadata length")

        metadataLength = struct.unpack("<I", metadataLengthBytes)[0]
        if metadataLength > MAX_METADATA_BYTES:
            raise ValueError("Chirp metadata exceeds the maximum size")

        metadataBytes = file.read(metadataLength)
        if len(metadataBytes) != metadataLength:
            raise ValueError("Chirp file contains truncated metadata")

        try:
            metadata = json.loads(
                metadataBytes.decode("utf-8"), parse_constant = RejectJsonConstant
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            raise ValueError("Chirp file contains invalid metadata") from error
        payload = file.read()

    ValidateMetadata(metadata)
    if len(payload) % np.dtype("<f4").itemsize != 0:
        raise ValueError("Chirp sample payload is truncated")

    samples = np.frombuffer(payload, dtype = "<f4").astype(np.float64)
    ValidateSamples(samples, metadata["channels"])
    return path, ChirpFileData(samples, metadata)


def Write(path, samples, metadata):
    path = GetChirpPath(path)
    samples = np.asarray(samples, dtype = np.float64).reshape(-1)
    if not isinstance(metadata, dict):
        raise ValueError("Chirp metadata must be a JSON object")
    metadata = copy.deepcopy(metadata)
    channels = metadata.get("channels")
    sampleRate = metadata.get("sampleRate")
    ValidateSamples(samples, channels)
    if sampleRate != SAMPLE_RATE:
        raise ValueError("Unsupported sample rate: " + str(sampleRate))

    maximumFloat = np.finfo(np.float32).max
    if np.any(np.abs(samples) > maximumFloat):
        raise ValueError("Samples exceed the float32 range")

    metadata.pop("bitsPerSample", None)
    metadata.pop("format", None)
    metadata.update(
        MakeMetadata(GetSampleDuration(samples, channels, sampleRate), channels, sampleRate)
    )
    ValidateMetadata(metadata)
    try:
        metadataBytes = json.dumps(metadata, allow_nan = False).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ValueError("Chirp metadata must contain valid finite JSON values") from error
    if len(metadataBytes) > MAX_METADATA_BYTES:
        raise ValueError("Chirp metadata exceeds the maximum size")

    payload = samples.astype("<f4").tobytes()
    path.parent.mkdir(parents = True, exist_ok = True)
    temporaryPath = None
    try:
        with tempfile.NamedTemporaryFile(
                mode = "wb", dir = path.parent,
                prefix = path.name + ".", suffix = ".tmp", delete = False
                ) as file:
            temporaryPath = Path(file.name)
            file.write(MAGIC)
            file.write(struct.pack("<I", len(metadataBytes)))
            file.write(metadataBytes)
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporaryPath, path)
    except Exception:
        if temporaryPath is not None:
            temporaryPath.unlink(missing_ok = True)
        raise

    return path


def Load(path):
    _, data = Read(path)
    return data


def Save(path, data):
    return Write(path, data.samples, data.metadata)


def ReadWav(path):
    wavPath = GetWavPath(path)

    with wave.open(str(wavPath), "rb") as wav:
        channels = wav.getnchannels()
        sampleRate = wav.getframerate()
        sampleWidth = wav.getsampwidth()
        bitsPerSample = sampleWidth * 8
        frameCount = wav.getnframes()
        wavPcm = wav.readframes(frameCount)

    if isinstance(channels, bool) or channels not in (1, 2):
        raise ValueError("Unsupported channel count: " + str(channels))
    if sampleRate != SAMPLE_RATE:
        raise ValueError("Unsupported sample rate: " + str(sampleRate))
    if sampleWidth not in (1, 2, 3):
        raise ValueError("Unsupported bit depth: " + str(bitsPerSample))
    expectedBytes = frameCount * channels * sampleWidth
    if len(wavPcm) != expectedBytes:
        raise ValueError("WAV sample payload is truncated")

    metadata = MakePcmMetadata(
        GetPcmDuration(wavPcm, channels, sampleRate, bitsPerSample),
        channels, sampleRate, bitsPerSample
    )
    return PcmFileData(wavPcm, metadata)


def WriteWav(path, pcm, metadata):
    wavPath = GetWavPath(path)
    if not isinstance(pcm, (bytes, bytearray, memoryview)):
        raise TypeError("PCM data must be bytes-like")
    pcm = bytes(pcm)
    metadata = copy.deepcopy(metadata)
    ValidatePcmMetadata(metadata)
    bitsPerSample = metadata["bitsPerSample"]
    ValidatePcm(pcm, metadata["channels"], bitsPerSample)
    frameSize = metadata["channels"] * (bitsPerSample // 8)
    expectedFrames = round(metadata["duration"] * metadata["sampleRate"])
    actualFrames = len(pcm) // frameSize
    if actualFrames != expectedFrames:
        raise ValueError("PCM payload does not match its declared duration")

    wavPath.parent.mkdir(parents = True, exist_ok = True)
    temporaryPath = None
    try:
        with tempfile.NamedTemporaryFile(
                dir = wavPath.parent, prefix = wavPath.name + ".",
                suffix = ".tmp", delete = False
                ) as file:
            temporaryPath = Path(file.name)
        with wave.open(str(temporaryPath), "wb") as wav:
            wav.setnchannels(metadata["channels"])
            wav.setsampwidth(bitsPerSample // 8)
            wav.setframerate(metadata["sampleRate"])
            wav.writeframes(pcm)
        os.replace(temporaryPath, wavPath)
    except Exception:
        if temporaryPath is not None:
            temporaryPath.unlink(missing_ok = True)
        raise

    return wavPath


def ChirpToWav(path):
    chirpPath, chirp = Read(path)
    pcm = SamplesToPcm(chirp._samples, chirp.channels)
    metadata = MakePcmMetadata(chirp.duration, chirp.channels, chirp.sampleRate)
    WriteWav(Path(chirpPath).with_suffix(".wav"), pcm, metadata)


def WavToChirp(path):
    wavPath = GetWavPath(path)
    data = ReadWav(wavPath)
    Write(wavPath.with_suffix(".chirp"), data._samples, data.metadata)
