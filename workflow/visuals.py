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
    if webcam_pos in ("top-left", "middle-left", "bottom-left"):
        available = [t for t in ("top-left", "middle-left", "bottom-left") if t != webcam_pos]
    elif webcam_pos in ("top-right", "middle-right", "bottom-right"):
        available = [t for t in ("top-right", "middle-right", "bottom-right") if t != webcam_pos]
    else:
        available = ["top-right", "middle-right"]

    resolved_1 = available[0] if len(available) > 0 and cfg.logo_position != "none" else None
    resolved_2 = available[1] if len(available) > 1 and cfg.logo2_position != "none" else None
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

    row, col = grid_map.get(position, (1, 0))
    cam_rect = get_grid_tile(position, cfg.cam_box_w, cfg.cam_box_h, cfg.width, cfg.height)

    if col == 0:
        card_rect = Rect(680, 60, cfg.width - 80, cfg.height - 60)
    elif col == 2:
        card_rect = Rect(80, 60, 1240, cfg.height - 60)
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

    # Outer border bezel
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

    # Apply subtle corner rounding to logo image to match the container
    mask = Image.new("L", logo.size, 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, logo.width, logo.height], radius=14 * scale, fill=255)
    logo.putalpha(mask)

    offset_x = x0 + ((tile_rect.width * scale) - logo.width) // 2
    offset_y = y0 + ((tile_rect.height * scale) - logo.height) // 2
    canvas.paste(logo, (offset_x, offset_y), logo)

def parse_structured_content(raw_blurb: str) -> tuple[str, list[str]]:
    """Splits blurb into a main narrative paragraph and individual bullet points."""
    cleaned = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', raw_blurb.strip())
    parts = cleaned.split("\n\n")

    paragraph = ""
    bullets = []

    for p in parts:
        lines = [l.strip() for l in p.splitlines() if l.strip()]
        if any(l.startswith(('*', '-')) for l in lines):
            for l in lines:
                if l.startswith(('*', '-')):
                    b_text = l.lstrip('*- ').strip()
                    if b_text:
                        bullets.append(b_text)
        else:
            if not paragraph:
                paragraph = " ".join(lines)

    return paragraph, bullets

def render_topic_slide(
    topic: Topic,
    total_topics: int,
    output_path: Path,
    cfg: PipelineConfig,
    position: str = "middle-left"
) -> Path:
    scale = 2
    canvas_w, canvas_h = cfg.width * scale, cfg.height * scale
    img = Image.new("RGB", (canvas_w, canvas_h), cfg.bg_color)
    draw = ImageDraw.Draw(img)

    card_rect, cam_rect = calculate_grid_layout(position, cfg)

    # Scaled typography
    font_meta = _load_font(18 * scale, bold=True)
    font_pill = _load_font(22 * scale, bold=True)
    font_title = _load_font(44 * scale, bold=True)
    font_subhead = _load_font(22 * scale, bold=True)
    font_body = _load_font(24 * scale, bold=False)
    font_url = _load_font(21 * scale, bold=False)

    cx0, cy0 = card_rect.x0 * scale, card_rect.y0 * scale
    cx1, cy1 = card_rect.x1 * scale, card_rect.y1 * scale
    draw.rounded_rectangle([cx0, cy0, cx1, cy1], radius=24 * scale, fill=cfg.card_color)

    # Camera Slot Bezel
    if cam_rect:
        cam_x0, cam_y0 = cam_rect.x0 * scale, cam_rect.y0 * scale
        cam_x1, cam_y1 = cam_rect.x1 * scale, cam_rect.y1 * scale
        draw.rounded_rectangle(
            [cam_x0 - 4 * scale, cam_y0 - 4 * scale, cam_x1 + 4 * scale, cam_y1 + 4 * scale],
            radius=20 * scale,
            outline=cfg.cam_border_color,
            width=3 * scale
        )

    # Logo Tiles with smooth rounded corners
    pos1, pos2 = resolve_unoccupied_tiles(position, cfg)
    if pos1:
        tile1 = get_grid_tile(pos1, cfg.cam_box_w, cfg.cam_box_h, cfg.width, cfg.height)
        draw_logo_tile(img, cfg.logo_path, tile1, cfg, scale=scale)
    if pos2:
        tile2 = get_grid_tile(pos2, cfg.cam_box_w, cfg.cam_box_h, cfg.width, cfg.height)
        draw_logo_tile(img, cfg.logo2_path, tile2, cfg, scale=scale)

    bar_margin = 46 * scale
    usable_w = (cx1 - bar_margin) - (cx0 + bar_margin)
    current_y = cy0 + 30 * scale

    # 1. Episode Header (Title + Date)
    if topic.post_title or topic.post_date:
        if topic.post_date:
            d_bbox = draw.textbbox((0, 0), topic.post_date, font=font_meta)
            draw.text((cx1 - bar_margin - (d_bbox[2] - d_bbox[0]), current_y), topic.post_date, fill=cfg.accent_color_rgb, font=font_meta)

        if topic.post_title:
            max_title_chars = int((card_rect.width - 240) / 11)
            clean_title = (topic.post_title[:max_title_chars] + '...') if len(topic.post_title) > max_title_chars else topic.post_title
            draw.text((cx0 + bar_margin, current_y), clean_title.upper(), fill=cfg.sub_color, font=font_meta)

        current_y += 32 * scale

    # 2. Segmented Progress Bar
    bar_y0 = current_y
    bar_h = 7 * scale
    total_bar_w = usable_w
    gap = 10 * scale
    segment_w = (total_bar_w - (gap * (total_topics - 1))) / total_topics

    for seg_idx in range(total_topics):
        s_start = (cx0 + bar_margin) + seg_idx * (segment_w + gap)
        s_end = s_start + segment_w
        seg_color = cfg.accent_color_rgb if seg_idx <= topic.index else cfg.inactive_seg_color
        draw.rounded_rectangle([s_start, bar_y0, s_end, bar_y0 + bar_h], radius=3 * scale, fill=seg_color)

    current_y = bar_y0 + bar_h + 24 * scale

    # 3. Dynamic Pill Badge
    pill_text = f"TOPIC {topic.index + 1:02d} OF {total_topics:02d}"
    t_bbox = draw.textbbox((0, 0), pill_text, font=font_pill)
    pw = (t_bbox[2] - t_bbox[0]) + (36 * scale)
    ph = (t_bbox[3] - t_bbox[1]) + (18 * scale)

    draw.rounded_rectangle([cx0 + bar_margin, current_y, cx0 + bar_margin + pw, current_y + ph], radius=10 * scale, fill=cfg.accent_color_rgb)
    draw.text((cx0 + bar_margin + 18 * scale, current_y + 8 * scale), pill_text, fill=(255, 255, 255), font=font_pill)
    current_y += ph + 22 * scale

    # 4. Clean Headline (wrapped appropriately)
    wrap_w = max(28, int(usable_w / (26 * scale)))
    wrapped_title = textwrap.wrap(topic.title, width=wrap_w)
    for line in wrapped_title[:3]:
        draw.text((cx0 + bar_margin, current_y), line, fill=cfg.text_color, font=font_title)
        current_y += 56 * scale

    current_y += 16 * scale

    # 5. Content Rendering (Full-width narrative + Key Developments OR 2-column list)
    paragraph, bullets = parse_structured_content(topic.blurb)

    if paragraph and bullets:
        # Full-width narrative paragraph
        for line in textwrap.wrap(paragraph, width=74)[:5]:
            draw.text((cx0 + bar_margin, current_y), line, fill=(200, 205, 215), font=font_body)
            current_y += 38 * scale

        current_y += 18 * scale
        draw.text((cx0 + bar_margin, current_y), "KEY DEVELOPMENTS:", fill=cfg.accent_color_rgb, font=font_subhead)
        current_y += 30 * scale

        # Top 4 link bullets formatted with bold bullets
        for b in bullets[:4]:
            b_wrapped = textwrap.wrap(b, width=70)
            for i, bw in enumerate(b_wrapped[:2]):
                prefix = "• " if i == 0 else "   "
                color = (245, 245, 247) if i == 0 else (180, 185, 195)
                draw.text((cx0 + bar_margin, current_y), prefix + bw, fill=color, font=font_body)
                current_y += 36 * scale
            current_y += 6 * scale

    elif bullets and not paragraph:
        # Two-column layout for financial / M&A deals
        col1 = bullets[:7]
        col2 = bullets[7:14]

        col_w = (usable_w - 40 * scale) // 2
        col1_x = cx0 + bar_margin
        col2_x = cx0 + bar_margin + col_w + 40 * scale

        y_left = current_y
        for b in col1:
            for i, line in enumerate(textwrap.wrap(b, width=34)[:2]):
                prefix = "• " if i == 0 else "   "
                draw.text((col1_x, y_left), prefix + line, fill=(230, 235, 245) if i == 0 else (175, 180, 190), font=font_body)
                y_left += 34 * scale
            y_left += 8 * scale

        y_right = current_y
        for b in col2:
            for i, line in enumerate(textwrap.wrap(b, width=34)[:2]):
                prefix = "• " if i == 0 else "   "
                draw.text((col2_x, y_right), prefix + line, fill=(230, 235, 245) if i == 0 else (175, 180, 190), font=font_body)
                y_right += 34 * scale
            y_right += 8 * scale

    elif paragraph:
        # Prose-only topic
        for line in textwrap.wrap(paragraph, width=74)[:12]:
            draw.text((cx0 + bar_margin, current_y), line, fill=(200, 205, 215), font=font_body)
            current_y += 38 * scale

    # 6. Source Anchor Citation (Compact font ensures complete URL fits without truncation)
    if topic.url:
        max_url_len = int(usable_w / (14 * scale))
        clean_url = (topic.url[:max_url_len] + '...') if len(topic.url) > max_url_len else topic.url
        draw.text((cx0 + bar_margin, cy1 - 45 * scale), f"Source: {clean_url}", fill=cfg.sub_color, font=font_url)

    final_img = img.resize((cfg.width, cfg.height), resample=Image.Resampling.LANCZOS)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_img.save(str(output_path), quality=95)
    return output_path