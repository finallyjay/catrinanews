"""La Catrina reads the sheet aloud: one ElevenLabs clip per calavera.

Plain REST over urllib (no SDK), like the rest of the project. The key comes from
ELEVENLABS_API_KEY in the environment, or from a .env here or in the parent folder.

Usage:
  python3 voz.py                          # latest hoja_*.json → site/audio/*.mp3
  python3 voz.py hoja_2026-10-31.json --solo 1
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import urllib.request

# Lucia (Soft, Warm, Pleasant): an older voice for the Catrina. Of three voices tried, she
# paused at every line end (6 pauses vs 2 for Laura D), so the rhyme is heard.
VOICE_ID = os.environ.get("HOJA_VOICE", "pPM4mM2SeUKR5pdrzgwS")
MODEL_ID = "eleven_v4"
# A little less stable than a narrator: calaveras are performed, not read.
SETTINGS = {"stability": 0.45, "similarity_boost": 0.75, "style": 0.35}

FUENTES = {"elpais": "El País"}


def api_key() -> str:
    if os.environ.get("ELEVENLABS_API_KEY"):
        return os.environ["ELEVENLABS_API_KEY"]
    for path in (".env", "../.env"):
        if os.path.exists(path):
            for line in open(path):
                if line.startswith("ELEVENLABS_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("ELEVENLABS_API_KEY not found (env, ./.env or ../.env)")


def guion(c: dict) -> str:
    """What the Catrina says: the headline as a newspaper cry, then the verses."""
    fuente = FUENTES.get(c.get("fuente", ""), c.get("fuente", ""))
    versos = "\n".join(c["versos"])
    return f"Según {fuente}: {c['titular']}.\n\n{versos}"


def tts(texto: str, key: str, previo: str | None = None, siguiente: str | None = None) -> bytes:
    body = {"text": texto, "model_id": MODEL_ID, "voice_settings": SETTINGS}
    # Stitching: neighbouring text keeps intonation continuous across clips.
    if previo:
        body["previous_text"] = previo
    if siguiente:
        body["next_text"] = siguiente
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?output_format=mp3_44100_128",
        data=json.dumps(body).encode(),
        headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def normalizar(path: str) -> None:
    """Even loudness across clips (Lucia peaks near 0 dB). Optional: needs ffmpeg."""
    if not shutil.which("ffmpeg"):
        return
    tmp = path + ".tmp.mp3"
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-i", path,
         "-af", "loudnorm=I=-18:TP=-2:LRA=11", "-b:a", "128k", tmp],
        check=True,
    )  # fmt: skip
    os.replace(tmp, path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("hoja", nargs="?", default=None)
    ap.add_argument("--solo", type=int, default=0, help="only the first N calaveras (to test)")
    args = ap.parse_args()
    path = args.hoja or sorted(glob.glob("hoja_*.json"))[-1]
    with open(path) as f:
        data = json.load(f)

    key = api_key()
    calaveras = [c for c in data["calaveras"] if c.get("versos")]
    if args.solo:
        calaveras = calaveras[: args.solo]
    textos = [guion(c) for c in calaveras]
    os.makedirs("site/audio", exist_ok=True)
    for i, (c, texto) in enumerate(zip(calaveras, textos)):
        audio = tts(
            texto, key,
            previo=textos[i - 1] if i > 0 else None,
            siguiente=textos[i + 1] if i + 1 < len(textos) else None,
        )
        nombre = f"audio/calavera-{i + 1:02d}.mp3"
        with open(os.path.join("site", nombre), "wb") as f:
            f.write(audio)
        normalizar(os.path.join("site", nombre))
        c["audio"] = nombre
        print(f"{nombre}  {len(audio) // 1024} KB  {c['titular'][:60]}")

    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
