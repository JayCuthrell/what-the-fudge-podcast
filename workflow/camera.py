import subprocess
import time
from pathlib import Path

class WebcamRecorder:
    def __init__(self, output_path: Path, device: str = "default", width: int = 1280, height: int = 720, fps: int = 30):
        self.output_path = output_path
        self.device = device
        self.width = width
        self.height = height
        self.fps = fps
        self.process = None

    def start(self):
        """Launches FFmpeg in the background recording video stream only."""
        cmd = [
            "ffmpeg", "-y",
            "-f", "avfoundation",
            "-framerate", str(self.fps),
            "-video_size", f"{self.width}x{self.height}",
            "-i", f"{self.device}:none",
            "-c:v", "h264_videotoolbox",
            "-b:v", "3500k",
            "-pix_fmt", "yuv420p",
            str(self.output_path)
        ]
        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            print(f"Failed to start camera capture: {e}")
            self.process = None

    def stop(self):
        """Gracefully closes FFmpeg to ensure MP4 headers write cleanly."""
        if not self.process:
            return
        try:
            self.process.communicate(input=b'q', timeout=3)
        except (subprocess.TimeoutExpired, ValueError):
            self.process.terminate()
            self.process.wait()
        self.process = None
        print(f"✓ Webcam stream saved: {self.output_path}")

def generate_mock_webcam_clip(output_path: Path, duration: float, width: int = 1280, height: int = 720):
    """Generates a synthetic test video for dry-run simulation."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"testsrc=size={width}x{height}:rate=30",
        "-t", f"{duration:.2f}",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        str(output_path)
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)