# What The Fudge - Audiogram Generator 🎙️✨

A high-performance Python script designed to transform podcast audio into branded social media videos with dynamic visual elements. 

## Features

* **Dynamic Waveform Styles**: Support for `mirror` (symmetrical) and `continuous` waveform visualizations.
* **Logo Pulse Effect**: A reactive background transformation that pulses in sync with audio intensity (RMS energy).
* **Scrolling Marquee**: An automated header displaying "Now Playing Episode for [Current Date]" with high-visibility path effects.
* **Branded Aesthetics**: Custom color integration using brand-specific orange (#f38c3c) with neon-style glow effects.
* **Performance Optimized**: Utilizes the `Agg` Matplotlib backend for headless rendering and supports multi-threaded exporting.
* **Test Mode**: Option to generate a 10-second preview for rapid iteration.

---

## Prerequisites

The following Python libraries are required:

* `moviepy >= 2.0.0`
* `librosa`
* `numpy`
* `matplotlib`
* `soundfile`
* `psutil` (optional — used for render performance monitoring)


---

## Installation

A `setup.sh` script is provided to automate the environment configuration on macOS (zsh).

```zsh
chmod +x setup.sh
./setup.sh

```

---

## Usage

Run the script by providing the path to your audio file and background image. 

### Basic Command

```zsh
python3 audiogram_gen.py <audio_file> <image_file>
```

### Advanced Options

| Flag | Description |
| --- | --- |
| `--test` | Generates a 10-second preview using `ultrafast` encoding. |
| `--style` | Choose between `mirror` (default) or `continuous` waveforms. |

### Notes on Recent Code Updates

- **Performance Monitor & CSV Logging**: The script now collects CPU and memory samples during rendering and appends a performance summary to `render_stats.csv` (timestamp, style, audio duration, render time, render-to-audio ratio, avg CPU, max memory).
- **Pre-rendered Waveform Cache**: Waveform frames are pre-rendered into an in-memory cache before compositing to significantly speed up export time.
- **Optimized Rendering Defaults**: The generator uses a reduced number of waveform points, multithreaded export, and an M1-optimized hardware encoder (`h264_videotoolbox`) where available to speed up exports. The `--test` flag uses an `ultrafast` preset for rapid previews.
- **Background Auto-resize & Crop**: Background images are auto-resized to 1920px width and center-cropped to 1080p when necessary for consistent output sizing.
- **Pulse Effect Disabled by Default**: The reactive logo pulse is disabled in the optimized path to prioritize export speed and determinism.
- **Output Naming**: Output files follow the pattern `podcast_<style>_optimized.mp4` to make it easy to identify rendered variants.

These updates are implemented in `audiogram_gen.py` and aim to provide faster, repeatable renders while capturing lightweight telemetry for tuning.

**Example (Test Run with Mirror Style):**

```zsh
python3 audiogram_gen.py audio.m4a background.png --test --style mirror

```

---

## Repository Structure

* `audiogram_gen.py`: Main script containing audio analysis and video compositing logic.
* `requirements.txt`: List of necessary Python dependencies.
* `setup.sh`: Shell script to initialize the `my_env` virtual environment.
* `.gitignore`: Pre-configured to ignore media outputs, environment folders, and 