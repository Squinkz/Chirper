import unittest

import numpy as np

from Chirper.core.ChirpSynth import ChirpSynth
from tests.render_helpers import MakeTone


class BandLimitedWaveTests(unittest.TestCase):
    SAMPLE_COUNT = 44100
    TEST_FREQUENCY = 5000
    WAVE_NAMES = (
        "SawAA",
        "Pulse50AA",
        "Pulse25AA",
        "Pulse12AA",
        "TriangleAA",
    )

    def GetAliasEnergy(self, samples):
        spectrum = np.abs(np.fft.rfft(samples)) ** 2.0
        allowedBins = np.zeros(len(spectrum), dtype = bool)
        allowedBins[0] = True
        harmonicCount = int(
            (ChirpSynth.SAMPLE_RATE * 0.5)
            // self.TEST_FREQUENCY
        )

        for harmonic in range(1, harmonicCount + 1):
            allowedBins[self.TEST_FREQUENCY * harmonic] = True

        return float(np.sum(spectrum[~allowedBins]))

    def test_AntiAliasedWavesRemainWithinRawAmplitude(self):
        synthesizer = ChirpSynth(channels = 1)
        times = (
            np.arange(self.SAMPLE_COUNT, dtype = np.float64)
            / synthesizer.SAMPLE_RATE
        )

        for waveName in self.WAVE_NAMES:
            wave = synthesizer.oscillator.GetWave(waveName)
            samples = np.asarray([
                wave(time, self.TEST_FREQUENCY)
                for time in times
            ])

            with self.subTest(wave = waveName):
                self.assertGreaterEqual(float(np.min(samples)), -1.0)
                self.assertLessEqual(float(np.max(samples)), 1.0)

    def test_VectorizedRenderingMatchesWaveGenerators(self):
        synthesizer = ChirpSynth(channels = 1)
        sampleCount = 2205
        times = (
            np.arange(
                1,
                sampleCount + 1,
                dtype = np.float64
            ) / synthesizer.SAMPLE_RATE
        )

        for waveName in self.WAVE_NAMES:
            wave = synthesizer.oscillator.GetWave(waveName)
            rendered, _, _, _ = MakeTone(
                synthesizer,
                self.TEST_FREQUENCY,
                sampleCount / synthesizer.SAMPLE_RATE,
                wave = wave,
                fadeIn = False,
                fadeOut = False
            )
            expected = np.asarray([
                wave(time, self.TEST_FREQUENCY)
                for time in times
            ])

            with self.subTest(wave = waveName):
                np.testing.assert_allclose(
                    rendered,
                    expected,
                    rtol = 0.0,
                    atol = 1e-12
                )

    def test_AntiAliasedWavesReduceAliasEnergy(self):
        synthesizer = ChirpSynth(channels = 1)
        times = (
            np.arange(self.SAMPLE_COUNT, dtype = np.float64)
            / synthesizer.SAMPLE_RATE
        )
        wavePairs = (
            ("Saw", "SawAA"),
            ("Pulse50", "Pulse50AA"),
            ("Pulse25", "Pulse25AA"),
            ("Pulse12", "Pulse12AA"),
            ("Triangle", "TriangleAA"),
        )

        for rawName, antiAliasedName in wavePairs:
            rawWave = synthesizer.oscillator.GetWave(rawName)
            antiAliasedWave = synthesizer.oscillator.GetWave(
                antiAliasedName
            )
            rawSamples = np.asarray([
                rawWave(time, self.TEST_FREQUENCY)
                for time in times
            ])
            antiAliasedSamples = np.asarray([
                antiAliasedWave(time, self.TEST_FREQUENCY)
                for time in times
            ])
            aliasRatio = (
                self.GetAliasEnergy(antiAliasedSamples)
                / self.GetAliasEnergy(rawSamples)
            )

            with self.subTest(wave = antiAliasedName):
                self.assertLess(aliasRatio, 0.05)

    def test_TriangleTableTransitionsAreContinuous(self):
        synthesizer = ChirpSynth(channels = 1)
        phases = np.linspace(0.0, 1.0, 2048, endpoint = False)
        waveId = synthesizer.oscillator.GetWaveId(
            synthesizer.oscillator.GetWave("TriangleAA")
        )
        below = synthesizer.oscillator.RenderBuiltIn(
            waveId, phases,
            (5512.5 - 0.01) / synthesizer.SAMPLE_RATE
        )
        above = synthesizer.oscillator.RenderBuiltIn(
            waveId, phases,
            (5512.5 + 0.01) / synthesizer.SAMPLE_RATE
        )

        self.assertLess(np.max(np.abs(below - above)), 0.00001)


if __name__ == "__main__":
    unittest.main()
