import os
import sys
import stat
import time
import importlib
from pathlib import Path

import pytest

# Ensure repo root is on sys.path so `import main` works
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def write_file(path: Path, size_bytes: int, content_byte: bytes = b"a") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        remaining = size_bytes
        chunk = content_byte * 8192
        while remaining > 0:
            to_write = chunk if remaining >= len(chunk) else content_byte * remaining
            f.write(to_write)
            remaining -= len(to_write)


def setup_env(monkeypatch, backup_dir: Path, source_dir: Path, max_bytes: int = 1_000_000_000, log_level: str = "INFO"):
    monkeypatch.setenv("BACKUP_STORAGE_DIR", str(backup_dir))
    monkeypatch.setenv("SOURCE_DIR", str(source_dir))
    monkeypatch.setenv("MAX_BACKUP_SIZE", str(max_bytes))
    monkeypatch.setenv("LOG_LEVEL", log_level)


def import_main_after_env():
    if "main" in sys.modules:
        # Ensure fresh import with current env
        return importlib.reload(sys.modules["main"])
    return importlib.import_module("main")


@pytest.fixture
def populated_source(tmp_path: Path):
    # Create a small tree in source
    src = tmp_path / "source"
    (src / "notes").mkdir(parents=True)
    write_file(src / "notes" / "a.txt", 1234)
    write_file(src / "notes" / "b.md", 4321)
    (src / "assets").mkdir()
    write_file(src / "assets" / "img.bin", 10_000)
    return src


def test_aggregate_stats_simple(monkeypatch, tmp_path: Path, populated_source: Path):
    backups = tmp_path / "backups"
    backups.mkdir()

    # Create two existing backup folders with some files
    (backups / "2025-01-01_00-00-00").mkdir()
    write_file(backups / "2025-01-01_00-00-00" / "file1", 2000)
    write_file(backups / "2025-01-01_00-00-00" / "file2", 3000)

    (backups / "2025-01-02_00-00-00").mkdir()
    write_file(backups / "2025-01-02_00-00-00" / "file3", 1500)

    # Also a stray file in root should be counted in total size only
    write_file(backups / "stray.bin", 500)

    setup_env(monkeypatch, backups, populated_source, max_bytes=10_000_000)
    main = import_main_after_env()

    heap, total = main.aggregate_dir_size_stats(str(backups))

    # Expect two dirs in heap
    assert len(heap) == 2
    # Validate tuple structure: (name, size, path)
    names = sorted([h[0] for h in heap])
    assert names == ["2025-01-01_00-00-00", "2025-01-02_00-00-00"]

    # Total should include both backup dirs plus stray file
    sizes_by_dir = {h[0]: h[1] for h in heap}
    assert sizes_by_dir["2025-01-01_00-00-00"] == 2000 + 3000
    assert sizes_by_dir["2025-01-02_00-00-00"] == 1500
    assert total == (2000 + 3000) + 1500 + 500


def test_backup_creates_new_timestamp_dir(monkeypatch, tmp_path: Path, populated_source: Path):
    backups = tmp_path / "backups"
    backups.mkdir()

    # Ensure MAX_BACKUP_SIZE large enough so no eviction occurs
    setup_env(monkeypatch, backups, populated_source, max_bytes=10_000_000, log_level="DEBUG")
    main = import_main_after_env()

    pre_dirs = set(p.name for p in backups.iterdir())
    main.backup()
    post_dirs = set(p.name for p in backups.iterdir())

    new_dirs = sorted(list(post_dirs - pre_dirs))
    assert len(new_dirs) == 1
    new_dir = backups / new_dirs[0]
    assert new_dir.is_dir()

    # Ensure copied content exists
    assert (new_dir / "notes" / "a.txt").exists()
    assert (new_dir / "notes" / "b.md").exists()
    assert (new_dir / "assets" / "img.bin").exists()


def test_backup_eviction_when_over_limit(monkeypatch, tmp_path: Path, populated_source: Path):
    backups = tmp_path / "backups"
    backups.mkdir()

    # Create two existing backups with sizes 5k and 6k
    (backups / "2025-01-01_00-00-00").mkdir()
    write_file(backups / "2025-01-01_00-00-00" / "f1", 5000)
    (backups / "2025-01-02_00-00-00").mkdir()
    write_file(backups / "2025-01-02_00-00-00" / "f2", 6000)

    # Source ~ 15k
    # Set MAX_BACKUP_SIZE to allow keeping only the newest existing backup + new one
    # total existing = 11k, source ~ 14k -> need to evict the oldest (5k) to get under limit ~ (6k + 14k)
    setup_env(monkeypatch, backups, populated_source, max_bytes=22_000)
    main = import_main_after_env()

    main.backup()

    # Oldest should be gone
    assert not (backups / "2025-01-01_00-00-00").exists()
    assert (backups / "2025-01-02_00-00-00").exists()

    # One new timestamp dir exists
    new_dirs = [p for p in backups.iterdir() if p.is_dir() and p.name not in {"2025-01-01_00-00-00", "2025-01-02_00-00-00"}]
    assert len(new_dirs) == 1
    # Contents copied
    assert (new_dirs[0] / "notes" / "a.txt").exists() and (new_dirs[0] / "assets" / "img.bin").exists()
