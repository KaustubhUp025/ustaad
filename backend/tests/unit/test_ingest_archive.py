import stat
from io import BytesIO
from zipfile import ZipFile, ZipInfo

import pytest

from jobs.ingest.archive import CHAT_FILE_REQUIRED, UNSAFE_ARCHIVE, read_whatsapp_zip
from jobs.ingest.parse import parse_chat


def synthetic_zip(entries: list[tuple[str | ZipInfo, bytes]]) -> bytes:
    archive = BytesIO()
    with ZipFile(archive, "w") as output:
        for name, content in entries:
            output.writestr(name, content)
    return archive.getvalue()


def zip_with_nul_name() -> bytes:
    archive = synthetic_zip([("badname.txt", b"synthetic")])
    return archive.replace(b"badname.txt", b"bad\x00ame.txt")


def test_android_export_returns_chat_bytes_and_only_safe_root_attachments():
    chat = (
        b"16/10/26, 9:00 am - Asha: voice.opus (file attached)\n"
        b"16/10/26, 9:01 am - Dev: missing.jpg (file attached)"
    )
    intake = read_whatsapp_zip(
        synthetic_zip(
            [
                ("group-history.txt", chat),
                ("voice.opus", b"synthetic audio"),
                ("nested/photo.jpg", b"synthetic nested image"),
            ]
        )
    )

    assert intake.chat_bytes == chat
    assert intake.attachment_basenames == ("voice.opus",)
    parsed = parse_chat(intake.chat_bytes, archive_filenames=intake.attachment_basenames)
    assert parsed.messages[0].attachment.available is True
    assert parsed.messages[1].attachment.available is False


@pytest.mark.parametrize(
    "unsafe_name",
    [
        "/absolute.txt",
        "../traversal.txt",
        "safe/../../traversal.txt",
        r"..\traversal.txt",
        r"C:\absolute.txt",
    ],
)
def test_unsafe_paths_reject_the_whole_archive(unsafe_name):
    data = synthetic_zip(
        [
            ("chat.txt", b"16/10/26, 9:00 am - Asha: Synthetic"),
            (unsafe_name, b"synthetic unsafe entry"),
        ]
    )

    with pytest.raises(ValueError, match=f"^{UNSAFE_ARCHIVE}$"):
        read_whatsapp_zip(data)


def test_nul_name_and_symlink_reject_the_whole_archive():
    with pytest.raises(ValueError, match=f"^{UNSAFE_ARCHIVE}$"):
        read_whatsapp_zip(zip_with_nul_name())

    symlink = ZipInfo("voice.opus")
    symlink.create_system = 3
    symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
    data = synthetic_zip(
        [
            ("chat.txt", b"16/10/26, 9:00 am - Asha: Synthetic"),
            (symlink, b"target.opus"),
        ]
    )
    with pytest.raises(ValueError, match=f"^{UNSAFE_ARCHIVE}$"):
        read_whatsapp_zip(data)


def test_missing_chat_file_is_rejected_with_fixed_error():
    data = synthetic_zip([("voice.opus", b"synthetic audio")])

    with pytest.raises(ValueError, match=f"^{CHAT_FILE_REQUIRED}$"):
        read_whatsapp_zip(data)


def test_multiple_chat_files_are_rejected_regardless_of_names():
    data = synthetic_zip(
        [
            ("first.txt", b"16/10/26, 9:00 am - Asha: First"),
            ("renamed-history.TXT", b"16/10/26, 9:01 am - Dev: Second"),
        ]
    )

    with pytest.raises(ValueError, match=f"^{CHAT_FILE_REQUIRED}$"):
        read_whatsapp_zip(data)
