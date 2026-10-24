import unittest

import numpy as np

from Chirper.core.ChirpSound import Sound
from Chirper.playback.ChirpMixer import ChirpMixer
from Chirper.playback.ChirpOutput import WinMMOutput
from Chirper.playback.ChirpPlayer import ChirpPlayer


class ManualOutput:
    def __init__(
            self, renderCallback, failureCallback,
            channels, sampleRate, bitsPerSample,
            blockFrames
            ):
        self.renderCallback = renderCallback
        self.channels = channels
        self.blockFrames = blockFrames
        self.started = False
        self.closed = False
        self.flushCount = 0
        self.flushActionCount = 0

    def Start(self):
        self.started = True

    def IsRunning(self):
        return self.started and not self.closed

    def Render(self):
        output = np.empty(
            self.blockFrames * self.channels,
            dtype = np.float64
        )
        return self.renderCallback(output)

    def Flush(self, beforeRefill = None):
        if self.IsRunning():
            self.flushCount += 1
        if beforeRefill is not None:
            self.flushActionCount += 1
            return beforeRefill()

    def GetLatency(self):
        return 0.0

    def GetStats(self):
        return {
            "blockFrames": self.blockFrames,
            "blocksRendered": 0,
        }

    def Close(self):
        self.closed = True


class FailingWaitHandle:
    def __init__(self, player, error):
        self.player = player
        self.error = error

    def Wait(self, timeout = None):
        self.player.HandleOutputFailure(self.error)
        return True

    def Stop(self):
        pass


class SingleCompletionKernel:
    def GetCurrentThread(self):
        return 1

    def GetThreadPriority(self, thread):
        return 0

    def SetThreadPriority(self, thread, priority):
        return True

    def WaitForSingleObject(self, event, timeout):
        return WinMMOutput.WAIT_OBJECT_0


class RealtimeMixerTests(unittest.TestCase):
    def test_DefaultOutputBufferingAllowsSchedulerHeadroom(self):
        mixer = ChirpMixer()
        output = WinMMOutput(mixer.MixBlock, lambda error: None)

        self.assertEqual(ChirpPlayer.BLOCK_FRAMES, 1024)
        self.assertEqual(mixer.blockFrames, 1024)
        self.assertEqual(output.blockFrames, 1024)
        self.assertEqual(output.bufferCount, 4)
        self.assertAlmostEqual(output.GetLatency(), (1024 * 4) / 44100)

    def test_OverlappingVoicesAreMixedIntoOneBlock(self):
        mixer = ChirpMixer(
            channels = 1,
            voices = 4,
            volume = 1.0,
            blockFrames = 4
        )
        firstHandle = mixer.Play(
            np.ones(4, dtype = np.float64)
        )
        secondHandle = mixer.Play(
            np.full(4, 0.5, dtype = np.float64)
        )

        block = mixer.MixBlock()

        np.testing.assert_array_equal(
            block,
            np.full(4, 1.5, dtype = np.float64)
        )
        self.assertTrue(firstHandle.Wait(0.0))
        self.assertTrue(secondHandle.Wait(0.0))

    def test_QueuedVoicesRemainSampleContiguous(self):
        mixer = ChirpMixer(
            channels = 1,
            voices = 1,
            blockFrames = 4
        )
        firstHandle = mixer.PlayQueued(
            np.array([1.0, 1.0]),
            voice = 0
        )
        secondHandle = mixer.PlayQueued(
            np.array([2.0, 2.0, 2.0]),
            voice = 0
        )

        firstBlock = mixer.MixBlock()
        secondBlock = mixer.MixBlock()

        np.testing.assert_array_equal(
            firstBlock,
            np.array([1.0, 1.0, 2.0, 2.0])
        )
        np.testing.assert_array_equal(
            secondBlock,
            np.array([2.0, 0.0, 0.0, 0.0])
        )
        self.assertTrue(firstHandle.Wait(0.0))
        self.assertTrue(secondHandle.Wait(0.0))

    def test_PlayStealsTheOldestVoiceAtTheLimit(self):
        mixer = ChirpMixer(
            channels = 1,
            voices = 2,
            blockFrames = 4
        )
        firstHandle = mixer.Play(np.ones(8))
        secondHandle = mixer.Play(np.ones(8))
        thirdHandle = mixer.Play(np.ones(8))

        self.assertTrue(firstHandle.Wait(0.0))
        self.assertTrue(secondHandle.IsPlaying())
        self.assertTrue(thirdHandle.IsPlaying())
        self.assertEqual(len(mixer.activeVoices), 2)

    def test_EmptyPlayDoesNotStopAnActiveVoice(self):
        mixer = ChirpMixer(channels = 1, voices = 1, blockFrames = 4)
        activeHandle = mixer.Play(np.ones(8, dtype = np.float64))

        emptyHandle = mixer.Play(np.empty(0, dtype = np.float64))

        self.assertTrue(activeHandle.IsPlaying())
        self.assertTrue(emptyHandle.Wait(0.0))
        np.testing.assert_array_equal(mixer.MixBlock(), np.ones(4))

    def test_PlayOwnsItsSampleBuffer(self):
        mixer = ChirpMixer(channels = 1, voices = 1, blockFrames = 4)
        source = np.ones(4, dtype = np.float64)

        mixer.Play(source)
        source.fill(0.0)

        np.testing.assert_array_equal(mixer.MixBlock(), np.ones(4))

    def test_VolumeChangesApplyWithoutReplacingVoices(self):
        mixer = ChirpMixer(
            channels = 1,
            voices = 1,
            blockFrames = 2
        )
        mixer.Play(np.ones(4))

        firstBlock = mixer.MixBlock()
        mixer.SetVolume(0.5)
        secondBlock = mixer.MixBlock()

        np.testing.assert_array_equal(
            firstBlock,
            np.ones(2)
        )
        np.testing.assert_array_equal(
            secondBlock,
            np.full(2, 0.25)
        )

    def test_PerPlayVolumeUsesPerceptualGain(self):
        mixer = ChirpMixer(
            channels = 1,
            voices = 1,
            blockFrames = 2
        )
        mixer.Play(np.ones(2), volume = 0.5)

        np.testing.assert_array_equal(
            mixer.MixBlock(),
            np.full(2, 0.25)
        )

    def test_StereoSamplesMustContainCompleteFrames(self):
        mixer = ChirpMixer(
            channels = 2,
            voices = 1,
            blockFrames = 2
        )

        with self.assertRaises(ValueError):
            mixer.Play(np.ones(3))

    def test_NonFiniteSamplesAreRejectedBeforePlayback(self):
        mixer = ChirpMixer(channels = 1)

        for value in (np.nan, np.inf, -np.inf):
            with self.subTest(value = value):
                with self.assertRaises(ValueError):
                    mixer.Play([value])

    def test_MixerRejectsBooleanVoicesAndNonFiniteVolumes(self):
        with self.assertRaises(ValueError):
            ChirpMixer(channels = True)
        with self.assertRaises(TypeError):
            ChirpMixer(voices = True)

        mixer = ChirpMixer(channels = 1)
        for value in (np.nan, np.inf, -np.inf):
            with self.subTest(value = value):
                with self.assertRaises(ValueError):
                    mixer.SetVolume(value)
                with self.assertRaises(ValueError):
                    mixer.Play([0.0], volume = value)
                with self.assertRaises(TypeError):
                    mixer.Play([0.0], voice = value)

        with self.assertRaises(ValueError):
            WinMMOutput(
                lambda samples: None, lambda error: None,
                bitsPerSample = 16.0
            )

    def test_InvalidPlaybackArgumentsDoNotReplaceActiveVoices(self):
        mixer = ChirpMixer(channels = 1, voices = 1, blockFrames = 2)
        activeHandle = mixer.Play(np.ones(4), voice = 0)

        with self.assertRaises(ValueError):
            mixer.Play(np.zeros(2), volume = np.nan, voice = 0)
        self.assertTrue(activeHandle.IsPlaying())

        with self.assertRaises(ValueError):
            mixer.PlaySolo(np.zeros(2), volume = np.inf)
        self.assertTrue(activeHandle.IsPlaying())

    def test_MixerRejectsFractionalCountsAndIndices(self):
        with self.assertRaises(TypeError):
            ChirpMixer(voices = 2.5)
        with self.assertRaises(TypeError):
            ChirpMixer(blockFrames = 4.5)

        mixer = ChirpMixer(channels = 1)
        with self.assertRaises(TypeError):
            mixer.Play([0.0], voice = 0.5)

    def test_MixBlockRejectsNonFloat64OutputBuffers(self):
        mixer = ChirpMixer(channels = 1, blockFrames = 2)
        output = np.zeros(2, dtype = np.float32)

        with self.assertRaises(TypeError):
            mixer.MixBlock(output)

        np.testing.assert_array_equal(output, np.zeros(2, dtype = np.float32))

    def test_QueuedPlaybackHasABoundedQueue(self):
        mixer = ChirpMixer(channels = 1, voices = 1, blockFrames = 1)
        mixer.PlayQueued([1.0], voice = 0)
        for _ in range(mixer.MAX_QUEUED_VOICES):
            mixer.PlayQueued([1.0], voice = 0)

        with self.assertRaises(OverflowError):
            mixer.PlayQueued([1.0], voice = 0)

    def test_ExtremeFiniteVoicesProduceFiniteMixerOutput(self):
        mixer = ChirpMixer(channels = 1, voices = 2, blockFrames = 1)
        maximum = np.finfo(np.float64).max
        mixer.Play([maximum])
        mixer.Play([maximum])

        output = mixer.MixBlock()

        self.assertTrue(np.all(np.isfinite(output)))
        self.assertEqual(output[0], maximum)

    def test_BlockingPlaybackPropagatesAsynchronousOutputFailures(self):
        player = ChirpPlayer(
            channels = 1,
            outputFactory = ManualOutput
        )
        error = RuntimeError("output failed")
        handle = FailingWaitHandle(player, error)
        player.mixer.Play = lambda samples, volume, voice: handle

        try:
            with self.assertRaisesRegex(RuntimeError, "output failed"):
                player.Play(Sound(samples = [0.0], channels = 1), blocking = True)
        finally:
            player.Close()

    def test_PlayerCanRetryFailedOutputCleanup(self):
        class RetryOutput(ManualOutput):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.closeCalls = 0

            def Close(self):
                self.closeCalls += 1
                if self.closeCalls == 1:
                    raise RuntimeError("cleanup failed")
                self.closed = True

        player = ChirpPlayer(channels = 1, outputFactory = RetryOutput)

        with self.assertRaisesRegex(RuntimeError, "cleanup failed"):
            player.Close()
        self.assertFalse(player.closed)

        player.Close()
        self.assertTrue(player.closed)
        self.assertEqual(player.output.closeCalls, 2)

    def test_OutputCleanupRetainsPreparedBuffersAfterDriverFailure(self):
        class FailingWinMM:
            def waveOutReset(self, waveOut):
                return 0

            def waveOutUnprepareHeader(self, waveOut, header, headerSize):
                return 5

        output = WinMMOutput(
            lambda samples: None, lambda error: None,
            channels = 1, blockFrames = 1
        )
        block = {"header": output.WaveHeader(), "prepared": True}
        output.waveOut = 1
        output.winmm = FailingWinMM()
        output.blocks = [block]

        with self.assertRaisesRegex(RuntimeError, "waveOutUnprepareHeader"):
            output.CloseDevice()

        self.assertEqual(output.waveOut, 1)
        self.assertEqual(output.blocks, [block])
        self.assertTrue(block["prepared"])

    def test_PlayerUsesOnePersistentOutputForAllVoices(self):
        player = ChirpPlayer(
            channels = 1,
            voices = 4,
            blockFrames = 4,
            outputFactory = ManualOutput
        )
        firstSound = Sound(
            samples = np.ones(4),
            channels = 1
        )
        secondSound = Sound(
            samples = np.full(4, 0.5),
            channels = 1
        )

        try:
            firstHandle = player.Play(firstSound)
            secondHandle = player.Play(secondSound)
            block = player.output.Render()

            np.testing.assert_array_equal(
                block,
                np.full(4, 1.5)
            )
            self.assertTrue(player.output.started)
            self.assertTrue(firstHandle.Wait(0.0))
            self.assertTrue(secondHandle.Wait(0.0))
        finally:
            output = player.output
            player.Close()

        self.assertTrue(output.closed)

    def test_PlayerSoloFlushesPreviouslyBufferedAudio(self):
        player = ChirpPlayer(
            channels = 1,
            voices = 2,
            blockFrames = 4,
            outputFactory = ManualOutput
        )
        firstSound = Sound(
            samples = np.ones(8),
            channels = 1
        )
        soloSound = Sound(
            samples = np.full(4, 0.25),
            channels = 1
        )

        try:
            firstHandle = player.Play(firstSound)
            soloHandle = player.PlaySolo(soloSound)
            block = player.output.Render()

            np.testing.assert_array_equal(
                block,
                np.full(4, 0.25)
            )
            self.assertTrue(firstHandle.Wait(0.0))
            self.assertTrue(soloHandle.Wait(0.0))
            self.assertEqual(player.output.flushCount, 1)
            self.assertEqual(
                player.output.flushActionCount,
                1
            )
        finally:
            player.Close()

    def test_FirstSoloPlaybackDoesNotFlushNewAudio(self):
        player = ChirpPlayer(
            channels = 1,
            voices = 1,
            blockFrames = 4,
            outputFactory = ManualOutput
        )
        sound = Sound(
            samples = np.array([0.1, 0.2, 0.3, 0.4]),
            channels = 1
        )

        try:
            player.PlaySolo(sound)
            block = player.output.Render()

            np.testing.assert_array_equal(
                block,
                sound.samples
            )
            self.assertEqual(player.output.flushCount, 0)
            self.assertEqual(
                player.output.flushActionCount,
                1
            )
        finally:
            player.Close()

    def test_OutputWorkerRefillsOneCompletedBlock(self):
        output = WinMMOutput(
            renderCallback = lambda samples: samples.fill(0.0),
            failureCallback = lambda error: None,
            channels = 1,
            blockFrames = 4
        )
        header = output.WaveHeader()
        header.dwFlags = output.WHDR_DONE
        block = {
            "header": header,
            "submissionOrder": 1,
        }
        filledBlocks = []
        submittedBlocks = []
        output.kernel32 = SingleCompletionKernel()
        output.bufferEvent = 1
        output.blocks = [block]
        output.running = True
        output.FillBlock = lambda completedBlock: (
            filledBlocks.append(completedBlock)
        )

        def SubmitBlock(completedBlock):
            submittedBlocks.append(completedBlock)
            output.running = False

        output.SubmitBlock = SubmitBlock
        output.OutputWorker()

        self.assertEqual(filledBlocks, [block])
        self.assertEqual(submittedBlocks, [block])

    def test_OutputWorkerPreservesBatchedSubmissionOrderAcrossWraparound(self):
        output = WinMMOutput(lambda samples: samples.fill(0.0), lambda error: None, channels = 1, blockFrames = 4)
        oldHeader = output.WaveHeader()
        oldHeader.dwFlags = output.WHDR_DONE
        newHeader = output.WaveHeader()
        newHeader.dwFlags = output.WHDR_DONE
        newerBlock = {"header": newHeader, "submissionOrder": 9}
        olderBlock = {"header": oldHeader, "submissionOrder": 8}
        filledBlocks = []
        submittedBlocks = []
        output.kernel32 = SingleCompletionKernel()
        output.bufferEvent = 1
        output.blocks = [newerBlock, olderBlock]
        output.running = True
        output.FillBlock = lambda block: filledBlocks.append(block)

        def SubmitBlock(block):
            submittedBlocks.append(block)
            if len(submittedBlocks) == 2:
                output.running = False

        output.SubmitBlock = SubmitBlock
        output.OutputWorker()

        self.assertEqual(filledBlocks, [olderBlock, newerBlock])
        self.assertEqual(submittedBlocks, [olderBlock, newerBlock])


if __name__ == "__main__":
    unittest.main()
