"""Keep machine-specific directories out of persisted solver artifacts."""
from pathlib import Path

_run_root: Path | None = None
_path_keys = {"script", "engine_script", "path", "balanced_model", "path_model",
              "transmission_model", "targets_file", "output_root", "history_path", "directory"}


def set_run_root(path: Path) -> None:
    global _run_root
    _run_root = path.resolve()


def public_data(value, key: str = ""):
    if isinstance(value, dict):
        return {name: public_data(item, str(name)) for name, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [public_data(item, key) for item in value]
    if key in _path_keys and isinstance(value, (str, Path)) and value:
        path = Path(value)
        if key in {"directory", "history_path"} and _run_root:
            try:
                return path.resolve().relative_to(_run_root).as_posix()
            except ValueError:
                pass
        return path.name
    return value
