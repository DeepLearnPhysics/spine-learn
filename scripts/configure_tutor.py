"""Save a Gemini API key locally without putting it in shell history or Git."""

from getpass import getpass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Prompt without echo and write an owner-readable credential file."""
    print("Use a free-tier project key from https://aistudio.google.com/api-keys")
    print("This does not enable billing or change your Google project settings.")
    key = getpass("Gemini API key (hidden): ").strip()
    if not key:
        print("No key entered; nothing changed.")
        return
    path = ROOT / ".gemini-api-key"
    path.touch(mode=0o600, exist_ok=True)
    path.chmod(0o600)
    path.write_text(key + "\n", encoding="utf-8")
    print("Key saved locally. Select Check connection in the lesson companion.")


if __name__ == "__main__":
    main()
