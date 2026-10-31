import subprocess
from pathlib import Path
import sounddevice as sd
import soundfile as sf
from config import PipelineConfig

class AudioRecorder:
    def __init__(self, output_path: Path, samplerate: int = 44100, channels: int = 1):
        self.output_path = output_path
        self.samplerate = samplerate
        self.channels = channels
        self.recording = False
        self.file = None
        self.stream = None

    def start(self):
        self.recording = True
        self.file = sf.SoundFile(str(self.output_path), mode='w', samplerate=self.samplerate, channels=self.channels)
        self.stream = sd.InputStream(samplerate=self.samplerate, channels=self.channels, callback=self._callback)
        self.stream.start()

    def _callback(self, indata, frames, time_info, status):
        if self.recording:
            self.file.write(indata)

    def stop(self):
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
        if self.file:
            self.file.close()

def normalize_audio(input_path: Path, output_path: Path, cfg: PipelineConfig) -> Path:
    """Normalizes mic recording to -14 LUFS using FFmpeg loudnorm filter."""
    cmd = [
    "ffmpeg", "-y", "-i", str(input_path),
    "-af", f"loudnorm=I={cfg.target_lufs}:LRA={cfg.loudness_range}:TP={cfg.true_peak}",
    "-ar", str(cfg.sample_rate),
    str(output_path)
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"Warning: Audio normalization failed ({e}). Proceeding with unmastered audio.")
        return input_path