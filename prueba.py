"""Feasibility test: can a local Gemma write calaveras that actually rhyme?

For each headline, asks Gemma (via Ollama) for a 4-line satirical calavera,
checks it with rima.check_stanza, and retries with feedback when lines 2 and 4
don't rhyme. Compares two prompting strategies:

  libre   the model writes the stanza directly
  pareja  the model first picks the two rhyming end words, then writes

Usage:
  python3 prueba.py                 # both strategies, 4 samples per headline
  python3 prueba.py --n 2 --estrategia pareja
"""

import argparse
import json
import os
import time
import urllib.error
import urllib.request

from rima import check_stanza, consonant_rhyme, rhyme_tail

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("HOJA_MODEL", "gemma3:4b")
MAX_TRIES = 3

# Hand-written, fictional headlines: no API calls spent while we test.
TITULARES = [
    "Una gran tecnológica despide a 10.000 empleados y anuncia beneficios récord",
    "Una red social cobra ahora por el botón de 'me gusta'",
    "La nueva app de inteligencia artificial promete sustituir a los médicos de cabecera",
    "Un fabricante de móviles deja de incluir el cargador y ahora tampoco la batería",
    "Una startup de criptomonedas desaparece con los ahorros de sus clientes",
]

SISTEMA = """Eres un poeta satírico mexicano que escribe calaveras literarias para el Día de Muertos,
en la tradición de la prensa del siglo XIX y de José Guadalupe Posada: versos humorísticos
donde la Muerte (la Flaca, la Catrina, la Huesuda) viene a llevarse a los poderosos.

Reglas:
- Exactamente 4 versos, en español.
- Versos de unas 8 sílabas (octosílabos).
- El verso 2 y el verso 4 DEBEN terminar en palabras que rimen en consonante
  (igual desde la vocal tónica: "capital"/"hospital", "panteón"/"millón").
- La sátira es sobre la empresa o el producto, nunca sobre personas concretas.

Ejemplo:
Estaba el gran empresario
contando su capital,
llegó la Flaca a su lado
y lo mandó al hospital."""

SCHEMA_LIBRE = {
    "type": "object",
    "properties": {"versos": {"type": "array", "items": {"type": "string"}}},
    "required": ["versos"],
}

SCHEMA_PAREJA = {
    "type": "object",
    "properties": {
        "rima": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Two words that rhyme, to end lines 2 and 4",
        },
        "versos": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["rima", "versos"],
}


def ollama_chat(messages: list[dict], schema: dict, max_tokens: int = 300, temperature: float = 0.9) -> dict:
    body = json.dumps({
        "model": MODEL,
        "messages": messages,
        "format": schema,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat", data=body, headers={"Content-Type": "application/json"}
    )
    for wait in (2, 5, None):  # Ollama returns an occasional transient 500
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                content = json.load(resp)["message"]["content"]
            return json.loads(content)
        except urllib.error.URLError:
            if wait is None:
                raise
            time.sleep(wait)


def pedir(titular: str, estrategia: str) -> list[dict]:
    """Returns one record per attempt, until it rhymes or MAX_TRIES is reached."""
    if estrategia == "pareja":
        instr = (
            f"Titular: {titular}\n\n"
            "Primero elige dos palabras que rimen en consonante (campo 'rima'). "
            "Después escribe la calavera: el verso 2 termina con la primera palabra "
            "y el verso 4 con la segunda."
        )
        schema = SCHEMA_PAREJA
    else:
        instr = f"Titular: {titular}\n\nEscribe la calavera."
        schema = SCHEMA_LIBRE

    messages = [{"role": "system", "content": SISTEMA}, {"role": "user", "content": instr}]
    attempts = []
    for intento in range(1, MAX_TRIES + 1):
        t0 = time.time()
        try:
            out = ollama_chat(messages, schema)
        except (json.JSONDecodeError, KeyError) as e:
            attempts.append({"intento": intento, "error": repr(e)})
            continue
        # The model sometimes packs several lines into one array item.
        versos = [v.strip() for item in out.get("versos", []) for v in item.split("\n") if v.strip()]
        res = check_stanza(versos)
        rec = {
            "intento": intento,
            "segundos": round(time.time() - t0, 1),
            "versos": versos,
            **res,
        }
        if estrategia == "pareja":
            pair = out.get("rima", [])
            rec["rima_elegida"] = pair
            rec["pareja_rima"] = len(pair) == 2 and consonant_rhyme(pair[0], pair[1])
        attempts.append(rec)
        if res["ok"]:
            break
        # Tell the model exactly what failed, in terms it can act on.
        if len(versos) == 4:
            fb = (
                f"No rima: el verso 2 termina en \"{versos[1].split()[-1]}\" (suena \"-{rhyme_tail(versos[1])}\") "
                f"y el verso 4 en \"{versos[3].split()[-1]}\" (suena \"-{rhyme_tail(versos[3])}\"). "
                "Reescribe la calavera para que los versos 2 y 4 rimen en consonante."
            )
        else:
            fb = f"Tiene {len(versos)} versos; deben ser exactamente 4. Reescríbela."
        messages += [
            {"role": "assistant", "content": json.dumps(out, ensure_ascii=False)},
            {"role": "user", "content": fb},
        ]
    return attempts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4, help="samples per headline")
    ap.add_argument("--estrategia", choices=["libre", "pareja", "ambas"], default="ambas")
    args = ap.parse_args()
    estrategias = ["libre", "pareja"] if args.estrategia == "ambas" else [args.estrategia]

    resultados = {}
    for est in estrategias:
        runs = []
        for titular in TITULARES:
            for _ in range(args.n):
                attempts = pedir(titular, est)
                runs.append({"titular": titular, "intentos": attempts})
                last = attempts[-1]
                mark = "✅" if last.get("ok") else "❌"
                print(f"[{est}] {mark} intentos={len(attempts)} | {titular[:50]}")
                for v in last.get("versos", []):
                    print(f"      {v}")
        resultados[est] = runs

    print("\n=== Resumen ===")
    for est, runs in resultados.items():
        total = len(runs)
        first = sum(1 for r in runs if r["intentos"][0].get("ok"))
        final = sum(1 for r in runs if r["intentos"][-1].get("ok"))
        odd = sum(1 for r in runs if r["intentos"][-1].get("rhyme_1_3"))
        octo = [r["intentos"][-1].get("octosyllabic", 0) for r in runs]
        secs = [a.get("segundos", 0) for r in runs for a in r["intentos"]]
        print(
            f"{est:7s} riman a la primera: {first}/{total} | tras ≤{MAX_TRIES} intentos: {final}/{total} | "
            f"bonus 1-3: {odd}/{total} | versos ~octosílabos: {sum(octo)}/{4 * total} | "
            f"media {sum(secs) / max(1, len(secs)):.1f}s por llamada"
        )
        if est == "pareja":
            ok_pair = sum(1 for r in runs if r["intentos"][0].get("pareja_rima"))
            print(f"        la pareja elegida rimaba de verdad (1er intento): {ok_pair}/{total}")

    with open("resultados.json", "w") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print("\nDetalle en resultados.json")


if __name__ == "__main__":
    main()
