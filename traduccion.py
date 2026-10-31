"""Line-by-line English gloss for each calavera.

The Spanish stays the original (that's where the rhyme is verified); the
English is a plain, line-aligned translation so non-Spanish readers get the joke.

Usage (adds translations to an existing results file and prints the sheet):
  python3 traduccion.py resultados_mejorada_gemma3_12b.json
"""

import json
import sys
import urllib.error

from prueba import ollama_chat

SCHEMA = {
    "type": "object",
    "properties": {"lines": {"type": "array", "items": {"type": "string"}}},
    "required": ["lines"],
}

SYSTEM = """You translate Mexican calaveras literarias (satirical Day of the Dead verses) into English.
Translate line by line: exactly one English line per Spanish line, same order.
Keep the meaning and the joke; do not try to rhyme. Keep names of Death as they are
(la Flaca, la Catrina, la Huesuda)."""


def traducir(versos: list[str]) -> list[str]:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": "\n".join(versos)},
    ]
    for _ in range(2):
        try:
            lines = ollama_chat(messages, SCHEMA).get("lines", [])
        except (json.JSONDecodeError, KeyError, urllib.error.URLError):
            continue
        lines = [ln.strip() for item in lines for ln in item.split("\n") if ln.strip()]
        if len(lines) == len(versos):
            return lines
    return []  # better no gloss than a misaligned one


def hoja(versos: list[str], lines: list[str]) -> str:
    width = max((len(v) for v in versos), default=0) + 4
    if not lines:
        return "\n".join(versos)
    return "\n".join(f"{v:<{width}}{e}" for v, e in zip(versos, lines))


def main() -> None:
    path = sys.argv[1]
    with open(path) as f:
        runs = json.load(f)
    for r in runs:
        versos = r["best"]["versos"]
        r["best"]["english"] = traducir(versos)
        print(f"— {r['titular']}")
        print(hoja(versos, r["best"]["english"]))
        print()
    with open(path, "w") as f:
        json.dump(runs, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
