import ast
import importlib
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

import Chirper as ChirperModule
from Chirper import Chirper
from Chirper.core import ChirpConstants, ChirpKernels
from Chirper.core import ChirpSound as ChirpSoundModule
from Chirper.core.ChirpDSP import ChirpDSP
from Chirper.core.ChirpOscillator import ChirpOscillator
from Chirper.core.ChirpSynth import ChirpRenderPlan, ChirpSynth
from Chirper.core.ChirpTone import Tone

from tests.architecture_cases import GetArchitectureHashes


# Includes the 3 ms endpoint fade applied when a filter input ends in silence.
EXPECTED_ARCHITECTURE_HASHES = {
    "band_pass": "e1cde9a2a51ad45aebb08d12fc241c4844be8afd412f59932cba76dbd665cb12",
    "band_pass_sweep": "e472949230f8f275639384d56c9a6250d3c8d872d86b006e564232d4be686569",
    "base_mono": "ba4236e6c82c0d2a418ca2a0b29d271d3acd786c07917213337508c6d9ff0a93",
    "base_stereo": "d550033d904b3950d2411ca09d2fb9b357cf6e8a091f7cfec8e204c33cc65cd3",
    "chorus": "0ff040808fbb05f705c2352a6fd4397d36d7eb848821964fa6c9d04c8a52a5b2",
    "control_sequence_stereo": "fe8839dda816f66590cd8cc2f0d357b25a4f31cf21c89f83e88c22be908acb74",
    "cut": "978534e99e111f0aaefb1da3ff950ef77913cb65450c8abbe1a93a7b850e8563",
    "delay": "585d2ea508c20c2cd36ffc4321094fc83602edcc1c888713037a034380b1bff9",
    "fade_in": "25604effab71a49c3c26aaa83ce06439a86917f7916a62779b54f3b4f541af6f",
    "fade_out": "a36c264186cc95f92a151d07dfc6f62469b11292fa555679765f711f0bc09067",
    "freeverb": "99f75b632b4486fc8f1da9f06684d41923ea4df08780dab76f8776ca8d60c826",
    "gain": "b3a035f78371f96b9eb38b24f3b6a5851cc3d74a4eb5452e6908e1e099d768be",
    "high_pass": "ecc3de7068e09ec693bc963adb1088ea3877ba20fc410f5be8dd47f23c4e69b4",
    "high_pass_sweep": "658ed9abc1c7e5101b9a2afcbd7f8ace173bda0807afd45a1fe715a2e196a0c9",
    "high_shelf": "ae5d933f23235a7ff841263804cd07b3a93eaa4ce2886aaa45eeda4c4002b1c3",
    "high_shelf_sweep": "b7baf8193bcfb7a30e35900c036b82fda93f48508b80f77dea7dacbdaa94c661",
    "insert_sequence_mono": "20cef0dc3b162623e989f42f8ff06d79c81a9079c3111a35a6ef7c667710673e",
    "low_pass": "55182ab92fdb8250e0d1cd718ef7460269338d9ad16fcfedc75f7f5f60e165ff",
    "low_pass_sweep": "39c6d45aeeb297a80e88e3dc65d276dcd064e5f6ed896115e54e8c22e054448b",
    "low_shelf": "a3b81667eaa9cda0f387979a1b1e8f6360ca51feebdeafc61bd053eb45751582",
    "low_shelf_sweep": "ba49330313e14910d01d2e3f4d527aeed867f76cfcc128242482597beb2fde79",
    "mix": "197af6cdc1b9426906c480c8cd8d160ea8c0df82fff6e7a03f4adcd431bdf880",
    "mtverb": "0b9b347b30a632774787f07fcee8a0b72b5bec7bc598a629448cee982de07288",
    "normalize": "c299a9e646da1f9e6de3077cfe5c26430b05818ecf5253700f75f9f59ff2424a",
    "notch": "fa578168fb919f00f23adf7dbef74582784e947a573824b8909fbf33c42453d8",
    "notch_sweep": "20b3d92d05f2e4e2139415ef0dee8c77436833cfd8d75abe33cdcd39dd7910a4",
    "pan_mono": "fab0213fb485aada43aced31dad700d7fd7e64f23579d3911d5b0d07b01b629f",
    "pan_stereo": "ffa961550cd0ee27efb231b0cf1e1145d96d7f94af03c3c1e148fb55ec0889d3",
    "peak": "de57f6a61f9128a03f04787ea4c87a9aac92293b42eb0f5f3dd6013347199c77",
    "peak_sweep": "003a68ef009477c222a35501df4f35a276f76f93a1169eeeb5000cc424c4028c",
    "phaser": "88697e10ebc3f28e17e365e79742c4567f41b8163416fcb676e1c5b6cd5aa0b2",
    "ping_pong": "5ab39725c7138e4523f59dd8ac573a412c8db34af548e23eb63302b3db752c8e",
    "reverse": "27e577e39243076f037168c32c8d0340783d07617c675a12d98a203b9a61c35a",
    "ring": "457c3860b99b2a5947f8d67b5bd9d7b2c7f537de72e7eef43eab7f31d40d2554",
    "schroverb": "fd08f8ad913296e6791fc2a8921cb18ed9422f4bd509880c64153ab833d9ef08",
    "soft_clip": "0a38e11db2345b81cc9d3882adee052fb1f5764f391fc791aff81b056549b8e6",
    "unison": "ca18025a7aac12b80d08da6e6253d19afc673c0bb0c4fee8290e2f71021a6b05",
    "wave_Noise": "2ac618fb6059a797354c877b084ca2c4341a6eee5e0b46267051f76a3e06ea6b",
    "wave_NoiseBP": "d76eef734dd00eb59190231733c28e056beb57b272bab1dca7ed1ffe8ec0fa7a",
    "wave_NoiseHP": "dc64f8b630758105c2c80392273299bc68bd668445e4fb187ec5ae43bb1fbf4d",
    "wave_NoiseLP": "8a5432020e65a7656435f06b5796150e15acf02b6eb7d91d65af47545cc0bcdf",
    "wave_NoiseQuanta": "1a1d321414690576d6c5aa2cd7d65680a848ac0218b3dbbe600956cd24896cc6",
    "wave_NoiseStep": "8305d23204ac8a47f8186877be431bdb8bb2f0ade9395d868f24d79a61af6bd5",
    "wave_Pulse12": "d96c10f09ba3d6fa4d022a3ac1a2a802e03e658c7649d4b6a874f8bbc85eb298",
    "wave_Pulse25": "f58776b5d7d119aae15e4051f41bc4ac58835b5d9616c5e70eb8503266a106c2",
    "wave_Pulse50": "938a5165fa8eb9a96eac9fe582099511d58064ef199a75fa47d5607972b0462f",
    "wave_Saw": "8decda50b9cc3c2d50420c0d323c6b067e722e6daa851db3136e12386c295044",
    "wave_Sine": "e60af3890dd744c3b341c5433870f502923b6e04110582abf5d05e5c32c587cf",
    "wave_Triangle": "f255f9894314f222a66d08aedf662da74e34465d217370c27081099501d514f8",
}


class ArchitectureEquivalenceTests(unittest.TestCase):
    def test_RenderingAndEffectsMatchCanonicalOutput(self):
        numbaWasEnabled = ChirpKernels.NUMBA_ENABLED
        try:
            ChirpKernels.SetNumbaEnabled(False)
            actualHashes = GetArchitectureHashes()
            self.assertEqual(set(actualHashes), set(EXPECTED_ARCHITECTURE_HASHES))
            for caseName, expectedHash in EXPECTED_ARCHITECTURE_HASHES.items():
                with self.subTest(caseName = caseName):
                    self.assertEqual(actualHashes[caseName], expectedHash)
        finally:
            ChirpKernels.SetNumbaEnabled(numbaWasEnabled)

    def test_ToneAndControlsLiveOutsideConstants(self):
        self.assertEqual(Tone.__module__, "Chirper.core.ChirpTone")
        self.assertFalse(hasattr(ChirpConstants, "Tone"))
        self.assertNotIn("Tone", ChirpConstants.__all__)

    def test_SoundDoesNotDependOnSequenceOrPatch(self):
        self.assertFalse(hasattr(ChirpSoundModule, "Sequence"))
        self.assertFalse(hasattr(ChirpSoundModule, "Patch"))

    def test_SubpackageDependenciesFlowOneWay(self):
        appPath = Path(__file__).resolve().parents[1]
        allowedDependencies = {
            "io": {"io"},
            "core": {"core", "io"},
            "composition": {"composition", "core"},
            "playback": {"playback", "io"},
        }

        for groupName, allowedGroups in allowedDependencies.items():
            groupPath = appPath / "Chirper" / groupName
            for sourcePath in groupPath.rglob("*.py"):
                relativeParts = sourcePath.relative_to(appPath).with_suffix("").parts
                if relativeParts[-1] == "__init__":
                    relativeParts = relativeParts[:-1]
                moduleName = ".".join(relativeParts)
                packageName = moduleName if sourcePath.stem == "__init__" else (
                    moduleName.rsplit(".", 1)[0]
                )

                tree = ast.parse(sourcePath.read_text(encoding = "utf-8"))
                for node in ast.walk(tree):
                    importedModules = []
                    if isinstance(node, ast.Import):
                        importedModules = [alias.name for alias in node.names]
                    elif isinstance(node, ast.ImportFrom):
                        importedModule = node.module or ""
                        if node.level:
                            importedModule = importlib.util.resolve_name(
                                ("." * node.level) + importedModule,
                                packageName
                            )
                        importedModules = [importedModule]
                    else:
                        continue

                    for importedModule in importedModules:
                        if not importedModule.startswith("Chirper."):
                            continue

                        importedGroup = importedModule.split(".")[1]
                        self.assertIn(
                            importedGroup,
                            allowedGroups,
                            moduleName + " must not import " + importedModule
                        )

    def test_SubpackagesImportWithoutUnrelatedGroups(self):
        appPath = Path(__file__).resolve().parents[1]
        importCases = {
            "Chirper.io": ("core", "composition", "playback"),
            "Chirper.core": ("composition", "playback"),
            "Chirper.composition": ("playback",),
            "Chirper.playback": ("core", "composition"),
        }

        for moduleName, forbiddenGroups in importCases.items():
            checks = "\n".join(
                "assert not any(name == 'Chirper." + group
                + "' or name.startswith('Chirper." + group + ".') for name in sys.modules)"
                for group in forbiddenGroups
            )
            command = "import sys\nimport " + moduleName + "\n" + checks
            result = subprocess.run(
                [sys.executable, "-c", command],
                cwd = appPath,
                capture_output = True,
                text = True
            )
            self.assertEqual(
                result.returncode,
                0,
                moduleName + " imported an unrelated group:\n" + result.stderr
            )

    def test_NoteNamesHaveDistinctSequenceAndFrequencyRoles(self):
        self.assertEqual(ChirperModule.Note.__module__, "Chirper.composition.ChirpSequence")
        self.assertIs(ChirperModule.N, ChirpConstants.EqualNote)
        self.assertIsInstance(ChirperModule.N, ChirperModule.NoteFrequency)
        self.assertFalse(hasattr(ChirpConstants, "Note"))
        self.assertFalse(hasattr(ChirperModule, "NoteEvent"))

    def test_DefaultOscillatorWaveIsSine(self):
        default = ChirpSynth(channels = 1).RenderSamples([Tone(440.0, 0.01)])
        sine = ChirpSynth(channels = 1).RenderSamples([
            Tone(440.0, 0.01).Wave("Sine")
        ])

        np.testing.assert_array_equal(default, sine)

    def test_SynthAndDSPOwnSeparateOperations(self):
        self.assertTrue(hasattr(ChirpSynth, "RenderSamples"))
        self.assertFalse(hasattr(ChirpSynth, "ApplySoundGain"))
        self.assertFalse(hasattr(ChirpSynth, "SamplesToBytes"))
        self.assertTrue(hasattr(ChirpDSP, "ApplySoundGain"))
        self.assertTrue(hasattr(ChirpDSP, "SamplesToBytes"))
        self.assertFalse(hasattr(ChirpDSP, "RenderSamples"))
        self.assertFalse(hasattr(ChirpDSP, "GetSampleBytesDuration"))
        self.assertFalse(hasattr(ChirpDSP, "MixSampleBytes"))

    def test_SynthAndDSPShareTheOscillatorModule(self):
        self.assertIsInstance(ChirpSynth(channels = 1).oscillator, ChirpOscillator)
        self.assertIsInstance(ChirpDSP(channels = 1).oscillator, ChirpOscillator)
        self.assertFalse(hasattr(ChirpSynth, "Sine"))

    def test_SoundsRemainFloatNativeUntilPcmIsRequested(self):
        sound = ChirperModule.Sound([
            Tone(440.0, 0.01),
        ], channels = 1)

        self.assertIsInstance(sound._samples, np.ndarray)
        self.assertIsNone(sound._pcm)

        processed = sound.Gain(0.5).FadeOut(0.005)
        self.assertIsInstance(processed._samples, np.ndarray)
        self.assertIsNone(processed._pcm)

        pcm = processed.pcm
        self.assertIsInstance(pcm, bytes)
        self.assertIs(processed.pcm, pcm)

    def test_SoundConstructionAndMixingUseExplicitNormalization(self):
        with self.assertRaises(TypeError):
            ChirperModule.Sound(
                samples = [0.5],
                channels = 1,
                normalize = True
            )

        normalized = ChirperModule.Sound(
            samples = [0.5],
            channels = 1
        ).Normalize(3.0)
        self.assertAlmostEqual(
            max(normalized.samples),
            10.0 ** (-3.0 / 20.0)
        )

        with self.assertRaises(TypeError):
            ChirperModule.Sound.Mix(
                [normalized],
                normalize = True
            )

        mixed = ChirperModule.Sound.Mix([
            normalized,
            normalized
        ]).Normalize(3.0)
        self.assertAlmostEqual(
            max(mixed.samples),
            10.0 ** (-3.0 / 20.0)
        )

    def test_DSPPreservesByteAndSampleRepresentations(self):
        dsp = ChirpDSP(channels = 1)
        samples = np.array([0.0, 0.5, -0.5], dtype = np.float64)
        pcm = dsp.SamplesToBytes(samples)

        self.assertIsInstance(dsp.ApplySoundGain(pcm, 0.5), bytes)
        self.assertIsInstance(dsp.ApplySoundDebias(pcm), bytes)
        self.assertIsInstance(dsp.ApplySoundClip(pcm, 0.5), bytes)
        self.assertIsInstance(
            dsp.ApplySoundGain(samples, 0.5),
            np.ndarray
        )
        self.assertIsInstance(dsp.ApplySoundDebias(samples), np.ndarray)
        self.assertIsInstance(
            dsp.ApplySoundClip(samples, 0.5),
            np.ndarray
        )

    def test_GainPreservesFloatHeadroomUntilAnExplicitBoundary(self):
        sound = ChirperModule.Sound(
            samples = [0.8, 0.4, -0.8],
            channels = 1
        )

        gained = sound.Gain(2.0)
        normalized = gained.Normalize()

        np.testing.assert_array_equal(
            gained.samples,
            [1.6, 0.8, -1.6]
        )
        np.testing.assert_array_equal(
            normalized.samples,
            [1.0, 0.5, -1.0]
        )
        np.testing.assert_allclose(
            ChirpDSP(channels = 1).BytesToSamples(
                gained.pcm
            ),
            [1.0, 0.8, -1.0],
            rtol = 0.0,
            atol = 1.0 / 32767.0
        )

    def test_ClipUsesAnExplicitSymmetricLimit(self):
        sound = ChirperModule.Sound(
            samples = [2.0, 0.5, -2.0],
            channels = 1
        )

        np.testing.assert_array_equal(
            sound.Clip(1.5).samples,
            [1.5, 0.5, -1.5]
        )
        np.testing.assert_array_equal(
            sound.Clip().samples,
            [1.0, 0.5, -1.0]
        )

    def test_CompiledRenderPlansAreReusable(self):
        synthesizer = ChirpSynth(channels = 2)
        notes = [
            Tone(440.0, 0.01).Wave("Sine"),
            Tone(660.0, 0.01).Wave("Sine"),
        ]
        plan = synthesizer.CompileSequence(notes)

        self.assertIsInstance(plan, ChirpRenderPlan)
        self.assertEqual(plan.sampleCount, 1764)
        firstRender = synthesizer.RenderSamples(plan)
        secondRender = synthesizer.RenderSamples(plan)
        directRender = ChirpSynth(channels = 2).RenderSamples(notes)

        np.testing.assert_array_equal(firstRender, secondRender)
        np.testing.assert_array_equal(firstRender, directRender)

    def test_ChirperUsesCompositionAndDelegatesCompatibilityMethods(self):
        chirper = Chirper(channels = 1, enabled = False)

        try:
            self.assertNotIsInstance(chirper, ChirpSynth)
            self.assertIsInstance(chirper.synth, ChirpSynth)
            self.assertIsInstance(chirper.dsp, ChirpDSP)
            np.testing.assert_array_equal(
                chirper.RenderSamples([Tone(440.0, 0.001)]),
                chirper.synth.RenderSamples([Tone(440.0, 0.001)])
            )
            self.assertEqual(
                chirper.SamplesToBytes([0.0, 0.5]),
                chirper.dsp.SamplesToBytes([0.0, 0.5])
            )
            chirper.pitch = 1.5
            self.assertEqual(chirper.synth.pitch, 1.5)
            with self.assertRaises(AttributeError):
                chirper.channels = 2
            with self.assertRaises(AttributeError):
                chirper.SAMPLE_RATE = 22050
            with self.assertRaises(AttributeError):
                chirper.synth = ChirpSynth(channels = 1)
            self.assertEqual(chirper.synth.channels, 1)
            self.assertEqual(chirper.dsp.channels, 1)
            self.assertEqual(chirper.player.channels, 1)
            self.assertEqual(chirper.player.mixer.channels, 1)
            chirper.SetVolume(0.5)
            self.assertEqual(chirper.player.mixer.volume, 0.25)
            self.assertEqual(
                chirper.GetStats(),
                {"blockFrames": 1024, "activeVoices": 0, "queuedVoices": 0}
            )
        finally:
            chirper.Close()

    def test_PublicImportsRemainAvailable(self):
        publicNames = (
            "Chirper",
            "JustRatio",
            "EqualRatio",
            "JustScale",
            "EqualScale",
            "NoteFrequency",
            "NoteLength",
            "Vibrato",
            "Tremolo",
            "Dynamics",
            "QFactor",
            "N",
            "L",
            "V",
            "T",
            "D",
            "JR",
            "ER",
            "JS",
            "ES",
            "Q",
            "Tone",
            "Control",
            "Wave",
            "Pitch",
            "Tempo",
            "Seconds",
            "VibratoDepth",
            "VibratoRate",
            "VibratoWave",
            "TremoloDepth",
            "TremoloRate",
            "TremoloWave",
            "Insert",
            "Sound",
            "Util",
            "Envelope",
            "Patch",
            "Patches",
            "Meter",
            "SetPatch",
            "Note",
            "Sequence",
            "ChirpDSP",
            "ChirpOscillator",
            "WaveTable",
            "ChirpMixer",
            "ChirpVoiceHandle",
            "ChirpRenderPlan",
            "ChirpSynth",
            "ChirpPlayer",
            "ChirpFile",
        )

        self.assertEqual(set(ChirperModule.__all__), set(publicNames))
        for name in publicNames:
            self.assertTrue(hasattr(ChirperModule, name), name)

        from Chirper.core.ChirpUtil import Util

        self.assertIs(ChirperModule.Util, Util)
        self.assertFalse(hasattr(ChirperModule, "Dyn"))
        self.assertFalse(hasattr(ChirperModule, "Tr"))
        self.assertIs(ChirperModule.D, ChirperModule.Dynamics)
        self.assertIs(ChirperModule.T, ChirperModule.Tremolo)
        self.assertIs(ChirperModule.JR, ChirperModule.JustRatio)
        self.assertIs(ChirperModule.ER, ChirperModule.EqualRatio)
        self.assertIs(ChirperModule.JS, ChirperModule.JustScale)
        self.assertIs(ChirperModule.ES, ChirperModule.EqualScale)
        self.assertFalse(hasattr(ChirperModule, "Ratio"))
        self.assertFalse(hasattr(ChirperModule, "R"))

        patchModule = importlib.import_module("Chirper.composition.ChirpPatches")
        self.assertEqual(patchModule.__all__, ["Patches"])
        self.assertFalse(hasattr(ChirperModule, "_SinePatch"))

        soundModule = importlib.import_module("Chirper.core.ChirpSound")
        toneModule = importlib.import_module("Chirper.core.ChirpTone")
        sequenceModule = importlib.import_module("Chirper.composition.ChirpSequence")
        self.assertFalse(hasattr(ChirperModule, "ChirpSound"))
        self.assertFalse(hasattr(soundModule, "ChirpSound"))
        for removedName in ("S", "UsePatch"):
            self.assertFalse(hasattr(ChirperModule, removedName))
        self.assertFalse(hasattr(soundModule, "S"))
        self.assertFalse(hasattr(toneModule, "T"))
        self.assertFalse(hasattr(sequenceModule, "UsePatch"))

    def test_FileFormatRoundTripRemainsValid(self):
        source = ChirperModule.Sound([
            Tone(440.0, 0.01),
        ], channels = 1)

        with tempfile.TemporaryDirectory() as tempDirectory:
            chirpPath = Path(tempDirectory) / "roundtrip.chirp"
            wavPath = Path(tempDirectory) / "roundtrip.wav"
            source.Save(chirpPath)
            chirpLoaded = ChirperModule.Sound.Load(chirpPath)
            chirpLoaded.SaveWav(wavPath)
            loaded = ChirperModule.Sound.LoadWav(wavPath)

        np.testing.assert_array_equal(
            chirpLoaded.samples,
            source.samples.astype(np.float32).astype(np.float64)
        )
        self.assertEqual(loaded.pcm, chirpLoaded.pcm)
        self.assertEqual(loaded.channels, source.channels)
