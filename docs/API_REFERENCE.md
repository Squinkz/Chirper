# Chirper API Reference

This document is a navigable reference for Chirper's public classes, methods,
controls, waves, presets, playback tools, and advanced component APIs.

```python
from Chirper import *
```

Only the classes, methods, and functions listed in this reference are public
API. Other names on Chirper's component classes and `ChirpFile` module are implementation
details, even where Chirper's naming style gives them capitalized names.

---

## Table Of Contents

- [Sound](#contents-sound)
- [Sequence](#contents-sequence)
- [Note](#contents-note)
- [SetPatch](#contents-setpatch)
- [Meter](#contents-meter)
- [Tone](#contents-tone)
- [Envelope](#contents-envelope)
- [Patch](#contents-patch)
- [Patches](#contents-patches)
- [Recipe Controls](#contents-controls)
- [Waves](#contents-waves)
- [Easing](#contents-easing)
- [Constants And Presets](#contents-constants)
- [Chirper](#contents-chirper)
- [ChirpVoiceHandle](#contents-voice-handle)
- [ChirpSynth](#contents-synth)
- [ChirpOscillator](#contents-oscillator)
- [ChirpDSP](#contents-dsp)
- [ChirpMixer](#contents-mixer)
- [ChirpPlayer](#contents-player)
- [ChirpFile](#contents-file)

---

<a id="contents-sound"></a>
### [Sound](#sound-reference)
- [`Sound()`](#sound-constructor)<br>
- [`SetDefaults()`](#sound-set-defaults)<br>
- [`Load()`](#sound-load)<br>
- [`LoadWav()`](#sound-load-wav)<br>
- [`Save()`](#sound-save)<br>
- [`SaveWav()`](#sound-save-wav)<br>
- [`Mix()`](#sound-mix)<br>
- [`Append()`](#sound-append)<br>
- [`Cut()`](#sound-cut)<br>
- [`FadeIn()`](#sound-fade-in)<br>
- [`FadeOut()`](#sound-fade-out)<br>
- [`Reverse()`](#sound-reverse)<br>
- [`Invert()`](#sound-invert)<br>
- [`Gain()`](#sound-gain)<br>
- [`Debias()`](#sound-debias)<br>
- [`Clip()`](#sound-clip)<br>
- [`Normalize()`](#sound-normalize)<br>
- [`SoftClip()`](#sound-soft-clip)<br>
- [`Ring()`](#sound-ring)<br>
- [`Chorus()`](#sound-chorus)<br>
- [`Phaser()`](#sound-phaser)<br>
- [`Pan()`](#sound-pan)<br>
- [`AutoPan()`](#sound-auto-pan)<br>
- [`Mono()`](#sound-mono)<br>
- [`Stereo()`](#sound-stereo)<br>
- [`LowPass()`](#sound-low-pass)<br>
- [`HighPass()`](#sound-high-pass)<br>
- [`BandPass()`](#sound-band-pass)<br>
- [`Notch()`](#sound-notch)<br>
- [`Peak()`](#sound-peak)<br>
- [`LowShelf()`](#sound-low-shelf)<br>
- [`HighShelf()`](#sound-high-shelf)<br>
- [`LowPassSweep()`](#sound-low-pass-sweep)<br>
- [`HighPassSweep()`](#sound-high-pass-sweep)<br>
- [`BandPassSweep()`](#sound-band-pass-sweep)<br>
- [`NotchSweep()`](#sound-notch-sweep)<br>
- [`PeakSweep()`](#sound-peak-sweep)<br>
- [`LowShelfSweep()`](#sound-low-shelf-sweep)<br>
- [`HighShelfSweep()`](#sound-high-shelf-sweep)<br>
- [`Schroverb()`](#sound-schroverb)<br>
- [`Freeverb()`](#sound-freeverb)<br>
- [`MTVerb()`](#sound-mtverb)<br>
- [`Delay()`](#sound-delay)<br>
- [`PingPong()`](#sound-ping-pong)<br>

<a id="sound-reference"></a>
## Sound

`Sound` is Chirper's rendered-audio object. It stores immutable floating-point
samples and returns a new `Sound` from every processing method.

<a id="sound-constructor"></a>
### `Sound(data = None, channels = None, layered = True)`

- `data`: A list of `Tone`, `Insert`, and recipe-control objects; a `Sequence`;
  or `None` for an empty sound.
- `channels`: `1` for mono or `2` for stereo. `None` uses `Sound.CHANNELS`.
- `layered`: Selects layered or sequential interpretation for a recipe list.

With `layered = True`, every `Tone` and `Insert` starts at the beginning of the
Sound. The result lasts as long as its longest layer. With `layered = False`,
each `Tone` or `Insert` starts after the previous one finishes. Recipe controls
affect the Tones that follow them in the list in either mode.

Layered rendering does not reduce gain, normalize, or clip the mixed samples.
When `data` is a `Sequence`, the Sequence supplies all timing and Chirper
ignores `layered`.

PCM, sample, and metadata keyword arguments are used by Chirper's loaders and
copy operations. Normal user code should use `data`, `Load()`, or `LoadWav()`.
Custom metadata fields are retained by loading, copying, and Sound processing
operations. Chirper recalculates reserved format, channel, and duration fields
to match the resulting Sound.

Useful properties are `samples`, `pcm`, `duration`, `channels`, `sampleRate`,
`bitsPerSample`, and `metadata`. Reading `samples` returns a writable copy.
Reading `metadata` returns a deep copy, so changing it cannot alter the Sound or
the metadata used by later save operations.
Reading `pcm` creates signed 16-bit PCM and clips at that conversion boundary.
Samples are stored internally as finite float64 values; `NaN` and infinity are
rejected. `bitsPerSample == 16` and
`metadata["format"] == "pcm_s16le"` describe the PCM representation produced
for playback and WAV export, not the internal samples or native `.chirp` data.

<a id="sound-set-defaults"></a>
### `Sound.SetDefaults(channels = None)`

- `channels`: New default channel count for subsequently created sounds. Must be
  `1` or `2`.

<a id="sound-load"></a>
### `Sound.Load(path)`

- `path`: `.chirp` path. A missing extension is appended and a different
  extension is replaced.

Returns a `Sound` loaded from Chirper's native file format.
Native samples are stored as little-endian float32 and promoted to Chirper's
internal float64 representation when loaded.

<a id="sound-load-wav"></a>
### `Sound.LoadWav(path)`

- `path`: WAV path. A missing extension is appended and a different extension
  is replaced.

Loads mono or stereo 44.1 kHz PCM WAV data. Supported source widths are 8, 16,
and 24 bits. Source PCM is decoded directly to float64 without an intermediate
16-bit conversion.

<a id="sound-save"></a>
### `sound.Save(path)`

- `path`: Destination `.chirp` path. A missing extension is appended and a
  different extension is replaced.

Writes unclipped little-endian float32 samples and returns the resolved output
`Path`. Values outside `[-1, 1]` are preserved. `NaN`, infinity, and values
outside the float32 range are rejected. Custom metadata must contain valid,
finite JSON values. Missing parent directories are created. The destination is
replaced atomically after the complete file has been written.

<a id="sound-save-wav"></a>
### `sound.SaveWav(path)`

- `path`: Destination WAV path. A missing extension is appended and a different
  extension is replaced.

Writes signed 16-bit PCM and returns the resolved output `Path`. Values outside
`[-1, 1]` clip at export. Missing parent directories are created. The
destination is replaced atomically after the complete file has been written.

<a id="sound-mix"></a>
### `Sound.Mix(sounds, channels = None, mixGain = 0.707)`

- `sounds`: List of `Sound` objects.
- `channels`: Output channel count. `None` uses the current Sound default.
- `mixGain`: Linear gain applied once after summing all inputs.

Inputs may have different durations and channel counts. Shorter sounds are
zero-padded. Mono sources are centered when mixing to stereo; stereo sources
are averaged when mixing to mono. Inputs must share the same sample rate. The
list must contain at least one Sound.

<a id="sound-append"></a>
### `sound.Append(sound, crossfade = 0.0, easing = "equalPower")`

- `sound`: The `Sound` to place after the current sound.
- `crossfade`: Overlap length in seconds. Zero or negative values concatenate
  the sounds directly.
- `easing`: Crossfade curve. This must be `"linear"` or `"equalPower"`.

The overlap cannot be longer than either Sound. If `crossfade` exceeds the
duration of the shorter Sound, the complete shorter Sound is used as the
overlap.

The default `"equalPower"` curve maintains constant combined power and prevents
the midpoint level dip that can occur when crossfading unrelated material. Its
incoming and outgoing gains are sine and cosine curves. Correlated signals can
reach approximately `+3 dB` at the midpoint. The `"linear"` curve keeps the two
gains summing to `1.0`, which preserves the level of identical or strongly
correlated material.

If either sound is stereo, the result is stereo and any mono input is centered.
The method returns a new `Sound` and does not clip or normalize its samples.

<a id="sound-cut"></a>
### `sound.Cut(duration, fade = 0.003)`

- `duration`: Number of seconds to keep.
- `fade`: Maximum fade-out length applied at the new end.

<a id="sound-fade-in"></a>
### `sound.FadeIn(duration, easing = "linear")`

- `duration`: Fade length in seconds.
- `easing`: Gain curve name or function.

Raises gain from zero across the beginning of the sound.

<a id="sound-fade-out"></a>
### `sound.FadeOut(duration, easing = "linear")`

- `duration`: Fade length in seconds.
- `easing`: Gain curve name or function.

Lowers gain to zero across the end of the sound.

<a id="sound-reverse"></a>
### `sound.Reverse()`

Reverses sample frames while preserving stereo channel pairs.

<a id="sound-invert"></a>
### `sound.Invert()`

Multiplies every sample by `-1`, reversing signal polarity.

<a id="sound-gain"></a>
### `sound.Gain(amount)`

- `amount`: Linear sample multiplier.

Gain does not clip. Floating-point samples may exceed `[-1, 1]` until an
explicit clipping or PCM boundary.

<a id="sound-debias"></a>
### `sound.Debias()`

Subtracts each channel's mean independently, centering each complete channel
around zero. It does not normalize or clip.

<a id="sound-clip"></a>
### `sound.Clip(limit = 1.0)`

- `limit`: Symmetric hard limit. `limit` is clamped to zero.

<a id="sound-normalize"></a>
### `sound.Normalize(headroom = 0.0)`

- `headroom`: Non-negative decibels below full scale.

Scales the largest absolute sample to `10 ** (-headroom / 20)`. It does not
debias or otherwise reshape the signal.

<a id="sound-soft-clip"></a>
### `sound.SoftClip(drive = 2.0, mix = 1.0)`

- `drive`: Saturation intensity.
- `mix`: Dry/wet proportion from `0` to `1`.

Applies normalized tanh saturation. The wet signal is bounded to `[-1, 1]`
before the dry/wet blend. Partial mixes preserve floating-point headroom and do
not clip the final result.

<a id="sound-ring"></a>
### `sound.Ring(freq, mix = 1.0, wave = "Sine")`

- `freq`: Carrier frequency in Hz.
- `mix`: Dry/wet proportion.
- `wave`: Built-in wave name, custom function, `WaveTable`, or `Sound` wave table.

Multiplies the source by the carrier waveform.

<a id="sound-chorus"></a>
### `sound.Chorus(rate = 0.8, depth = 0.003, delay = 0.015, voices = 2, feedback = 0.0, spread = 1.0, mix = 0.5, wave = "Sine")`

- `rate`: LFO frequency in Hz.
- `depth`: Delay modulation depth in seconds.
- `delay`: Base delay in seconds.
- `voices`: Number of modulated delay taps.
- `feedback`: Feedback clamped to `[-0.95, 0.95]`.
- `spread`: Voice and stereo LFO phase separation from `0` to `1`.
- `mix`: Dry/wet proportion.
- `wave`: LFO wave.

<a id="sound-phaser"></a>
### `sound.Phaser(rate = 0.5, minFreq = 300.0, maxFreq = 1600.0, stages = 6, feedback = 0.2, spread = 1.0, mix = 0.5, wave = "Sine")`

- `rate`: LFO frequency in Hz.
- `minFreq`, `maxFreq`: All-pass sweep range in Hz.
- `stages`: Number of cascaded first-order all-pass stages.
- `feedback`: Feedback clamped to `[-0.95, 0.95]`.
- `spread`: Stereo LFO phase separation.
- `mix`: Dry/wet proportion.
- `wave`: LFO wave.

<a id="sound-pan"></a>
### `sound.Pan(amount)`

- `amount`: Position clamped to `-1` left through `0` center to `1` right.

Mono is promoted to stereo and placed with equal-power panning. Existing
stereo is rotated and narrowed toward the requested side. Panning does not
clip, so a hard-panned stereo sum may exceed full scale.

<a id="sound-auto-pan"></a>
### `sound.AutoPan(depth = 1.0, rate = 1.0, wave = "Sine", offset = 0.0)`

- `depth`: Pan movement from `0` through `1`.
- `rate`: LFO frequency in Hz.
- `wave`: Built-in wave name, custom function, `WaveTable`, or `Sound` wave table.
- `offset`: Starting position in the LFO cycle, expressed in degrees.

Uses one bipolar LFO as an equal-power pan position. With the default sine
wave, `offset = 0` starts at center, `90` starts at the right, and `-90` starts
at the left. This is spatial movement rather than separate left/right gain
modulation, so it does not turn into tremolo when both channels are centered.

Mono is promoted to stereo. Existing stereo is continuously rotated and
narrowed using the same behavior as `Pan()`. AutoPan does not clip or normalize.

<a id="sound-mono"></a>
### `sound.Mono()`

Returns mono audio. Stereo frames use `(left + right) * 0.5`.

<a id="sound-stereo"></a>
### `sound.Stereo()`

Returns stereo audio. Mono is placed equally in both channels using
equal-power center gains.

<a id="sound-low-pass"></a>
### `sound.LowPass(freq, q = Q.MID)`

- `freq`: Cutoff in Hz.
- `q`: Resonance/Q.

<a id="sound-high-pass"></a>
### `sound.HighPass(freq, q = Q.MID)`

- `freq`: Cutoff in Hz.
- `q`: Resonance/Q.

<a id="sound-band-pass"></a>
### `sound.BandPass(freq, q = Q.MID)`

- `freq`: Center frequency in Hz.
- `q`: Bandwidth/Q.

<a id="sound-notch"></a>
### `sound.Notch(freq, q = Q.MID)`

- `freq`: Rejected center frequency in Hz.
- `q`: Bandwidth/Q.

<a id="sound-peak"></a>
### `sound.Peak(freq, db, q = Q.MID)`

- `freq`: Center frequency in Hz.
- `db`: Boost or cut in decibels.
- `q`: Bandwidth/Q.

<a id="sound-low-shelf"></a>
### `sound.LowShelf(freq, db, q = Q.MID)`

- `freq`: Shelf transition frequency.
- `db`: Low-frequency boost or cut.
- `q`: Shelf slope/Q.

<a id="sound-high-shelf"></a>
### `sound.HighShelf(freq, db, q = Q.MID)`

- `freq`: Shelf transition frequency.
- `db`: High-frequency boost or cut.
- `q`: Shelf slope/Q.

Filter frequencies are clamped below Nyquist. Filter output remains floating
point and is not normalized or clipped. When the input ends at zero, any
remaining filter response is faded over the final `0.003` seconds so filtering
does not turn a silent endpoint into an audible discontinuity.

Inside a Patch recipe, the incoming `freq` value can be passed directly to any
filter or used in arithmetic such as `freq * 4.0`. The filter then tracks the
Note's bend, step bend, scoped bends, portamento, trill, and vibrato. Cutoff
changes are smoothed over approximately `0.001` seconds to prevent abrupt
coefficient changes from clicking. A regular number still creates a fixed
filter frequency. Tone-level pitch effects remain local to their Tone and do
not affect a separate filter automatically.

<a id="sound-low-pass-sweep"></a>
### `sound.LowPassSweep(startFreq, endFreq, q = Q.MID, easing = "linear")`

Sweeps a low-pass cutoff between the two frequencies.

<a id="sound-high-pass-sweep"></a>
### `sound.HighPassSweep(startFreq, endFreq, q = Q.MID, easing = "linear")`

Sweeps a high-pass cutoff between the two frequencies.

<a id="sound-band-pass-sweep"></a>
### `sound.BandPassSweep(startFreq, endFreq, q = Q.MID, easing = "linear")`

Sweeps a band-pass center frequency.

<a id="sound-notch-sweep"></a>
### `sound.NotchSweep(startFreq, endFreq, q = Q.MID, easing = "linear")`

Sweeps a notch center frequency.

<a id="sound-peak-sweep"></a>
### `sound.PeakSweep(startFreq, endFreq, db, q = Q.MID, easing = "linear")`

Sweeps the center frequency of a fixed peak boost or cut.

<a id="sound-low-shelf-sweep"></a>
### `sound.LowShelfSweep(startFreq, endFreq, db, q = Q.MID, easing = "linear")`

Sweeps a low-shelf transition frequency.

<a id="sound-high-shelf-sweep"></a>
### `sound.HighShelfSweep(startFreq, endFreq, db, q = Q.MID, easing = "linear")`

Sweeps a high-shelf transition frequency.

All sweep methods interpolate frequency geometrically. `easing` accepts a curve
name or function and shapes sweep progress; it does not change frequency
interpolation into linear Hz. Either sweep endpoint can use the incoming Patch
`freq`; both endpoints continue tracking performance pitch while the sweep moves
between them.

<a id="sound-schroverb"></a>
### `sound.Schroverb(wet = 0.35, decay = 0.72, roomSize = 1.0, tail = None)`

- `wet`: Wet proportion.
- `decay`: Feedback amount.
- `roomSize`: Delay-size multiplier, minimum `0.25`.
- `tail`: Added tail seconds, or `None` to calculate the complete network tail.

Schroverb is a Schroeder-style reverb network. It preserves the input channel
count. Stereo channels pass through independent copies of the same delay
network, so the effect does not create stereo width. At `wet = 0.0`, it returns
the original duration without adding a tail.

<a id="sound-freeverb"></a>
### `sound.Freeverb(wet = 0.35, decay = 0.84, damping = 0.5, width = 1.0, tail = None)`

- `wet`: Wet proportion.
- `decay`: Feedback amount.
- `damping`: High-frequency damping.
- `width`: Stereo width.
- `tail`: Added tail seconds, or `None` to calculate the complete network tail.

Freeverb is based on the open-source Freeverb algorithm. It preserves the input
channel count. The `width` control shapes the reverb field when the input is
stereo. At `wet = 0.0`, it returns the original duration without adding a tail.

<a id="sound-mtverb"></a>
### `sound.MTVerb(wet = 0.35, decay = 0.72, mode = "room", tail = None)`

- `wet`: Wet proportion.
- `decay`: Feedback amount.
- `mode`: `"room"`, `"hall"`, or `"plate"`; values `0`, `1`, and `2` are
  also accepted.
- `tail`: Added tail seconds, or `None` to calculate the complete network tail.

MTVerb emulates the reverb unit in the Roland MT-32 and CM-32. It is based on
the implementation in the Munt emulator. It preserves the input channel count
and produces a stereo reverb field from stereo input. At `wet = 0.0`, it
returns the original duration without adding a tail.

<a id="sound-delay"></a>
### `sound.Delay(delay = 0.25, decay = 0.5, count = None, extend = True)`

- `delay`: Seconds between repetitions.
- `decay`: Gain multiplier for each repetition.
- `count`: Number of repetitions, or `None` to derive a useful count.
- `extend`: Whether repetitions may extend beyond the source duration.

When `count = None`, repetitions continue until their gain falls below `0.01`,
subject to a maximum automatic tail length of 30 seconds. An explicit `count`
is not subject to that automatic-tail limit.

<a id="sound-ping-pong"></a>
### `sound.PingPong(delay = 0.25, decay = 0.5, count = None, width = 1.0, extend = True)`

- `delay`, `decay`, `count`, `extend`: Same meanings as `Delay()`.
- `width`: Stereo movement from `0` centered to `1` full left/right.

Ping-pong delay always returns stereo and automatically promotes mono input.
Mono echoes alternate between left and right according to `width`. For stereo
input, odd echoes move each source channel toward the opposite side and even
echoes retain the original channel orientation. The stereo source is not first
collapsed to mono.

---

<a id="contents-sequence"></a>
### [Sequence](#sequence-reference)

- [`Sequence()`](#sequence-constructor)<br>
- [`Start()`](#sequence-start)<br>
- [`End()`](#sequence-end)<br>
- [`FirstBar()`](#sequence-first-bar)<br>
- [`LastBar()`](#sequence-last-bar)<br>
- [`Trim()`](#sequence-trim)<br>
- [`Gain()`](#sequence-gain)<br>
- [Sequence composition](#sequence-composition)<br>
- [`RenderSamples()`](#sequence-render-samples)<br>
- [`Render()`](#sequence-render)<br>

<a id="sequence-reference"></a>
## Sequence

`Sequence` arranges `Note` events on a musical timeline. Notes render through
the active `Patch` and are mixed into a single floating-point output. Notes
using a polyphonic Patch may overlap freely; a monophonic Patch resolves its
Note durations before rendering.

<a id="sequence-constructor"></a>
### `Sequence(events = None)`

- `events`: List containing `Tempo`, `Meter`, `SetPatch`, and `Note`
  objects.

Bars are zero-indexed integers. Beats are zero-indexed and accept decimals.
A Note beat must be at least zero and less than the active Meter's beat count.
Notes outside that range are omitted during rendering and produce a summarized
warning. They do not overflow into another bar. Note durations and audio tails
may continue across bar boundaries normally.

Tempo defaults to `120`, Meter defaults to `4/4`, and the active Patch defaults
to `Patches.SuperSine`.

A directly constructed Sequence may contain at most one `Tempo` command and
one `Meter` command. Their positions in the list do not matter. Both apply to
the complete Sequence from local bar `0`, beat `0`.

Each Sequence has its own Tempo and Meter. If either command is omitted, that
Sequence uses the corresponding default instead of inheriting from a Sequence
concatenated before it. `SetPatch` is different: it affects only Notes that
follow it in the same event list.

Chirper infers the Sequence span from the latest included Note endpoint, then
rounds that span up to a complete bar. Patch layers, inserted Sounds, envelope
releases, and effect tails do not extend the musical span. Their audio is not
cut off; it may continue beyond the span and overlap the next concatenated
Sequence.

```python
sequence = Sequence([
    Tempo(120),
    Meter(4, 4),
    SetPatch(Patches.SuperSaw),
    Note(0, 0, N.C4, L.L4, D.D10),
])
```

<a id="sequence-start"></a>
### `sequence.Start(bar, beat)`

Returns a new Sequence beginning at the selected position. Earlier Notes are
omitted and the selected position becomes local time zero. The source Sequence
is not modified.

<a id="sequence-end"></a>
### `sequence.End(bar, beat)`

Returns a new Sequence ending at the selected position. Notes beginning at or
after that position are omitted. The source Sequence is not modified.

Selections are half-open: `Start()` is included and `End()` is excluded. An
included Note retains its complete duration and release tail, even when its
audio continues beyond `End()`. Equal positions produce an empty Sequence; an
end before the start raises a `ValueError`. Negative selection positions clamp
to the beginning, but selection beats at or beyond the active Meter's beat
count raise a `ValueError`.

Both methods may be chained. Their positions refer to the same original
timeline rather than being rebased between calls:

```python
section = sequence.Start(4, 0).End(6, 0)
```

They also operate on concatenated and repeated Sequences. Global bars are
resolved through components in playback order, using the Meter and Tempo of
the component occupying each position. Every concatenated component begins a
new logical bar.

<a id="sequence-first-bar"></a>
### `sequence.FirstBar()`

Returns the zero-indexed number of the first bar containing a valid Note, or
`None` when the Sequence contains no valid Notes. Only authored Note start
positions count. Note durations, release tails, Patch layers, inserted Sounds,
and generated arpeggio Notes do not make later bars occupied.

The result describes the current Sequence. Existing selections, concatenation,
repetition, and each component's Meter are respected.

<a id="sequence-last-bar"></a>
### `sequence.LastBar()`

Returns the zero-indexed number of the last bar containing a valid authored
Note, or `None` when the Sequence contains no valid Notes. A Note extending
into a later bar does not make that later bar occupied.

<a id="sequence-trim"></a>
### `sequence.Trim()`

Returns a new Sequence beginning at its first occupied bar and ending after
its last occupied bar. The first occupied bar becomes bar `0`. The source
Sequence is not modified.

Trimming removes complete leading and trailing blank bars. Included Notes keep
their complete durations and audio tails. An empty Sequence produces a new
empty Sequence.

<a id="sequence-gain"></a>
### `sequence.Gain(amount)`

- `amount`: Finite non-negative linear amplitude multiplier.

Returns a new Sequence with every Note amplitude and Note fade target scaled
by `amount`. The source Sequence is not modified. Gain operates through cut,
concatenated, and repeated Sequence structures, and repeated calls compound.
Patch designer gains, Patch balance, and rendered DSP are not changed.

<a id="sequence-composition"></a>
### Sequence composition

`+` concatenates Sequences and `*` repeats them without rendering:

```python
song = intro + (verse * 2) + chorus
```

Both operators return a new Sequence and snapshot the source event structure;
they do not mutate their operands. Patches, Sounds, and other referenced audio
objects remain shared. Repetition accepts integers, supports either operand
order, and produces an empty Sequence for zero or negative counts.

Every component retains its own local bar positions, Tempo, Meter, selection,
and musical span. Chirper places all component Notes on one timeline before
monophonic resolution and rendering. Compatible monophonic oscillator state
may therefore continue across component boundaries. A monophonic Note may
shorten a Note in the previous component. Audio tails overlap the next
component instead of delaying it.

<a id="sequence-render-samples"></a>
### `sequence.RenderSamples(channels = 2)`

- `channels`: Output channel count, `1` or `2`.

Returns a one-dimensional interleaved float64 sample array.

<a id="sequence-render"></a>
### `sequence.Render(channels = 2)`

Renders and returns a `Sound`.

---

<a id="contents-note"></a>
### [Note](#note-reference)

- [`Note()`](#note-constructor)<br>
- [`Bend()`](#note-bend)<br>
- [`BendIn()`](#note-bend-in)<br>
- [`BendOut()`](#note-bend-out)<br>
- [`StepBend()`](#note-step-bend)<br>
- [`Trill()`](#note-trill)<br>
- [`Chord()`](#note-chord)<br>
- [`Arpeggio()`](#note-arpeggio)<br>
- [`Pan()`](#note-pan)<br>
- [`AutoPan()`](#note-auto-pan)<br>
- [`Vibrato()`](#note-vibrato)<br>
- [`Tremolo()`](#note-tremolo)<br>
- [`Fade()`](#note-fade)<br>
- [`FadeIn()`](#note-fade-in)<br>
- [`FadeOut()`](#note-fade-out)<br>

<a id="note-reference"></a>
## Note

`Note` describes musical placement and performance. It does not select an
oscillator wave; the active Patch owns synthesis choices.

<a id="note-constructor"></a>
### `Note(bar, beat, freq, duration, amplitude = 1.0)`

- `bar`: Zero-indexed bar position.
- `beat`: Zero-indexed beat position within the bar.
- `freq`: Frequency passed into the Patch recipe.
- `duration`: Whole-note fraction resolved by sequence tempo.
- `amplitude`: Linear gain passed into the Patch recipe.

<a id="note-bend"></a>
### `note.Bend(target, easing = "linear")`

- `target`: Target frequency or ratio. Values below `20.0` are ratios for
  pitched layers; values of `20.0` or more are absolute frequencies. Constants
  such as `N.MIN`, `N.MAX`, and `ER.FIFTH` may be used.
- `easing`: Bend progress curve name or function.

Noise layers always interpret `target` as an absolute cutoff frequency or clock
rate, including values below `20.0`. A Patch frequency derived from the incoming
`freq` value inherits the bend proportionally. A frequency written as an
independent number in the Patch recipe does not inherit it.

`Insert()` does not pitch-shift rendered samples. A Patch recipe may still
construct a new Sound from its incoming `freq` value and then insert that
Sound. Tones synthesized this way inherit the bend before the Sound is
inserted.

Calling `Bend()` replaces any previous `StepBend()`, `BendIn()`, and
`BendOut()` on the same Note.

<a id="note-bend-in"></a>
### `note.BendIn(start, duration, easing = "linear")`

- `start`: Starting frequency or ratio, interpreted by the same rules as a
  `Bend()` target.
- `duration`: Whole-note fraction resolved by Sequence Tempo.
- `easing`: Curve name or function controlling movement into the Note pitch.

Starts at `start` and moves to the authored Note frequency during the beginning
of the Note. The normal Note frequency is then held. Patch frequencies derived
from the incoming `freq` value inherit the movement proportionally.

<a id="note-bend-out"></a>
### `note.BendOut(target, duration, easing = "linear")`

- `target`: Final frequency or ratio, interpreted by the same rules as a
  `Bend()` target.
- `duration`: Whole-note fraction resolved by Sequence Tempo.
- `easing`: Curve name or function controlling movement out of the Note pitch.

Holds the authored Note frequency, then moves to `target` during the end of the
Note. The target is reached at note-off and remains active through an envelope
release tail.

`BendIn()` and `BendOut()` may be combined. If their durations exceed the Note
duration, Chirper shortens both proportionally so they meet at the authored
frequency. Negative durations become zero. Calling either method replaces
`Bend()` or `StepBend()` while preserving the other scoped bend.

Scoped Note bends follow the original Note timeline through chord rolls and
arpeggio steps; they do not restart for each generated event.

<a id="note-step-bend"></a>
### `note.StepBend(target, ratios = None, easing = "linear")`

- `target`: Target frequency or ratio, interpreted by the same rules as
  `Bend()`.
- `ratios`: Frequency ratios used as bend steps. `None` uses `ES.CHROMATIC` for
  equal-tempered semitone movement.
- `easing`: Curve name or function controlling when transitions between ratio
  steps occur.

Ratios are copied, sorted into ascending order and deduplicated when
`StepBend()` is called. Unison (`1.0`) is added when absent, and ratios below
`1.0` are ignored. Ratios must otherwise be finite positive numbers.

Only ratios that fit between the starting and target frequencies are used. For
a descending bend, their reciprocals are applied. If the target extends beyond
the supplied list, octave-shifted copies of the list are generated. Ratios in a
new octave that are not higher than the last accepted ratio are skipped, which
keeps extended scales and chords moving in one direction. For example, a major
ninth chord beginning on C ascends as:

```text
C, E, G, B, D, E, G, B, D
```

With linear easing, each available ratio occupies an equal portion of the bend,
including the starting and final ratios. Other easing curves redistribute the
time spent on each step. Note vibrato is applied after the stepped bend.
Patch frequencies derived from the incoming `freq` value inherit the movement
proportionally. Independent numeric frequencies do not. `Insert()` does not
pitch-shift samples that have already been rendered. Calling `StepBend()`
replaces any previous `Bend()`, `BendIn()`, and `BendOut()` on the same Note.

<a id="note-trill"></a>
### `note.Trill(target, length = L.L32)`

- `target`: Alternate frequency or ratio. Values below `20.0` are ratios;
  values of `20.0` or more are absolute frequencies.
- `length`: Whole-note fraction determining how long each frequency is held.
  Sequence Tempo resolves it to seconds.

Alternates pitched Patch layers between the Note frequency and `target`,
starting on the Note frequency. One complete cycle lasts twice `length`.
Oscillator phase remains continuous. The Patch transient and envelope are not
retriggered at each transition. Noise layers and independent numeric Patch
frequencies do not trill. `Insert()` does not pitch-shift samples that have
already been rendered.

`Bend()`, `StepBend()`, `BendIn()`, and `BendOut()` move the complete trill
pair. Note vibrato is applied after the active trill frequency is selected.
Alternation stops at note-off, and the frequency active on the final gate
sample is held through the release tail.

<a id="note-chord"></a>
### `note.Chord(pattern, roll = 0.0, dynamics = None, inversion = 0)`

- `pattern`: List of frequency ratios or absolute frequencies forming the
  additional chord voices.
- `roll`: Signed whole-note fraction controlling the delay between adjacent
  pitches. Sequence Tempo resolves it to seconds.
- `dynamics`: Optional nonempty list of nonnegative gain multipliers shaping
  the chord from its lowest pitch to its highest pitch.
- `inversion`: Signed integer controlling how many times the chord voices are
  rotated. `None` is treated as `0`.

Values below `20.0` are ratios relative to the original Note frequency. Values
of `20.0` or more are absolute frequencies. A pattern cannot mix ratios and
absolute frequencies. The list is copied while preserving its order and
duplicate pitches are removed after frequency resolution and inversion.

The original Note is always included as the chord root. Supplied unison ratios
or frequencies matching the root are ignored to avoid doubling it. Every other
frequency becomes a separate Note with the same amplitude, Patch selection,
and performance controls.

A positive inversion moves the lowest pitch to the top and raises it by one
octave for each rotation. A negative inversion moves the highest pitch to the
bottom and lowers it by one octave. Complete rotations retain their octave
movement instead of collapsing to the original register. Nonzero inversion is
applied to the pitch-sorted unique chord after resolving ratios and adding the
root.

One dynamics value applies to every generated Note. Multiple values are
control points distributed across the complete pitch-sorted chord, regardless
of its pattern order or roll direction. Intermediate values use perceptual
gain interpolation. Exact zero control points remain silent; interpolation
next to zero uses `D.D01` as its lower gain floor. The resulting gains multiply
the original Note amplitude and Fade target. Values above `1.0` are allowed,
and no automatic normalization or voice compensation is performed. Dynamics
are resolved before a short roll omits pitches at or beyond the Note endpoint.

With `roll = 0.0`, generated Notes retain the original bar, beat, and duration
and play simultaneously. A positive roll orders pitches from low to high and
keeps the lowest pitch on the beat. A negative roll orders pitches from high to
low and keeps the highest pitch on the beat. No pitch begins before the authored
beat. The magnitude is the delay between adjacent pitches.

All rolled pitches end at the original Note's endpoint, so later pitches have
shorter durations. A pitch whose offset reaches or exceeds that endpoint is not
generated. Note-level fades and scoped bends follow the original Note's
timeline. Each generated Note invokes the Patch recipes independently; the
Patch envelope's monophonic retrigger setting continues to apply. Through a
monophonic Patch, a nonzero roll behaves as a succession of notes; with no roll,
the normal same-time priority rule applies and only the lowest frequency is
retained.

`Chord()` and `Arpeggio()` are mutually exclusive. Whichever function is called
last replaces the other.

<a id="note-arpeggio"></a>
### `note.Arpeggio(pattern, step = L.L16, dynamics = None, rotation = 0)`

- `pattern`: List of frequency ratios or absolute frequencies.
- `step`: Whole-note fraction determining the duration of each generated Note.
  Sequence Tempo resolves it to seconds.
- `dynamics`: Optional nonempty list of nonnegative gain multipliers shaping
  one complete arpeggio cycle.
- `rotation`: Signed integer controlling how many places the pattern is
  rotated. `None` is treated as `0`.

Values below `20.0` are ratios relative to the original Note frequency. Values
of `20.0` or more are absolute frequencies. A pattern cannot mix ratios and
absolute frequencies. The list is copied while preserving its order and
duplicates. The original Note frequency is inserted at the beginning unless
the pattern already starts at unison or that frequency.

Rotation is applied after inserting the original Note frequency. Positive
values move pitches from the beginning to the end. Negative values move pitches
from the end to the beginning. Rotation wraps around the pattern length and
does not change any frequency or octave. Arpeggio order is preserved; the
pattern is not sorted before rotation, and duplicate pitches remain separate.

The complete pattern repeats until the original Note duration ends. A final
partial step is shortened to the remaining duration. Each step is a new Note
routed through the same Patch selection. Patch transient recipes and envelopes
therefore restart for every step. Release tails may overlap later steps.
Compatible monophonic oscillator layers may preserve their oscillator and
modulation phases between steps. Polyphonic steps use independent voices.

One dynamics value applies to every generated Note. Multiple values are
control points distributed across the resolved pattern order, including an
automatically inserted base frequency, and repeat with every pattern cycle.
Intermediate values use perceptual gain interpolation. Exact zero control
points remain silent; interpolation next to zero uses `D.D01` as its lower gain
floor. The resulting gains multiply the original Note amplitude and Fade
target. Values above `1.0` are allowed, and no automatic normalization or voice
compensation is performed.

`Arpeggio()` and `Chord()` are mutually exclusive. Whichever function is called
last replaces the other.

Note performance controls apply to every generated step. `Fade()`, `FadeIn()`,
`FadeOut()`, `Bend()`, `StepBend()`, `BendIn()`, and `BendOut()` follow the
complete original Note instead of restarting at each step. Explicit phase
settings in Patch Tones still reset their oscillator phases.

<a id="note-pan"></a>
### `note.Pan(amount)`

- `amount`: Additional pan from `-1` to `1`.

Applies to the complete rendered Patch after Tone panning.

<a id="note-auto-pan"></a>
### `note.AutoPan(depth = 1.0, rate = 1.0, wave = "Sine", offset = 0.0)`

- `depth`: Pan movement from `0` through `1`.
- `rate`: LFO frequency in Hz.
- `wave`: Pan LFO wave.
- `offset`: Starting position in the LFO cycle, expressed in degrees.

Applies to the complete rendered Patch after Tone panning. `Note.Pan()` sets
the center of the movement. Compatible adjacent notes rendered through a
monophonic Patch continue the AutoPan LFO instead of restarting it.

<a id="note-vibrato"></a>
### `note.Vibrato(depth = None, rate = None, wave = None)`

- `depth`: Pitch deviation in cents.
- `rate`: LFO frequency in Hz.
- `wave`: LFO wave.

Omitted values use synthesizer defaults. The incoming Patch `freq` value carries
the Note vibrato. Tones derived from that value inherit it, and their own Tone
vibrato compounds with it.

<a id="note-tremolo"></a>
### `note.Tremolo(depth = None, rate = None, wave = None)`

- `depth`: Modulation depth from `0` to `1`.
- `rate`: LFO frequency in Hz.
- `wave`: LFO wave.

Applies to the completed Patch output and compounds with Tone tremolo.

<a id="note-fade"></a>
### `note.Fade(target, easing = "linear")`

- `target`: Final linear gain, clamped to `0` through `1`.
- `easing`: Gain curve name or function.

Shapes the completed Patch output, including inserted sounds.

<a id="note-fade-in"></a>
### `note.FadeIn(duration, easing = "linear")`

- `duration`: Whole-note fraction resolved by Sequence Tempo.
- `easing`: Gain curve name or function.

Raises the completed Patch output from silence to normal gain during the
beginning of the Note. It applies to all Patch layers and inserted sounds.

<a id="note-fade-out"></a>
### `note.FadeOut(duration, easing = "linear")`

- `duration`: Whole-note fraction resolved by Sequence Tempo.
- `easing`: Gain curve name or function.

Lowers the completed Patch output from normal gain to silence at note-off.
Envelope release samples after note-off remain silent.

`FadeIn()` and `FadeOut()` may overlap; their gains multiply. Both also multiply
with `Fade()`, Patch envelopes, Tone fades, and other gain modulation. Negative
durations become zero, and durations longer than the Note are limited to its
length. Scoped Note fades follow the original timeline through chord rolls and
arpeggio steps.

---

<a id="contents-setpatch"></a>
### [SetPatch](#setpatch-reference)

- [`SetPatch()`](#setpatch-constructor)<br>

<a id="setpatch-reference"></a>
## SetPatch

<a id="setpatch-constructor"></a>
### `SetPatch(patch, balance = 0.0, polyphonic = None, portamento = None)`

- `patch`: Patch used by following Notes.
- `balance`: Section balance from `-1` to `1`, clamped to that range. `-1`
  selects only the transient, `0` preserves the Patch designer's balance, and
  `1` selects only the body.
- `polyphonic`: Polyphony override, or `None` for the Patch default.
- `portamento`: Portamento override, or `None` for the Patch default.

Negative balance attenuates only the body layer; positive balance attenuates
only the transient layer. Neither side is boosted beyond its
designer-defined gain. Settings belong only to this Sequence selection, and
`SetPatch` never mutates the shared Patch.

Portamento is ignored while polyphony is enabled. For a monophonic Patch with
portamento enabled, an incoming Note glides from the previous Note's pitch only
when their authored durations overlap. The overlap duration controls the glide
time. Notes separated by a gap or touching exactly at their boundaries do not
glide. If the previous Note has a bend, the glide begins at the bend frequency
reached when the incoming Note starts. Pitch moves at a constant perceptual
rate, with equal musical intervals occupying equal portions of the transition.

---

<a id="contents-meter"></a>
### [Meter](#meter-reference)

- [`Meter()`](#meter-constructor)<br>

<a id="meter-reference"></a>
## Meter

<a id="meter-constructor"></a>
### `Meter(beats, unit)`

- `beats`: Positive integer beats per bar.
- `unit`: Positive integer note-value denominator.

`Meter(4, 4)` is four quarter-note beats per bar. `Meter(6, 8)` is six
eighth-note beats per bar. A Sequence may contain one Meter command. Its
position in the event list does not matter because it applies to the complete
Sequence.

---

<a id="contents-tone"></a>
### [Tone](#tone-reference)

- [`Tone()`](#tone-constructor)<br>
- [`Wave()`](#tone-wave)<br>
- [`Vibrato()`](#tone-vibrato)<br>
- [`Tremolo()`](#tone-tremolo)<br>
- [`Mod()`](#tone-mod)<br>
- [`Pan()`](#tone-pan)<br>
- [`AutoPan()`](#tone-auto-pan)<br>
- [`Phase()`](#tone-phase)<br>
- [`Bend()`](#tone-bend)<br>
- [`BendIn()`](#tone-bend-in)<br>
- [`BendOut()`](#tone-bend-out)<br>
- [`Arpeggio()`](#tone-arpeggio)<br>
- [`Fade()`](#tone-fade)<br>
- [`FadeIn()`](#tone-fade-in)<br>
- [`FadeOut()`](#tone-fade-out)<br>
- [`Unison()`](#tone-unison)<br>
- [`Rest()`](#tone-rest)<br>

<a id="tone-reference"></a>
## Tone

`Tone` describes one oscillator event. Tone methods mutate the Tone and return
it, allowing method chaining.

<a id="tone-constructor"></a>
### `Tone(freq = N.C4, duration = 0.25, amplitude = 1.0)`

- `freq`: Frequency in Hz. `None` produces silence.
- `duration`: Seconds, or a whole-note fraction while Tempo mode is active.
- `amplitude`: Non-negative linear sample gain.

Pitched oscillator frequencies below `20.0` Hz are raised to `20.0` while
rendering. They are not upper-clamped. Noise frequencies may go below `20.0`
because they control filter cutoffs or update rates instead of oscillator
pitch.

<a id="tone-wave"></a>
### `tone.Wave(wave)`

- `wave`: Built-in wave name, custom function, `WaveTable`, or `Sound` wave table.

Sets the wave used by the Tone. The default oscillator wave is `"Sine"`.

<a id="tone-vibrato"></a>
### `tone.Vibrato(depth = None, rate = None, wave = None)`

- `depth`: Pitch deviation in cents.
- `rate`: LFO frequency in Hz.
- `wave`: LFO wave.

<a id="tone-tremolo"></a>
### `tone.Tremolo(depth = None, rate = None, wave = None)`

- `depth`: Gain-modulation depth from `0` to `1`.
- `rate`: LFO frequency in Hz.
- `wave`: LFO wave.

<a id="tone-mod"></a>
### `tone.Mod(freq, depth = 1.0, wave = "Sine")`

- `freq`: Phase-modulator frequency in Hz.
- `depth`: Phase offset depth in radians.
- `wave`: Modulator wave.

Applies phase modulation to the oscillator. This produces the related spectra
commonly associated with basic FM synthesis. `JustRatio` and `EqualRatio`
contain frequency multipliers for musical intervals.

<a id="tone-pan"></a>
### `tone.Pan(amount)`

- `amount`: Position from `-1` left to `1` right.

Applies to this `Tone` before `Note` panning.

<a id="tone-auto-pan"></a>
### `tone.AutoPan(depth = 1.0, rate = 1.0, wave = "Sine", offset = 0.0)`

- `depth`: Pan movement from `0` through `1`.
- `rate`: LFO frequency in Hz.
- `wave`: Pan LFO wave.
- `offset`: Starting position in the LFO cycle, expressed in degrees.

Applies automatic equal-power panning to this oscillator layer. `Tone.Pan()`
sets the center of the movement. Compatible Tones in a sequential Sound recipe
continue the AutoPan LFO. Tone and Note panning compound hierarchically.

<a id="tone-phase"></a>
### `tone.Phase(degrees)`

- `degrees`: Oscillator starting position, wrapped to one cycle.

With a custom `Sound` wave table, phase selects the starting position within
the table. `90` degrees starts one quarter of the way through it.

<a id="tone-bend"></a>
### `tone.Bend(target, easing = "linear")`

- `target`: Final frequency or ratio. For pitched waves, values below `20.0`
  are ratios and values of `20.0` or more are absolute frequencies. Noise waves
  always interpret the value as an absolute cutoff frequency or clock rate.
- `easing`: Bend curve name or function.

Moves across the complete Tone duration. Calling `Bend()` replaces any previous
`BendIn()` or `BendOut()` on the same Tone.

<a id="tone-bend-in"></a>
### `tone.BendIn(start, duration, easing = "linear")`

- `start`: Starting frequency or ratio, interpreted by the same rules as a
  `Bend()` target.
- `duration`: Seconds, or a whole-note fraction while Tempo mode is active.
- `easing`: Curve name or function controlling movement into the Tone pitch.

Starts at `start` and moves to the authored Tone frequency during the beginning
of the Tone. The authored frequency is then held.

<a id="tone-bend-out"></a>
### `tone.BendOut(target, duration, easing = "linear")`

- `target`: Final frequency or ratio, interpreted by the same rules as a
  `Bend()` target.
- `duration`: Seconds, or a whole-note fraction while Tempo mode is active.
- `easing`: Curve name or function controlling movement out of the Tone pitch.

Holds the authored Tone frequency, then moves to `target` during the end of the
Tone. If a Patch envelope extends the oscillator layer beyond its authored
duration, the target remains active through that extension.

`BendIn()` and `BendOut()` may be combined. If their durations exceed the Tone
duration, Chirper shortens both proportionally so they meet at the authored
frequency. Negative durations become zero. Calling either method replaces
`Bend()` while preserving the other scoped bend.

<a id="tone-arpeggio"></a>
### `tone.Arpeggio(pattern, step = 0.125, dynamics = None, rotation = 0)`

- `pattern`: List of frequency ratios or absolute frequencies.
- `step`: Duration of each generated Tone in seconds, including while a Tempo
  control is active.
- `dynamics`: Optional nonempty list of nonnegative gain multipliers shaping
  one complete arpeggio cycle.
- `rotation`: Signed integer controlling forward or backward pattern rotation.
  `None` is treated as `0`.

Pattern validation, frequency interpretation, base-frequency insertion, order,
and repetition follow `Note.Arpeggio()`. The Tone is compiled into consecutive
oscillator events until its original duration is exhausted, and the final event
is shortened when necessary.

Inside a Patch, a ratio pattern derived from the incoming `freq` value retains
Note-level pitch performance. Absolute-frequency pattern values are explicit
and do not inherit it.

Dynamics interpolation and repetition also follow `Note.Arpeggio()`. The
resulting gains multiply the Tone amplitude and Fade target for each generated
oscillator event.

Compatible oscillator and modulation state continues between generated events.
Tone scoped bends and fades restart for each event, and an explicit `Phase()`
setting resets each event to that phase. When used inside a Patch recipe, Tone
arpeggiation remains inside one Patch Note and does not retrigger the Patch
transient or envelope.

<a id="tone-fade"></a>
### `tone.Fade(target, easing = "linear")`

- `target`: Final linear amplitude, clamped from `0` to `1` when rendered.
- `easing`: Amplitude curve name or function.

`Tone` `Fade` shapes only this oscillator layer.

<a id="tone-fade-in"></a>
### `tone.FadeIn(duration, easing = "linear")`

- `duration`: Seconds, or a whole-note fraction while Tempo mode is active.
- `easing`: Gain curve name or function.

Raises this oscillator layer from silence to normal gain during the beginning
of the Tone.

<a id="tone-fade-out"></a>
### `tone.FadeOut(duration, easing = "linear")`

- `duration`: Seconds, or a whole-note fraction while Tempo mode is active.
- `easing`: Gain curve name or function.

Lowers this oscillator layer from normal gain to silence during the end of the
Tone. Samples added by a Patch envelope after the authored Tone duration remain
silent.

`FadeIn()` and `FadeOut()` may overlap; their gains multiply. Both also multiply
with `Fade()` and other gain modulation. Negative durations become zero, and
durations longer than the Tone are limited to its length.

<a id="tone-unison"></a>
### `tone.Unison(voices = 3, detune = 10.0, spread = 1.0)`

- `voices`: Number of synthesized voices.
- `detune`: Maximum detuning in cents.
- `spread`: Stereo voice spread from `0` to `1`.

Each voice is synthesized independently. Voice gain is divided by the voice
count before summing. Noise waves do not support Unison.

<a id="tone-rest"></a>
### `Tone.Rest(duration)`

- `duration`: Rest duration under the current seconds or Tempo mode.

Returns a silent Tone.

---

<a id="contents-envelope"></a>
### [Envelope](#envelope-reference)

- [`Envelope()`](#envelope-constructor)<br>

<a id="envelope-reference"></a>
## Envelope

`Envelope` defines body-layer amplitude over time for a `Patch`.

<a id="envelope-constructor"></a>
### `Envelope(attack, decay, sustain, release, retrigger = True, attackCurve = -5.0, decayCurve = 5.0, releaseCurve = 5.0)`

- `attack`: Seconds spent rising from zero to `1.0`.
- `decay`: Seconds spent moving from `1.0` to the sustain gain.
- `sustain`: Linear gain held until note-off. `None` is treated as zero.
- `release`: Seconds spent moving from the current gain to zero after note-off.
- `retrigger`: Whether contiguous monophonic Notes start independent envelopes.
- `attackCurve`: Exponential coefficient for the attack transition.
- `decayCurve`: Exponential coefficient for the decay transition.
- `releaseCurve`: Exponential coefficient for the release transition.

Envelope transitions use the normalized exponential curve
`(1 - exp(-curve * time)) / (1 - exp(-curve))`, where time runs from `0.0`
to `1.0` within each stage. Negative coefficients accelerate toward the end,
positive coefficients accelerate near the beginning, and `0.0` produces a
linear transition.

Negative stage durations and sustain gains are clamped to zero. Sustain gain is
not upper-clamped, so values above `1.0` may intentionally boost the signal.
Zero-length stages are instantaneous.

Note duration is the gate time. Release begins at note-off and extends the
rendered sustain beyond that duration. If note-off occurs during attack or
decay, release begins from the gain reached at that point. A sustain of `0.0`
allows decay to reach silence while the Note remains held; note-off still
starts the release stage immediately from the current gain.

With `retrigger = True`, every Note starts a new envelope and an earlier release
tail may overlap it. With `retrigger = False`, compatible contiguous Notes on a
monophonic Patch preserve envelope progress. A gap or an incompatible body
layer starts a new envelope. One-shot behavior can be created by making the
Note duration match the attack and decay stages.

---

<a id="contents-patch"></a>
### [Patch](#patch-reference)

- [`Patch()`](#patch-constructor)<br>
- [`RenderSamples()`](#patch-render-samples)<br>
- [`Render()`](#patch-render)<br>

<a id="patch-reference"></a>
## Patch

`Patch` defines two simultaneous sections named `transient` and `body`. Both
sections begin at note-on and use the same recipe rules.

<a id="patch-constructor"></a>
### `Patch(transient = None, body = None, transientGain = 1.0, bodyGain = 1.0, envelope = None, polyphonic = True, portamento = False)`

- `transient`: Function receiving `(freq, dur, amp)`, or `None`.
- `body`: Function receiving `(freq, dur, amp)`, or `None`.
- `transientGain`: Designer-defined transient-section multiplier.
- `bodyGain`: Designer-defined body-section multiplier.
- `envelope`: An `Envelope` applied to the rendered body layer, or `None`.
- `polyphonic`: When `True`, Notes may overlap. When `False`, each new `Note`
  ends the inherited duration of the previous `Note` using this `Patch`.
- `portamento`: Default overlap-driven portamento setting for this Patch.

Each recipe must return a list containing `Tone`, `Insert`, and supported
control objects. Every Tone and Insert in that list starts at the beginning of
the section. They are mixed as simultaneous layers.

The incoming `freq` value carries Note-level bend, vibrato, trill, and
portamento information. Pass it into `Tone`, or use ordinary arithmetic such
as `freq * 2.0`, to preserve those performance controls. A frequency written as
an independent number is explicit and does not inherit Note-level pitch
performance.

`Insert()` adds already rendered samples and does not resynthesize or
pitch-shift them. A recipe can first build a new Sound from the incoming `freq`
value, apply Sound effects, and then return `Insert(processedSound)`. In that
case, the Tones used to build the Sound inherit Note-level pitch performance
before the Sound is inserted. Chain Sound methods such as `Gain()` or
`HighPass()` before inserting when processing is required.

The envelope does not affect the transient layer. Body Tones that remain
active at note-off are rendered through the release stage. Tones ending before
note-off retain their explicit duration. Inserted Sounds are shaped by the
envelope but are not extended; they must contain their own release material.

Subclasses may define `Transient(self, freq, dur, amp)` and
`Body(self, freq, dur, amp)` methods instead of passing standalone recipe
functions to the constructor.

Monophonic resolution happens before recipes run, so `dur` receives the
shortened duration. If several Notes begin together, Chirper keeps the lowest
frequency. If those frequencies are equal, it keeps the first declared Note.

Only a duration inherited from `dur` is shortened. A Tone with an independent
duration and an inserted Sound continue for their full lengths, so they may
overlap later Notes. A body envelope may end a body layer earlier by reaching
zero.

Compatible adjacent Tone layers preserve oscillator, vibrato, tremolo, and
AutoPan phase. A gap or an incompatible layer starts a new rendered phrase and
restores the normal boundary fades. A Note fade remains compatible only when
its ending gain matches the next Note's starting gain.

When monophonic portamento is enabled, Chirper measures the authored overlap
before shortening the previous Note. The incoming Note starts at the previous
pitch and reaches its own pitch over the overlap. Patch frequencies derived
from the incoming `freq` value inherit this movement proportionally. Noise
layers and independent numeric frequencies do not. Insert does not pitch-shift
already rendered samples.

<a id="patch-render-samples"></a>
### `patch.RenderSamples(freq, duration, amplitude = 1.0, channels = 2, transientGain = None, bodyGain = None)`

Renders the `Patch` directly and returns interleaved floating-point samples.
Durations are seconds. Omitted gains use the `Patch` defaults; explicit gains
override them for this render.

<a id="patch-render"></a>
### `patch.Render(freq, duration, amplitude = 1.0, channels = 2, transientGain = None, bodyGain = None)`

Renders the `Patch` directly and returns a `Sound`.

---

<a id="contents-patches"></a>
### [Patches](#patches-reference)

- [Built-in patches](#patches-built-in)

<a id="patches-reference"></a>
## Patches

<a id="patches-built-in"></a>
### Built-in patches

`Patches` contains ready-to-use Patch objects:

```text
Sine, Triangle, Square, Saw
SuperSine, SuperTriangle, SuperSquare, SuperSaw
CowBell
```

Use them with `SetPatch(Patches.SuperSaw)` or render them directly.

---

<a id="contents-controls"></a>
### [Recipe Controls](#controls-reference)

- [`Wave()`](#control-wave)<br>
- [`Pitch()`](#control-pitch)<br>
- [`Tempo()`](#control-tempo)<br>
- [`Seconds()`](#control-seconds)<br>
- [`VibratoDepth()`](#control-vibrato-depth)<br>
- [`VibratoRate()`](#control-vibrato-rate)<br>
- [`VibratoWave()`](#control-vibrato-wave)<br>
- [`TremoloDepth()`](#control-tremolo-depth)<br>
- [`TremoloRate()`](#control-tremolo-rate)<br>
- [`TremoloWave()`](#control-tremolo-wave)<br>
- [`Insert()`](#control-insert)<br>

<a id="controls-reference"></a>
## Recipe Controls

Recipe controls set defaults for Tones that follow them in a recipe list. They
work in both layered and sequential Sound recipes. Layered timing does not
change their declaration order: a control still affects only later Tones in
the list.

Patch recipes support `Pitch`, vibrato controls, tremolo controls, and
`Insert`. Patch durations are always seconds, so `Tempo` and `Seconds` do not
alter Patch timing. Patch recipes reject the standalone `Wave` control. A
Patch Tone uses `"Sine"` when `.Wave()` is omitted. Call `Tone.Wave()` to
select a different wave for that Tone.

<a id="control-wave"></a>
### `Wave(wave)`

Sets the default wave for following Tones in a Sound recipe or a direct
`ChirpSynth` recipe. Patch recipes reject this command. Wave selection in a
Patch is local to each Tone: call `Tone.Wave()` to override the default
`"Sine"` wave.

<a id="control-pitch"></a>
### `Pitch(amount)`

Sets the frequency multiplier for following Tones. Values below `0.1` use
`0.1`. The multiplier applies to all oscillator frequencies on those Tones,
including Bend targets, arpeggio frequencies, performance pitch targets, and
the phase-modulation frequency supplied to `Tone.Mod()`.

<a id="control-tempo"></a>
### `Tempo(bpm)`

In a Sound or direct `ChirpSynth` recipe, `Tempo` interprets following Tone
durations as whole-note fractions at the requested quarter-note beats per
minute. It continues to apply until another `Tempo` command changes it or
`Seconds()` disables it.

In a Sequence, one `Tempo` command may appear anywhere in the event list and
applies to the complete Sequence. Patch recipes always receive seconds, so
`Tempo` does not alter Patch Tone durations.

<a id="control-seconds"></a>
### `Seconds()`

Returns following Tone durations to seconds in a Sound or direct `ChirpSynth`
recipe. Patch Tone durations are already interpreted as seconds.

<a id="control-vibrato-depth"></a>
### `VibratoDepth(depth)`

Sets default `Vibrato` depth in cents.

<a id="control-vibrato-rate"></a>
### `VibratoRate(rate)`

Sets default `Vibrato` rate in Hz.

<a id="control-vibrato-wave"></a>
### `VibratoWave(wave)`

Sets the default `Vibrato` wave.

<a id="control-tremolo-depth"></a>
### `TremoloDepth(depth)`

Sets default `Tremolo` depth from `0` to `1`.

<a id="control-tremolo-rate"></a>
### `TremoloRate(rate)`

Sets default `Tremolo` rate in Hz.

<a id="control-tremolo-wave"></a>
### `TremoloWave(wave)`

Sets the default `Tremolo` wave.

<a id="control-insert"></a>
### `Insert(sound)`

Adds the rendered samples of `sound` to a recipe. Chirper converts mono and
stereo data to the recipe's output channel count when necessary. It does not
resynthesize or pitch-shift the inserted samples.

In `Sound(..., layered = True)`, the Insert starts at the beginning alongside
the other layers. In `Sound(..., layered = False)`, it starts after every
preceding Tone or Insert has finished. In a Patch recipe, it starts at note-on
alongside the other layers in its transient or body section.

---

<a id="contents-waves"></a>
### [Waves](#waves-reference)

- [Pitched waves](#waves-pitched)<br>
- [Noise waves](#waves-noise)<br>
- [Custom waves](#waves-custom)<br>

<a id="waves-reference"></a>
## Waves

Wave names are case-insensitive and ignore underscores and hyphens.

<a id="waves-pitched"></a>
### Pitched waves

|Wave|Description|
|---:|:---|
|`"Sine"`|A sine wave.|
|`"Triangle"`|A triangle wave|
|`"Saw"`|A sawtooth wave|
|`"Pulse50"`|50% duty cycle pulse wave (square wave)|
|`"Pulse25"`|25% duty cycle pulse wave|
|`"Pulse12"`|12.5% duty cycle pulse wave|
|`"TriangleAA"`|An anti-aliased triangle wave|
|`"SawAA"`|An anti-aliased sawtooth wave|
|`"Pulse50AA"`|An anti-aliased 50% duty cycle pulse wave (square wave)|
|`"Pulse25AA"`|An anti-aliased 25% duty cycle pulse wave|
|`"Pulse12AA"`|An anti-aliased 12.5% duty cycle pulse wave|

The `AA` waves reduce aliasing while keeping the corresponding non-AA waves
available as separate waveform choices.

<a id="waves-noise"></a>
### Noise waves

|Wave|Description|
|---:|:---|
|`"Noise"`|White noise|
|`"NoiseLP"`|Low-passed white noise (note/tone frequency controls the cutoff)|
|`"NoiseHP"`|High-passed white noise (note/tone frequency controls the cutoff)|
|`"NoiseBP"`|Band-passed white noise (note/tone frequency controls the midpoint)|
|`"NoiseStep"`|Sample and hold noise (note/tone frequency controls the clock rate)|
|`"NoiseQuanta"`|Binary noise that randomly updates between `-1.0` and `+1.0` (note/tone frequency controls the update rate)|

For filtered noise, the `Tone` frequency supplies the filter cutoff or center
frequency. `NoiseLP` and `NoiseHP` use one-pole filters with an approximately
6 dB-per-octave slope. `NoiseBP` combines one-pole high-pass and low-pass
filtering around its center frequency.

`NoiseStep` uses frequency as its regular random-value update rate.
`NoiseQuanta` uses frequency as the number of random update opportunities per
second. Low frequencies produce sparse binary transitions. Frequencies at or
above the sample rate choose a new binary state every sample. The noise waves
do not apply makeup gain.

<a id="waves-custom"></a>
### Custom waves

A wave argument may be:

- A built-in name.
- A function receiving `(time, frequency)` and returning one sample.
- A `WaveTable`.
- A `Sound`, whose complete mono sample data becomes a cyclic table.

Stereo Sounds are collapsed to mono before becoming wave tables. A Sound used
as a wave must contain at least one sample frame. Its complete duration forms
one oscillator cycle.

---

<a id="contents-easing"></a>
### [Easing](#easing-reference)

- [Easing names](#easing-names)<br>
- [Custom easing functions](#easing-custom)<br>

<a id="easing-reference"></a>
## Easing

<a id="easing-names"></a>
### Easing names

Easing names are case-insensitive and ignore underscores and hyphens:

|Concave|Convex|S-Shaped|
|:---:|:---:|:---:|
|![linear](img/easing/linear.png)<br>`"linear"`|![linear](img/easing/linear.png)<br>`"linear"`|![linear](img/easing/linear.png)<br>`"linear"`|
|![insine](img/easing/insine.png)<br>`"inSine"`|![outsine](img/easing/outsine.png)<br>`"outSine"`|![inoutsine](img/easing/inoutsine.png)<br>`"inOutSine"`|
|![inquad](img/easing/inquad.png)<br>`"inQuad"`|![outquad](img/easing/outquad.png)<br>`"outQuad"`|![inoutquad](img/easing/inoutquad.png)<br>`"inOutQuad"`|
|![incubic](img/easing/incubic.png)<br>`"inCubic"`|![outcubic](img/easing/outcubic.png)<br>`"outCubic"`|![inoutcubic](img/easing/inoutcubic.png)<br>`"inOutCubic"`|
|![inquart](img/easing/inquart.png)<br>`"inQuart"`|![outquart](img/easing/outquart.png)<br>`"outQuart"`|![inoutquart](img/easing/inoutquart.png)<br>`"inOutQuart"`|
|![inquint](img/easing/inquint.png)<br>`"inQuint"`|![outquint](img/easing/outquint.png)<br>`"outQuint"`|![inoutquint](img/easing/inoutquint.png)<br>`"inOutQuint"`|
|![incircle](img/easing/incircle.png)<br>`"inCircle"`|![outcircle](img/easing/outcircle.png)<br>`"outCircle"`|![inoutcircle](img/easing/inoutcircle.png)<br>`"inOutCircle"`|
|![inexpo](img/easing/inexpo.png)<br>`"inExpo"`|![outexpo](img/easing/outexpo.png)<br>`"outExpo"`|![inoutexpo](img/easing/inoutexpo.png)<br>`"inOutExpo"`|
|![inelastic](img/easing/inelastic.png)<br>`"inElastic"`|![outelastic](img/easing/outelastic.png)<br>`"outElastic"`|![inoutelastic](img/easing/inoutelastic.png)<br>`"inOutElastic"`|
|![inback](img/easing/inback.png)<br>`"inBack"`|![outback](img/easing/outback.png)<br>`"outBack"`|![inoutback](img/easing/inoutback.png)<br>`"inOutBack"`|
|![inbounce](img/easing/inbounce.png)<br>`"inBounce"`|![outbounce](img/easing/outbounce.png)<br>`"outBounce"`|![inoutbounce](img/easing/inoutbounce.png)<br>`"inOutBounce"`|
|![inlog](img/easing/inlog.png)<br>`"inLog"`|![outlog](img/easing/outlog.png)<br>`"outLog"`|![inoutlog](img/easing/inoutlog.png)<br>`"inOutLog"`|

|3rd Order|5th Order|7th Order|
|:---:|:---:|:---:|
|![smoothstep3](img/easing/smoothstep3.png)<br>`"smoothStep3"`|![smoothstep5](img/easing/smoothstep5.png)<br>`"smoothStep5"`|![smoothstep7](img/easing/smoothstep7.png)<br>`"smoothStep7"`|

`lin`, `logarithmic`, and `cos` are also accepted.
`equalPower` is an alias for `outSine`, and `cosine` is an alias for
`inOutSine`.

<a id="easing-custom"></a>
### Custom easing functions

Any argument that accepts an easing name also accepts a function taking one
progress value and returning one interpolated value:

```python
def SmoothStep(t):
    return t * t * (3.0 - (2.0 * t))

sound = sound.FadeIn(0.25, SmoothStep)
tone = Tone(440.0, 0.5).Bend(880.0, SmoothStep)
note = Note(0, 0, N.C4, L.L4).Fade(D.D08, SmoothStep)
```

Chirper clamps the input `t` to `[0, 1]`. The returned value must be a finite
number, but it is not clamped; custom curves may deliberately overshoot below
`0` or above `1`. Custom easing functions use the Python path for the affected
operation because custom Python functions cannot be passed into Chirper's
Numba kernels. Other operations remain accelerated.

---

<a id="contents-constants"></a>
### [Constants And Presets](#constants-reference)

- [`NoteFrequency() / N`](#constants-notes)<br>
- [`NoteLength / L`](#constants-lengths)<br>
- [`Vibrato / V`](#constants-vibrato)<br>
- [`Tremolo / T`](#constants-tremolo)<br>
- [`Dynamics / D`](#constants-dynamics)<br>
- [`QFactor / Q`](#constants-q)<br>
- [`JustRatio / JR`](#constants-just-ratio)<br>
- [`EqualRatio / ER`](#constants-equal-ratio)<br>
- [`EqualScale / ES and JustScale / JS`](#constants-scales)<br>

<a id="constants-reference"></a>
## Constants And Presets

<a id="constants-notes"></a>
### `NoteFrequency(concertA = 440.0, ratio = EqualRatio)` / N

- `concertA`: Frequency assigned to A4.
- `ratio`: Ratio namespace used to calculate intervals from A4.

Constructs a read-only table of note frequencies from `C1` through `B9`. `N` is
the default table, constructed with an A4 frequency of `440.0` and
`EqualRatio`. Sharps use `S` in the name, such as `N.FS4`; equivalent flats are
also available, such as `N.GB4`.

```python
concertPitch = N
baroquePitch = NoteFrequency(415.0, EqualRatio)
justPitch = NoteFrequency(440.0, JustRatio)
```

Constructed tables cannot be modified. `N.MIN` is `20.0` and `N.MAX` is
`20000.0`. These are descriptive values for the commonly audible frequency
range, not enforced synthesis limits. They are ordinary numeric values and
support the same arithmetic as the named note frequencies.

<a id="constants-lengths"></a>
### NoteLength / L

Note lengths are expressed as fractions of a whole note:

```python
# Regular notes
L.L8X     8       # octuple note
L.L4X     4       # quadruple note
L.L2X     2       # double note
L.L1      1       # whole note
L.L2      1 / 2   # half note
L.L4      1 / 4   # quarter note
L.L8      1 / 8   # 8th note
L.L16     1 / 16  # 16th note
L.L32     1 / 32  # 32nd note
L.L64     1 / 64  # 64th note

# Dotted notes
L.L1D     3 / 2
L.L2D     3 / 4
L.L4D     3 / 8
L.L8D     3 / 16
L.L16D    3 / 32
L.L32D    3 / 64
L.L64D    3 / 128

# Triplets
L.L1T     2 / (3 *  1)
L.L2T     2 / (3 *  2)
L.L4T     2 / (3 *  4)
L.L8T     2 / (3 *  8)
L.L16T    2 / (3 * 16)
L.L32T    2 / (3 * 32)
L.L64T    2 / (3 * 64)
```

Descriptive and traditional notation names are aliases for these values, such
as `WHOLE`, `QUARTER`, `CROTCHET`, and `QUAVER`.

<a id="constants-vibrato"></a>
### Vibrato / V

Pitch-depth presets in cents:

```python
V.NONE      0.0
V.XLIGHT   12.5
V.LIGHT    25.0
V.MEDIUM   50.0
V.HEAVY    75.0
V.XHEAVY  100.0
```

<a id="constants-tremolo"></a>
### Tremolo / T

Gain-modulation depth presets:

```python
T.NONE    0.000
T.XLIGHT  0.125
T.LIGHT   0.250
T.MEDIUM  0.500
T.HEAVY   0.750
T.XHEAVY  1.000
```

<a id="constants-dynamics"></a>
### Dynamics / D

Perceptually spaced linear gains from `D.D00` through `D.D15`. Each step is about 3 dB.

```python
D.D00   0.0000000
D.D01   0.0078125
D.D02   0.0110485
D.D03   0.0156250
D.D04   0.0220971
D.D05   0.0312500
D.D06   0.0441942
D.D07   0.0625000
D.D08   0.0883883
D.D09   0.1250000
D.D10   0.1767767
D.D11   0.2500000
D.D12   0.3535534
D.D13   0.5000000
D.D14   0.7071068
D.D15   1.0000000
```

<a id="constants-q"></a>

### QFactor / Q

Resonance/slope control for filters:

```python
Q.BROAD   0.250
Q.WIDE    0.500
Q.MID     0.707
Q.NARROW  1.000
Q.TIGHT   2.000
```

<a id="constants-just-ratio"></a>

### JustRatio / JR

Frequency multipliers for just-intonation musical intervals:

```python
JR.UNISON   = JR.UNI    = 1.0
JR.MIN2                 = 16.0 / 15.0
JR.MAJ2                 =  9.0 /  8.0
JR.MIN3                 =  6.0 /  5.0
JR.MAJ3                 =  5.0 /  4.0
JR.FOURTH               =  4.0 /  3.0
JR.AUG4                 = 45.0 / 32.0
JR.DIM5                 = 64.0 / 45.0
JR.FIFTH                =  3.0 /  2.0
JR.MIN6                 =  8.0 /  5.0
JR.MAJ6                 =  5.0 /  3.0
JR.MIN7                 =  9.0 /  5.0
JR.MAJ7                 = 15.0 /  8.0
JR.OCTAVE   = JR.OCT    = 2.0
```

<a id="constants-equal-ratio"></a>

### EqualRatio / ER

Frequency multipliers for twelve-tone equal temperament. The interval names
match `JustRatio`, but each semitone is calculated as `2 ** (semitones / 12)`.
`ER.AUG4` and `ER.DIM5` are the same six-semitone ratio.

```python
ER.UNISON   = ER.UNI    = 2.0 ** (0.0 / 12.0)
ER.MIN2                 = 2.0 ** (1.0 / 12.0)
ER.MAJ2                 = 2.0 ** (2.0 / 12.0)
ER.MIN3                 = 2.0 ** (3.0 / 12.0)
ER.MAJ3                 = 2.0 ** (4.0 / 12.0)
ER.FOURTH               = 2.0 ** (5.0 / 12.0)
ER.AUG4     = ER.DIM5   = 2.0 ** (6.0 / 12.0)
ER.FIFTH                = 2.0 ** (7.0 / 12.0)
ER.MIN6                 = 2.0 ** (8.0 / 12.0)
ER.MAJ6                 = 2.0 ** (9.0 / 12.0)
ER.MIN7                 = 2.0 ** (10.0 / 12.0)
ER.MAJ7                 = 2.0 ** (11.0 / 12.0)
ER.OCTAVE   = ER.OCT    = 2.0 ** (12.0 / 12.0)
```

<a id="constants-scales"></a>

### EqualScale / ES and JustScale / JS

Lists of ascending frequency ratios in just intonation and equal temperament.<br>
Equal temperament is `ES` and just intonation is `JS`.

Each built-in scale starts at unison.<br>
Chord lists use the same interval constants, so enharmonic chord tones keep
their musical spelling where possible:

```python
# Scales
CHROMATIC
WHOLE_TONE
MAJOR
MINOR
HALF_WHOLE
WHOLE_HALF
DIMINISHED   # Alias for WHOLE_HALF
DOM_DIM      # Alias for HALF_WHOLE
HARM_MAJ     # Harmonic major
MELO_MIN     # Melodic minor
HARM_MIN     # Harmonic minor
PENTA_MIN    # Pentatonic minor
PENTA        # Alias for PENTA_MIN
PENTA_MAJ    # Pentatonic major
PENTA_NEUT   # Neutral pentatonic
PENTA_BLUES  # Pentatonic minor with added diminished fifth
BLUES        # Alias for PENTA_BLUES

# Modes
IONIAN       # Alias for MAJOR
DORIAN
PHRYGIAN
LYDIAN
MIXOLYDIAN
AEOLIAN      # Alias for MINOR
LOCRIAN
LYDIAN_DOM   # Lydian dominant

# Chords
MAJ
MIN
SUS2
SUS4
DIM
AUG
FOURTH
FIFTH
POWER        # 5th chord with octave
MIN6
MAJ6
SIXTH        # Alias for MAJ6
MAJ7
MIN7
DOM7
SEVENTH      # Alias for DOM7
DIM7
HALFDIM7
MIN7B5       # Alias for HALFDIM7
MINMAJ7
MAJMIN7      # Alias for DOM7
AUG7
AUGMAJ7
ADD9
MAJADD9      # Alias for ADD9
MINADD9
MINMAJ9
MAJ9
MIN9
DOM9
MAJMIN9      # Alias for DOM9
SUS7
SUS9
```

---

<a id="contents-chirper"></a>
### [Chirper](#chirper-reference)

- [`Chirper()`](#chirper-constructor)<br>
- [`Play()`](#chirper-play)<br>
- [`PlayQueued()`](#chirper-play-queued)<br>
- [`PlaySolo()`](#chirper-play-solo)<br>
- [`SetVolume()`](#chirper-set-volume)<br>
- [`GetStats()`](#chirper-get-stats)<br>
- [`StopAll()`](#chirper-stop-all)<br>
- [`Close()`](#chirper-close)<br>

<a id="chirper-reference"></a>
## Chirper

`Chirper` composes a synthesizer, DSP processor, and player. Completed Sounds
are the normal playback input.

<a id="chirper-constructor"></a>
### `Chirper(volume = 1.0, channels = 2, voices = 16, enabled = True)`

- `volume`: Initial perceptual master volume from `0` to `1`.
- `channels`: Playback channel count.
- `voices`: Maximum simultaneous mixer voices.
- `enabled`: When `False`, no output device is opened and playback methods
  return `None`.

The channel count is fixed when `Chirper` is constructed because the
synthesizer, DSP processor, mixer, and output stream must share one format.

Advanced components are available as `chirper.synth`, `chirper.dsp`, and
`chirper.player`. These component references and the facade's audio-format
values cannot be replaced after construction.

`Chirper` can be used as a context manager. Leaving a `with Chirper(...)` block
calls `Close()` automatically.

<a id="chirper-play"></a>
### `chirper.Play(sound, volume = 1.0, blocking = False, voice = None)`

- `sound`: `Sound`, `ChirpFileData`, `PcmFileData`, or signed 16-bit PCM bytes.
- `volume`: Per-play perceptual volume.
- `blocking`: Wait for mixer completion and buffered latency.
- `voice`: Optional voice index. An explicit voice replaces its current sound.

Returns a `ChirpVoiceHandle`, or `None` when playback is disabled.

<a id="chirper-play-queued"></a>
### `chirper.PlayQueued(sound, volume = 1.0, voice = None)`

Queues the Sound sample-contiguously on one voice and returns a
`ChirpVoiceHandle`. When `voice` is omitted, Chirper uses a free voice when one
is available and otherwise uses voice zero. Queued playback is non-blocking.

<a id="chirper-play-solo"></a>
### `chirper.PlaySolo(sound, volume = 1.0, blocking = False)`

Stops active and queued sounds, flushes buffered output, and starts the new
Sound on voice zero. Returns a `ChirpVoiceHandle`, or `None` when playback is
disabled. With `blocking = True`, the call waits for mixer completion and the
estimated output-buffer latency.

<a id="chirper-set-volume"></a>
### `chirper.SetVolume(volume)`

Sets perceptual master playback volume from `0` to `1`.

<a id="chirper-get-stats"></a>
### `chirper.GetStats()`

Returns the player's real-time output statistics and active voice count. The
returned dictionary contains `blockFrames`, `bufferCount`, `blocksRendered`,
`batchedRefills`, `maximumRenderSeconds`, `blockDurationSeconds`, and
`activeVoices`, and `queuedVoices`. When playback is disabled, only
`blockFrames`, `activeVoices`, and `queuedVoices` are present.

<a id="chirper-stop-all"></a>
### `chirper.StopAll()`

Stops every active and queued voice and flushes buffered output.

<a id="chirper-close"></a>
### `chirper.Close()`

Releases the output stream. Calling it more than once is safe.

---

<a id="contents-voice-handle"></a>
### [ChirpVoiceHandle](#voice-handle-reference)

- [`Stop()`](#voice-handle-stop)<br>
- [`Wait()`](#voice-handle-wait)<br>
- [`IsPlaying()`](#voice-handle-is-playing)<br>

<a id="voice-handle-reference"></a>
## ChirpVoiceHandle

Playback methods return handles used to control or inspect one active or
queued voice.

<a id="voice-handle-stop"></a>
### `handle.Stop()`

Stops the voice if it is active or queued. Audio already submitted to the
output device is not removed from its hardware buffer.

<a id="voice-handle-wait"></a>
### `handle.Wait(timeout = None)`

- `timeout`: Maximum wait in seconds, or `None` to wait indefinitely.

Waits until the voice has been consumed by the mixer, stopped, or removed from
its queue. Returns `True` when that occurs, or `False` if `timeout` expires.

`Wait()` does not wait for samples already buffered by the output device to
finish playing. Use `Play(..., blocking = True)` when the script must wait for
both mixer completion and the estimated output-buffer latency.

<a id="voice-handle-is-playing"></a>
### `handle.IsPlaying()`

Returns true while the voice is active or queued.

---

<a id="contents-synth"></a>
### [ChirpSynth](#synth-reference)

- [`ChirpSynth()`](#synth-constructor)<br>
- [`CompileSequence()`](#synth-compile-sequence)<br>
- [`RenderPlan()`](#synth-render-plan)<br>
- [`RenderSamples()`](#synth-render-samples)<br>
- [`ChirpRenderPlan`](#synth-render-plan-object)<br>

<a id="synth-reference"></a>
## ChirpSynth

<a id="synth-constructor"></a>
### `ChirpSynth(channels = 2)`

Creates a direct synthesizer for mono or stereo sample rendering.

<a id="synth-compile-sequence"></a>
### `synth.CompileSequence(recipe)`

- `recipe`: Sequential list of `Tone` and recipe-control objects.

Compiles a sequential Tone recipe into a reusable `ChirpRenderPlan`.

<a id="synth-render-plan"></a>
### `synth.RenderPlan(plan)`

- `plan`: Plan returned by this synthesizer's `CompileSequence()` method.

Renders a plan created by the same synthesizer instance. Rendering resets
oscillator phase and stateful noise-filter state at the start of the plan. It
does not rewind the oscillator's random stream, so repeated plans containing
noise produce new variations during the same application run.

<a id="synth-render-samples"></a>
### `synth.RenderSamples(recipeOrPlan)`

- `recipeOrPlan`: Sequential recipe or a plan compiled by this synthesizer.

Compiles when necessary and returns interleaved float64 samples.

<a id="synth-render-plan-object"></a>
### `ChirpRenderPlan`

A compiled recipe returned by `CompileSequence()`. Treat its contents as
read-only. A plan may be rendered repeatedly by the `ChirpSynth` instance that
created it. Its constructor and stored event representation are internal.

---

<a id="contents-oscillator"></a>
### [ChirpOscillator](#oscillator-reference)

- [`ChirpOscillator()`](#oscillator-constructor)<br>
- [`GetWave()`](#oscillator-get-wave)<br>
- [`RenderWave()`](#oscillator-render-wave)<br>
- [`ResetState()`](#oscillator-reset-state)<br>
- [`WaveTable()`](#wave-table-constructor)<br>
- [`GetValue()`](#wave-table-get-value)<br>
- [`GetValues()`](#wave-table-get-values)<br>

<a id="oscillator-reference"></a>
## ChirpOscillator

<a id="oscillator-constructor"></a>
### `ChirpOscillator(sampleRate = 44100)`

Creates the shared waveform resolver and renderer.

<a id="oscillator-get-wave"></a>
### `oscillator.GetWave(wave)`

Resolves a built-in name, custom function, `WaveTable`, or `Sound`.

<a id="oscillator-render-wave"></a>
### `oscillator.RenderWave(wave, frequency, frameCount, phaseDegrees = 0.0)`

Renders a mono waveform into a float64 sample array. Negative frequencies use
zero. Positive frequencies are not upper-clamped.

<a id="oscillator-reset-state"></a>
### `oscillator.ResetState()`

Resets noise-filter, sample-and-hold, and quantized-noise state. It does not
rewind the oscillator's random stream, so later renders continue producing new
noise values within the same application run.

<a id="wave-table-constructor"></a>
### `WaveTable(sound)`

- `sound`: Non-empty mono or stereo `Sound`. Stereo is averaged to mono.

Creates an immutable cyclic table from a Sound. Passing the Sound directly to
a wave argument performs this conversion automatically.

<a id="wave-table-get-value"></a>
### `waveTable.GetValue(phase)`

- `phase`: Cyclic table position where `0` is the start and `1` wraps back to
  the start.

Returns one linearly interpolated sample.

<a id="wave-table-get-values"></a>
### `waveTable.GetValues(phases)`

- `phases`: Array-like cyclic table positions.

Returns linearly interpolated float64 samples for all positions.

---

<a id="contents-dsp"></a>
### [ChirpDSP](#dsp-reference)

- [`ChirpDSP()`](#dsp-constructor)<br>
- [`SamplesToBytes()`](#dsp-samples-to-bytes)<br>
- [`BytesToSamples()`](#dsp-bytes-to-samples)<br>
- [`GetSampleDuration()`](#dsp-get-sample-duration)<br>
- [`MixSamples()`](#dsp-mix-samples)<br>
- [`ApplySoundAppend()`](#dsp-apply-sound-append)<br>
- [`NormalizeSamples()`](#dsp-normalize-samples)<br>
- [`ApplySoundGain()`](#dsp-apply-sound-gain)<br>
- [`ApplySoundDebias()`](#dsp-apply-sound-debias)<br>
- [`ApplySoundClip()`](#dsp-apply-sound-clip)<br>
- [`ApplySoundSoftClip()`](#dsp-apply-sound-soft-clip)<br>
- [`ApplySoundRing()`](#dsp-apply-sound-ring)<br>
- [`ApplySoundChorus()`](#dsp-apply-sound-chorus)<br>
- [`ApplySoundPhaser()`](#dsp-apply-sound-phaser)<br>
- [`ApplySoundCut()`](#dsp-apply-sound-cut)<br>
- [`ApplySoundFadeIn()`](#dsp-apply-sound-fade-in)<br>
- [`ApplySoundFadeOut()`](#dsp-apply-sound-fade-out)<br>
- [`ApplySoundReverse()`](#dsp-apply-sound-reverse)<br>
- [`ApplySoundPan()`](#dsp-apply-sound-pan)<br>
- [`ApplySoundAutoPan()`](#dsp-apply-sound-auto-pan)<br>
- [`ApplySoundMono()`](#dsp-apply-sound-mono)<br>
- [`ApplySoundStereo()`](#dsp-apply-sound-stereo)<br>
- [`ApplySoundLowPass()`](#dsp-apply-sound-low-pass)<br>
- [`ApplySoundHighPass()`](#dsp-apply-sound-high-pass)<br>
- [`ApplySoundBandPass()`](#dsp-apply-sound-band-pass)<br>
- [`ApplySoundNotch()`](#dsp-apply-sound-notch)<br>
- [`ApplySoundPeak()`](#dsp-apply-sound-peak)<br>
- [`ApplySoundLowShelf()`](#dsp-apply-sound-low-shelf)<br>
- [`ApplySoundHighShelf()`](#dsp-apply-sound-high-shelf)<br>
- [`ApplySoundLowPassSweep()`](#dsp-apply-sound-low-pass-sweep)<br>
- [`ApplySoundHighPassSweep()`](#dsp-apply-sound-high-pass-sweep)<br>
- [`ApplySoundBandPassSweep()`](#dsp-apply-sound-band-pass-sweep)<br>
- [`ApplySoundNotchSweep()`](#dsp-apply-sound-notch-sweep)<br>
- [`ApplySoundPeakSweep()`](#dsp-apply-sound-peak-sweep)<br>
- [`ApplySoundLowShelfSweep()`](#dsp-apply-sound-low-shelf-sweep)<br>
- [`ApplySoundHighShelfSweep()`](#dsp-apply-sound-high-shelf-sweep)<br>
- [`ApplySoundSchroverb()`](#dsp-apply-sound-schroverb)<br>
- [`ApplySoundFreeverb()`](#dsp-apply-sound-freeverb)<br>
- [`ApplySoundMTVerb()`](#dsp-apply-sound-mtverb)<br>
- [`ApplySoundDelay()`](#dsp-apply-sound-delay)<br>
- [`ApplySoundPingPong()`](#dsp-apply-sound-ping-pong)<br>

<a id="dsp-reference"></a>
## ChirpDSP

`ChirpDSP` is the direct processor behind Sound methods. Most users should use
the Sound facade because it preserves channel and format information.

<a id="dsp-constructor"></a>
### `ChirpDSP(channels = 2)`

Creates a mono or stereo processor.

Unless stated otherwise, direct effects accept a one-dimensional interleaved
finite float sample array or signed 16-bit PCM bytes and preserve that
representation. Inputs must contain complete frames for the processor's channel
count. Non-finite samples and numeric effect arguments are rejected. Effect
arguments have the same meanings as the corresponding `Sound` methods. Results
do not share mutable NumPy storage with their inputs, including when an effect
has no audible work to perform.

<a id="dsp-samples-to-bytes"></a>
### `dsp.SamplesToBytes(samples)`

- `samples`: Floating-point sample data.

Rejects non-finite values, clips to `[-1, 1]`, and returns signed 16-bit PCM
bytes.

<a id="dsp-bytes-to-samples"></a>
### `dsp.BytesToSamples(sampleBytes)`

- `sampleBytes`: Signed 16-bit PCM bytes.

Returns a float64 sample array in `[-1, 1]`.

<a id="dsp-get-sample-duration"></a>
### `dsp.GetSampleDuration(samples)`

Returns sample duration in seconds using the DSP instance's channel count.

<a id="dsp-mix-samples"></a>
### `dsp.MixSamples(sampleArrays, mixGain = 0.707)`

- `sampleArrays`: List of sample arrays using the same channel layout.
- `mixGain`: Linear gain applied once after summing.

Mixes to the longest input without clipping or normalization.

<a id="dsp-apply-sound-append"></a>
### `dsp.ApplySoundAppend(soundData, appendedData, crossfade = 0.0, easing = "equalPower")`

Appends data with the same channel layout, optionally overlapping the end of
`soundData` with the start of `appendedData`. The overlap is limited to the
shorter input. The result uses the representation of `soundData`; returning PCM
therefore clips at the PCM conversion boundary. Direct DSP use does not perform
channel conversion. `easing` must be `"linear"` or `"equalPower"`.

<a id="dsp-normalize-samples"></a>
### `dsp.NormalizeSamples(samples, headroom = 0.0)`

Peak-normalizes float samples using non-negative decibel headroom.

<a id="dsp-apply-sound-gain"></a>
### `dsp.ApplySoundGain(soundData, gain = 1.0, offset = 0.0)`

- `gain`: Linear multiplier.
- `offset`: Constant added after multiplication.

<a id="dsp-apply-sound-debias"></a>
### `dsp.ApplySoundDebias(soundData)`

Subtracts the independent mean of each configured channel.

<a id="dsp-apply-sound-clip"></a>
### `dsp.ApplySoundClip(soundData, limit = 1.0)`

Applies a symmetric hard limit.

<a id="dsp-apply-sound-soft-clip"></a>
### `dsp.ApplySoundSoftClip(soundData, drive = 2.0, mix = 1.0)`

Applies normalized tanh saturation with a dry/wet mix. The wet signal is
bounded before blending; float input is not clipped after the blend.

<a id="dsp-apply-sound-ring"></a>
### `dsp.ApplySoundRing(soundData, freq, mix = 1.0, wave = "Sine")`

Applies ring modulation using the selected carrier wave and frequency.

<a id="dsp-apply-sound-chorus"></a>
### `dsp.ApplySoundChorus(soundData, rate = 0.8, depth = 0.003, delay = 0.015, voices = 2, feedback = 0.0, spread = 1.0, mix = 0.5, wave = "Sine")`

Applies the chorus described by [`Sound.Chorus()`](#sound-chorus).

<a id="dsp-apply-sound-phaser"></a>
### `dsp.ApplySoundPhaser(soundData, rate = 0.5, minFreq = 300.0, maxFreq = 1600.0, stages = 6, feedback = 0.2, spread = 1.0, mix = 0.5, wave = "Sine")`

Applies the phaser described by [`Sound.Phaser()`](#sound-phaser).

<a id="dsp-apply-sound-cut"></a>
### `dsp.ApplySoundCut(soundData, duration, fade = 0.003)`

Keeps `duration` seconds and fades the new end by at most `fade` seconds.

<a id="dsp-apply-sound-fade-in"></a>
### `dsp.ApplySoundFadeIn(soundData, duration, easing = "linear")`

Applies a gain fade across the start of the data.

<a id="dsp-apply-sound-fade-out"></a>
### `dsp.ApplySoundFadeOut(soundData, duration, easing = "linear")`

Applies a gain fade across the end of the data.

<a id="dsp-apply-sound-reverse"></a>
### `dsp.ApplySoundReverse(soundData)`

Reverses complete sample frames.

<a id="dsp-apply-sound-pan"></a>
### `dsp.ApplySoundPan(soundData, pan)`

Rotates and narrows stereo data toward `pan`. A mono DSP instance leaves the
input mono; use `ApplySoundStereo()` to promote it.

<a id="dsp-apply-sound-auto-pan"></a>
### `dsp.ApplySoundAutoPan(soundData, depth = 1.0, rate = 1.0, wave = "Sine", offset = 0.0, center = 0.0)`

Applies the one-LFO equal-power panning described by [`Sound.AutoPan()`](#sound-auto-pan).
`center` shifts the center of movement and is clamped to `[-1, 1]`. Mono input
is returned as interleaved stereo; stereo input retains its channel layout.

<a id="dsp-apply-sound-mono"></a>
### `dsp.ApplySoundMono(soundData)`

Collapses stereo data by averaging each frame. A mono DSP instance returns a
copy unchanged.

<a id="dsp-apply-sound-stereo"></a>
### `dsp.ApplySoundStereo(soundData, pan = 0.0)`

Promotes mono data to stereo with equal-power placement at `pan`. A stereo DSP
instance returns a copy unchanged.

<a id="dsp-apply-sound-low-pass"></a>
### `dsp.ApplySoundLowPass(soundData, freq, q = 0.707)`

Applies a low-pass biquad.

<a id="dsp-apply-sound-high-pass"></a>
### `dsp.ApplySoundHighPass(soundData, freq, q = 0.707)`

Applies a high-pass biquad.

<a id="dsp-apply-sound-band-pass"></a>
### `dsp.ApplySoundBandPass(soundData, freq, q = 0.707)`

Applies a band-pass biquad.

<a id="dsp-apply-sound-notch"></a>
### `dsp.ApplySoundNotch(soundData, freq, q = 0.707)`

Applies a notch biquad.

<a id="dsp-apply-sound-peak"></a>
### `dsp.ApplySoundPeak(soundData, freq, db, q = 0.707)`

Applies a peak boost or cut.

<a id="dsp-apply-sound-low-shelf"></a>
### `dsp.ApplySoundLowShelf(soundData, freq, db, q = 0.707)`

Applies a low-shelf boost or cut.

<a id="dsp-apply-sound-high-shelf"></a>
### `dsp.ApplySoundHighShelf(soundData, freq, db, q = 0.707)`

Applies a high-shelf boost or cut.

Fixed and swept biquads preserve silent input endpoints by fading any remaining
filter response over the final `0.003` seconds. This does not extend the input.

<a id="dsp-apply-sound-low-pass-sweep"></a>
### `dsp.ApplySoundLowPassSweep(soundData, startFreq, endFreq, q = 0.707, easing = "linear")`

Sweeps a low-pass biquad using geometric frequency interpolation.

<a id="dsp-apply-sound-high-pass-sweep"></a>
### `dsp.ApplySoundHighPassSweep(soundData, startFreq, endFreq, q = 0.707, easing = "linear")`

Sweeps a high-pass biquad using geometric frequency interpolation.

<a id="dsp-apply-sound-band-pass-sweep"></a>
### `dsp.ApplySoundBandPassSweep(soundData, startFreq, endFreq, q = 0.707, easing = "linear")`

Sweeps a band-pass biquad using geometric frequency interpolation.

<a id="dsp-apply-sound-notch-sweep"></a>
### `dsp.ApplySoundNotchSweep(soundData, startFreq, endFreq, q = 0.707, easing = "linear")`

Sweeps a notch biquad using geometric frequency interpolation.

<a id="dsp-apply-sound-peak-sweep"></a>
### `dsp.ApplySoundPeakSweep(soundData, startFreq, endFreq, db, q = 0.707, easing = "linear")`

Sweeps the frequency of a fixed peak boost or cut.

<a id="dsp-apply-sound-low-shelf-sweep"></a>
### `dsp.ApplySoundLowShelfSweep(soundData, startFreq, endFreq, db, q = 0.707, easing = "linear")`

Sweeps the frequency of a fixed low-shelf boost or cut.

<a id="dsp-apply-sound-high-shelf-sweep"></a>
### `dsp.ApplySoundHighShelfSweep(soundData, startFreq, endFreq, db, q = 0.707, easing = "linear")`

Sweeps the frequency of a fixed high-shelf boost or cut.

<a id="dsp-apply-sound-schroverb"></a>
### `dsp.ApplySoundSchroverb(soundData, wet = 0.35, decay = 0.72, roomSize = 1.0, tail = None)`

Applies the mono/dual-mono Schroeder reverb described by
[`Sound.Schroverb()`](#sound-schroverb).

<a id="dsp-apply-sound-freeverb"></a>
### `dsp.ApplySoundFreeverb(soundData, wet = 0.35, decay = 0.84, damping = 0.5, width = 1.0, tail = None)`

Applies the reverb described by [`Sound.Freeverb()`](#sound-freeverb).

<a id="dsp-apply-sound-mtverb"></a>
### `dsp.ApplySoundMTVerb(soundData, wet = 0.35, decay = 0.72, mode = "room", tail = None)`

Applies the reverb described by [`Sound.MTVerb()`](#sound-mtverb).

<a id="dsp-apply-sound-delay"></a>
### `dsp.ApplySoundDelay(soundData, delaySettings = None)`

- `delaySettings`: `(delay, decay, count, extend)`, or `None` for no effect.

[`Sound.Delay()`](#sound-delay) provides the normal public argument form.

<a id="dsp-apply-sound-ping-pong"></a>
### `dsp.ApplySoundPingPong(soundData, delaySettings = None)`

- `delaySettings`: `(delay, decay, count, width, extend)`, or `None` for no
  effect.

Returns stereo data. [`Sound.PingPong()`](#sound-ping-pong) provides the normal
public argument form.

---

<a id="contents-mixer"></a>
### [ChirpMixer](#mixer-reference)

- [`ChirpMixer()`](#mixer-constructor)<br>
- [`SetVolume()`](#mixer-set-volume)<br>
- [`Play()`](#mixer-play)<br>
- [`PlayQueued()`](#mixer-play-queued)<br>
- [`PlaySolo()`](#mixer-play-solo)<br>
- [`MixBlock()`](#mixer-mix-block)<br>
- [`GetStats()`](#mixer-get-stats)<br>
- [`StopAll()`](#mixer-stop-all)<br>

<a id="mixer-reference"></a>
## ChirpMixer

<a id="mixer-constructor"></a>
### `ChirpMixer(channels = 2, voices = 16, volume = 1.0, blockFrames = 1024)`

Creates the real-time floating-point voice mixer.

<a id="mixer-set-volume"></a>
### `mixer.SetVolume(volume)`

Sets perceptual master volume from `0` to `1`.

<a id="mixer-play"></a>
### `mixer.Play(samples, volume = 1.0, voice = None)`

Starts samples immediately. Uses a free voice or steals the oldest voice when
necessary. `volume` is a perceptual control from `0` to `1`. Samples must be
finite, contain complete frames for the mixer's channel count, and use the
mixer's existing channel layout. The mixer copies the samples before playback,
so later changes to the caller's array do not affect the voice. Returns a
`ChirpVoiceHandle`.

Playing an empty sample array returns an already completed handle. It does not
stop or replace an active voice.

<a id="mixer-play-queued"></a>
### `mixer.PlayQueued(samples, volume = 1.0, voice = None)`

Queues samples contiguously on a voice and returns a `ChirpVoiceHandle`. When
`voice` is omitted, the mixer uses a free voice when possible and otherwise
queues on voice zero. Each voice can hold at most 256 queued sounds; attempting
to exceed that limit raises `OverflowError`.

<a id="mixer-play-solo"></a>
### `mixer.PlaySolo(samples, volume = 1.0)`

Stops all active and queued voices, then starts samples on voice zero. Returns
a `ChirpVoiceHandle`.

<a id="mixer-mix-block"></a>
### `mixer.MixBlock(output = None)`

Mixes one fixed-size block. Supplying a correctly sized float64 array reuses
that output buffer. The supplied array must be writable and contiguous. Normal
mixing does not clip. If otherwise finite inputs overflow float64 during
summation, the result is reduced to the largest finite value instead of
returning infinity or `NaN`.

<a id="mixer-get-stats"></a>
### `mixer.GetStats()`

Returns a coherent snapshot containing `activeVoices` and `queuedVoices`.

<a id="mixer-stop-all"></a>
### `mixer.StopAll()`

Stops active voices and clears queues.

---

<a id="contents-player"></a>
### [ChirpPlayer](#player-reference)

- [`ChirpPlayer()`](#player-constructor)<br>
- [`Load()`](#player-load)<br>
- [`SetVolume()`](#player-set-volume)<br>
- [`Play()`](#player-play)<br>
- [`PlayQueued()`](#player-play-queued)<br>
- [`PlaySolo()`](#player-play-solo)<br>
- [`GetStats()`](#player-get-stats)<br>
- [`StopAll()`](#player-stop-all)<br>
- [`Close()`](#player-close)<br>

<a id="player-reference"></a>
## ChirpPlayer

<a id="player-constructor"></a>
### `ChirpPlayer(channels = 2, sampleRate = 44100, bitsPerSample = 16, voices = 16, volume = 1.0, enabled = True, blockFrames = 1024)`

Creates a `ChirpMixer` and Windows WinMM output stream. Playback supports
44.1 kHz signed 16-bit mono or stereo output.

`ChirpPlayer` can be used as a context manager. Leaving a
`with ChirpPlayer(...)` block calls `Close()` automatically.

<a id="player-load"></a>
### `player.Load(path)`

Loads a `.chirp` file and returns `ChirpFileData`.

<a id="player-set-volume"></a>
### `player.SetVolume(volume)`

Sets perceptual mixer master volume.

<a id="player-play"></a>
### `player.Play(sound, volume = 1.0, blocking = False, voice = None)`

Plays a Sound, `ChirpFileData`, `PcmFileData`, or raw signed 16-bit PCM bytes.
Sound and file objects are converted between mono and stereo when their channel
count differs from the player. Raw PCM bytes are interpreted using the
player's configured channel count.

Returns a `ChirpVoiceHandle`, or `None` when playback is disabled. With
`blocking = True`, the call waits for mixer completion and the estimated
output-buffer latency.

<a id="player-play-queued"></a>
### `player.PlayQueued(sound, volume = 1.0, voice = None)`

Queues Sound on a mixer voice and returns a `ChirpVoiceHandle`. This method is
always non-blocking.

<a id="player-play-solo"></a>
### `player.PlaySolo(sound, volume = 1.0, blocking = False)`

Flushes existing playback and starts Sound alone on voice zero. Returns a
`ChirpVoiceHandle`, or `None` when playback is disabled.

<a id="player-get-stats"></a>
### `player.GetStats()`

Returns the same statistics described by `Chirper.GetStats()`.

<a id="player-stop-all"></a>
### `player.StopAll()`

Stops mixer voices and flushes output.

<a id="player-close"></a>
### `player.Close()`

Closes the output stream safely.

---

<a id="contents-file"></a>
### [ChirpFile](#file-reference)

- [`ChirpFileData()`](#file-chirp-data)<br>
- [`PcmFileData()`](#file-pcm-data)<br>
- [`MakeMetadata()`](#file-make-metadata)<br>
- [`MakePcmMetadata()`](#file-make-pcm-metadata)<br>
- [`Read()`](#file-read)<br>
- [`Write()`](#file-write)<br>
- [`Load()`](#file-load)<br>
- [`Save()`](#file-save)<br>
- [`ReadWav()`](#file-read-wav)<br>
- [`WriteWav()`](#file-write-wav)<br>
- [`ChirpToWav()`](#file-chirp-to-wav)<br>
- [`WavToChirp()`](#file-wav-to-chirp)<br>

<a id="file-reference"></a>
## ChirpFile

`ChirpFile` is the direct file module. `Sound.Load()`, `Sound.Save()`, and their
WAV counterparts are preferable when a Sound result is wanted.

<a id="file-chirp-data"></a>
### `ChirpFile.ChirpFileData(samples, metadata)`

- `samples`: One-dimensional interleaved sample data.
- `metadata`: Native Chirp metadata.

Contains immutable float64 samples and normalized metadata. The `samples`
property returns a writable copy. Other useful properties are `sampleRate`,
`channels`, `duration`, `sampleFormat`, and `metadata`. Custom metadata fields
are retained. The `metadata` property returns a deep copy. Reserved metadata is
validated, including an exact whole-frame match between the declared duration
and sample payload.

<a id="file-pcm-data"></a>
### `ChirpFile.PcmFileData(pcm, metadata)`

- `pcm`: Complete PCM sample frames as bytes-like data.
- `metadata`: Matching PCM metadata.

Preserves the source PCM bytes and bit depth while also decoding directly to
immutable float64 samples. The `samples` property returns a writable copy.
Other useful properties are `pcm`, `sampleRate`, `channels`, `bitsPerSample`,
`duration`, `sampleFormat`, and `metadata`. Supported formats are unsigned
8-bit PCM, signed little-endian 16-bit PCM, and signed little-endian 24-bit
PCM. The `metadata` property returns a deep copy, and the declared duration must
match the complete PCM frame count.

<a id="file-make-metadata"></a>
### `ChirpFile.MakeMetadata(duration, channels, sampleRate = 44100)`

- `duration`: Sample duration in seconds.
- `channels`: `1` for mono or `2` for stereo.
- `sampleRate`: Sample rate in Hz. File validation requires `44100`.

Creates metadata for native little-endian float32 `.chirp` samples.

<a id="file-make-pcm-metadata"></a>
### `ChirpFile.MakePcmMetadata(duration, channels, sampleRate = 44100, bitsPerSample = 16)`

- `duration`: PCM duration in seconds.
- `channels`: `1` for mono or `2` for stereo.
- `sampleRate`: Sample rate in Hz. File validation requires `44100`.
- `bitsPerSample`: PCM width: `8`, `16`, or `24`.

Creates matching PCM metadata for an 8-, 16-, or 24-bit WAV payload.

<a id="file-read"></a>
### `ChirpFile.Read(path)`

- `path`: `.chirp` path. A missing extension is appended and a different
  extension is replaced.

Reads native little-endian float32 `.chirp` data. Returns a tuple containing
the resolved `Path` and a `ChirpFileData` object.

<a id="file-write"></a>
### `ChirpFile.Write(path, samples, metadata)`

- `path`: Destination `.chirp` path. A missing extension is appended and a
  different extension is replaced.
- `samples`: One-dimensional interleaved sample data.
- `metadata`: Metadata containing the channel count and 44.1 kHz sample rate.

Writes unclipped samples as native little-endian float32 and returns the
resolved output `Path`. Metadata must be strict JSON with finite numeric values.
Missing parent directories are created, and an existing destination is replaced
atomically only after the complete file has been written.

<a id="file-load"></a>
### `ChirpFile.Load(path)`

- `path`: `.chirp` path. A missing extension is appended and a different
  extension is replaced.

Loads little-endian float32 `.chirp` data and returns `ChirpFileData`. Samples
are promoted to float64 without clipping.

<a id="file-save"></a>
### `ChirpFile.Save(path, data)`

- `path`: Destination `.chirp` path. A missing extension is appended and a
  different extension is replaced.
- `data`: Object exposing `samples` and matching `metadata`.

Writes the samples and metadata of a `ChirpFileData`-compatible object as an
unclipped little-endian float32 `.chirp` file and returns the resolved output
`Path`. Missing parent directories are created.

<a id="file-read-wav"></a>
### `ChirpFile.ReadWav(path)`

- `path`: WAV path. A missing extension is appended and a different extension
  is replaced.

Loads a mono or stereo 44.1 kHz PCM WAV and returns `PcmFileData`. Source 8-,
16-, or 24-bit PCM bytes and bit depth are preserved, and samples are decoded
directly to float64 without intermediate quantization.

<a id="file-write-wav"></a>
### `ChirpFile.WriteWav(path, pcm, metadata)`

- `path`: Destination WAV path. A missing extension is appended and a different
  extension is replaced.
- `pcm`: Complete 8-, 16-, or 24-bit PCM sample frames.
- `metadata`: Matching metadata created by `MakePcmMetadata()`.

Writes unsigned 8-bit, signed little-endian 16-bit, or signed little-endian
24-bit PCM bytes and matching metadata to WAV, then returns the resolved output
`Path`. Missing parent directories are created, and an existing destination is
replaced atomically only after the complete file has been written.

<a id="file-chirp-to-wav"></a>
### `ChirpFile.ChirpToWav(path)`

- `path`: `.chirp` path. A missing extension is appended and a different
  extension is replaced.

Creates a signed 16-bit PCM WAV beside the selected `.chirp` file. Native
samples outside `[-1, 1]` clip during this conversion. The destination uses the
same base name with a `.wav` extension. This function returns `None`.

<a id="file-wav-to-chirp"></a>
### `ChirpFile.WavToChirp(path)`

- `path`: WAV path. A missing extension is appended and a different extension
  is replaced.

Creates a `.chirp` file beside the selected WAV. Source PCM is decoded directly
at its original 8-, 16-, or 24-bit precision before the samples are stored as
native float32. The destination uses the same base name with a `.chirp`
extension. This function returns `None`.
