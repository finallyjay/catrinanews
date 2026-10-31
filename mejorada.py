"""Improved generation: meter feedback, a banned crutch rhyme, and best-of-k.

Builds on prueba.py's baseline ("libre"):
  1. Retry feedback covers meter too ("line 3 has 11 syllables, make it 8"),
     not only the 2-4 rhyme.
  2. "panteón" is banned as a line ending: the 4B model leaned on it in 10 of
     its 20 baseline rhymes.
  3. Best-of-k: k independent candidates per headline, each with up to
     MAX_TRIES rounds of feedback, and code picks the best one by score.
  4. Optional `evitar`: rhyme sounds already used elsewhere in the sheet are
     banned too, so the model can't swap one crutch rhyme for another.

Usage:
  python3 mejorada.py                      # gemma3:4b, 2 per headline, k=3
  HOJA_MODEL=gemma3:12b python3 mejorada.py
"""

import argparse
import json
import urllib.error
import time

import prueba
from prueba import SCHEMA_LIBRE, SISTEMA, TITULARES, ollama_chat
from rima import _words, check_stanza, rhyme_tail

MAX_TRIES = 3
BANNED_ENDINGS = {"panteón", "panteon"}

SISTEMA_MEJORADO = SISTEMA + """
- Prohibido terminar un verso en "panteón": es la rima fácil, busca otra.
- Usa solo palabras reales del español; no inventes palabras para que rime.
- Que la burla sea concreta: usa un detalle del titular (la cifra, el producto, la promesa)."""


def rhyme_sounds(versos: list[str], res: dict) -> set[str]:
    """The rhyme sounds a stanza actually uses (2-4, plus 1-3 when they rhyme)."""
    if len(versos) != 4:
        return set()
    sounds = {rhyme_tail(versos[1])} if res.get("ok") else set()
    if res.get("rhyme_1_3"):
        sounds.add(rhyme_tail(versos[0]))
    return sounds


def banned_lines(versos: list[str], evitar: frozenset = frozenset()) -> list[tuple[int, str, str]]:
    """Lines ending in a banned word, or in a rhyme sound already used in the sheet.

    `evitar` holds sounds, not words: banning words only made the model swap
    "razón" for "decepción", "perfección", "lección"... all still "-ón".
    """
    out = []
    for i, v in enumerate(versos):
        if not _words(v):
            continue
        word, tail = _words(v)[-1], rhyme_tail(v)
        if word in BANNED_ENDINGS or tail in evitar:
            out.append((i + 1, word, tail))
    return out


def score(res: dict, versos: list[str], evitar: frozenset = frozenset()) -> int:
    if "meter" not in res:
        return -100
    return (
        (100 if res["ok"] else 0)
        + (10 if res["rhyme_1_3"] else 0)
        + 5 * res["octosyllabic"]
        - 30 * len(banned_lines(versos, evitar))
    )


def good_enough(res: dict, versos: list[str], evitar: frozenset = frozenset()) -> bool:
    return res.get("ok", False) and res["octosyllabic"] >= 3 and not banned_lines(versos, evitar)


def feedback(versos: list[str], res: dict, evitar: frozenset = frozenset()) -> str:
    if len(versos) != 4:
        return f"Tiene {len(versos)} versos; deben ser exactamente 4. Reescríbela."
    issues = []
    if not res["ok"]:
        issues.append(
            f"No rima: el verso 2 termina en \"{_words(versos[1])[-1]}\" (suena \"-{rhyme_tail(versos[1])}\") "
            f"y el verso 4 en \"{_words(versos[3])[-1]}\" (suena \"-{rhyme_tail(versos[3])}\"); "
            "deben rimar en consonante."
        )
    for n, word, tail in banned_lines(versos, evitar):
        if word in BANNED_ENDINGS:
            issues.append(f"El verso {n} termina en \"{word}\", que está prohibido.")
        else:
            issues.append(f"El verso {n} termina en \"{word}\" (rima en \"-{tail}\"), una rima ya usada en la hoja.")
    for i, m in enumerate(res["meter"]):
        if not 7 <= m <= 9:
            issues.append(f"El verso {i + 1} tiene {m} sílabas; déjalo en unas 8.")
    return " ".join(issues) + " Reescribe la calavera corrigiendo esto."


def candidate(titular: str, evitar: frozenset = frozenset()) -> dict:
    instr = f"Titular: {titular}\n\nEscribe la calavera."
    if evitar:
        sonidos = ", ".join(f'"-{t}"' for t in sorted(evitar))
        instr += f"\nEstas rimas ya se usaron en la hoja; busca otras: {sonidos}."
    messages = [
        {"role": "system", "content": SISTEMA_MEJORADO},
        {"role": "user", "content": instr},
    ]
    best, calls, t0 = None, 0, time.time()
    for _ in range(MAX_TRIES):
        calls += 1
        try:
            out = ollama_chat(messages, SCHEMA_LIBRE)
        except (json.JSONDecodeError, KeyError, urllib.error.URLError):
            continue
        versos = [v.strip() for item in out.get("versos", []) for v in item.split("\n") if v.strip()]
        res = check_stanza(versos)
        cur = {"versos": versos, "res": res, "score": score(res, versos, evitar)}
        if best is None or cur["score"] > best["score"]:
            best = cur
        if good_enough(res, versos, evitar):
            break
        messages += [
            {"role": "assistant", "content": json.dumps(out, ensure_ascii=False)},
            {"role": "user", "content": feedback(versos, res, evitar)},
        ]
    best = best or {"versos": [], "res": {"ok": False}, "score": -100}
    best["calls"], best["seconds"] = calls, round(time.time() - t0, 1)
    return best


def calavera(titular: str, k: int, evitar: frozenset = frozenset()) -> dict:
    cands = [candidate(titular, evitar) for _ in range(k)]
    best = max(cands, key=lambda c: c["score"])
    return {
        "titular": titular,
        "best": best,
        "calls": sum(c["calls"] for c in cands),
        "seconds": round(sum(c["seconds"] for c in cands), 1),
        "candidates": cands,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=2, help="calaveras per headline")
    ap.add_argument("--k", type=int, default=3, help="candidates per calavera")
    args = ap.parse_args()

    runs = []
    for titular in TITULARES:
        for _ in range(args.n):
            r = calavera(titular, args.k)
            runs.append(r)
            b = r["best"]
            res = b["res"]
            mark = "✅" if res.get("ok") else "❌"
            print(f"{mark} score={b['score']} meter={res.get('meter')} {r['seconds']}s | {titular[:50]}")
            for v in b["versos"]:
                print(f"      {v}")

    total = len(runs)
    ok = sum(1 for r in runs if r["best"]["res"].get("ok"))
    odd = sum(1 for r in runs if r["best"]["res"].get("rhyme_1_3"))
    octo = sum(r["best"]["res"].get("octosyllabic", 0) for r in runs)
    banned = sum(len(banned_lines(r["best"]["versos"])) for r in runs)  # only "panteón" here
    secs = sum(r["seconds"] for r in runs) / total
    calls = sum(r["calls"] for r in runs) / total
    print(f"\n=== Resumen ({prueba.MODEL}, k={args.k}) ===")
    print(
        f"riman 2-4: {ok}/{total} | bonus 1-3: {odd}/{total} | versos ~octosílabos: {octo}/{4 * total} | "
        f"'panteón' al final: {banned} | {calls:.1f} llamadas y {secs:.0f}s por calavera"
    )
    out = f"resultados_mejorada_{prueba.MODEL.replace(':', '_')}.json"
    with open(out, "w") as f:
        json.dump(runs, f, ensure_ascii=False, indent=2)
    print(f"Detalle en {out}")


if __name__ == "__main__":
    main()
