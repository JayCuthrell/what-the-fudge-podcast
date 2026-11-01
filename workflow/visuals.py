import re
import textwrap
from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from config import PipelineConfig
from content import Topic

@dataclass
class Rect:
    x0: int
    y0: int
    x1: int
    y1: int

    @property
    def width(self) -> int:
        return self.x1 - self.x0

    @property
    def height(self) -> int:
        return self.y1 - self.y0

def get_grid_tile(position: str, tile_w: int, tile_h: int, canvas_w: int = 1920, canvas_h: int = 1080) -> Rect:
    col_w, row_h = canvas_w // 3, canvas_h // 3
    grid_map = {
        "top-left":      (0, 0), "top-center":    (0, 1), "top-right":     (0, 2),
        "middle-left":   (1, 0), "center":        (1, 1), "middle-right":  (1, 2),
        "bottom-left":   (2, 0), "bottom-center": (2, 1), "bottom-right": (2, 2),
    }
    row, col = grid_map.get(position, (0, 0))
    x0 = col * col_w + (col_w - tile_w) // 2
    y0 = row * row_h + (row_h - tile_h) // 2
    return Rect(x0, y0, x0 + tile_w, y0 + tile_h)

def resolve_unoccupied_tiles(webcam_pos: str, cfg: PipelineConfig) -> tuple[str | None, str | None]:
    pos1 = cfg.logo_position
    pos2 = cfg.logo2_position

    if webcam_pos in ("top-left", "middle-left", "bottom-left"):
        available = [t for t in ("top-left", "middle-left", "bottom-left") if t != webcam_pos]
    elif webcam_pos in ("top-right", "middle-right", "bottom-right"):
        available = [t for t in ("top-right", "middle-right", "bottom-right") if t != webcam_pos]
    elif webcam_pos == "top-center":
        available = ["top-left", "top-right"]
    elif webcam_pos == "bottom-center":
        available = ["bottom-left", "bottom-right"]
    else:
        available = ["top-right", "middle-right"]

    resolved_1 = None
    if pos1 != "none":
        resolved_1 = available[0] if pos1 == "auto" and len(available) > 0 else (pos1 if pos1 != webcam_pos else None)

    resolved_2 = None
    if pos2 != "none":
        if pos2 == "auto":
            remaining = [t for t in available if t != resolved_1]
            resolved_2 = remaining[0] if remaining else None
        else:
            resolved_2 = pos2 if (pos2 != webcam_pos and pos2 != resolved_1) else None

    return resolved_1, resolved_2

def calculate_grid_layout(position: str, cfg: PipelineConfig) -> tuple[Rect, Rect | None]:
    if position == "none":
        return Rect(140, 60, cfg.width - 140, cfg.height - 60), None

    col_w, row_h = cfg.width // 3, cfg.height // 3
    grid_map = {
        "top-left":      (0, 0), "top-center":    (0, 1), "top-right":     (0, 2),
        "middle-left":   (1, 0), "center":        (1, 1), "middle-right":  (1, 2),
        "bottom-left":   (2, 0), "bottom-center": (2, 1), "bottom-right": (2, 2),
    }

    row, col = grid_map.get(position, (2, 2))
    cam_rect = get_grid_tile(position, cfg.cam_box_w, cfg.cam_box_h, cfg.width, cfg.height)

    if col == 2:
        card_rect = Rect(80, 60, 1240, cfg.height - 60)
    elif col == 0:
        card_rect = Rect(680, 60, cfg.width - 80, cfg.height - 60)
    elif row == 0:
        card_rect = Rect(100, 380, cfg.width - 100, cfg.height - 60)
    elif row == 2:
        card_rect = Rect(100, 60, cfg.width - 100, 700)
    else:
        card_rect = Rect(80, 60, 1240, cfg.height - 60)

    return card_rect, cam_rect

def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFCompact.ttf",
        "/Library/Fonts/Arial.ttf"
    ]
    for path in font_paths:
        try:
            return ImageFont.truetype(path, size, index=1 if bold else 0)
        except Exception:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()

def draw_logo_tile(canvas: Image.Image, logo_path: Path, tile_rect: Rect, cfg: PipelineConfig, scale: int = 1):
    if not logo_path.exists():
        return

    draw = ImageDraw.Draw(canvas)
    x0, y0 = tile_rect.x0 * scale, tile_rect.y0 * scale
    x1, y1 = tile_rect.x1 * scale, tile_rect.y1 * scale

    if cfg.logo_border:
        draw.rounded_rectangle(
            [x0 - 4 * scale, y0 - 4 * scale, x1 + 4 * scale, y1 + 4 * scale],
            radius=20 * scale,
            fill=cfg.logo_card_bg,
            outline=cfg.cam_border_color,
            width=2 * scale
        )

    logo = Image.open(logo_path).convert("RGBA")
    max_w = (tile_rect.width - 32) * scale
    max_h = (tile_rect.height - 32) * scale
    logo.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)

    offset_x = x0 + ((tile_rect.width * scale) - logo.width) // 2
    offset_y = y0 + ((tile_rect.height * scale) - logo.height) // 2
    canvas.paste(logo, (offset_x, offset_y), logo)

def render_topic_slide(
    topic: Topic,
    total_topics: int,
    output_path: Path,
    cfg: PipelineConfig,
    position: str = "bottom-left"
) -> Path:
    scale = 2
    canvas_w, canvas_h = cfg.width * scale, cfg.height * scale
    img = Image.new("RGB", (canvas_w, canvas_h), cfg.bg_color)
    draw = ImageDraw.Draw(img)

    card_rect, cam_rect = calculate_grid_layout(position, cfg)

    # Scaled Fonts
    font_meta = _load_font(18 * scale, bold=True)
    font_pill = _load_font(22 * scale, bold=True)
    font_title = _load_font(48 * scale, bold=True)
    font_blurb = _load_font(26 * scale, bold=False)
    font_url = _load_font(24 * scale, bold=False)

    # 1. Main Card Background
    cx0, cy0 = card_rect.x0 * scale, card_rect.y0 * scale
    cx1, cy1 = card_rect.x1 * scale, card_rect.y1 * scale
    draw.rounded_rectangle([cx0, cy0, cx1, cy1], radius=24 * scale, fill=cfg.card_color)

    # 2. Camera Cutout Bezel
    if cam_rect:
        cam_x0, cam_y0 = cam_rect.x0 * scale, cam_rect.y0 * scale
        cam_x1, cam_y1 = cam_rect.x1 * scale, cam_rect.y1 * scale
        draw.rounded_rectangle(
            [cam_x0 - 4 * scale, cam_y0 - 4 * scale, cam_x1 + 4 * scale, cam_y1 + 4 * scale],
            radius=20 * scale,
            outline=cfg.cam_border_color,
            width=3 * scale
        )

    # 3. Sidebar Logos
    pos1, pos2 = resolve_unoccupied_tiles(position, cfg)
    if pos1:
        tile1 = get_grid_tile(pos1, cfg.cam_box_w, cfg.cam_box_h, cfg.width, cfg.height)
        draw_logo_tile(img, cfg.logo_path, tile1, cfg, scale=scale)
    if pos2:
        tile2 = get_grid_tile(pos2, cfg.cam_box_w, cfg.cam_box_h, cfg.width, cfg.height)
        draw_logo_tile(img, cfg.logo2_path, tile2, cfg, scale=scale)

    bar_margin = 44 * scale
    current_y = cy0 + 28 * scale

    # 4. Top Episode Header (Title + Date)
    if topic.post_title or topic.post_date:
        # Date right aligned
        if topic.post_date:
            d_bbox = draw.textbbox((0, 0), topic.post_date, font=font_meta)
            d_w = d_bbox[2] - d_bbox[0]
            draw.text((cx1 - bar_margin - d_w, current_y), topic.post_date, fill=cfg.accent_color_rgb, font=font_meta)

        # Title left aligned (truncated if too long to prevent date overlap)
        if topic.post_title:
            max_title_chars = int((card_rect.width - 240) / 12)
            clean_title = (topic.post_title[:max_title_chars] + '...') if len(topic.post_title) > max_title_chars else topic.post_title
            draw.text((cx0 + bar_margin, current_y), clean_title.upper(), fill=cfg.sub_color, font=font_meta)

        current_y += 32 * scale

    # 5. Segmented Progress Bar
    bar_y0 = current_y
    bar_h = 7 * scale
    bar_x0 = cx0 + bar_margin
    bar_x1 = cx1 - bar_margin
    total_bar_w = bar_x1 - bar_x0
    gap = 10 * scale
    segment_w = (total_bar_w - (gap * (total_topics - 1))) / total_topics

    for seg_idx in range(total_topics):
        s_start = bar_x0 + seg_idx * (segment_w + gap)
        s_end = s_start + segment_w
        seg_color = cfg.accent_color_rgb if seg_idx <= topic.index else cfg.inactive_seg_color
        draw.rounded_rectangle([s_start, bar_y0, s_end, bar_y0 + bar_h], radius=3 * scale, fill=seg_color)

    # 6. Topic Pill Badge
    pill_text = f"TOPIC {topic.index + 1:02d} OF {total_topics:02d}"
    t_bbox = draw.textbbox((0, 0), pill_text, font=font_pill)
    t_width = t_bbox[2] - t_bbox[0]
    t_height = t_bbox[3] - t_bbox[1]

    pad_h = 20 * scale
    pad_v = 10 * scale
    pill_box_w = t_width + (pad_h * 2)
    pill_box_h = t_height + (pad_v * 2)

    pill_x0 = cx0 + bar_margin
    pill_y0 = bar_y0 + 26 * scale
    pill_x1 = pill_x0 + pill_box_w
    pill_y1 = pill_y0 + pill_box_h

    draw.rounded_rectangle([pill_x0, pill_y0, pill_x1, pill_y1], radius=10 * scale, fill=cfg.accent_color_rgb)
    draw.text((pill_x0 + pad_h, pill_y0 + pad_v - (2 * scale)), pill_text, fill=(255, 255, 255), font=font_pill)

    # 7. Topic Title
    wrap_w = max(26, int((card_rect.width - 100) / 26))
    wrapped_title = textwrap.wrap(topic.title, width=wrap_w)
    current_y = pill_y1 + 26 * scale

    for line in wrapped_title[:3]:
        draw.text((cx0 + bar_margin, current_y), line, fill=cfg.text_color, font=font_title)
        current_y += 62 * scale

    # 8. Discussion Blurb & Bullets (Cleaned of Markdown Link Syntax)
    if topic.blurb:
        blurb_clean = topic.blurb.strip()
        if blurb_clean.lower().startswith("blurb:"):
            blurb_clean = blurb_clean[6:].strip()

        # Convert markdown links [text](url) -> text for display
        blurb_clean = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', blurb_clean)

        wrapped_blurb = textwrap.wrap(blurb_clean, width=max(36, int((card_rect.width - 100) / 16)))
        current_y += 20 * scale
        for line in wrapped_blurb[:5]:
            draw.text((cx0 + bar_margin, current_y), line, fill=(185, 190, 200), font=font_blurb)
            current_y += 42 * scale

    # 9. Source Citation Anchor
    if topic.url:
        max_url_len = int(card_rect.width / 14)
        clean_url = (topic.url[:max_url_len] + '...') if len(topic.url) > max_url_len else topic.url
        draw.text((cx0 + bar_margin, cy1 - 60 * scale), f"Source: {clean_url}", fill=cfg.sub_color, font=font_url)

    final_img = img.resize((cfg.width, cfg.height), resample=Image.Resampling.LANCZOS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(str(output_path), quality=95)
    return output_path