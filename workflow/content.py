import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

@dataclass
class Topic:
    index: int
    title: str
    url: str
    blurb: str

def parse_markdown(filepath: Path) -> List[Topic]:
    if not filepath.exists():
        raise FileNotFoundError(f"Markdown file not found: {filepath}")

    content = filepath.read_text(encoding="utf-8")
    sections = re.split(r'\n(?=##\s+)', content)
    topics = []

    for idx, section in enumerate(sections):
        sec = section.strip()
        if not sec:
            continue
        lines = sec.splitlines()
        title = lines[0].lstrip('#').strip()
        body = "\n".join(lines[1:]).strip()

        url_match = re.search(r'https?://[^\s\)]+', body)
        url = url_match.group(0) if url_match else ""

        blurb_lines = [l for l in lines[1:] if not l.lower().startswith("link:")]
        blurb = "\n".join(blurb_lines).strip()

        topics.append(Topic(index=idx, title=title, url=url, blurb=blurb))

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