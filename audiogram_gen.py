import sys
import time
import os
import csv
import psutil
import warnings
import datetime
import argparse
import numpy as np
import librosa
import tempfile
import subprocess
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
from moviepy import VideoClip, AudioFileClip, ImageClip, CompositeVideoClip

warnings.filterwarnings("ignore")

class PerformanceMonitor:
    def __init__(self, style):
        self.start_time = time.perf_counter()
        self.process = psutil.Process(os.getpid())
        self.style = style
        self.cpu_samples = []
        self.mem_samples = []

    def sample(self):
        """Captures a snapshot of current resource usage."""
        self.cpu_samples.append(psutil.cpu_percent())
        self.mem_samples.append(self.process.memory_info().rss / (1024 * 1024))

    def log_to_csv(self, stats, filename="render_stats.csv"):
        """Logs performance metrics to a CSV file."""
        file_exists = os.path.isfile(filename)
        with open(filename, mode='a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=stats.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(stats)

    def get_report(self, audio_duration):
        """Generates the final performance summary and saves to CSV."""
        end_time = time.perf_counter()
        total_render_time = end_time - self.start_time
        ratio = total_render_time / audio_duration
        
        stats = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "style": self.style,
            "audio_duration_sec": round(audio_duration, 2),
            "render_time_sec": round(total_render_time, 2),
            "render_to_audio_ratio": round(ratio, 2),
            "avg_cpu_percent": round(np.mean(self.cpu_samples), 1) if self.cpu_samples else 0,
            "max_mem_mb": round(np.max(self.mem_samples), 1) if self.mem_samples else 0
        }
        self.log_to_csv(stats)
        return stats

def fig_to_numpy_transparent(fig):
    """Converts a matplotlib figure to a transparent numpy array."""
    fig.canvas.draw()
    return np.array(fig.canvas.buffer_rgba())

def create_text_clip(text, color, duration, scroll=True):
    """Generates a text overlay clip, optionally scrolling or static."""
    fig_txt, ax_txt = plt.subplots(figsize=(20, 1.2), dpi=100, facecolor='none')
    ax_txt.set_facecolor('none')
    txt = ax_txt.text(0.5, 0.5, text, color=color, fontsize=42, fontweight='bold', ha='center', va='center')
    txt.set_path_effects([
        path_effects.withStroke(linewidth=5, foreground='black', alpha=0.8),
        path_effects.Normal()
    ])
    ax_txt.axis('off')
    fig_txt.tight_layout(pad=0)
    text_img = fig_to_numpy_transparent(fig_txt)
    plt.close(fig_txt)
    
    txt_clip = ImageClip(text_img).with_duration(duration)
    
    if scroll:
        speed = 280 
        def scroll_pos(t):
            x_pos = 1920 - (speed * t) % (1920 + txt_clip.w)
            return (x_pos, 45) 
        return txt_clip.with_position(scroll_pos)
    else:
        # Static stamp positioned near the top
        return txt_clip.with_position(("center", 45))

def load_audio_safely(audio_path, sr=22050, duration=None, fast_mode=False):
    """Normalizes audio. Bypasses librosa analysis completely in fast modes."""
    print(f"--- 0. Normalizing Audio to Broadcast Standards (-16 LUFS) ---")
    normalized_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    
    try:
        cmd = [
            "ffmpeg", "-y", "-i", audio_path, 
            "-af", "loudnorm=I=-16:LRA=11:TP=-1.5", 
            "-ar", str(sr), 
            normalized_wav
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        if fast_mode:
            return None, None, normalized_wav

        y, sr_out = librosa.load(normalized_wav, sr=sr, duration=duration)
        return y, sr_out, normalized_wav
        
    except subprocess.CalledProcessError as e:
        print(f"Error during audio normalization: {e}")
        if fast_mode:
            return None, None, audio_path
        y, sr_out = librosa.load(audio_path, sr=sr, duration=duration)
        return y, sr_out, audio_path

def create_audiogram(audio_path, bg_image_path, style="mirror", test_mode=False, fast_render=False, text_only=False, static_text=False):
    if fast_render:
        monitor_style = "fast_static"
    elif text_only and static_text:
        monitor_style = "text_only_static"
    elif text_only:
        monitor_style = "text_only_scroll"
    else:
        monitor_style = style
        
    monitor = PerformanceMonitor(monitor_style)
    
    if fast_render:
        output_path = "podcast_fast_render.mp4"
    elif text_only:
        output_path = "podcast_text_only.mp4"
    else:
        output_path = f"podcast_{style}_optimized.mp4"
        
    now = datetime.datetime.now()
    date_label = f"Now Playing Episode for {now.strftime('%B %d %Y')}"
    brand_orange = '#f38c3c' 
    
    print(f"--- 1. Loading Audio & Analyzing ---")
    duration_to_load = 10 if test_mode else None
    skip_librosa = fast_render or text_only
    y, sr, normalized_audio_path = load_audio_safely(audio_path, sr=22050, duration=duration_to_load, fast_mode=skip_librosa)
    
    audio = AudioFileClip(normalized_audio_path)
    duration = min(10, audio.duration) if test_mode else audio.duration
    if test_mode: audio = audio.subclipped(0, duration)
    
    fps = 24
    bg = ImageClip(bg_image_path).with_duration(duration).resized(width=1920)
    if bg.h > 1080: bg = bg.cropped(y_center=bg.h/2, height=1080)
    
    if fast_render:
        print(f"--- 2 & 3. Skipping Animations for Fast Render ---")
        final = bg.with_audio(audio)
        
    elif text_only:
        print(f"--- 2. Compositing Text Banner Only (Skipping Waveform) ---")
        text_clip = create_text_clip(date_label, brand_orange, duration, scroll=not static_text)
        
        if static_text:
            print(f"--- 2a. Flattening static composite to skip frame rendering ---")
            # Create a temporary 1-second composite to extract a single flattened frame
            temp_comp = CompositeVideoClip([bg.with_duration(1), text_clip.with_duration(1)])
            flattened_frame = temp_comp.get_frame(0)
            
            # Use the flattened frame as a standard ImageClip (renders instantly)
            final = ImageClip(flattened_frame).with_duration(duration).with_audio(audio)
        else:
            final = CompositeVideoClip([bg, text_clip]).with_audio(audio)
        
    else:
        print(f"--- 2. Pre-rendering Waveform Cache ---")
        hop_length = int(sr / fps)
        rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop_length)[0]
        if np.max(rms) > 0: rms = (rms / np.max(rms))

        n_points = 100 
        x_axis = np.linspace(0, 10, n_points)
        fig, ax = plt.subplots(figsize=(12, 4), dpi=80, facecolor='none')
        ax.set_facecolor('none')
        
        waveform_frames = []
        y_zeros = np.zeros(n_points)
        
        if style == "mirror":
            line_main_t, = ax.plot(x_axis, y_zeros, color=brand_orange, linewidth=3, zorder=3)
            line_main_b, = ax.plot(x_axis, -y_zeros, color=brand_orange, linewidth=3, zorder=3)
            fill = ax.fill_between(x_axis, -y_zeros, y_zeros, color=brand_orange, alpha=0.12)
            ax.set_ylim(-1.5, 1.5)
        else:
            line_main, = ax.plot(x_axis, y_zeros, color=brand_orange, linewidth=4)
            fill = ax.fill_between(x_axis, 0, y_zeros, color=brand_orange, alpha=0.15)
            ax.set_ylim(0, 1.5)
        
        ax.axis('off')
        fig.tight_layout(pad=0)

        for idx in range(len(rms)):
            new_y = [max(0.01, rms[max(0, min(len(rms)-1, idx + (i - n_points//2)))] * 1.2) for i in range(n_points)]
            fill.remove()
            if style == "mirror":
                line_main_t.set_ydata(new_y)
                line_main_b.set_ydata([-v for v in new_y])
                fill = ax.fill_between(x_axis, [-v for v in new_y], new_y, color=brand_orange, alpha=0.12)
            else:
                line_main.set_ydata(new_y)
                fill = ax.fill_between(x_axis, 0, new_y, color=brand_orange, alpha=0.15)
            
            waveform_frames.append(fig_to_numpy_transparent(fig))
            if idx % 100 == 0: monitor.sample()
        plt.close(fig)

        print(f"--- 3. Compositing Master (Animations Enabled) ---")
        wf_y = 750 if style == "mirror" else 800
        waveform_clip = VideoClip(lambda t: waveform_frames[min(int(t*fps), len(waveform_frames)-1)], duration=duration).with_position(("center", wf_y))
        
        scrolling_text = create_text_clip(date_label, brand_orange, duration, scroll=True)
        final = CompositeVideoClip([bg, scrolling_text, waveform_clip]).with_audio(audio)

    print(f"--- 4. Exporting with Hardware Acceleration ---")
    final.write_videofile(
        output_path, 
        fps=fps, 
        codec="h264_videotoolbox", 
        audio_codec="aac", 
        bitrate="3000k",           
        threads=8, 
        preset="ultrafast" if test_mode else "medium"
    )
    
    stats = monitor.get_report(duration)
    print(f"\n🚀 Render Ratio: {stats['render_to_audio_ratio']}:1 | Avg CPU: {stats['avg_cpu_percent']}% | Stats saved to render_stats.csv")

    if normalized_audio_path != audio_path and os.path.exists(normalized_audio_path):
        try:
            os.remove(normalized_audio_path)
        except Exception as e:
            print(f"Warning: Could not remove temporary file {normalized_audio_path}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate an audiogram video from an audio file and a background image.")
    parser.add_argument("audio", help="Path to the input audio file (e.g., .m4a, .mp3)")
    parser.add_argument("image", help="Path to the background image file (e.g., .png, .jpg)")
    parser.add_argument("--test", action="store_true", help="Render only the first 10 seconds for quick testing.")
    parser.add_argument("--style", choices=["continuous", "mirror"], default="mirror", help="Waveform animation style.")
    parser.add_argument("--fast-render", action="store_true", help="Skip all animations entirely (static background image only).")
    parser.add_argument("--text-only", action="store_true", help="Skip waveform, render only the text banner.")
    parser.add_argument("--static-text", action="store_true", help="When used with --text-only, stamps the text statically instead of scrolling it.")
    args = parser.parse_args()
    
    create_audiogram(
        args.audio, 
        args.image, 
        style=args.style, 
        test_mode=args.test, 
        fast_render=args.fast_render, 
        text_only=args.text_only,
        static_text=args.static_text
    )