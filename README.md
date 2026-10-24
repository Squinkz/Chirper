# Chirper

Chirper is a small Python library for synthesizing and playing sounds and music.

It is a modular system that composes a synthesizer, a sequencer, a DSP engine and a playback mixer.

## Requirements and Installation

Chirper requires numpy and Python 3.10 or newer.

From the Chirper project root:

```powershell
python -m pip install -e .
```

For faster rendering, install numba as well:

```powershell
python -m pip install -e ".[performance]"
```

If you are working from source without installing, run scripts from the Chirper project root or add it to `PYTHONPATH`.

## Documentation

- [Quick Start Guide](docs/QUICKSTART.md) provides a tutorial for getting up and running.
- [API reference](docs/API_REFERENCE.md) provides a comprehensive guide to the Chirper API.

## Demo

```python
from Chirper import *

# TODO:
# Add example
```

## Tests

Run the test suite from the project root:

```powershell
python -m unittest discover -s tests -t .
```

## License

Chirper is available under the [MIT License](LICENSE).
