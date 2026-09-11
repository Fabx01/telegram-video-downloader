#!/usr/bin/env python3
"""Download media from a Telegram message link using the user's account."""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


PROJECT_DIR = Path(__file__).resolve().parent
ENV_FILE = PROJECT_DIR / ".env"
DEFAULT_LINKS_DIR = PROJECT_DIR / "links"


@dataclass(frozen=True)
class TelegramLink:
    chat: str | int
    message_id: int
    private_channel_id: int | None = None


@dataclass(frozen=True)
class LinkItem:
    link: TelegramLink
    source: str


@dataclass(frozen=True)
class DownloadResult:
    path: Path
    skipped: bool = False


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
    def __init__(self, label: str) -> None:
        self.label = label
        self.last_update = 0.0

    def __call__(self, current: int, total: int) -> None:
        now = time.monotonic()
        if current != total and now - self.last_update < 0.2:
            return
        self.last_update = now
        percent = current / total * 100 if total else 0
        print(
            f"\r{self.label} Baixando: {percent:6.2f}% "
            f"({human_size(current)} / {human_size(total)})",
            end="",
            flush=True,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Baixa mídias do Telegram. Sem LINK, lê automaticamente links/*.txt."
        ),
    )
    parser.add_argument(
        "links",
        nargs="*",
        metavar="LINK",
        help="um ou mais links de mensagens do Telegram",
    )
    parser.add_argument(
        "-f",
        "--links-file",
        action="append",
        type=Path,
        default=[],
        help="arquivo com um link por linha; pode ser repetido",
    )
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


def read_link_file(
    path: Path,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise RuntimeError(f"não foi possível ler {path}: {exc}") from exc

    active: list[tuple[str, str]] = []
    paused: list[tuple[str, str]] = []
    pause_reached = False
    for line_number, line in enumerate(lines, start=1):
        value = line.strip()
        if not value or value.startswith("#"):
            continue

        directive = value.split("#", maxsplit=1)[0].strip().casefold()
        if directive == "!pause":
            pause_reached = True
            continue

        target = paused if pause_reached else active
        target.append((value, f"{path}:{line_number}"))

    return active, paused


def collect_links(
    args: argparse.Namespace,
) -> tuple[list[LinkItem], int, list[Path], int]:
    raw_links = [
        (value, f"argumento {position}")
        for position, value in enumerate(args.links, start=1)
    ]
    paused_raw_links: list[tuple[str, str]] = []
    files = list(args.links_file)

    if not raw_links and not files:
        DEFAULT_LINKS_DIR.mkdir(parents=True, exist_ok=True)
        files = sorted(DEFAULT_LINKS_DIR.glob("*.txt"))
        if not files:
            links_file = DEFAULT_LINKS_DIR / "links.txt"
            try:
                links_file.write_text(
                    "# Cole um link de mensagem do Telegram por linha.\n"
                    "# Linhas vazias e linhas iniciadas com # são ignoradas.\n"
                    "# Use !pause para adiar todos os links abaixo dele.\n",
                    encoding="utf-8",
                )
            except OSError as exc:
                raise RuntimeError(
                    f"não foi possível criar o arquivo de links: {exc}"
                ) from exc
            raise ValueError(
                f"nenhum link informado. O arquivo {links_file} foi criado; "
                "adicione um link por linha e execute novamente"
            )

    for path in files:
        active_from_file, paused_from_file = read_link_file(path)
        raw_links.extend(active_from_file)
        paused_raw_links.extend(paused_from_file)

    if not raw_links and not paused_raw_links:
        file_names = ", ".join(str(path) for path in files)
        raise ValueError(
            f"nenhum link encontrado em {file_names}. "
            "Adicione um link de mensagem por linha e execute novamente"
        )

    items: list[LinkItem] = []
    seen: set[tuple[str, int]] = set()
    rejected = 0
    for raw_link, source in raw_links:
        try:
            link = parse_telegram_link(raw_link)
        except ValueError as exc:
            print(f"Aviso: link ignorado em {source}: {exc}", file=sys.stderr)
            rejected += 1
            continue

        key = (str(link.chat), link.message_id)
        if key in seen:
            print(f"Aviso: link duplicado ignorado em {source}", file=sys.stderr)
            continue
        seen.add(key)
        items.append(LinkItem(link=link, source=source))

    paused_count = 0
    paused_seen = set(seen)
    for raw_link, source in paused_raw_links:
        try:
            link = parse_telegram_link(raw_link)
        except ValueError as exc:
            print(
                f"Aviso: entrada pausada inválida em {source}: {exc}",
                file=sys.stderr,
            )
            continue

        key = (str(link.chat), link.message_id)
        if key in paused_seen:
            print(
                f"Aviso: link pausado duplicado ignorado em {source}",
                file=sys.stderr,
            )
            continue
        paused_seen.add(key)
        paused_count += 1

    if not items and not paused_count:
        raise ValueError("nenhum link válido foi encontrado")
    return items, rejected, files, paused_count


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


def safe_filename(value: str) -> str:
    name = Path(value).name
    name = re.sub(r"[^\w.()\[\] -]+", "_", name, flags=re.UNICODE).strip(" .")
    return name or "media"


def output_path_for(message, link: TelegramLink, output_dir: Path) -> Path:
    file_info = getattr(message, "file", None)
    original_name = getattr(file_info, "name", None)
    extension = getattr(file_info, "ext", None) or ""
    media_name = safe_filename(original_name or f"media{extension}")
    chat_id = link.private_channel_id or str(link.chat).lstrip("@")
    prefix = safe_filename(f"chat_{chat_id}_msg_{link.message_id}")
    return output_dir / f"{prefix}_{media_name}"


async def resolve_entity(client, link: TelegramLink, cache: dict[str, object]):
    cache_key = str(link.chat)
    if cache_key in cache:
        return cache[cache_key]

    if link.private_channel_id is not None:
        entity = await find_private_chat(client, int(link.chat))
        if entity is None:
            raise RuntimeError(
                "a conversa privada não foi encontrada. Confirme que esta conta "
                "participa dela e que o link abre no Telegram"
            )
    else:
        entity = await client.get_entity(link.chat)

    cache[cache_key] = entity
    return entity


async def download_one(
    client,
    args: argparse.Namespace,
    item: LinkItem,
    position: int,
    total: int,
    entity_cache: dict[str, object],
) -> DownloadResult:
    link = item.link
    label = f"[{position}/{total}]"
    entity = await resolve_entity(client, link, entity_cache)
    message = await client.get_messages(entity, ids=link.message_id)
    if message is None:
        raise RuntimeError("mensagem não encontrada ou sem acesso")
    if not message.media:
        raise RuntimeError("a mensagem não contém mídia para baixar")

    output_path = output_path_for(message, link, args.output.resolve())
    expected_size = getattr(getattr(message, "file", None), "size", None)
    if (
        output_path.is_file()
        and expected_size
        and output_path.stat().st_size == expected_size
    ):
        print(f"{label} Já existe, ignorado: {output_path.name}")
        return DownloadResult(path=output_path, skipped=True)

    chat_title = getattr(entity, "title", link.chat)
    print(f"{label} {chat_title} | mensagem {link.message_id}")
    result = await client.download_media(
        message,
        file=str(output_path),
        progress_callback=ProgressPrinter(label),
    )
    print()
    if not result:
        raise RuntimeError("o Telegram não retornou um arquivo para essa mensagem")
    return DownloadResult(path=Path(result))


async def download_all(
    args: argparse.Namespace,
    items: list[LinkItem],
    rejected: int,
) -> tuple[int, int, int]:
    try:
        from telethon import TelegramClient
        from telethon.errors import RPCError
    except ImportError as exc:
        raise RuntimeError(
            "Telethon não está instalado. Execute: pip install -r requirements.txt"
        ) from exc

    if not args.api_id or not args.api_hash:
        raise ValueError(
            "preencha TELEGRAM_API_ID e TELEGRAM_API_HASH no .env ou use "
            "--api-id e --api-hash"
        )
    try:
        api_id = int(args.api_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("TELEGRAM_API_ID deve ser um número válido") from exc

    args.output.mkdir(parents=True, exist_ok=True)
    args.session.parent.mkdir(parents=True, exist_ok=True)

    client = TelegramClient(str(args.session), api_id, args.api_hash)
    completed = 0
    skipped = 0
    failed = rejected
    entity_cache: dict[str, object] = {}
    try:
        try:
            await client.start()
        except RPCError as exc:
            raise RuntimeError(f"erro de autenticação no Telegram: {exc}") from exc

        total = len(items)
        for position, item in enumerate(items, start=1):
            try:
                result = await download_one(
                    client,
                    args,
                    item,
                    position,
                    total,
                    entity_cache,
                )
            except Exception as exc:
                print(
                    f"[{position}/{total}] Falha ({item.source}): {exc}",
                    file=sys.stderr,
                )
                failed += 1
                continue

            if result.skipped:
                skipped += 1
            else:
                completed += 1
    except RPCError as exc:
        raise RuntimeError(f"erro retornado pelo Telegram: {exc}") from exc
    finally:
        await client.disconnect()

    return completed, skipped, failed


def main() -> int:
    try:
        load_environment()
        parser = build_parser()
        args = parser.parse_args()
        items, rejected, files, paused = collect_links(args)
        if files:
            print(
                f"Encontrados {len(items) + paused} link(s) válido(s) em "
                f"{len(files)} arquivo(s): {len(items)} na fila e "
                f"{paused} pausado(s)."
            )
        else:
            print(f"Recebidos {len(items)} link(s) válido(s).")
        if items:
            completed, skipped, failed = asyncio.run(
                download_all(args, items, rejected)
            )
        else:
            completed, skipped, failed = 0, 0, rejected
    except (ValueError, RuntimeError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nDownload interrompido.", file=sys.stderr)
        return 130

    print(
        f"Resumo: {completed} baixado(s), {skipped} já existente(s), "
        f"{paused} pausado(s), {failed} falha(s)."
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
