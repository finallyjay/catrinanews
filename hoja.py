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
import re
import time
import urllib.error

os.environ.setdefault("HOJA_MODEL", "gemma3:12b")

import prueba  # noqa: E402  (reads HOJA_MODEL at import)
from fuentes import titulares  # noqa: E402
from mejorada import calavera, rhyme_sounds  # noqa: E402
from prueba import ollama_chat  # noqa: E402
from traduccion import hoja as formato, traducir  # noqa: E402

CATEGORIAS = [
    "móviles y hardware",
    "redes sociales",
    "inteligencia artificial",
    "cripto y finanzas",
    "regulación y multas",
    "apps y suscripciones",
    "ciberseguridad",
    "videojuegos y entretenimiento",
    "comercio y consumo",
    "otros",
]

SELECCION = """Eres el editor de una hoja volante de calaveras literarias, la sátira de Día de Muertos
que la prensa mexicana del siglo XIX dedicaba a los poderosos.

De la lista de titulares, elige los que mejor se prestan a una calavera satírica:
- SÍ: empresas, productos, apps, promesas tecnológicas incumplidas, precios absurdos, modas.
- NO: titulares centrados en una persona concreta con nombre y apellidos.
- NO: muertes reales, enfermedades, violencia, guerras, delitos con víctimas, tragedias.
- NO: noticias positivas sin nada que satirizar (premios, logros científicos).
- Variedad: la hoja necesita temas distintos. Para cada elegido indica primero su categoría
  y después su tema en dos o tres palabras.

Categorías (elige la que mejor describa ESE titular; titulares distintos suelen tener categorías distintas):
- "móviles y hardware": teléfonos, plegables, relojes, gadgets, dispositivos.
- "redes sociales": Instagram, TikTok, X, Facebook, 'me gusta', influencers.
- "inteligencia artificial": modelos de IA, chatbots, promesas de la IA.
- "cripto y finanzas": criptomonedas, bolsa, inversiones, startups que cierran.
- "regulación y multas": multas, leyes, juicios, Bruselas contra las tecnológicas.
- "apps y suscripciones": apps, servicios de pago, precios de suscripciones.
- "ciberseguridad": hackeos, fallos de seguridad, vulnerabilidades, ciberataques.
- "videojuegos y entretenimiento": consolas, juegos, streaming, series.
- "comercio y consumo": tiendas, colas, compras, comercio electrónico.
- "otros": solo si no encaja en ninguna.

Ejemplos: "El iPhone Duo recibe quejas por roturas" → móviles y hardware.
"La mayor multa a Meta por 43 millones de infracciones" → regulación y multas.
"Millones de ciberataques tras un fallo en el 70% de las webs" → ciberseguridad.
Devuelve los números de los elegidos, del más satirizable al menos."""

SCHEMA_SELECCION = {
    "type": "object",
    "properties": {
        "elegidos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "n": {"type": "integer"},
                    "categoria": {"type": "string", "enum": CATEGORIAS},
                    "tema": {"type": "string"},
                    "motivo": {"type": "string"},
                },
                "required": ["n", "categoria", "tema", "motivo"],
            },
        }
    },
    "required": ["elegidos"],
}


# Code-level guard: the model once picked "Porno deepfake: la violencia contra las mujeres…"
# despite the prompt. These are never material for a joke, whatever the model says.
SENSIBLES = re.compile(
    r"violen|víctima|muert|muri|asesin|suicid|abuso|acoso|porno|sexual|guerra|terroris|"
    r"cáncer|enferm|hospital|niñ|menor|secuestr|tirote|atentad",
    re.IGNORECASE,
)


def elegir(items: list[dict], n: int) -> list[dict]:
    lista = "\n".join(f"{i}. {t['titular']}" for i, t in enumerate(items))
    try:
        out = ollama_chat(
            [
                {"role": "system", "content": SELECCION},
                {"role": "user", "content": f"{lista}\n\nElige como máximo {n + 6}. Motivo de una frase corta."},
            ],
            SCHEMA_SELECCION,
            max_tokens=1600,  # a list with reasons doesn't fit in the 300 used for a stanza
            temperature=0.2,  # an editor's pick, not a creative one
        )
    except (json.JSONDecodeError, KeyError, urllib.error.URLError):
        return []
    picks = out.get("elegidos", [])
    # If every pick got the same category, the classification is noise (it happened):
    # ignore it and rely on the topic-word check alone.
    usar_categoria = len({e.get("categoria") for e in picks}) > 1
    elegidos, vistos, temas, categorias = [], set(), [], set()
    for e in picks:
        i = e.get("n")
        if not (isinstance(i, int) and 0 <= i < len(items)) or i in vistos:  # the model may invent indices
            continue
        # One headline per category: the model understands that "iPhone Duo" and
        # "foldable phones" are the same story; code enforces that it isn't repeated.
        if SENSIBLES.search(items[i]["titular"]):
            continue
        categoria = e.get("categoria", "otros")
        if usar_categoria and categoria != "otros" and categoria in categorias:
            continue
        # Within "otros", fall back to topics that share a meaningful word.
        palabras = {w for w in e.get("tema", "").lower().split() if len(w) >= 3}
        if palabras and any(palabras & t for t in temas):
            continue
        vistos.add(i)
        categorias.add(categoria)
        temas.append(palabras)
        elegidos.append({**items[i], "tema": e.get("tema", ""), "categoria": categoria, "motivo": e.get("motivo", "")})
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
        print(f"  · [{e['categoria']}] ({e['tema']}) {e['titular']}  <{e['fuente']}>")

    hoja, usadas = [], set()
    for e in elegidos:
        r = calavera(e["titular"], args.k, frozenset(usadas))
        versos = r["best"]["versos"]
        usadas.update(rhyme_sounds(versos, r["best"]["res"]))  # each calavera must find fresh rhyme sounds
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
