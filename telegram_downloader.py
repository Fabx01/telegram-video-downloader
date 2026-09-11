#!/usr/bin/env python3
"""Download media from a Telegram message link using the user's account."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


ENV_FILE = Path(__file__).resolve().with_name(".env")


@dataclass(frozen=True)
class TelegramLink:
    chat: str | int
    message_id: int
    private_channel_id: int | None = None


def parse_telegram_link(value: str) -> TelegramLink:
    raw = value.strip()
    if "://" not in raw:
        raw = f"https://{raw}"

    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {
        "t.me",
        "www.t.me",
        "telegram.me",
        "www.telegram.me",
    }:
        raise ValueError("use um link t.me ou telegram.me válido")

    parts = [part for part in parsed.path.split("/") if part]
    if parts and parts[0] == "s":
        parts = parts[1:]

    if parts and parts[0] == "c":
        if len(parts) not in {3, 4} or not parts[-1].isdigit():
            raise ValueError(
                "formato privado esperado: https://t.me/c/ID/MENSAGEM"
            )
        if not parts[1].isdigit() or int(parts[1]) <= 0:
            raise ValueError("o ID do canal privado é inválido")
        channel_id = int(parts[1])
        link = TelegramLink(
            chat=int(f"-100{channel_id}"),
            message_id=int(parts[-1]),
            private_channel_id=channel_id,
        )
    elif parts and parts[0] in {"joinchat", "+"}:
        raise ValueError("esse tipo de link não aponta diretamente para uma mensagem")
    elif len(parts) in {2, 3} and parts[-1].isdigit():
        link = TelegramLink(chat=parts[0], message_id=int(parts[-1]))
    else:
        raise ValueError(
            "formato esperado: https://t.me/c/ID/MENSAGEM ou "
            "https://t.me/USUARIO/MENSAGEM"
        )

    if link.message_id <= 0:
        raise ValueError("o ID da mensagem deve ser maior que zero")
    return link


def human_size(byte_count: int) -> str:
    size = float(byte_count)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


class ProgressPrinter:
    def __init__(self) -> None:
        self.last_update = 0.0

    def __call__(self, current: int, total: int) -> None:
        now = time.monotonic()
        if current != total and now - self.last_update < 0.2:
            return
        self.last_update = now
        percent = current / total * 100 if total else 0
        print(
            f"\rBaixando: {percent:6.2f}% "
            f"({human_size(current)} / {human_size(total)})",
            end="",
            flush=True,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Baixa a mídia de uma mensagem do Telegram.",
    )
    parser.add_argument("link", help="link da mensagem no Telegram")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("downloads"),
        help="pasta de destino (padrão: ./downloads)",
    )
    parser.add_argument(
        "--session",
        type=Path,
        default=Path(".telegram_downloader"),
        help="arquivo local da sessão (padrão: ./.telegram_downloader)",
    )
    parser.add_argument("--api-id", type=int, default=os.getenv("TELEGRAM_API_ID"))
    parser.add_argument("--api-hash", default=os.getenv("TELEGRAM_API_HASH"))
    return parser


def load_environment() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError as exc:
        raise RuntimeError(
            "python-dotenv não está instalado. Execute: pip install -r requirements.txt"
        ) from exc

    load_dotenv(ENV_FILE)


async def find_private_chat(client, peer_id: int):
    from telethon import utils

    async for dialog in client.iter_dialogs():
        if utils.get_peer_id(dialog.entity) == peer_id:
            return dialog.entity
    return None


async def download(args: argparse.Namespace, link: TelegramLink) -> Path:
    try:
        from telethon import TelegramClient
        from telethon.errors import RPCError
    except ImportError as exc:
        raise RuntimeError(
            "Telethon não está instalado. Execute: pip install -r requirements.txt"
        ) from exc

    if not args.api_id or not args.api_hash:
        raise ValueError(
            "defina TELEGRAM_API_ID e TELEGRAM_API_HASH ou use "
            "--api-id e --api-hash"
        )

    args.output.mkdir(parents=True, exist_ok=True)
    args.session.parent.mkdir(parents=True, exist_ok=True)

    client = TelegramClient(str(args.session), int(args.api_id), args.api_hash)
    try:
        await client.start()

        if link.private_channel_id is not None:
            entity = await find_private_chat(client, int(link.chat))
            if entity is None:
                raise RuntimeError(
                    "a conversa privada não foi encontrada. Confirme que esta conta "
                    "participa dela e que o link abre no Telegram"
                )
        else:
            entity = await client.get_entity(link.chat)

        message = await client.get_messages(entity, ids=link.message_id)
        if message is None:
            raise RuntimeError("mensagem não encontrada ou sem acesso")
        if not message.media:
            raise RuntimeError("a mensagem não contém mídia para baixar")

        print(f"Mensagem encontrada no chat: {getattr(entity, 'title', link.chat)}")
        result = await client.download_media(
            message,
            file=str(args.output.resolve()),
            progress_callback=ProgressPrinter(),
        )
        print()
        if not result:
            raise RuntimeError("o Telegram não retornou um arquivo para essa mensagem")
        return Path(result)
    except RPCError as exc:
        raise RuntimeError(f"erro retornado pelo Telegram: {exc}") from exc
    finally:
        await client.disconnect()


def main() -> int:
    try:
        load_environment()
        parser = build_parser()
        args = parser.parse_args()
        link = parse_telegram_link(args.link)
        saved_path = asyncio.run(download(args, link))
    except (ValueError, RuntimeError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nDownload interrompido.", file=sys.stderr)
        return 130

    print(f"Concluído: {saved_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
