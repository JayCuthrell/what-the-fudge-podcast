# What The Fudge - Audiogram Generator 🎙️✨

A high-performance Python script designed to transform podcast audio into branded social media videos with dynamic visual elements. 

## Features

* **Dynamic Waveform Styles**: Support for `mirror` (symmetrical) and `continuous` waveform visualizations.
* **Performance Optimized**: Utilizes an in-memory cache for pre-rendered waveform frames, a reduced number of waveform points, multi-threaded export, and hardware-accelerated encoding (`h264_videotoolbox` on Apple Silicon) to ensure fast exports.
* **Performance Monitoring**: Collects CPU and memory samples during rendering and appends a performance summary to `render_stats.csv`.
* **Test Mode**: A `--test` flag to generate a 10-second preview for rapid iteration and testing.
* **Automatic Sizing**: Background images are automatically resized to 1920px width and center-cropped to a 1080p aspect ratio for consistent output.
* **Smart Output Naming**: Output files follow the pattern `podcast_<style>_optimized.mp4` to easily identify rendered variants.

### Visual Effects

* **Logo Pulse Effect**: A reactive background transformation that pulses in sync with audio intensity (RMS energy).
* **Scrolling Marquee**: An automated header displaying "Now Playing Episode for [Current Date]" with high-visibility path effects.
* **Branded Aesthetics**: Custom color integration using brand-specific orange (#f38c3c) with neon-style glow effects.
* **Performance Optimized**: Utilizes the `Agg` Matplotlib backend for headless rendering and supports multi-threaded exporting.
* **Test Mode**: Option to generate a 10-second preview for rapid iteration.

---

## Installation

1.  **Clone the repository:**
    ```sh
    git clone <your-repo-url>
    cd what-the-fudge-podcast
    ```

2.  **Create and activate a virtual environment:**
    ```sh
    python3 -m venv my_env
    source my_env/bin/activate
    ```

3.  **Install the required dependencies:**
    ```sh
    pip install -r requirements.txt
    ```

A `setup.sh` script is also provided to automate this environment configuration on macOS (zsh).

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

| Flag | Argument | Description | Default |
| :--- | :--- | :--- | :--- |
| `--test` | | Generates a 10-second preview using `ultrafast` encoding. | |
| `--style` | `mirror` or `continuous` | Sets the waveform visualization style. | `mirror` |
| `--enable-pulse` | | Enables the reactive logo pulse effect. | Disabled |

**Example (Test Run with Mirror Style):**

```zsh
python3 audiogram_gen.py audio.m4a background.png --test --style mirror
```

---

## Repository Structure

* `audiogram_gen.py`: Main script containing audio analysis and video compositing logic.
* `requirements.txt`: List of necessary Python dependencies.
* `setup.sh`: Shell script to initialize the `my_env` virtual environment.
* `.gitignore`: Pre-configured to ignore media outputs, environment folders, and logs