# Dawn Chorus

**Put your phone away. Listen to the morning.**

Dawn Chorus is a listening-walk bird bingo that runs entirely on your own laptop. You get a checklist of the birds likely to be near you this week, you go for a walk with your phone recording in your pocket and the screen off, and when you get back an open-source model tells you who was singing. A local language model then writes you a short field-journal page about the walk.

Built for the [Hacktoberfest Open-Source AI Challenge, Week 1: "Touch Grass"](https://dev.to/challenges/hacktoberfest-week1-2026-10-05). The idea: **the screen should be the shortest part of the experience.**

![Python 3.9](https://img.shields.io/badge/python-3.9-blue) ![License MIT](https://img.shields.io/badge/code-MIT-green) ![Offline first](https://img.shields.io/badge/runs-offline-success)

> The story, real walk results and demo video are in the DEV post: [Dawn Chorus on DEV](https://dev.to/)

---

## Contents

1. [How it works](#how-it-works)
2. [Features](#features)
3. [Quick start](#quick-start)
4. [Taking a walk](#taking-a-walk)
5. [Upload straight from your phone](#upload-straight-from-your-phone)
6. [Running fully offline](#running-fully-offline)
7. [Why open-source AI](#why-open-source-ai)
8. [Limitations (please read)](#limitations-please-read)
9. [Project structure](#project-structure)
10. [Testing and preflight](#testing-and-preflight)
11. [Privacy](#privacy)
12. [License and credits](#license-and-credits)

---

## How it works

```
 Walk settings (lat, lon, date)
            |
            v
 BirdNET location + week model ---> "Today's likely birds" (12-bird bingo card)
            |
   You walk. Phone records. Screen off.
            |
            v
 Upload recording --> ffmpeg (48 kHz mono WAV)
            |
            v
 BirdNET audio model (local, with location/week species filter)
            |
            v
 Detections: species, confidence, time heard
            |
            v
 Gemma via Ollama (local) writes the field journal,
 checked against the detections before it is shown
            |
            v
 Results: bingo found, other birds heard, timeline, field journal
            |
            v
 "Listen for these next time"  -->  go outside again
```

Everything after the first model download happens on your machine. No audio is uploaded anywhere.

## Features

| Feature | What it does |
|---|---|
| **Today's Outdoor Quest** | A bingo card of the 12 birds most likely at your location this week, from BirdNET's own location and week model. Works before you go outside and needs no internet. |
| **Walk recording upload** | Accepts WAV, MP3, M4A, OGG and FLAC. Files are converted with ffmpeg. |
| **Listening Room** | While BirdNET works, you see the real waveform of your recording, a playhead that scans across it, and each bird appearing at the moment it was heard. Progress is real, not animated filler. |
| **Location-aware detection** | Detections are limited to species that plausibly occur at your location in that week of the year, which sharply cuts false positives. |
| **Bingo birds vs. other birds** | Birds on your card are separated from other birds that were heard. |
| **Walk timeline** | A time axis for the whole recording, one row per species, dot size showing confidence. |
| **Field journal** | A short journal page written by a local Gemma model. The text is checked against the detections, and if the model mentions a bird that was not detected, the app shows a plain template card instead and labels it as one. |
| **Grass Ratio** | Time outside (recording length) versus time on this screen, measured while the page is open. |
| **Confidence slider** | Re-filters stored results instantly without re-running the analysis. |
| **Printable bingo card** | A paper version of the card, so the phone can stay in your pocket. |
| **Downloads and history** | Download the field card as Markdown. Every walk is saved as JSON in `walks/`. |
| **Gemma status and retry** | A small status indicator shows whether Ollama and the model are ready, with a Retry button if the card could not be written. |
| **Test mode** | Under Advanced, skip the location filter to check the model on any clip. For debugging only. |

## Quick start

Tested on **Python 3.9 on Windows 10/11**. Newer Python versions may fail to install the TensorFlow-based dependencies.

```bash
# 1. Install Ollama from https://ollama.com/download, then pull a Gemma model
ollama pull gemma3:4b

# 2. Install ffmpeg (Windows example)
winget install ffmpeg

# 3. Install the Python dependencies
pip install -r requirements.txt

# 4. Start the app
python -m streamlit run app.py
```

Then open http://localhost:8501.

On Windows you can also just double-click **`run.bat`**. It activates a virtual environment if one exists, starts Ollama if it is not running, runs the preflight check, prints the address to open on your phone, and launches the app.

Notes:
- The first BirdNET run downloads its model weights (about 125 MB). After that, everything works offline.
- Set your latitude and longitude in the sidebar. The defaults in the repo are only city-level.
- The Gemma model name is a single setting in `config.py`. Use a smaller model such as `gemma3:1b` for speed on a weak laptop.

## Taking a walk

1. Open the app and look at **Today's Outdoor Quest**. Optionally print the bingo card.
2. Set your phone's voice recorder to M4A or WAV. Switch on airplane mode.
3. Start recording and put the phone in a chest pocket with the microphone uncovered and out of the wind. Screen off.
4. Walk for 20 to 30 minutes. Notice things.
5. Stop the recording, then upload it in the app (see below).
6. Read your field journal and see which birds you missed. Go back tomorrow.

Why a phone recorder and not the browser microphone? Browsers stop recording when the phone screen locks, and they refuse microphone access over plain HTTP on a local network. The native recorder app avoids both problems and keeps the screen genuinely off.

## Upload straight from your phone

1. Put the phone and the laptop on the same Wi-Fi network.
2. Start the app with `run.bat`. It prints an address such as `http://192.168.x.x:8501`.
3. If Windows asks, allow Python through the firewall on **private** networks.
4. Open that address in your phone's browser and pick the recording with the file picker.

The upload limit is 200 MB. A 30-minute M4A is usually under 40 MB.

If the phone cannot connect, check the firewall, make sure both devices are on the same network, and turn off any VPN. Campus and public Wi-Fi often block device-to-device traffic. In that case transfer the file by cable, Bluetooth or a cloud drive and upload it from the laptop.

## Running fully offline

1. While online, once: pull the Gemma model (`ollama pull gemma3:4b`) and run one analysis so BirdNET downloads its model weights.
2. After that, turn off Wi-Fi or enable airplane mode and run the app as usual.
3. To check it yourself, run:

```bash
python scripts/preflight.py --offline
```

This blocks outbound network access for the process and runs a detection and a field card to confirm that no internet is needed.

Telemetry is disabled in `.streamlit/config.toml`.

## Why open-source AI

The detection core is open and local, and that is what makes the project work in the places it is meant for.

- **It works with no signal.** BirdNET runs on the laptop, so the app is useful in a forest or on a campus trail with no connection.
- **Your recordings stay with you.** A walk recording carries your location and can include other people's voices. Nothing leaves the machine.
- **No per-request cost.** Analyzing an hour of audio every day costs nothing, which a metered audio API would not.
- **A specialist model beats a general one for this job.** BirdNET is trained specifically for bird sound identification and has a built-in location and week model that powers the bingo card and the false-positive filter.
- **You can inspect and adjust it.** The confidence threshold, the species filter and the model choice are all in your hands.

To be honest about it: the Gemma part is replaceable with almost any small local model, because it only turns a structured list of detections into a short journal entry. BirdNET is the part that is not replaceable by a general-purpose closed API running without internet.

## Limitations (please read)

- **Detections are 3-second windows, not individual birds.** The app reports where a species was heard and how often, never how many birds there were.
- **A phone microphone in a pocket is noisy.** Wind, clothing rustle and traffic reduce accuracy. Lower confidence thresholds give more false positives, and the sidebar says so.
- **The location filter can hide real birds.** A bird outside the expected list for your place and week will not be reported. Test mode lets you check the raw model output.
- **BirdNET weights are non-commercial.** See [CREDITS.md](CREDITS.md).
- **Gemma 4B on a laptop CPU is not instant.** The first card after starting Ollama is the slowest. A template card is shown if Gemma is not running.
- **Windows first.** `run.bat` is a Windows script. The Python app itself should run elsewhere, but only Windows has been tested.
- **Not a substitute for an expert.** Treat the identifications as strong hints and verify unusual birds with a second source.

## Project structure

```
dawn-chorus/
|-- app.py                  # Streamlit app and page flow
|-- detect.py               # audio conversion, BirdNET detection, location/week filter
|-- card.py                 # Gemma prompt, Ollama status, verification, template fallback
|-- config.py               # model name, thresholds, timeouts
|-- ui.py                   # HTML builders for the interface components
|-- hero.py                 # time-of-day hero scene
|-- icons.py                # inline icon set
|-- styles.css              # all styling
|-- run.bat                 # one-click launcher (Windows)
|-- requirements.txt
|-- requirements-dev.txt
|-- .streamlit/config.toml  # theme, telemetry off
|-- scripts/
|   |-- preflight.py        # environment checks, with --offline mode
|   |-- summarize_walks.py  # table of all saved walks
|   `-- get_ip.py           # prints the LAN address for phone uploads
|-- tests/                  # unit and integration tests
|-- examples/example_walk.json
|-- samples/README.md       # where to get test clips
`-- walks/                  # saved walk results (git-ignored)
```

## Testing and preflight

```bash
pytest                              # test suite
python scripts/preflight.py         # checks Python, ffmpeg, Ollama, Gemma, BirdNET cache, disk space
python scripts/preflight.py --offline
python scripts/summarize_walks.py   # summary table of your saved walks
```

Test audio is not included in the repository. See `samples/README.md` for where to download Creative Commons bird recordings.

## Privacy

- Audio is processed locally and is never uploaded.
- Saved walks live in `walks/` on your machine and are excluded from git.
- Coordinates shown in this repository are rounded to city level.
- The Grass Ratio's screen time is measured only while the page is open, and is stored locally.

## License and credits

- Dawn Chorus code: [MIT](LICENSE).
- **BirdNET** (Cornell Lab of Ornithology and Chemnitz University of Technology): model weights are licensed CC BY-NC-SA 4.0, so non-commercial use only. The `birdnet` Python package is MIT licensed.
- **Gemma** by Google, run locally through **Ollama**, under their respective terms.
- **Streamlit** for the interface.
- Test recordings come from **Xeno-canto** under their individual licenses and are not redistributed in this repository.

Full details are in [CREDITS.md](CREDITS.md).
