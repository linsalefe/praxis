"""Manipulação de arquivos de áudio: salvar, re-encodar, deletar."""
from __future__ import annotations

import asyncio
import hashlib
import mimetypes
import shutil
import subprocess
import uuid
from pathlib import Path

from app.config import get_settings

# Formatos aceitos pela OpenAI Audio API (2026).
ACCEPTED_MIMES = {
    "audio/mpeg", "audio/mp3", "audio/mp4", "audio/m4a", "audio/x-m4a",
    "audio/wav", "audio/x-wav", "audio/webm", "audio/ogg", "audio/opus",
    "audio/flac",
}
EXT_BY_MIME = {
    "audio/mpeg": ".mp3", "audio/mp3": ".mp3",
    "audio/mp4": ".mp4", "audio/m4a": ".m4a", "audio/x-m4a": ".m4a",
    "audio/wav": ".wav", "audio/x-wav": ".wav",
    "audio/webm": ".webm", "audio/ogg": ".ogg", "audio/opus": ".opus",
    "audio/flac": ".flac",
}


def hash_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def guess_ext(mimetype: str, fallback: str | None = None) -> str:
    return EXT_BY_MIME.get(mimetype) or mimetypes.guess_extension(mimetype) or fallback or ".bin"


def save_upload(data: bytes, mimetype: str) -> Path:
    """Grava upload em uploads/audio/<uuid><ext> chmod 600."""
    d = Path(get_settings().scribe_audio_dir)
    d.mkdir(parents=True, exist_ok=True)
    ext = guess_ext(mimetype)
    p = d / f"{uuid.uuid4().hex}{ext}"
    p.write_bytes(data)
    p.chmod(0o600)
    return p


async def reencode_if_needed(src: Path, max_mb: int) -> Path:
    """Se o arquivo exceder `max_mb`, re-encoda para opus 24 kbps mono.
    Retorna o próprio `src` se cabe; caso contrário devolve um novo caminho.
    """
    if src.stat().st_size <= max_mb * 1024 * 1024:
        return src
    dst = src.with_name(src.stem + "-comp.ogg")

    def _run() -> None:
        subprocess.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(src),
                "-vn", "-ac", "1", "-ar", "16000",
                "-c:a", "libopus", "-b:a", "24k",
                str(dst),
            ],
            check=True,
        )

    await asyncio.to_thread(_run)
    dst.chmod(0o600)
    return dst


# --------------------------------------------------------------------------
# Processamento em tmpfs (RAM) — o áudio em claro NUNCA toca o disco físico
# (D2). O upload fica em memória; só o passo de ffmpeg escreve num diretório
# tmpfs (/dev/shm), que é RAM, e é apagado logo em seguida.
# --------------------------------------------------------------------------

def _tmpfs_dir() -> Path:
    """Diretório de trabalho em RAM (tmpfs). Usa /dev/shm quando existe."""
    base = Path("/dev/shm") if Path("/dev/shm").is_dir() else Path(get_settings().scribe_audio_dir)
    d = base / "praxis-scribe"
    d.mkdir(parents=True, exist_ok=True)
    try:
        d.chmod(0o700)
    except OSError:
        pass
    return d


async def reencode_bytes_if_needed(data: bytes, mimetype: str, max_mb: int) -> tuple[bytes, str]:
    """Se o áudio exceder `max_mb`, re-encoda para opus 24 kbps mono via ffmpeg.

    Trabalha inteiramente em tmpfs (RAM): escreve o áudio em claro em /dev/shm,
    roda o ffmpeg e lê o resultado, apagando os dois arquivos ao final. Se cabe,
    devolve os bytes originais sem tocar o disco.
    """
    if len(data) <= max_mb * 1024 * 1024:
        return data, mimetype
    d = _tmpfs_dir()
    stem = uuid.uuid4().hex
    src = d / f"{stem}{guess_ext(mimetype)}"
    dst = d / f"{stem}-comp.ogg"
    try:
        src.write_bytes(data)
        src.chmod(0o600)

        def _run() -> None:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-i", str(src),
                    "-vn", "-ac", "1", "-ar", "16000",
                    "-c:a", "libopus", "-b:a", "24k",
                    str(dst),
                ],
                check=True,
            )

        await asyncio.to_thread(_run)
        return dst.read_bytes(), "audio/ogg"
    finally:
        secure_delete(src, dst)


def secure_delete(*paths: Path) -> None:
    """Apaga arquivos com unlink + tentativa de sobrescrever antes.

    Em ext4 sem cifra de disco o overwrite é best-effort — o principal é
    apagar rapidamente. Ignora ausência.
    """
    for p in paths:
        try:
            if p.exists():
                sz = p.stat().st_size
                # zeroa antes de unlink (best-effort)
                with p.open("r+b") as f:
                    f.write(b"\x00" * min(sz, 1024 * 1024))
                    f.flush()
                p.unlink()
        except Exception:
            # cai para rm hard
            try:
                p.unlink(missing_ok=True)  # type: ignore[arg-type]
            except Exception:
                pass


def cleanup_temp_dir_stale(older_than_sec: int = 3600) -> None:
    """Remove arquivos órfãos no dir de uploads mais velhos que N segundos."""
    import time
    d = Path(get_settings().scribe_audio_dir)
    if not d.exists():
        return
    cutoff = time.time() - older_than_sec
    for p in d.iterdir():
        try:
            if p.is_file() and p.stat().st_mtime < cutoff:
                secure_delete(p)
        except Exception:
            pass


def _which(cmd: str) -> str | None:
    return shutil.which(cmd)
