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

def calculate_grid_layout(position: str, cfg: PipelineConfig) -> tuple[Rect, Rect | None]:
    """
    Computes (card_rect, cam_rect) across a 3x3 Rule of Thirds grid.
    Columns: 0-640, 640-1280, 1280-1920
    Rows:    0-360, 360-720,  720-1080
    """
    if position == "none":
        return Rect(160, 140, cfg.width - 160, cfg.height - 140), None

    col_w, row_h = cfg.width // 3, cfg.height // 3
    grid_map = {
        "top-left":      (0, 0), "top-center":    (0, 1), "top-right":     (0, 2),
        "middle-left":   (1, 0), "center":        (1, 1), "middle-right":  (1, 2),
        "bottom-left":   (2, 0), "bottom-center": (2, 1), "bottom-right": (2, 2),
    }

    row, col = grid_map.get(position, (2, 2))

    # Center camera box inside cell
    cam_x0 = col * col_w + (col_w - cfg.cam_box_w) // 2
    cam_y0 = row * row_h + (row_h - cfg.cam_box_h) // 2
    cam_rect = Rect(cam_x0, cam_y0, cam_x0 + cfg.cam_box_w, cam_y0 + cfg.cam_box_h)

    # Shift card to remaining screen area
    if col == 2:  # Camera on Right -> Card occupies Left 2 columns
        card_rect = Rect(80, 100, 1240, cfg.height - 100)
    elif col == 0:  # Camera on Left -> Card occupies Right 2 columns
        card_rect = Rect(680, 100, cfg.width - 80, cfg.height - 100)
    elif row == 0:  # Camera Top-Center -> Card occupies Bottom 2 rows
        card_rect = Rect(120, 380, cfg.width - 120, cfg.height - 100)
    elif row == 2:  # Camera Bottom-Center -> Card occupies Top 2 rows
        card_rect = Rect(120, 100, cfg.width - 120, 700)
    else:  # Center -> Card docks to Left 2/3
        card_rect = Rect(80, 100, 1240, cfg.height - 100)

    return card_rect, cam_rect

def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()

def render_topic_slide(
    topic: Topic,
    total_topics: int,
    output_path: Path,
    cfg: PipelineConfig,
    position: str = "bottom-right"
) -> Path:
    img = Image.new("RGB", (cfg.width, cfg.height), cfg.bg_color)
    draw = ImageDraw.Draw(img)

    card_rect, cam_rect = calculate_grid_layout(position, cfg)

    font_pill = _load_font("/System/Library/Fonts/Helvetica.ttc", 26)
    font_title = _load_font("/System/Library/Fonts/Helvetica.ttc", 50)
    font_url = _load_font("/System/Library/Fonts/Helvetica.ttc", 26)

    # 1. Draw Slide Content Card
    draw.rounded_rectangle(
        [card_rect.x0, card_rect.y0, card_rect.x1, card_rect.y1],
        radius=24,
        fill=cfg.card_color
    )

    # 2. Draw Camera Bezel Slot (if webcam enabled)
    if cam_rect:
        draw.rounded_rectangle(
            [cam_rect.x0 - 4, cam_rect.y0 - 4, cam_rect.x1 + 4, cam_rect.y1 + 4],
            radius=18,
            outline=cfg.cam_border_color,
            width=3
        )

    # 3. Dynamic Segmented Progress Bar (fitted to card width)
    bar_y0 = card_rect.y0 + 36
    bar_height = 6
    bar_x0 = card_rect.x0 + 44
    bar_x1 = card_rect.x1 - 44
    total_bar_w = bar_x1 - bar_x0
    gap = 10
    segment_w = (total_bar_w - (gap * (total_topics - 1))) / total_topics

    for seg_idx in range(total_topics):
        s_start = bar_x0 + seg_idx * (segment_w + gap)
        s_end = s_start + segment_w
        seg_color = cfg.accent_color_rgb if seg_idx <= topic.index else cfg.inactive_seg_color
        draw.rounded_rectangle([s_start, bar_y0, s_end, bar_y0 + bar_height], radius=3, fill=seg_color)

    # 4. Topic Pill Badge
    pill_text = f"TOPIC {topic.index + 1:02d} OF {total_topics:02d}"
    pill_x, pill_y = card_rect.x0 + 44, bar_y0 + 32
    draw.rounded_rectangle([pill_x, pill_y, pill_x + 210, pill_y + 38], radius=10, fill=cfg.accent_color_rgb)
    draw.text((pill_x + 18, pill_y + 6), pill_text, fill=(255, 255, 255), font=font_pill)

    # 5. Dynamically Wrapped Title (scaled to card width)
    wrap_chars = max(24, int((card_rect.width - 100) / 26))
    wrapped = textwrap.wrap(topic.title, width=wrap_chars)
    title_start_y = pill_y + 70
    for i, line in enumerate(wrapped[:4]):
        draw.text((card_rect.x0 + 44, title_start_y + (i * 64)), line, fill=cfg.text_color, font=font_title)

    # 6. Source URL Citation
    if topic.url:
        max_url_len = int(card_rect.width / 18)
        clean_url = (topic.url[:max_url_len] + '...') if len(topic.url) > max_url_len else topic.url
        draw.text((card_rect.x0 + 44, card_rect.y1 - 60), f"Source: {clean_url}", fill=cfg.sub_color, font=font_url)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path))
    return output_path