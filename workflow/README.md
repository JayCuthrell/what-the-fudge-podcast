# What The Fudge (WTF) Podcast Automation Pipeline

An automated Python production and YouTube publishing pipeline engineered for macOS (Apple Silicon). The system directly ingests 11ty Markdown blog posts, dynamically renders supersampled slides on a classic Rule of Thirds grid, records microphone and webcam feeds, masters broadcast audio to YouTube loudness standards (-14 LUFS), composites final video via Apple Silicon hardware acceleration (`h264_videotoolbox`), publishes to YouTube with timed chapter markers, and writes the resulting YouTube Video ID directly back to the 11ty post.

---

## Key Features

* **11ty Blog Post Ingestion (`--file` / `-f`):** Reads native 11ty Markdown files (e.g., `wtf-031.md`), parses YAML frontmatter (`title`, `date`, `permalink`), strips Liquid/HTML embed shortcodes, and auto-generates deep-link anchor URLs pointing to `[https://fudge.org/archive/](https://fudge.org/archive/)[permalink]#[topic]`.


* **Adaptive Rule of Thirds Layout Engine:** Divides a 1920×1080 canvas into 9 cells (640×360 px each). Slide content cards, headlines, segmented progress bars, and citations dynamically reflow depending on where the camera is placed.


* **Dual Brand Graphic Support:** Unoccupied tiles in the sidebar automatically host podcast logos (`logo_path` and `logo2_path`). Logos are masked with matching corner radiuses to align with container bezels.


* **Supersampled High-Density Typography:** Renders slide visuals at 2× resolution (3840×2160) and downsamples with Lanczos filtering to eliminate text compression halos and chroma bleed.


* **Hybrid Content Layouts:**
* *Mixed Editorial:* Displays full-width macro narrative paragraphs followed by a dedicated `"KEY DEVELOPMENTS:"` bullet list.


* *Deals & M&A Lists:* Automatically formats bullet-only sections (such as funding rounds and acquisitions) into a balanced two-column grid.




* **Hardware-Accelerated Inset Webcam:** Captures raw video from macOS `avfoundation` devices (FaceTime HD camera or iPhone Continuity Camera) and composites the stream using Apple Silicon's `h264_videotoolbox` encoder.


* **Broadcast Audio Mastering:** Masters audio to **-14.0 LUFS** and **-1.5 dB True Peak** with FFmpeg's `loudnorm` filter.


* **Interactive Terminal Teleprompter:** Prompts pacing with live duration counters, single-key slide transitions (`Space` or `T`), and automatic chapter timestamp tracking.


* **In-Place Markdown Publishing:** Upon upload, automatically updates `<custom-youtube slug="PLACEHOLDER">` and `[https://youtu.be/PLACEHOLDER](https://youtu.be/PLACEHOLDER)` in the original 11ty markdown source with the live YouTube Video ID.



---

## Pipeline Architecture

```
                    +------------------------------------+
                    |   11ty Markdown Post (wtf-XXX.md)  |
                    +------------------------------------+
                                      |
                     [content.py: Frontmatter & Anchors]
                                      |
                                      v
       +--------------------------------------------------------------+
       |                  Rule of Thirds Slide Renderer               |
       |  - 2x Supersampling (3840x2160 -> 1080p Lanczos)             |
       |  - Auto-mapped Logo Tiles + Subtitle & Date Header           |
       |  - Mixed Narrative & 2-Column List Engines                   |
       +--------------------------------------------------------------+
                                      |
       +------------------------------+-------------------------------+
       |                                                              |
       v                                                              v
[audio.py: sounddevice]                                    [camera.py: avfoundation]
Raw Audio (.wav)                                           Raw Webcam (.mp4)
       |                                                              |
       v                                                              |
[FFmpeg: loudnorm Pass]                                               |
Mastered Audio (-14 LUFS / -1.5 dB TP)                                |
       |                                                              |
       +------------------------------+-------------------------------+
                                      |
                                      v
                         [video.py: Hardware Compositor]
                         - Hardware H.264 VideoToolbox
                         - Timeline Progress Bar Runner
                         - Picture-in-Picture Inset Overlay
                                      |
                                      v
                             final_video.mp4
                                      |
                         [uploader.py: YouTube Data API]
                         - Uploads unlisted / public video
                         - Sets title, chapters, and anchor links
                         - Replaces PLACEHOLDER tags in 11ty post

```

---

## Directory Structure

```text
├── audio.py            # Audio recording (sounddevice) and EBU R128 loudness mastering
├── camera.py           # Background macOS avfoundation webcam capture and test pattern generator
├── config.py           # Central dataclass config (palettes, dimensions, audio targets, paths)
├── content.py          # 11ty frontmatter parsing, slugification, and anchor link generation
├── main.py             # CLI orchestration, terminal teleprompter, and recording runner
├── uploader.py         # YouTube OAuth 2.0 authentication, upload, and markdown updater
├── video.py            # FFmpeg concatenation, hardware compositing, and animated progress runner
├── visuals.py          # 2x supersampled PIL graphics engine with Rule of Thirds layout reflow
├── test_pipeline.py    # Unit tests covering parsing, timestamps, descriptions, and mock pipelines
├── requirements.txt    # Python runtime package dependencies
└── client_secrets.json # Google Cloud OAuth 2.0 Desktop Client secret (user-provided)

```

---

## Prerequisites & Installation

### 1. System Requirements

* **Operating System:** macOS Monterey, Ventura, Sonoma, Sequoia, or later (Apple Silicon M-series recommended).


* **System Utilities:** FFmpeg compiled with `videotoolbox` support:


```bash
brew install ffmpeg

```


* **Python:** Python 3.10+ (tested through Python 3.14).



### 2. Environment Setup

Clone the repository and install dependencies inside a dedicated virtual environment:

```bash
git clone https://github.com/your-username/what-the-fudge-podcast.git
cd what-the-fudge-podcast/workflow

python3 -m venv my_env
source my_env/bin/activate

pip install -r requirements.txt

```

`requirements.txt` dependencies:

```text
sounddevice
soundfile
Pillow
google-api-python-client
google-auth-oauthlib

```

### 3. Google Cloud OAuth Setup

1. Open the [Google Cloud Console](https://console.cloud.google.com/) and create a project.
2. Enable the **YouTube Data API v3**.
3. Configure the **OAuth Consent Screen** (User Type: *External*, add your YouTube Google account as a *Test User*).
4. Go to **Credentials > Create Credentials > OAuth client ID** and select **Desktop app**.
5. Download the credentials, rename the file to `client_secrets.json`, and place it in the project root.



---

## Configuration (`config.py`)

All global pipeline parameters are centralized in `config.py`:

```python
@dataclass(frozen=True)
class PipelineConfig:
    # Working Paths
    topics_file: Path = Path("topics.md")
    slides_dir: Path = Path("rendered_slides")
    raw_audio_path: Path = Path("raw_recording.wav")
    mastered_audio_path: Path = Path("mastered_recording.wav")
    raw_webcam_path: Path = Path("raw_webcam.mp4")
    output_video_path: Path = Path("final_video.mp4")
    client_secrets_path: Path = Path("client_secrets.json")

    # Brand Graphics
    logo_path: Path = Path("wtf-podcast.jpg")       # Tile 0: Main wordmark
    logo_position: str = "auto"                    # "auto", grid position, or "none"
    logo2_path: Path = Path("fudge-org.png")       # Tile 6: Secondary badge
    logo2_position: str = "auto"                   # "auto", grid position, or "none"
    logo_card_bg: tuple = (28, 31, 38)
    logo_border: bool = True

    # Audio Loudness Targets (EBU R128 / YouTube)
    target_lufs: float = -14.0
    loudness_range: float = 11.0
    true_peak: float = -1.5
    sample_rate: int = 44100

    # Video & Theme Dimensions
    width: int = 1920
    height: int = 1080
    bg_color: tuple = (18, 20, 24)
    card_color: tuple = (28, 31, 38)
    accent_color_rgb: tuple = (243, 140, 60)       # #f38c3c Orange
    accent_color_hex: str = "0xf38c3c"
    inactive_seg_color: tuple = (45, 49, 60)
    text_color: tuple = (245, 245, 247)
    sub_color: tuple = (156, 163, 175)

    # Inset Camera Dimensions (560x315 inside 640x360 cell)
    cam_box_w: int = 560
    cam_box_h: int = 315
    webcam_position: str = "middle-left"
    webcam_device: str = "2"                       # "2" for iPhone Continuity Camera, "0" for FaceTime HD

    # Encoding
    video_fps: int = 30
    video_bitrate: str = "4000k"
    audio_bitrate: str = "192k"

```

To determine available camera indexes on macOS, run:

```bash
ffmpeg -f avfoundation -list_devices true -i ""

```

---

## 11ty Blog Post Format

The parser handles native 11ty posts directly. Markdown files should follow this structure:

```markdown
---
title: "What The Fudge for November 1, 2026: The $3T Capex Reckoning, Credit Tightening, and Enterprise Flows"
permalink: "/archive/wtf-031/"
description: "A look at the market fallout from Big Tech capex and credit tightening."
date: 2026-11-01
tags: [WTF]
---

<custom-youtube slug="PLACEHOLDER"></custom-youtube>

Subscribe and Listen: [https://youtu.be/PLACEHOLDER](https://youtu.be/PLACEHOLDER)

## 🎙️ The $3 Trillion Capex Reckoning

The bill for frontier infrastructure has arrived in public earnings... and public markets are delivering an immediate reality check. Alphabet, Meta, Microsoft, Amazon, and Oracle now have a collective $3 trillion committed to AI spending over the coming cycle.

* [Alphabet, Meta, Microsoft, Amazon, and Oracle have a collective $3T+ in AI spending commitments](https://www.techmeme.com/...)
* [Alphabet reports Q3 negative free cash flow of $9.07B, worse than expected](https://www.techmeme.com/...)

## 📍 Field Report: The Neocloud Credit Squeeze

The tightening is moving down the stack into private debt markets. Specialized neocloud operators that scaled rapidly on debt-financed clusters are suddenly encountering strict capital discipline.

* [Sources: neoclouds CoreWeave, Nebius, and Nscale have effectively been shut out of the bond market](https://www.techmeme.com/...)

## 💰 M&A Funding, and Capital Flows

* Salesforce, the cloud software pioneer, agreed to acquire Rune for [$375M](https://www.techmeme.com/...).
* OpenAI, the frontier AI research company, raised [~$11B pre-IPO round](https://www.techmeme.com/...).
* Baseten, the AI model serving infrastructure platform, raised [~$2B venture round](https://www.techmeme.com/...).

```

---

## Usage Guide

### CLI Options

| Flag | Short | Default | Description |
| --- | --- | --- | --- |
| `--file` | `-f` | `config.topics_file` | Path to 11ty markdown post or local topics file (supports `~`). |
| `--dry-run` |  | `False` | Simulates the session without microphone, webcam, or YouTube upload. |
| `--auto-advance` |  | `None` | Automatically transitions slides every $N$ seconds (hands-free testing). |
| `--webcam` |  | `False` | Enables webcam capture and compositing into the chosen grid block. |
| `--webcam-pos` |  | `bottom-left` | Anchors camera to one of 9 Rule of Thirds cells. |

Valid `--webcam-pos` options:
`top-left`, `top-center`, `top-right`, `middle-left`, `center`, `middle-right`, `bottom-left`, `bottom-center`, `bottom-right`, `none`.

---

### Workflow Examples

#### 1. Dry Run / Layout Review

Test slide rendering, 2-column lists, and branding without opening audio devices or uploading to YouTube:

```bash
python3 main.py \
  --file ~/github/fudge-org-eleventy-excellent-4.3.3/src/posts/podcast/wtf-031.md \
  --dry-run \
  --webcam \
  --webcam-pos middle-left \
  --auto-advance 2.0

```

Check generated slides inside `rendered_slides/slide_*.png` to verify typography, padding, and logo placement.

#### 2. Live Recording Session

Run the teleprompter with live camera and microphone recording:

```bash
python3 main.py \
  --file ~/github/fudge-org-eleventy-excellent-4.3.3/src/posts/podcast/wtf-031.md \
  --webcam \
  --webcam-pos middle-left

```

* **Start:** Press `Enter` to arm the audio and video recorders.
* **Transition:** Tap `Space` or `T` when finished speaking on a topic to advance the slide and register a timestamp.


* **Finish:** Tap `Space` or `T` on the final topic to complete the recording.



#### 3. Upload & In-Place 11ty Update

When prompted with `Upload to YouTube? (y/n):`:

1. Type `y`.
2. The uploader completes the OAuth handshake, caches the token in `token.json`, and uploads `final_video.mp4`.


3. The video title and description (complete with clickable timestamp chapters and anchor URLs) are populated.


4. The script scans the Markdown source file and replaces `slug="PLACEHOLDER"` and `youtu.be/PLACEHOLDER` with the live YouTube Video ID.


5. Commit and deploy the post:
```bash
git add src/posts/podcast/wtf-031.md
git commit -m "publish(podcast): wtf-031 video embed"
git push

```



---

## Testing

Run the automated test suite to verify Markdown parsing, timestamp formatting, description compilation, and pipeline orchestration:

```bash
python3 -m unittest -v test_pipeline.py

```

All 10 tests should pass cleanly:

```text
test_empty_file_raises_error (test_pipeline.TestMarkdownParser) ... ok
test_markdown_without_explicit_link (test_pipeline.TestMarkdownParser) ... ok
test_missing_file_raises_error (test_pipeline.TestMarkdownParser) ... ok
test_valid_markdown_parsing (test_pipeline.TestMarkdownParser) ... ok
test_dry_run_orchestration (test_pipeline.TestPipelineDryRun) ... ok
test_hour_transitions (test_pipeline.TestTimestampFormatting) ... ok
test_multi_minute (test_pipeline.TestTimestampFormatting) ... ok
test_under_one_minute (test_pipeline.TestTimestampFormatting) ... ok
test_zero_seconds (test_pipeline.TestTimestampFormatting) ... ok
test_description_structure (test_pipeline.TestYouTubeDescriptionBuilder) ... ok

```