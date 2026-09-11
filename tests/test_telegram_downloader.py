import argparse
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from telegram_downloader import collect_links, output_path_for, parse_telegram_link


class TelegramLinkTests(unittest.TestCase):
    def test_private_message_link(self):
        link = parse_telegram_link("https://t.me/c/1234567890/123")

        self.assertEqual(link.chat, -1001234567890)
        self.assertEqual(link.message_id, 123)
        self.assertEqual(link.private_channel_id, 1234567890)

    def test_public_message_link(self):
        link = parse_telegram_link("https://t.me/canal_publico/456")

        self.assertEqual(link.chat, "canal_publico")
        self.assertEqual(link.message_id, 456)

    def test_collects_valid_unique_links_from_file(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            links_file = Path(temporary_dir) / "aulas.txt"
            links_file.write_text(
                "# lista de aulas\n"
                "https://t.me/c/1234567890/101\n"
                "\n"
                "link-invalido\n"
                "https://t.me/c/1234567890/101\n"
                "https://t.me/c/1234567890/102\n",
                encoding="utf-8",
            )
            args = argparse.Namespace(links=[], links_file=[links_file])

            items, rejected, files = collect_links(args)

        self.assertEqual([item.link.message_id for item in items], [101, 102])
        self.assertEqual(rejected, 1)
        self.assertEqual(files, [links_file])

    def test_creates_default_links_file_when_missing(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            links_dir = Path(temporary_dir) / "links"
            args = argparse.Namespace(links=[], links_file=[])

            with patch("telegram_downloader.DEFAULT_LINKS_DIR", links_dir):
                with self.assertRaisesRegex(ValueError, "foi criado"):
                    collect_links(args)

            self.assertTrue((links_dir / "links.txt").is_file())

    def test_explains_when_links_file_has_only_comments(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            links_file = Path(temporary_dir) / "links.txt"
            links_file.write_text("# Nenhum link ainda.\n", encoding="utf-8")
            args = argparse.Namespace(links=[], links_file=[links_file])

            with self.assertRaisesRegex(ValueError, "Adicione um link"):
                collect_links(args)

    def test_output_name_cannot_escape_download_directory(self):
        message = SimpleNamespace(
            file=SimpleNamespace(name="../../Aula 01.mp4", ext=".mp4")
        )
        link = parse_telegram_link("https://t.me/c/1234567890/123")

        output = output_path_for(message, link, Path("downloads"))

        self.assertEqual(
            output,
            Path("downloads/chat_1234567890_msg_123_Aula 01.mp4"),
        )


if __name__ == "__main__":
    unittest.main()
