import argparse
import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock

from telegram_downloader import collect_links, output_path_for, parse_telegram_link
from telegram_downloader import build_parser, PROJECT_DIR, download_one, LinkItem


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

            items, rejected, files, paused = collect_links(args)

        self.assertEqual([item.link.message_id for item in items], [101, 102])
        self.assertEqual(rejected, 1)
        self.assertEqual(files, [links_file])
        self.assertEqual(paused, 0)

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

    def test_pause_is_independent_for_each_links_file(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            directory = Path(temporary_dir)
            redes = directory / "redes.txt"
            logica = directory / "logica.txt"
            redes.write_text(
                "https://t.me/c/1234567890/101\n"
                "!pause # continuar depois\n"
                "https://t.me/c/1234567890/102\n"
                "https://t.me/c/1234567890/103\n",
                encoding="utf-8",
            )
            logica.write_text(
                "https://t.me/c/1234567890/201\n"
                "https://t.me/c/1234567890/202\n"
                "https://t.me/c/1234567890/203\n"
                "https://t.me/c/1234567890/204\n"
                "!PAUSE\n"
                "https://t.me/c/1234567890/205\n",
                encoding="utf-8",
            )
            args = argparse.Namespace(links=[], links_file=[redes, logica])

            items, rejected, files, paused = collect_links(args)

        self.assertEqual(
            [item.link.message_id for item in items],
            [101, 201, 202, 203, 204],
        )
        self.assertEqual(rejected, 0)
        self.assertEqual(files, [redes, logica])
        self.assertEqual(paused, 3)

    def test_file_can_pause_all_downloads(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            links_file = Path(temporary_dir) / "links.txt"
            links_file.write_text(
                "!pause\nhttps://t.me/c/1234567890/101\n",
                encoding="utf-8",
            )
            args = argparse.Namespace(links=[], links_file=[links_file])

            items, rejected, files, paused = collect_links(args)

        self.assertEqual(items, [])
        self.assertEqual(rejected, 0)
        self.assertEqual(files, [links_file])
        self.assertEqual(paused, 1)

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


class DownloadTests(unittest.IsolatedAsyncioTestCase):
    def test_paths_are_anchored_to_project(self):
        args = build_parser().parse_args([])
        self.assertEqual(args.output, PROJECT_DIR / "downloads")
        self.assertEqual(args.session, PROJECT_DIR / ".telegram_downloader")
        args = build_parser().parse_args(["--output", "videos", "--session", "sessions/test"])
        self.assertEqual(args.output, PROJECT_DIR / "videos")
        self.assertEqual(args.session, PROJECT_DIR / "sessions/test")

    async def test_partial_files_are_replaced_or_removed(self):
        for outcome in ("success", "failure", "cancel", "truncated"):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as tmp:
                args = argparse.Namespace(output=Path(tmp))
                link = parse_telegram_link("https://t.me/example/123")
                item = LinkItem(link, "test")
                message = SimpleNamespace(media=True, file=SimpleNamespace(name="video.mp4", size=4, ext=".mp4"))
                destination = output_path_for(message, link, args.output)
                partial = destination.with_name(destination.name + ".part")
                destination.write_bytes(b"old")
                partial.write_bytes(b"stale partial data")
                client = SimpleNamespace(get_messages=AsyncMock(return_value=message))

                async def transfer(message, file, progress_callback):
                    self.assertFalse(destination.exists())
                    file.write(b"done" if outcome == "success" else b"x")
                    if outcome == "failure":
                        raise OSError("connection lost")
                    if outcome == "cancel":
                        raise asyncio.CancelledError()
                    return file

                client.download_media = AsyncMock(side_effect=transfer)
                with patch("telegram_downloader.resolve_entity", new=AsyncMock(return_value=SimpleNamespace(title="Test"))):
                    if outcome == "success":
                        result = await download_one(client, args, item, 1, 1, {})
                        self.assertEqual(result.path, destination)
                        self.assertEqual(destination.read_bytes(), b"done")
                    else:
                        error = {"failure": OSError, "cancel": asyncio.CancelledError, "truncated": RuntimeError}[outcome]
                        with self.assertRaises(error):
                            await download_one(client, args, item, 1, 1, {})
                        self.assertFalse(destination.exists())
                self.assertFalse(partial.exists())

    async def test_complete_file_is_kept_and_stale_partial_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = argparse.Namespace(output=Path(tmp))
            link = parse_telegram_link("https://t.me/example/123")
            message = SimpleNamespace(media=True, file=SimpleNamespace(name="video.mp4", size=4, ext=".mp4"))
            destination = output_path_for(message, link, args.output)
            partial = destination.with_name(destination.name + ".part")
            destination.write_bytes(b"done")
            partial.write_bytes(b"x")
            client = SimpleNamespace(get_messages=AsyncMock(return_value=message), download_media=AsyncMock())
            with patch("telegram_downloader.resolve_entity", new=AsyncMock(return_value=SimpleNamespace(title="Test"))):
                result = await download_one(client, args, LinkItem(link, "test"), 1, 1, {})
            self.assertTrue(result.skipped)
            self.assertEqual(destination.read_bytes(), b"done")
            self.assertFalse(partial.exists())
            client.download_media.assert_not_called()


if __name__ == "__main__":
    unittest.main()
