import argparse
import os
import sys
import time
import tty
import termios

from config import PipelineConfig, VALID_WEBCAM_POSITIONS
from content import parse_markdown, format_timestamp, build_youtube_description
from audio import AudioRecorder, normalize_audio
from camera import WebcamRecorder, generate_mock_webcam_clip
from visuals import render_topic_slide
from video import assemble_final_video
from uploader import YouTubeUploader

def wait_for_key(allowed=('t', ' ')):
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while True:
            char = sys.stdin.read(1)
            if char.lower() in allowed or char in ('\r', '\n'):
                return char.lower()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

def run(dry_run: bool = False, auto_interval: float = None, enable_webcam: bool = False, webcam_pos: str = "bottom-right"):
    cfg = PipelineConfig()

    try:
        topics = parse_markdown(cfg.topics_file)
    except Exception as e:
        sys.exit(f"Error parsing Markdown: {e}")

    actual_cam_pos = webcam_pos if enable_webcam else "none"

    # Step 1: Pre-render slides adapted to the chosen grid position
    print(f"\n[1/5] Pre-rendering {len(topics)} slides (Layout: {actual_cam_pos})...")
    slide_paths = []
    for t in topics:
        slide_out = cfg.slides_dir / f"slide_{t.index:02d}.png"
        render_topic_slide(t, len(topics), slide_out, cfg, position=actual_cam_pos)
        slide_paths.append(slide_out)
    print("✓ Adaptive slide layout ready.")

    # Step 2: Initialize Recorders
    audio_rec = AudioRecorder(cfg.raw_audio_path, samplerate=cfg.sample_rate) if not dry_run else None
    cam_rec = WebcamRecorder(cfg.raw_webcam_path, device=cfg.webcam_device) if (enable_webcam and not dry_run) else None

    slide_records = []
    chapters = []

    os.system("clear")
    print("=" * 65)
    print(f" PODCAST TELEPROMPTER | Webcam: {actual_cam_pos.upper()}")
    print("=" * 65)

    if auto_interval:
        print(f"Auto-advancing every {auto_interval:.1f}s...")
        time.sleep(1.5)
    else:
        print("Tap [SPACE] or [T] to transition slides and log timestamps.")
        print("Press [ENTER] to start recording...")
        sys.stdin.readline()

    if audio_rec:
        audio_rec.start()
    if cam_rec:
        cam_rec.start()

    start_time = time.time()

    for idx, item in enumerate(topics):
        current_time = 0.0 if idx == 0 else (time.time() - start_time)
        tc_str = format_timestamp(current_time)

        slide_records.append((slide_paths[idx], current_time))
        chapters.append((tc_str, item.title, item.url))

        os.system("clear")
        print("=" * 65)
        print(f" TOPIC {idx + 1} OF {len(topics)} | Marker: {tc_str} | Layout: {actual_cam_pos}")
        print("=" * 65)
        print(f"\nTITLE: {item.title}\n")
        if item.url:
            print(f"LINK:  {item.url}\n")
        print(f"BLURB:\n{item.blurb}\n")
        print("-" * 65)

        if idx < len(topics) - 1:
            if auto_interval:
                time.sleep(auto_interval)
            else:
                print("👉 Tap [T] or [SPACE] for next topic...")
                wait_for_key(('t', ' '))
        else:
            if auto_interval:
                time.sleep(auto_interval)
            else:
                print("🏁 Final topic. Tap [T] or [SPACE] to finish...")
                wait_for_key(('t', ' '))

    if cam_rec:
        cam_rec.stop()
    if audio_rec:
        audio_rec.stop()

    total_duration = time.time() - start_time
    print(f"\n[2/5] Session ended. Duration: {format_timestamp(total_duration)}")

    # Step 3: Loudness Normalization Pass
    active_audio = cfg.raw_audio_path
    if not dry_run:
        print("\n[3/5] Mastering audio to -14 LUFS...")
        active_audio = normalize_audio(cfg.raw_audio_path, cfg.mastered_audio_path, cfg)
    else:
        print("\n[3/5] [DRY RUN] Skipping audio mastering.")

    # Step 4: Video Compilation
    active_webcam = cfg.raw_webcam_path if enable_webcam else None
    if dry_run and enable_webcam:
        print("Generating mock video feed for dry run...")
        generate_mock_webcam_clip(cfg.raw_webcam_path, total_duration)
        active_webcam = cfg.raw_webcam_path

    if not dry_run:
        print(f"\n[4/5] Compositing video (Picture-in-Picture: {actual_cam_pos})...")
        try:
            video_file = assemble_final_video(
                audio_file=active_audio,
                slide_records=slide_records,
                total_duration=total_duration,
                output_video=cfg.output_video_path,
                cfg=cfg,
                webcam_video=active_webcam,
                webcam_position=actual_cam_pos
            )
            print(f"✓ Video ready: {video_file}")
        except Exception as e:
            print(f"Video assembly failed: {e}")
            return
    else:
        print("[4/5] [DRY RUN] Skipping final FFmpeg export.")
        video_file = cfg.output_video_path

    # Step 5: Description & Upload
    description = build_youtube_description(chapters)
    print("\n[5/5] --- YouTube Description ---")
    print(description)
    print("--------------------------------\n")

    if not dry_run and input("Upload to YouTube? (y/n): ").strip().lower() == 'y':
        uploader = YouTubeUploader(cfg)
        vid_id = uploader.upload(video_file, f"Discussion: {topics[0].title}", description)
        print(f"\n🚀 Live at: https://youtu.be/{vid_id}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Podcast Teleprompter with Rule-of-Thirds Webcam Inset")
    parser.add_argument("--dry-run", action="store_true", help="Run without microphone or YouTube upload.")
    parser.add_argument("--auto-advance", type=float, metavar="SEC", help="Hands-free advance interval.")
    parser.add_argument("--webcam", action="store_true", help="Enable webcam overlay inside a Rule-of-Thirds block.")
    parser.add_argument(
        "--webcam-pos",
        choices=VALID_WEBCAM_POSITIONS,
        default="bottom-right",
        help="Specify which of the 9 Rule of Thirds cells to anchor the camera (default: bottom-right)."
    )
    args = parser.parse_args()

    run(
        dry_run=args.dry_run,
        auto_interval=args.auto_advance,
        enable_webcam=args.webcam,
        webcam_pos=args.webcam_pos
    )