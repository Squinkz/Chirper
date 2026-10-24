import ctypes
from numbers import Integral
import threading
import time

import numpy as np


class WinMMOutput:
    WAVE_MAPPER = -1
    WAVE_FORMAT_PCM = 1
    CALLBACK_EVENT = 0x00050000
    WHDR_DONE = 0x00000001
    WAIT_OBJECT_0 = 0x00000000
    WAIT_TIMEOUT = 0x00000102
    WAIT_FAILED = 0xFFFFFFFF
    WAVERR_STILLPLAYING = 33
    THREAD_PRIORITY_HIGHEST = 2
    THREAD_PRIORITY_ERROR_RETURN = 0x7FFFFFFF
    BUFFER_COUNT = 4

    class WaveFormat(ctypes.Structure):
        _fields_ = [
            ("wFormatTag",      ctypes.c_ushort),
            ("nChannels",       ctypes.c_ushort),
            ("nSamplesPerSec",  ctypes.c_uint),
            ("nAvgBytesPerSec", ctypes.c_uint),
            ("nBlockAlign",     ctypes.c_ushort),
            ("wBitsPerSample",  ctypes.c_ushort),
            ("cbSize",          ctypes.c_ushort),
        ]

    class WaveHeader(ctypes.Structure):
        _fields_ = [
            ("lpData",          ctypes.c_void_p),
            ("dwBufferLength",  ctypes.c_uint),
            ("dwBytesRecorded", ctypes.c_uint),
            ("dwUser",          ctypes.c_void_p),
            ("dwFlags",         ctypes.c_uint),
            ("dwLoops",         ctypes.c_uint),
            ("lpNext",          ctypes.c_void_p),
            ("reserved",        ctypes.c_void_p),
        ]

    def __init__(
            self, renderCallback, failureCallback,
            channels = 2, sampleRate = 44100,
            bitsPerSample = 16, blockFrames = 1024,
            bufferCount = BUFFER_COUNT
            ):
        if (
                isinstance(bitsPerSample, bool)
                or not isinstance(bitsPerSample, Integral)
                or bitsPerSample != 16
                ):
            raise ValueError("WinMMOutput only supports 16-bit PCM")
        if isinstance(channels, bool) or not isinstance(channels, Integral) or channels not in (1, 2):
            raise ValueError("WinMMOutput only supports 1 or 2 channels")
        if isinstance(sampleRate, bool) or not isinstance(sampleRate, Integral) or sampleRate <= 0:
            raise ValueError("sampleRate must be a positive integer")
        if isinstance(blockFrames, bool) or not isinstance(blockFrames, Integral) or blockFrames < 1:
            raise ValueError("blockFrames must be a positive integer")
        if isinstance(bufferCount, bool) or not isinstance(bufferCount, Integral) or bufferCount < 2:
            raise ValueError("bufferCount must be an integer of at least 2")

        self.renderCallback = renderCallback
        self.failureCallback = failureCallback
        self.channels = int(channels)
        self.sampleRate = int(sampleRate)
        self.bitsPerSample = bitsPerSample
        self.blockFrames = int(blockFrames)
        self.blockSamples = self.blockFrames * self.channels
        self.blockBytes = self.blockSamples * bitsPerSample // 8
        self.bufferCount = int(bufferCount)
        self.blockDuration = self.blockFrames / self.sampleRate
        self.waveOut = None
        self.bufferEvent = None
        self.kernel32 = None
        self.winmm = None
        self.blocks = []
        self.thread = None
        self.running = False
        self.error = None
        self.lock = threading.RLock()
        self.mixBuffer = np.empty(self.blockSamples, dtype = np.float64)
        self.blocksRendered = 0
        self.batchedRefills = 0
        self.maximumRenderSeconds = 0.0
        self.nextSubmissionOrder = 1

# -----------------------------------
# Device Setup
# -----------------------------------

    def Check(self, result, functionName):
        if result != 0:
            raise RuntimeError(functionName + " failed with error " + str(result))

    def OpenDevice(self):
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error = True)
        self.winmm = ctypes.WinDLL("winmm", use_last_error = True)
        self.kernel32.CreateEventW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_bool, ctypes.c_wchar_p]
        self.kernel32.CreateEventW.restype = ctypes.c_void_p
        self.kernel32.SetEvent.argtypes = [ctypes.c_void_p]
        self.kernel32.SetEvent.restype = ctypes.c_bool
        self.kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        self.kernel32.WaitForSingleObject.restype = ctypes.c_uint
        self.kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        self.kernel32.CloseHandle.restype = ctypes.c_bool
        self.kernel32.GetCurrentThread.argtypes = []
        self.kernel32.GetCurrentThread.restype = ctypes.c_void_p
        self.kernel32.GetThreadPriority.argtypes = [ctypes.c_void_p]
        self.kernel32.GetThreadPriority.restype = ctypes.c_int
        self.kernel32.SetThreadPriority.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.kernel32.SetThreadPriority.restype = ctypes.c_bool
        self.winmm.waveOutOpen.argtypes = [
            ctypes.POINTER(ctypes.c_void_p), ctypes.c_uint,
            ctypes.POINTER(self.WaveFormat), ctypes.c_size_t,
            ctypes.c_size_t, ctypes.c_uint
        ]
        self.winmm.waveOutOpen.restype = ctypes.c_uint
        self.winmm.waveOutPrepareHeader.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(self.WaveHeader), ctypes.c_uint
        ]
        self.winmm.waveOutPrepareHeader.restype = ctypes.c_uint
        self.winmm.waveOutWrite.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(self.WaveHeader), ctypes.c_uint
        ]
        self.winmm.waveOutWrite.restype = ctypes.c_uint
        self.winmm.waveOutReset.argtypes = [ctypes.c_void_p]
        self.winmm.waveOutReset.restype = ctypes.c_uint
        self.winmm.waveOutUnprepareHeader.argtypes = [
            ctypes.c_void_p, ctypes.POINTER(self.WaveHeader), ctypes.c_uint
        ]
        self.winmm.waveOutUnprepareHeader.restype = ctypes.c_uint
        self.winmm.waveOutClose.argtypes = [ctypes.c_void_p]
        self.winmm.waveOutClose.restype = ctypes.c_uint
        self.bufferEvent = self.kernel32.CreateEventW(None, False, False, None)
        if not self.bufferEvent:
            raise OSError(ctypes.get_last_error(), "CreateEventW failed")

        waveOut = ctypes.c_void_p()
        blockAlign = self.channels * self.bitsPerSample // 8
        waveFormat = self.WaveFormat(
            self.WAVE_FORMAT_PCM,
            self.channels,
            self.sampleRate,
            self.sampleRate * blockAlign,
            blockAlign,
            self.bitsPerSample,
            0
        )
        result = self.winmm.waveOutOpen(
            ctypes.byref(waveOut),
            ctypes.c_uint(self.WAVE_MAPPER).value,
            ctypes.byref(waveFormat),
            self.bufferEvent,
            0,
            self.CALLBACK_EVENT
        )
        if result != 0:
            self.kernel32.CloseHandle(self.bufferEvent)
            self.bufferEvent = None
            self.Check(result, "waveOutOpen")
        self.waveOut = waveOut

    def CreateBlock(self):
        buffer = ctypes.create_string_buffer(self.blockBytes)
        header = self.WaveHeader(ctypes.cast(buffer, ctypes.c_void_p), self.blockBytes, 0, None, 0, 0, None, None)
        pcmSamples = np.frombuffer(buffer, dtype = "<i2", count = self.blockSamples)
        result = self.winmm.waveOutPrepareHeader(self.waveOut, ctypes.byref(header), ctypes.sizeof(header))
        self.Check(result, "waveOutPrepareHeader")
        return {
            "buffer": buffer,
            "header": header,
            "pcmSamples": pcmSamples,
            "prepared": True,
            "submissionOrder": 0,
        }

# -----------------------------------
# Streaming
# -----------------------------------

    def FillBlock(self, block):
        startTime = time.perf_counter()
        self.renderCallback(self.mixBuffer)
        np.nan_to_num(self.mixBuffer, copy = False, nan = 0.0, posinf = 1.0, neginf = -1.0)
        np.clip(self.mixBuffer, -1.0, 1.0, out = self.mixBuffer)
        np.multiply(self.mixBuffer, 32767.0, out = self.mixBuffer)
        np.rint(self.mixBuffer, out = self.mixBuffer)
        np.copyto(block["pcmSamples"], self.mixBuffer, casting = "unsafe")
        renderSeconds = time.perf_counter() - startTime
        self.blocksRendered += 1
        self.maximumRenderSeconds = max(self.maximumRenderSeconds, renderSeconds)

    def SubmitBlock(self, block):
        block["submissionOrder"] = self.nextSubmissionOrder
        self.nextSubmissionOrder += 1
        result = self.winmm.waveOutWrite(self.waveOut, ctypes.byref(block["header"]), ctypes.sizeof(block["header"]))
        self.Check(result, "waveOutWrite")

    def Start(self):
        with self.lock:
            if self.running:
                if self.error is not None:
                    raise self.error
                return

            if self.error is not None:
                raise self.error

            try:
                self.OpenDevice()
                self.blocks = []
                self.nextSubmissionOrder = 1
                for _ in range(self.bufferCount):
                    self.blocks.append(self.CreateBlock())
                for block in self.blocks:
                    self.FillBlock(block)
                    self.SubmitBlock(block)
            except Exception:
                self.CloseDevice()
                raise

            self.running = True
            self.thread = threading.Thread(target = self.OutputWorker, daemon = True)
            try:
                self.thread.start()
            except Exception:
                self.running = False
                self.thread = None
                self.CloseDevice()
                raise

    def OutputWorker(self):
        threadHandle = self.kernel32.GetCurrentThread()
        previousPriority = self.kernel32.GetThreadPriority(threadHandle)
        priorityRaised = self.kernel32.SetThreadPriority(threadHandle, self.THREAD_PRIORITY_HIGHEST)

        try:
            while True:
                waitResult = self.kernel32.WaitForSingleObject(self.bufferEvent, 100)
                if waitResult == self.WAIT_FAILED:
                    raise OSError(ctypes.get_last_error(), "WaitForSingleObject failed")

                with self.lock:
                    if not self.running:
                        return
                    if waitResult == self.WAIT_TIMEOUT:
                        continue

                    completedBlocks = sorted(
                        (block for block in self.blocks if (block["header"].dwFlags & self.WHDR_DONE)),
                        key = lambda block: block["submissionOrder"]
                    )
                    if len(completedBlocks) > 1:
                        self.batchedRefills += len(completedBlocks) - 1

                    for block in completedBlocks:
                        self.FillBlock(block)
                        self.SubmitBlock(block)
        except Exception as error:
            with self.lock:
                self.error = error
                self.running = False
            self.failureCallback(error)
        finally:
            if priorityRaised and previousPriority != self.THREAD_PRIORITY_ERROR_RETURN:
                self.kernel32.SetThreadPriority(threadHandle, previousPriority)

# -----------------------------------
# Output Control
# -----------------------------------

    def GetLatency(self):
        return self.blockDuration * self.bufferCount

    def GetStats(self):
        with self.lock:
            return {
                "blockFrames": self.blockFrames,
                "bufferCount": self.bufferCount,
                "blocksRendered": self.blocksRendered,
                "batchedRefills": self.batchedRefills,
                "maximumRenderSeconds": self.maximumRenderSeconds,
                "blockDurationSeconds": self.blockDuration,
            }

    def Flush(self, beforeRefill = None):
        with self.lock:
            shouldRefill = bool(self.waveOut and self.running)
            if shouldRefill:
                result = self.winmm.waveOutReset(self.waveOut)
                self.Check(result, "waveOutReset")

            actionResult = None
            try:
                if beforeRefill is not None:
                    actionResult = beforeRefill()
            finally:
                if shouldRefill:
                    for block in self.blocks:
                        self.FillBlock(block)
                        self.SubmitBlock(block)

            return actionResult

    def CloseDevice(self):
        waveOut = self.waveOut
        if not waveOut:
            self.blocks = []
            if self.bufferEvent and self.kernel32:
                if not self.kernel32.CloseHandle(self.bufferEvent):
                    raise OSError(ctypes.get_last_error(), "CloseHandle failed")
                self.bufferEvent = None
            return

        result = self.winmm.waveOutReset(waveOut)
        self.Check(result, "waveOutReset")
        for block in self.blocks:
            if block.get("prepared", False):
                deadline = time.monotonic() + 5.0
                while True:
                    result = self.winmm.waveOutUnprepareHeader(
                        waveOut, ctypes.byref(block["header"]), ctypes.sizeof(block["header"])
                    )
                    if result == 0:
                        break
                    if result != self.WAVERR_STILLPLAYING or time.monotonic() >= deadline:
                        self.Check(result, "waveOutUnprepareHeader")
                    time.sleep(0.01)
                block["prepared"] = False

        result = self.winmm.waveOutClose(waveOut)
        self.Check(result, "waveOutClose")
        self.waveOut = None
        self.blocks = []
        if self.bufferEvent:
            if not self.kernel32.CloseHandle(self.bufferEvent):
                raise OSError(ctypes.get_last_error(), "CloseHandle failed")
            self.bufferEvent = None

    def Close(self):
        with self.lock:
            self.running = False
            thread = self.thread
            if self.bufferEvent:
                self.kernel32.SetEvent(self.bufferEvent)

        if (thread is not None and thread is not threading.current_thread()):
            thread.join(timeout = 5.0)
            if thread.is_alive():
                raise RuntimeError("Audio output worker did not stop")

        with self.lock:
            self.thread = None
            self.CloseDevice()


__all__ = [
    "WinMMOutput",
]
