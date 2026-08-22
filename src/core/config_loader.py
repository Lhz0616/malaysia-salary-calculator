import json
import os
import sys
from decimal import Decimal


def get_resource_path(relative_path: str) -> str:
    """
    Resolve a resource path relative to:
    1. PyInstaller bundled directory (sys._MEIPASS for --onedir embedded assets)
    2. Launched program directory (os.path.dirname(sys.argv[0]) / sys.executable)
    3. Project source root directory (in development mode)
    """
    candidates = []

    # 1. PyInstaller extracted temp folder (for embedded assets / styles / icons)
    if hasattr(sys, "_MEIPASS"):
        candidates.append(getattr(sys, "_MEIPASS"))
        candidates.append(os.path.join(getattr(sys, "_MEIPASS"), "src"))

    # 2. Directory of the launched program (.exe location)
    if getattr(sys, "argv", None) and sys.argv:
        candidates.append(os.path.dirname(os.path.abspath(sys.argv[0])))
    if getattr(sys, "executable", None):
        candidates.append(os.path.dirname(os.path.abspath(sys.executable)))

    # 3. Fallback: resolve relative to this source file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.abspath(os.path.join(current_dir, "..", "..")))
    candidates.append(os.path.abspath(os.path.join(current_dir, "..")))

    # Prepare relative path variations (with and without 'src/' prefix)
    rel_paths = [relative_path]
    if relative_path.startswith("src/") or relative_path.startswith("src\\"):
        rel_paths.append(relative_path[4:])
    else:
        rel_paths.append(os.path.join("src", relative_path))

    for base_path in candidates:
        for rel in rel_paths:
            path = os.path.join(base_path, rel)
            if os.path.exists(path):
                return os.path.normpath(path)

    return os.path.normpath(os.path.join(candidates[0] if candidates else "", relative_path))

_DATA_DIRS = [".data", "data", "src/data"]

# Module-level cache for all loaded data/*.json files (ponytail: simple in-process cache)
_ALL_CONFIGS: dict | None = None


def _resolve_data_dir() -> str:
    """
    Returns the first existing data directory among .data, data, src/data.
    Prioritizes external directories next to the executable so user modifications
    take precedence. Falls back to bundled/dev data directories.
    If none exist yet, returns a path to '.data' next to the executable.
    """
    # 1. Check external data directories next to executable
    exe_dir = None
    if getattr(sys, "argv", None) and sys.argv:
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    elif getattr(sys, "executable", None):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))

    if exe_dir:
        for dirname in [".data", "data", "src/data"]:
            ext_path = os.path.join(exe_dir, dirname)
            if os.path.isdir(ext_path):
                return ext_path

    # 2. Check general resource paths (including _MEIPASS and dev root)
    for rel in _DATA_DIRS:
        path = get_resource_path(rel)
        if os.path.isdir(path):
            return path

    # 3. Default target directory for saving configs
    if exe_dir:
        return os.path.join(exe_dir, ".data")
    return get_resource_path(".data")


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
    os.makedirs(data_dir, exist_ok=True)

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


