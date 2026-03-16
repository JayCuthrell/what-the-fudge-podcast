import sys
import warnings
import datetime
import argparse
import numpy as np
import librosa
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
from moviepy import VideoClip, AudioFileClip, ImageClip, CompositeVideoClip

warnings.filterwarnings("ignore")

def fig_to_numpy_transparent(fig):
    fig.canvas.draw()
    return np.array(fig.canvas.buffer_rgba())

def create_text_clip(text, color, duration):
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
    speed = 280 
    def scroll_pos(t):
        x_pos = 1920 - (speed * t) % (1920 + txt_clip.w)
        return (x_pos, 45) 
    return txt_clip.with_position(scroll_pos)

def create_audiogram(audio_path, bg_image_path, style="mirror", test_mode=False):
    output_path = f"podcast_{style}_ultimate.mp4"
    now = datetime.datetime.now()
    date_label = f"Now Playing Episode for {now.strftime('%B %d %Y')}"
    brand_orange = '#f38c3c' 
    
    print(f"--- 1. Loading Audio & Analyzing ---")
    audio = AudioFileClip(audio_path)
    duration = min(10, audio.duration) if test_mode else audio.duration
    if test_mode: audio = audio.subclipped(0, duration)
    
    y, sr = librosa.load(audio_path, sr=22050, duration=duration if test_mode else None)
    fps = 24
    hop_length = int(sr / fps)
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop_length)[0]
    if np.max(rms) > 0: rms = (rms / np.max(rms))

    print(f"--- 2. Setting Up Layers ---")
    bg = ImageClip(bg_image_path).with_duration(duration).resized(width=1920)
    if bg.h > 1080: bg = bg.cropped(y_center=bg.h/2, height=1080)
    
    # Waveform Setup
    n_points = 150 
    x_axis = np.linspace(0, 10, n_points)
    y_axis = np.zeros(n_points)
    fig, ax = plt.subplots(figsize=(12, 4), dpi=100, facecolor='none')
    ax.set_facecolor('none')

    if style == "mirror":
        line_main_t, = ax.plot(x_axis, y_axis, color=brand_orange, linewidth=3, zorder=3)
        line_glow_t, = ax.plot(x_axis, y_axis, color=brand_orange, linewidth=9, alpha=0.25, zorder=2)
        line_main_b, = ax.plot(x_axis, -y_axis, color=brand_orange, linewidth=3, zorder=3)
        line_glow_b, = ax.plot(x_axis, -y_axis, color=brand_orange, linewidth=9, alpha=0.25, zorder=2)
        fill_coll = [ax.fill_between(x_axis, -y_axis, y_axis, color=brand_orange, alpha=0.12)]
        ax.set_ylim(-1.5, 1.5)
    else:
        line_main, = ax.plot(x_axis, y_axis, color=brand_orange, linewidth=4)
        line_glow, = ax.plot(x_axis, y_axis, color=brand_orange, linewidth=12, alpha=0.2)
        fill_coll = [ax.fill_between(x_axis, 0, y_axis, color=brand_orange, alpha=0.15)]
        ax.set_ylim(0, 1.5)
    ax.axis('off')
    fig.tight_layout(pad=0)

    def make_wf_frame(t):
        idx = int(t * fps)
        if idx < len(rms):
            new_y = [max(0.01, rms[max(0, min(len(rms)-1, idx + (i - n_points//2)))] * 1.2) for i in range(n_points)]
            fill_coll[0].remove()
            if style == "mirror":
                line_main_t.set_ydata(new_y); line_glow_t.set_ydata(new_y)
                line_main_b.set_ydata([-v for v in new_y]); line_glow_b.set_ydata([-v for v in new_y])
                fill_coll[0] = ax.fill_between(x_axis, [-v for v in new_y], new_y, color=brand_orange, alpha=0.12)
            else:
                line_main.set_ydata(new_y); line_glow.set_ydata(new_y)
                fill_coll[0] = ax.fill_between(x_axis, 0, new_y, color=brand_orange, alpha=0.15)
        return fig_to_numpy_transparent(fig)

    # --- REFINED: Pulse Transform ---
    def pulse_frame(get_frame, t):
        idx = int(t * fps)
        val = rms[idx] if idx < len(rms) else 0
        scale = 1.0 + (val * 0.04) # 4% pulse
        frame = get_frame(t)
        # We manually resize the frame array to avoid ghosting layers
        return ImageClip(frame).resized(scale).with_position("center").get_frame(t)

    # Transform the background to pulse
    pulsing_bg = bg.transform(pulse_frame)

    print(f"--- 3. Compositing Master ---")
    wf_y = 750 if style == "mirror" else 800
    waveform_clip = VideoClip(make_wf_frame, duration=duration).with_position(("center", wf_y))
    scrolling_text = create_text_clip(date_label, brand_orange, duration)
    
    final = CompositeVideoClip([pulsing_bg, scrolling_text, waveform_clip]).with_audio(audio)

    print(f"--- 4. Exporting ---")
    final.write_videofile(output_path, fps=fps, codec="libx264", audio_codec="aac", threads=8, preset="ultrafast")
    plt.close(fig)
    print(f"--- Success! Created {output_path} ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("audio"); parser.add_argument("image")
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--style", choices=["continuous", "mirror"], default="mirror")
    args = parser.parse_args()
    create_audiogram(args.audio, args.image, style=args.style, test_mode=args.test)
