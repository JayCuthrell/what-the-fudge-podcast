import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List

@dataclass
class Topic:
    index: int
    title: str
    url: str
    blurb: str
    post_title: str = ""
    post_date: str = ""

def slugify(text: str) -> str:
    """Converts a heading into a clean anchor slug (stripping emojis/punctuation)."""
    text = re.sub(r'[^\w\s-]', '', text, flags=re.UNICODE)
    slug = re.sub(r'[\s_]+', '-', text.lower().strip())
    return re.sub(r'-+', '-', slug).strip('-')

def strip_emojis(text: str) -> str:
    """Strips leading or embedded emojis so FreeType does not render tofu boxes."""
    emoji_pattern = re.compile(
        r'[\U00010000-\U0010ffff'
        r'\U00002600-\U000027BF'
        r'\U00002300-\U000023FF'
        r'\U00002B50\U0000FE0F]+',
        flags=re.UNICODE
    )
    cleaned = emoji_pattern.sub('', text)
    return re.sub(r'^[^\w\d]+', '', cleaned).strip()

def format_post_date(date_str: str) -> str:
    try:
        dt = datetime.strptime(str(date_str).strip(), "%Y-%m-%d")
        return dt.strftime("%B %d, %Y")
    except Exception:
        return str(date_str).strip()

def parse_markdown(filepath: Path) -> List[Topic]:
    if not filepath.exists():
        raise FileNotFoundError(f"Markdown file not found: {filepath}")

    raw_content = filepath.read_text(encoding="utf-8")
    
    # 1. Parse Frontmatter
    post_title, post_date, post_permalink = "", "", ""
    body = raw_content

    if raw_content.startswith("---"):
        parts = raw_content.split("---", 2)
        if len(parts) >= 3:
            fm_text, body = parts[1], parts[2]
            for line in fm_text.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k, v = k.strip().lower(), v.strip().strip('"').strip("'")
                    if k == "title": post_title = v
                    elif k == "date": post_date = v
                    elif k == "permalink": post_permalink = v

    # 2. Strip newsletter footers (e.g. ### #OpenToWork or trailing ---)
    body = body.split("\n---")[0]
    # Remove HTML / Liquid tags
    body = re.sub(r'<custom-youtube.*?>.*?</custom-youtube>', '', body, flags=re.DOTALL)
    body = re.sub(r'\{%.*?%\}', '', body).strip()

    # 3. Split sections by ##
    raw_sections = re.split(r'\n(?=##\s+)', body)
    valid_sections = [s.strip() for s in raw_sections if s.strip().startswith("##")]
    
    topics = []
    # FIX: Enumerate over valid_sections only to guarantee 0-indexed count
    for topic_idx, section in enumerate(valid_sections):
        lines = section.splitlines()
        raw_heading = lines[0].lstrip('#').strip()
        clean_heading = strip_emojis(raw_heading)

        # 4. Construct Anchor URL
        url_match = re.search(r'https?://[^\s\)]+', "\n".join(lines[1:]))
        explicit_url = url_match.group(0) if url_match else ""

        if post_permalink:
            clean_slug = slugify(raw_heading)
            permalink_clean = post_permalink.strip().strip("/")
            if permalink_clean.startswith("archive/"):
                base_path = permalink_clean
            elif permalink_clean:
                base_path = f"archive/{permalink_clean}"
            else:
                base_path = "archive"
            final_url = f"https://fudge.org/{base_path}/#{clean_slug}"
        else:
            final_url = explicit_url

        # Exclude sub-headings (###) from speaking blurb
        blurb_lines = []
        for line in lines[1:]:
            if line.strip().startswith("###"):
                break
            if not line.lower().startswith("link:"):
                blurb_lines.append(line)

        topics.append(Topic(
            index=topic_idx,
            title=clean_heading,
            url=final_url,
            blurb="\n".join(blurb_lines).strip(),
            post_title=post_title,
            post_date=format_post_date(post_date) if post_date else ""
        ))

    if not topics:
        raise ValueError(f"No valid '## Topic' headers found in {filepath}")
    return topics

def format_timestamp(seconds: float) -> str:
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

def build_youtube_description(chapters: list[tuple[str, str, str]]) -> str:
    lines = ["Episode Chapters & Referenced Links:\n"]
    for tc, title, url in chapters:
        lines.append(f"{tc} - {title}")
        if url:
            lines.append(f"🔗 {url}")
        lines.append("")
    return "\n".join(lines).strip()