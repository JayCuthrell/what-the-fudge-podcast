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
    # Remove emojis and non-alphanumeric chars (keep spaces and hyphens)
    text = re.sub(r'[^\w\s-]', '', text, flags=re.UNICODE)
    # Lowercase and replace spaces/underscores with hyphens
    slug = re.sub(r'[\s_]+', '-', text.lower().strip())
    # Remove consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')

def format_post_date(date_str: str) -> str:
    """Formats YYYY-MM-DD into 'November 01, 2026'."""
    date_str = str(date_str).strip()
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%B %d, %Y")
    except Exception:
        return date_str

def parse_markdown(filepath: Path) -> List[Topic]:
    if not filepath.exists():
        raise FileNotFoundError(f"Markdown file not found: {filepath}")

    raw_content = filepath.read_text(encoding="utf-8")
    
    # 1. Parse 11ty Frontmatter if present
    post_title = ""
    post_date = ""
    post_permalink = ""
    body = raw_content

    if raw_content.startswith("---"):
        parts = raw_content.split("---", 2)
        if len(parts) >= 3:
            fm_text, body = parts[1], parts[2]
            for line in fm_text.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k = k.strip().lower()
                    v = v.strip().strip('"').strip("'")
                    if k == "title": post_title = v
                    elif k == "date": post_date = v
                    elif k == "permalink": post_permalink = v

    # 2. Strip Liquid / Nunjucks tags like {% youtube "..." %}
    body = re.sub(r'\{%.*?%\}', '', body).strip()

    # 3. Split sections by ##
    sections = re.split(r'\n(?=##\s+)', body)
    topics = []

    for idx, section in enumerate(sections):
        sec = section.strip()
        if not sec.startswith("##"):
            continue
        lines = sec.splitlines()
        raw_heading = lines[0].lstrip('#').strip()

        # Check for explicit 'Link:' line (for legacy topics.md files)
        url_match = re.search(r'https?://[^\s\)]+', "\n".join(lines[1:]))
        explicit_url = url_match.group(0) if url_match else ""

        # Construct 11ty Anchor URL: https://fudge.org/archive/[permalink]#[topic]
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

        # Clean blurb and talking points
        blurb_lines = [l for l in lines[1:] if not l.lower().startswith("link:")]
        blurb = "\n".join(blurb_lines).strip()
        formatted_date = format_post_date(post_date) if post_date else ""

        topics.append(Topic(
            index=idx,
            title=raw_heading,
            url=final_url,
            blurb=blurb,
            post_title=post_title,
            post_date=formatted_date
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