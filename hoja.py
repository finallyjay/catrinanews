"""Today's sheet: real headlines → pick the satirizable ones → calaveras → English gloss.

Usage:
  python3 hoja.py                    # El País tech + Google News, 5 calaveras, gemma3:12b
  python3 hoja.py --fuente elpais --n 3 --k 2
  HOJA_MODEL=gemma3:4b python3 hoja.py
"""

import argparse
import datetime
import json
import os
import time
import urllib.error

os.environ.setdefault("HOJA_MODEL", "gemma3:12b")

import prueba  # noqa: E402  (reads HOJA_MODEL at import)
from fuentes import titulares  # noqa: E402
from mejorada import calavera, end_words  # noqa: E402
from prueba import ollama_chat  # noqa: E402
from traduccion import hoja as formato, traducir  # noqa: E402

SELECCION = """Eres el editor de una hoja volante de calaveras literarias, la sátira de Día de Muertos
que la prensa mexicana del siglo XIX dedicaba a los poderosos.

De la lista de titulares, elige los que mejor se prestan a una calavera satírica:
- SÍ: empresas, productos, apps, promesas tecnológicas incumplidas, precios absurdos, modas.
- NO: titulares centrados en una persona concreta con nombre y apellidos.
- NO: muertes reales, enfermedades, violencia, guerras, delitos con víctimas, tragedias.
- NO: noticias positivas sin nada que satirizar (premios, logros científicos).
Devuelve los números de los elegidos, del más satirizable al menos."""

SCHEMA_SELECCION = {
    "type": "object",
    "properties": {
        "elegidos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"n": {"type": "integer"}, "motivo": {"type": "string"}},
                "required": ["n", "motivo"],
            },
        }
    },
    "required": ["elegidos"],
}


def elegir(items: list[dict], n: int) -> list[dict]:
    lista = "\n".join(f"{i}. {t['titular']}" for i, t in enumerate(items))
    try:
        out = ollama_chat(
            [
                {"role": "system", "content": SELECCION},
                {"role": "user", "content": f"{lista}\n\nElige como máximo {n + 3}. Motivo de una frase corta."},
            ],
            SCHEMA_SELECCION,
            max_tokens=1200,  # a list with reasons doesn't fit in the 300 used for a stanza
            temperature=0.2,  # an editor's pick, not a creative one
        )
    except (json.JSONDecodeError, KeyError, urllib.error.URLError):
        return []
    elegidos, vistos = [], set()
    for e in out.get("elegidos", []):
        i = e.get("n")
        if isinstance(i, int) and 0 <= i < len(items) and i not in vistos:  # the model may invent indices
            vistos.add(i)
            elegidos.append({**items[i], "motivo": e.get("motivo", "")})
        if len(elegidos) == n:
            break
    return elegidos


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fuente", choices=["elpais", "google", "ambas"], default="ambas")
    ap.add_argument("--n", type=int, default=5, help="calaveras in the sheet")
    ap.add_argument("--k", type=int, default=3, help="candidates per calavera")
    args = ap.parse_args()
    fuentes = ["elpais", "google"] if args.fuente == "ambas" else [args.fuente]

    t0 = time.time()
    items = titulares(fuentes, limite=25)
    print(f"{len(items)} titulares de {', '.join(fuentes)}")
    elegidos = elegir(items, args.n)
    print(f"Elegidos {len(elegidos)} ({prueba.MODEL}):")
    for e in elegidos:
        print(f"  · {e['titular']}  [{e['fuente']}]  — {e['motivo']}")

    hoja, usadas = [], set()
    for e in elegidos:
        r = calavera(e["titular"], args.k, frozenset(usadas))
        versos = r["best"]["versos"]
        usadas.update(end_words(versos))  # each calavera must find fresh rhymes
        english = traducir(versos) if r["best"]["res"].get("ok") else []
        hoja.append({**e, "versos": versos, "english": english, "check": r["best"]["res"], "segundos": r["seconds"]})
        mark = "✅" if r["best"]["res"].get("ok") else "❌"
        print(f"\n{mark} {e['titular']}  [{e['fuente']}]")
        print(formato(versos, english))

    fecha = datetime.date.today().isoformat()
    out = f"hoja_{fecha}.json"
    with open(out, "w") as f:
        json.dump({"fecha": fecha, "modelo": prueba.MODEL, "calaveras": hoja}, f, ensure_ascii=False, indent=2)
    print(f"\nHoja en {out} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
