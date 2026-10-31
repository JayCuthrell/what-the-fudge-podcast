import subprocess
from pathlib import Path
from typing import List, Tuple
from config import PipelineConfig
from visuals import calculate_grid_layout

def assemble_final_video(
    audio_file: Path,
    slide_records: List[Tuple[Path, float]],
    total_duration: float,
    output_video: Path,
    cfg: PipelineConfig,
    webcam_video: Path = None,
    webcam_position: str = "bottom-right"
) -> Path:
    concat_file = output_video.parent / "concat_script.tmp"

    with open(concat_file, "w") as f:
        for i in range(len(slide_records)):
            img_path, start_t = slide_records[i]
            duration = (slide_records[i + 1][1] - start_t) if i < len(slide_records) - 1 else max(total_duration - start_t, 2.0)
            f.write(f"file '{img_path.resolve()}'\n")
            f.write(f"duration {duration:.2f}\n")
        f.write(f"file '{slide_records[-1][0].resolve()}'\n")

    _, cam_rect = calculate_grid_layout(webcam_position, cfg)
    use_cam_overlay = webcam_video and webcam_video.exists() and cam_rect is not None
    
    # Safeguard against division by zero in the FFmpeg filter graph
    safe_duration = max(total_duration, 1.0)

    if use_cam_overlay:
        # Scale webcam, overlay onto background slide, then draw the bottom progress runner
        filter_graph = (
            f"[1:v]scale={cfg.cam_box_w}:{cfg.cam_box_h}:force_original_aspect_ratio=increase,"
            f"crop={cfg.cam_box_w}:{cfg.cam_box_h}[cam];"
            f"[0:v][cam]overlay={cam_rect.x0}:{cam_rect.y0}:eof_action=pass[composed];"
            f"[composed]drawbox=x=0:y=ih-8:w='iw*(t/{safe_duration:.2f})':h=8:color={cfg.accent_color_hex}:t=fill,"
            f"fps={cfg.video_fps},format=yuv420p[outv]"
        )
        input_args = [
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-i", str(webcam_video),
            "-i", str(audio_file)
        ]
        map_args = ["-map", "[outv]", "-map", "2:a"]
    else:
        # Draw bottom progress runner only
        filter_graph = (
            f"fps={cfg.video_fps},"
            f"drawbox=x=0:y=ih-8:w='iw*(t/{safe_duration:.2f})':h=8:color={cfg.accent_color_hex}:t=fill,"
            f"format=yuv420p"
        )
        input_args = [
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-i", str(audio_file)
        ]
        map_args = ["-map", "0:v", "-map", "1:a"]

    cmd = [
        "ffmpeg", "-y",
        *input_args,
        "-filter_complex" if use_cam_overlay else "-vf", filter_graph,
        *map_args,
        "-c:v", "h264_videotoolbox",
        "-b:v", cfg.video_bitrate,
        "-c:a", "aac", "-b:a", cfg.audio_bitrate,
        "-shortest", str(output_video)
    ]

    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except subprocess.CalledProcessError:
        print("Hardware encoder failed; falling back to libx264...")
        idx = cmd.index("h264_videotoolbox")
        cmd[idx] = "libx264"
        cmd.insert(idx + 1, "-preset")
        cmd.insert(idx + 2, "veryfast")
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    finally:
        if concat_file.exists():
            concat_file.unlink()

    return output_video