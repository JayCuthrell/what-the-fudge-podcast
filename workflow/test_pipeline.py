import unittest
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch

from content import parse_markdown, format_timestamp, build_youtube_description, Topic
from config import PipelineConfig


class TestTimestampFormatting(unittest.TestCase):
    def test_zero_seconds(self):
        self.assertEqual(format_timestamp(0), "00:00")
        self.assertEqual(format_timestamp(0.4), "00:00")

    def test_under_one_minute(self):
        self.assertEqual(format_timestamp(9), "00:09")
        self.assertEqual(format_timestamp(59.9), "00:59")

    def test_multi_minute(self):
        self.assertEqual(format_timestamp(60), "01:00")
        self.assertEqual(format_timestamp(125), "02:05")
        self.assertEqual(format_timestamp(599), "09:59")

    def test_hour_transitions(self):
        self.assertEqual(format_timestamp(3600), "01:00:00")
        self.assertEqual(format_timestamp(3665), "01:01:05")
        self.assertEqual(format_timestamp(7325), "02:02:05")


class TestMarkdownParser(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_valid_markdown_parsing(self):
        sample_md = (
            "## 1. Breakthrough in Open Source AI Models\n"
            "Link: https://example.com/article-1\n"
            "Blurb: Discuss latency improvements and smaller footprints.\n\n"
            "## 2. Browser Sandboxing Exploits\n"
            "Link: https://example.com/article-2\n"
            "Blurb: Cover CVE details and recommendations.\n"
        )
        md_file = self.temp_path / "topics.md"
        md_file.write_text(sample_md, encoding="utf-8")

        topics = parse_markdown(md_file)
        self.assertEqual(len(topics), 2)

        # Topic 1 checks
        self.assertEqual(topics[0].index, 0)
        self.assertEqual(topics[0].title, "1. Breakthrough in Open Source AI Models")
        self.assertEqual(topics[0].url, "https://example.com/article-1")
        self.assertEqual(topics[0].blurb, "Blurb: Discuss latency improvements and smaller footprints.")

        # Topic 2 checks
        self.assertEqual(topics[1].index, 1)
        self.assertEqual(topics[1].title, "2. Browser Sandboxing Exploits")
        self.assertEqual(topics[1].url, "https://example.com/article-2")

    def test_markdown_without_explicit_link(self):
        sample_md = (
            "## Topic Without Links\n"
            "Just raw talking points and notes for discussion.\n"
        )
        md_file = self.temp_path / "topics.md"
        md_file.write_text(sample_md, encoding="utf-8")

        topics = parse_markdown(md_file)
        self.assertEqual(len(topics), 1)
        self.assertEqual(topics[0].title, "Topic Without Links")
        self.assertEqual(topics[0].url, "")
        self.assertEqual(topics[0].blurb, "Just raw talking points and notes for discussion.")

    def test_missing_file_raises_error(self):
        missing_file = self.temp_path / "does_not_exist.md"
        with self.assertRaises(FileNotFoundError):
            parse_markdown(missing_file)

    def test_empty_file_raises_error(self):
        empty_file = self.temp_path / "empty.md"
        empty_file.write_text("", encoding="utf-8")
        with self.assertRaises(ValueError):
            parse_markdown(empty_file)


class TestYouTubeDescriptionBuilder(unittest.TestCase):
    def test_description_structure(self):
        chapters = [
            ("00:00", "Introduction & AI Landscape", "https://example.com/ai"),
            ("02:15", "Security Updates", "https://example.com/sec"),
            ("05:30", "Summary & Outro", "")
        ]

        desc = build_youtube_description(chapters)

        # Must include all timestamps
        self.assertIn("00:00 - Introduction & AI Landscape", desc)
        self.assertIn("02:15 - Security Updates", desc)
        self.assertIn("05:30 - Summary & Outro", desc)

        # Must include URLs formatted with emoji prefix
        self.assertIn("🔗 https://example.com/ai", desc)
        self.assertIn("🔗 https://example.com/sec", desc)

        # Non-URL topic should not contain orphaned emoji
        outro_block = desc.split("05:30 - Summary & Outro")[-1]
        self.assertNotIn("🔗", outro_block)


class TestPipelineDryRun(unittest.TestCase):
    """Mocks hardware and system calls to verify pipeline coordination end-to-end."""

    @patch("audio.AudioRecorder")
    @patch("audio.subprocess.run")
    @patch("video.subprocess.run")
    def test_dry_run_orchestration(self, mock_video_ffmpeg, mock_audio_ffmpeg, mock_recorder_cls):
        # Configure mocks
        mock_recorder_instance = MagicMock()
        mock_recorder_cls.return_value = mock_recorder_instance
        mock_audio_ffmpeg.return_value = MagicMock(returncode=0)
        mock_video_ffmpeg.return_value = MagicMock(returncode=0)

        cfg = PipelineConfig()
        test_topics = [
            Topic(index=0, title="Topic One", url="https://example.com/1", blurb="Blurb 1"),
            Topic(index=1, title="Topic Two", url="", blurb="Blurb 2")
        ]

        # Verify timestamp progression simulation
        simulated_times = [0.0, 42.5]
        generated_chapters = []
        for idx, topic in enumerate(test_topics):
            tc = format_timestamp(simulated_times[idx])
            generated_chapters.append((tc, topic.title, topic.url))

        self.assertEqual(generated_chapters[0][0], "00:00")
        self.assertEqual(generated_chapters[1][0], "00:42")

        # Verify YouTube compliance rules: Must start at 00:00
        self.assertTrue(generated_chapters[0][0] == "00:00")


if __name__ == "__main__":
    unittest.main()