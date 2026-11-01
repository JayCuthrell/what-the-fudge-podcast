from dataclasses import dataclass, field
from pathlib import Path

VALID_WEBCAM_POSITIONS = (
    "top-left", "top-center", "top-right",
    "middle-left", "center", "middle-right",
    "bottom-left", "bottom-center", "bottom-right",
    "none"
)

@dataclass(frozen=True)
class PipelineConfig:
    work_dir: Path = Path(".")
    topics_file: Path = Path("topics.md")
    slides_dir: Path = Path("rendered_slides")
    raw_audio_path: Path = Path("raw_recording.wav")
    mastered_audio_path: Path = Path("mastered_recording.wav")
    raw_webcam_path: Path = Path("raw_webcam.mp4")
    output_video_path: Path = Path("final_video.mp4")
    client_secrets_path: Path = Path("client_secrets.json")

    # Brand Graphics
    logo_path: Path = Path("wtf-podcast.png")       # Primary text logo
    logo_position: str = "auto"                    # "auto", specific tile, or "none"
    logo2_path: Path = Path("wtf-badge.png")        # Secondary graphic / illustration badge
    logo2_position: str = "auto"                   # "auto", specific tile, or "none"
    logo_card_bg: tuple = (28, 31, 38)
    logo_border: bool = True

    # Audio Loudness Targets (YouTube Standards)
    target_lufs: float = -14.0
    loudness_range: float = 11.0
    true_peak: float = -1.5
    sample_rate: int = 44100

    # Video Dimensions & Visual Palette
    width: int = 1920
    height: int = 1080
    bg_color: tuple = (18, 20, 24)
    card_color: tuple = (28, 31, 38)
    cam_border_color: tuple = (45, 49, 60)
    accent_color_rgb: tuple = (243, 140, 60)       # #f38c3c
    accent_color_hex: str = "0xf38c3c"
    inactive_seg_color: tuple = (45, 49, 60)
    text_color: tuple = (245, 245, 247)
    sub_color: tuple = (156, 163, 175)

    # Webcam Inset Dimensions
    cam_box_w: int = 560
    cam_box_h: int = 315
    webcam_position: str = "bottom-left"
    webcam_device: str = "2"                       # "2" for iPhone Continuity Camera, "0" for FaceTime HD

    # Encoding
    video_fps: int = 30
    video_bitrate: str = "4000k"
    audio_bitrate: str = "192k"
    youtube_scopes: tuple = field(default_factory=lambda: ("https://www.googleapis.com/auth/youtube.upload",))