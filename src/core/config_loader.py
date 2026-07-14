import os
import sys
import json
from decimal import Decimal

def get_resource_path(relative_path: str) -> str:
    """
    Resolve a resource path relative to the directory of the launched program
    (the .exe in packaged mode, or the script in dev), so data folders shipped
    next to it (./src/data, ./data, ./.data) are found without relying on
    PyInstaller's _MEIPASS temp folder.
    """
    # Directory of the launched program (robust to the current working dir).
    candidates = []
    if getattr(sys, "argv", None) and sys.argv:
        candidates.append(os.path.dirname(os.path.abspath(sys.argv[0])))

    # Fallback: resolve relative to this file (two levels up to project root).
    current_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.abspath(os.path.join(current_dir, "..", "..")))

    for base_path in candidates:
        path = os.path.join(base_path, relative_path)
        if os.path.exists(path):
            return path

    # No existing match; return the first candidate's path so callers can report it.
    return os.path.join(candidates[0], relative_path)

_DATA_DIRS = ["src/data", "data", ".data"]

# Module-level cache for all loaded data/*.json files (ponytail: simple in-process cache)
_ALL_CONFIGS: dict | None = None


def _resolve_data_dir() -> str:
    """
    Returns the first existing data directory among src/data, data, .data.
    Falls back to src/data (as resolved by get_resource_path) if none exist yet.
    """
    for rel in _DATA_DIRS:
        path = get_resource_path(rel)
        if os.path.isdir(path):
            return path
    return get_resource_path(_DATA_DIRS[0])


def load_all_configs() -> dict:
    """
    Loads every *.json file in the data directory into a dict keyed by filename
    stem (e.g. 'epf_contribution_rates', 'eis_contribution'). All calculators
    should refer to this single in-memory collection instead of reading files
    individually.
    """
    data_dir = _resolve_data_dir()
    configs: dict = {}
    if not os.path.isdir(data_dir):
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    for fname in sorted(os.listdir(data_dir)):
        if not fname.endswith(".json"):
            continue
        stem = os.path.splitext(fname)[0]
        abs_path = os.path.join(data_dir, fname)
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                configs[stem] = json.load(f)
        except Exception as e:
            print(f"Error reading {abs_path}: {e}", file=sys.stderr)

    return configs


def get_configs(reload: bool = False) -> dict:
    """
    Returns the globally loaded data configs dict, loading it on first access
    or when reload is True.
    """
    global _ALL_CONFIGS
    if _ALL_CONFIGS is None or reload:
        _ALL_CONFIGS = load_all_configs()
    return _ALL_CONFIGS


def get_config(name: str, reload: bool = False):
    """
    Returns the loaded data config for a given file stem (e.g. 'socso_contribution').
    """
    return get_configs(reload).get(name)


def save_all_config(configs: dict | None = None) -> None:
    """
    Saves every entry of the globally loaded configs back to its dedicated
    data file (keyed by filename stem). When configs is omitted, the cached
    global configs are used, so callers editing the in-memory dict (e.g. the
    UI config page) only need to update the relevant entry and call this.
    """
    if configs is None:
        configs = get_configs()

    data_dir = _resolve_data_dir()
    if not os.path.isdir(data_dir):
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    for stem, data in configs.items():
        abs_path = os.path.join(data_dir, f"{stem}.json")
        try:
            with open(abs_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error writing {abs_path}: {e}", file=sys.stderr)
            raise e


def parse_contribution_range(range_str: str):
    """
    Parses range strings like '<=30', '>30;<=50', '>6000' for contributions matching.
    Returns a callable lambda(x) -> bool. x is expected to be a Decimal.
    """
    parts = range_str.split(';')
    conditions = []
    for part in parts:
        part = part.strip()
        if part.startswith(">="):
            val = Decimal(part[2:])
            conditions.append(lambda x, v=val: x >= v)
        elif part.startswith(">"):
            val = Decimal(part[1:])
            conditions.append(lambda x, v=val: x > v)
        elif part.startswith("<="):
            val = Decimal(part[2:])
            conditions.append(lambda x, v=val: x <= v)
        elif part.startswith("<"):
            val = Decimal(part[1:])
            conditions.append(lambda x, v=val: x <= v)
    return lambda x: all(cond(x) for cond in conditions)


