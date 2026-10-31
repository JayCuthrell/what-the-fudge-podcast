# 🎙️ Automated YouTube Podcast Pipeline

A modular Python pipeline designed for macOS that transforms a simple Markdown list of topics into a fully polished, YouTube-ready video.

This tool provides a terminal-based teleprompter, records your microphone audio, masters the audio to YouTube's loudness standards (-14 LUFS), dynamically renders 1080p title slides with adaptive layouts, optionally records and composites your webcam, encodes the video using Apple Silicon hardware acceleration, and automatically uploads the final product to YouTube with interactive chapter timestamps.

## ✨ Features

* **Markdown Driven:** Write your script in a simple `.md` file. The tool parses titles, links, and talking points automatically.
* **Terminal Teleprompter:** Step through your talking points with a single keystroke (`T` or `Space`) while recording.
* **Webcam Integration (Rule of Thirds Grid):** Record video from your Mac's webcam simultaneously. The layout engine uses a 3x3 grid system, allowing you to anchor your camera feed in any of 9 positions (e.g., `bottom-right`, `top-left`) while the slide card, headline, and progress indicators adaptively reflow around it.
* **Smart Audio Mastering:** Uses FFmpeg's `loudnorm` filter to hit exact YouTube broadcast standards (-14 LUFS, -1.5 TP).
* **Dynamic Visuals:** Renders beautiful 1080p cards via `Pillow` featuring segmented progress bars and real-time bottom timeline runners.
* **Hardware Accelerated:** Offloads video encoding to the Apple Media Engine (`h264_videotoolbox`) for lightning-fast renders.
* **Automated YouTube Chapters:** Injects perfectly formatted `MM:SS` chapter marks and citation links into the video description.
* **Dry-Run & Auto-Advance:** Test your script timing and visual rendering without arming the mic or burning CPU cycles.

## 📂 Project Structure

The codebase is highly modular, separating business logic into distinct, testable files:

```text
podcast_pipeline/
├── config.py           # Unified settings, visual palette, layout grids, and hardware flags
├── content.py          # Markdown parser, timestamp math, and description generator
├── audio.py            # Sounddevice mic capture and FFmpeg loudness mastering
├── camera.py           # macOS AVFoundation webcam recorder and mock generator
├── visuals.py          # Pillow 1080p adaptive slide renderer and progress UI
├── video.py            # FFmpeg assembly, PiP compositing, timeline animations, and muxing
├── uploader.py         # Google OAuth and YouTube Data API client
├── main.py             # CLI orchestrator and terminal teleprompter loop
├── test_pipeline.py    # Unittest suite for logic and timestamp verification
├── setup.sh            # Automated venv creation and dependency installation
├── requirements.txt    # Python package dependencies
├── topics.md           # Your input file (Markdown)
└── client_secrets.json # (Required) Your YouTube API OAuth credentials
```

## ⚙️ Prerequisites & Setup

### 1. System Dependencies (macOS)

You must have FFmpeg installed for audio mastering, webcam capture via `avfoundation`, and video encoding:

```bash
brew install ffmpeg
```

### 2. Python Dependencies

Use the provided setup script to create an isolated virtual environment and install the required packages (`sounddevice`, `soundfile`, `Pillow`, and Google API clients). 

```bash
chmod +x setup.sh
./setup.sh
source my_env/bin/activate
```

*(Note: Terminal/VS Code must be granted Microphone and Camera access in macOS System Settings > Privacy & Security)*

### 3. YouTube API Credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the **YouTube Data API v3**.
3. Create an **OAuth 2.0 Client ID** (Desktop App).
4. Download the JSON file, rename it to `client_secrets.json`, and place it in the root directory.

## 📝 Preparing Your Content

Create a `topics.md` file in the root directory. Use `##` for topics. The script automatically extracts the first URL it finds to use as a citation.

```markdown
## 1. Breakthrough in Open Source AI
Link: https://example.com/ai-article
Discuss latency improvements and smaller footprints.

## 2. Browser Security Exploits
Link: https://example.com/security
Cover CVE details and mitigation strategies.
```

## 🚀 Usage Guide

Run the orchestrator from your terminal.

### Live Recording (Audio Only)

Arms the microphone, opens the teleprompter, renders centered topic cards, and prompts for upload:

```bash
python main.py
```

* **Controls:** Press `[Space]` or `[T]` to mark a chapter and advance to the next slide.

### Live Recording with Webcam (Picture-in-Picture)

Activates the webcam and places it in the bottom-right block of the 3x3 grid, shifting the text card to the left:

```bash
python main.py --webcam --webcam-pos bottom-right
```

*Supported positions:* `top-left`, `top-center`, `top-right`, `middle-left`, `center`, `middle-right`, `bottom-left`, `bottom-center`, `bottom-right`.

### Dry Run (Rehearsal Mode)

Simulates the teleprompter and renders the visual slides into the `rendered_slides/` folder so you can inspect layouts, but skips mic/camera recording and video encoding.

```bash
# Test the layout shifting for a top-right camera anchor
python main.py --dry-run --webcam --webcam-pos top-right
```

### Hands-Free Simulation

Auto-advances topics on a strict timer. Great for testing pacing and pipeline flow without manual input.

```bash
python main.py --dry-run --auto-advance 5.0
```

## 🧪 Testing

Run the included unit tests to verify timestamp logic, markdown parsing, and pipeline orchestration mockups:

```bash
python -m unittest -v test_pipeline.py
```