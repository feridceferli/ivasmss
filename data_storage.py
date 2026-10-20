"""JSON storage paths for a single bot instance and a persistent disk."""
import json
import os
import tempfile
from pathlib import Path


def data_path(name):
    folder = os.environ.get("DB_FOLDER", "").strip()
    destination = Path(name)
    if folder:
        root = Path(folder).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        destination = root / name
        source = Path(name)
        # Preserve existing local records on the first switch to a mounted disk.
        if not destination.exists() and source.is_file() and source.resolve() != destination:
            with source.open(encoding="utf-8") as stream:
                atomic_save(json.load(stream), destination)
    if name == "required_channels.json":
        # Seed repository-backed requirements at startup without changing other JSON files.
        from required_channels_config import load_channels
        atomic_save(load_channels(destination), destination)
    return str(destination)


def atomic_save(data, filename):
    target = Path(filename)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent,
                                         prefix=target.name + ".", suffix=".tmp", delete=False) as stream:
            temporary = stream.name
            json.dump(data, stream, indent=4, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
