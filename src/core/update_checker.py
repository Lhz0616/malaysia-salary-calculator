import json
import urllib.request
import urllib.error
from PySide6.QtCore import QThread, Signal

CURRENT_VERSION = "0.1.0"
DEFAULT_REPO = "Lhz0616/malaysia-salary-calculator"

def parse_version(v_str: str):
    """Clean version string into a tuple of integers for comparison, e.g. 'v1.2.3' -> (1, 2, 3)."""
    v_clean = v_str.lstrip("vV").strip()
    parts = []
    for part in v_clean.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            break
    return tuple(parts)

class UpdateCheckerThread(QThread):
    """
    Background thread to check for new releases on GitHub without blocking the GUI.
    Emits update_available(latest_version, release_url, release_notes) if a newer version exists.
    """
    update_available = Signal(str, str, str)  # (latest_version, release_url, release_notes)

    def __init__(self, repo_slug=DEFAULT_REPO, current_version=CURRENT_VERSION, parent=None):
        super().__init__(parent)
        self.repo_slug = repo_slug
        self.current_version = current_version

    def run(self):
        url = f"https://api.github.com/repos/{self.repo_slug}/releases/latest"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "MalaysianPayrollEngine-UpdateChecker",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    latest_tag = data.get("tag_name", "")
                    release_url = data.get("html_url", f"https://github.com/{self.repo_slug}/releases")
                    release_notes = data.get("body", "")

                    if parse_version(latest_tag) > parse_version(self.current_version):
                        self.update_available.emit(latest_tag, release_url, release_notes)
        except Exception:
            # Quietly fail on network errors or rate-limits so UI experience is uninterrupted
            pass
