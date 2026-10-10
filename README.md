# 🐦 Dawn Chorus

> An offline-first, screen-free bird-listening walk bingo app powered by open-source AI.

*Tested on Python 3.9 on Windows 10/11. Newer Python versions may fail to install TensorFlow-based dependencies.*

**60-Second Summary**: Dawn Chorus turns your daily walk into a tranquil audio bingo game. Put your phone in your pocket, start recording with your native voice recorder app, and enjoy a 20–30 minute walk completely screen-free. Afterwards, upload your recording. Dawn Chorus runs BirdNET locally to identify bird species, then prompts a local Gemma model via Ollama to craft a warm, accurate field card summarizing your walk.

## 🚀 Quick Start
```bash
git clone https://github.com/your-repo/dawn-chorus.git
cd dawn-chorus
pip install -r requirements.txt
ollama pull gemma3:4b
streamlit run app.py
```

## 🔌 Run it fully offline

A core goal of Dawn Chorus is offline operation. You can take this to a cabin in the woods and it will work entirely without an internet connection.
1. Connect to the internet once to install dependencies, run `ollama pull gemma3:4b`, and start the app (`streamlit run app.py`).
2. Run your first inference or change the location to your target offline location while still connected, which triggers `birdnet` to download its model weights and species lists into your local environment.
3. Turn off your Wi-Fi/data. The app will now run entirely locally using the cached models and species lists!

## ⚙️ How it works

```text
[Phone Audio] --> (Upload) --> [Local FFmpeg] (WAV/Chunks) 
                                     |
                                     v
[User Location/Time] ---------> [Local BirdNET] (Species Detections)
                                     |
                                     v
[Ollama: Gemma3:4b] <---------- (Prompt + Detections)
                                     |
                                     v
                                [Field Card UI]
```

## 🌲 Why open-source AI?

Most modern AI apps demand continuous screen attention, high-bandwidth streaming, and proprietary cloud APIs. Dawn Chorus flips this paradigm:
- **100% Offline & Private**: Recordings never leave your machine. BirdNET runs locally and offline.
- **No API keys or per-request cost**: Everything runs on your local hardware.
- **Swappable LLM**: Gemma only writes the field card and is easily swappable, although the BirdNET core model is not swappable.

## 🧪 Before every walk

To properly use Dawn Chorus in the wild, follow this checklist before you step outside:
- [ ] **Open the app and set location:** Enter your latitude/longitude in the sidebar. The default is set to a city-level coordinate in `config.py`, but you should enter your local coordinates.
- [ ] **Charge your phone** fully.
- [ ] Set your phone voice recorder app to save as **`.m4a`** or **`.wav`**.
- [ ] **Start Ollama** on your laptop.
- [ ] Run **`run.bat`** and ensure the preflight checks pass.
- [ ] (Optional) Test the printed local network URL on your phone browser.
- [ ] Put your phone in **airplane mode** (to prove the app works 100% offline and prevent interruptions).
- [ ] Start recording, place the phone in a **chest pocket** (microphone uncovered, out of wind), and turn screen off.
- [ ] Note the start time and the weather conditions.
- [ ] Walk outside for 20-30 minutes.

## 📱 Upload straight from your phone

If you prefer not to transfer files to your laptop via USB, you can upload recordings straight from your phone's browser over your local Wi-Fi:
1. Ensure your laptop and phone are on the **same Wi-Fi network**.
2. Run `run.bat` on your laptop. It will print a local URL (e.g. `http://192.168.1.5:8501`).
3. If prompted by Windows Defender Firewall, **allow Python** on **PRIVATE networks**.
4. Open the printed URL on your phone's browser.
5. Tap the upload button and use your phone's **file picker** to choose the recording directly from the recorder app's folder.

## 📊 Results from my real walks

*Walk 1:*
- **Date:** [FILL IN]
- **Duration:** [FILL IN]
- **Bingo Score:** [FILL IN]
- **Total Species Detected:** [FILL IN]
- **Highlight:** [FILL IN]

*Walk 2:*
- **Date:** [FILL IN]
- **Duration:** [FILL IN]
- **Bingo Score:** [FILL IN]
- **Total Species Detected:** [FILL IN]
- **Highlight:** [FILL IN]

## 📸 Screenshots

![Hero Mode]([FILL IN PLACEHOLDER FOR IMAGE PATH])
![Quest Bingo Card]([FILL IN PLACEHOLDER FOR IMAGE PATH])
![Upload Area]([FILL IN PLACEHOLDER FOR IMAGE PATH])
![Discoveries]([FILL IN PLACEHOLDER FOR IMAGE PATH])
![Timeline]([FILL IN PLACEHOLDER FOR IMAGE PATH])
![Field Journal]([FILL IN PLACEHOLDER FOR IMAGE PATH])

## 📜 License & Credits

- **Dawn Chorus Source Code**: Released under the MIT License.
- **BirdNET**: Model weights by the Center for Conservation Bioacoustics at the Cornell Lab of Ornithology and Chemnitz University of Technology (**CC BY-NC-SA 4.0** for non-commercial use). `birdnet` Python package by Stefan Taubert (MIT).
- **Gemma**: Governed by the Gemma Terms of Use.
- **Ollama**: MIT License.
- **Streamlit**: Apache 2.0.
- **Xeno-canto**: Audio sample clips used for testing are not redistributed. See `CREDITS.md` and `samples/README.md` for full attribution.
