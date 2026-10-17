"""Pure validation and intake for uploaded WhatsApp ZIP archives."""

import stat
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath, PureWindowsPath
from zipfile import BadZipFile, ZipFile, ZipInfo

UNSAFE_ARCHIVE = "The ZIP archive is invalid or contains an unsafe entry."
CHAT_FILE_REQUIRED = "The ZIP archive must contain exactly one chat text file."


@dataclass(frozen=True)
class ArchiveIntake:
    chat_bytes: bytes
    attachment_basenames: tuple[str, ...]


def _safe_path(info: ZipInfo) -> PurePosixPath:
    original = info.orig_filename
    normalized = original.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        "\x00" in original
        or not normalized
        or normalized.startswith("/")
        or PureWindowsPath(original).drive
        or any(part in {"", ".", ".."} for part in normalized.split("/"))
    ):
        raise ValueError(UNSAFE_ARCHIVE)

    mode = info.external_attr >> 16
    file_type = stat.S_IFMT(mode)
    if file_type not in {0, stat.S_IFREG, stat.S_IFDIR} or info.flag_bits & 1:
        raise ValueError(UNSAFE_ARCHIVE)
    return path


def read_whatsapp_zip(data: bytes) -> ArchiveIntake:
    """Return the single chat file and safe root-level attachment names."""

    try:
        with ZipFile(BytesIO(data)) as archive:
            files: list[tuple[ZipInfo, PurePosixPath]] = []
            seen: set[str] = set()
            for info in archive.infolist():
                path = _safe_path(info)
                normalized = path.as_posix()
                if normalized in seen:
                    raise ValueError(UNSAFE_ARCHIVE)
                seen.add(normalized)
                if not info.is_dir():
                    files.append((info, path))

            chats = [(info, path) for info, path in files if path.suffix.lower() == ".txt"]
            if len(chats) != 1:
                raise ValueError(CHAT_FILE_REQUIRED)

            chat_info, chat_path = chats[0]
            chat_bytes = archive.read(chat_info)
            attachments = tuple(
                sorted(
                    path.name
                    for _, path in files
                    if len(path.parts) == 1 and path != chat_path
                )
            )
    except ValueError:
        raise
    except (BadZipFile, RuntimeError, OSError):
        raise ValueError(UNSAFE_ARCHIVE) from None

    return ArchiveIntake(chat_bytes=chat_bytes, attachment_basenames=attachments)
