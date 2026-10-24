from .core.ChirpDSP import ChirpDSP
from .core.ChirpSynth import ChirpSynth
from .playback.ChirpPlayer import ChirpPlayer


class Chirper:
    SAMPLE_RATE = ChirpSynth.SAMPLE_RATE
    BITS_PER_SAMPLE = ChirpSynth.BITS_PER_SAMPLE
    MIN_FREQ = ChirpSynth.MIN_FREQ

    def __init__(self, volume = 1.0, channels = 2, voices = 16, enabled = True):
        self.synth = ChirpSynth(channels = channels)
        self.dsp = ChirpDSP(channels = channels)
        self.player = ChirpPlayer(channels = channels, voices = voices, volume = volume, enabled = enabled)

    def __setattr__(self, name, value):
        if name in ("synth", "dsp", "player"):
            if name in self.__dict__:
                raise AttributeError("Chirper components cannot be replaced")
            object.__setattr__(self, name, value)
            return
        if name in ("SAMPLE_RATE", "BITS_PER_SAMPLE", "MIN_FREQ", "channels"):
            raise AttributeError(
                "Chirper audio format is fixed when it is constructed"
            )

        delegated = False
        synthesizer = self.__dict__.get("synth")
        if synthesizer is not None and hasattr(synthesizer, name):
            setattr(synthesizer, name, value)
            delegated = True

        dsp = self.__dict__.get("dsp")
        if dsp is not None and hasattr(dsp, name):
            setattr(dsp, name, value)
            delegated = True

        if delegated:
            return

        object.__setattr__(self, name, value)

    def __getattr__(self, name):
        synthesizer = self.__dict__.get("synth")
        if synthesizer is not None and hasattr(synthesizer, name):
            return getattr(synthesizer, name)

        dsp = self.__dict__.get("dsp")
        if dsp is not None and hasattr(dsp, name):
            return getattr(dsp, name)

        raise AttributeError(type(self).__name__ + " has no attribute " + repr(name))

    def Play(self, sound, volume = 1.0, blocking = False, voice = None):
        return self.player.Play(sound, volume, blocking, voice)

    def PlayQueued(self, sound, volume = 1.0, voice = None):
        return self.player.PlayQueued(sound, volume, voice)

    def PlaySolo(self, sound, volume = 1.0, blocking = False):
        return self.player.PlaySolo(sound, volume, blocking)

    def SetVolume(self, volume):
        self.player.SetVolume(volume)

    def GetStats(self):
        return self.player.GetStats()

    def StopAll(self):
        self.player.StopAll()

    def Close(self):
        self.player.Close()

    def __enter__(self):
        return self

    def __exit__(self, exceptionType, exception, traceback):
        self.Close()
