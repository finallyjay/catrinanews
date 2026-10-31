"""Spanish rhyme and meter checks, in plain code.

A small model can write a calavera, but it can't reliably hear whether two
Spanish lines rhyme or count their syllables. This module does that part.

Rhyme (rima consonante): two lines rhyme when everything from the stressed
vowel of their last word to the end sounds the same ("muerte" / "suerte").
Assonance (rima asonante): only the vowels from that point match
("muerte" / "duele").

Meter: metric syllables of a line, with synalepha (sinalefa) between words and
the classic end-of-line rule: +1 if the last word is stressed on the final
syllable (aguda), -1 if it is stressed three from the end (esdrújula).
"""

import re
import unicodedata

STRONG = set("aeoáéó")
WEAK = set("iuü")
ACCENTED = set("áéíóú")
VOWELS = STRONG | WEAK | ACCENTED
_PLAIN = str.maketrans("áéíóúü", "aeiouu")


def _words(line: str) -> list[str]:
    line = unicodedata.normalize("NFC", line.lower())
    return re.findall(r"[a-záéíóúüñ]+", line)


def _letters(word: str) -> list[str]:
    """Letters with silent ones marked as consonants, and final 'y' as a vowel.

    - 'u' in que/qui/gue/gui is silent (not 'ü').
    - 'y' at the end of a word, or between consonants, sounds like 'i' (rey, hoy).
    """
    chars = list(word)
    out = []
    for i, ch in enumerate(chars):
        prev = chars[i - 1] if i > 0 else ""
        nxt = chars[i + 1] if i + 1 < len(chars) else ""
        if ch == "u" and prev in ("q", "g") and nxt in ("e", "i", "é", "í"):
            out.append("_")  # silent
        elif ch == "y" and (nxt == "" or nxt not in VOWELS) and prev and prev in VOWELS:
            out.append("i")  # rey, hoy, muy
        elif ch == "y" and nxt == "" and not prev:
            out.append("i")  # the word "y"
        else:
            out.append(ch)
    return out


def nuclei(word: str) -> list[tuple[int, int]]:
    """Spans (start, end) of each syllable nucleus in the word.

    Diphthongs (weak+strong, strong+weak, weak+weak) stay in one nucleus.
    Two strong vowels, or an accented weak vowel (í, ú), split into two.
    """
    letters = _letters(word)
    spans = []
    i = 0
    while i < len(letters):
        if letters[i] not in VOWELS:
            i += 1
            continue
        start = i
        i += 1
        while i < len(letters) and letters[i] in VOWELS:
            a, b = letters[i - 1], letters[i]
            hiatus = (a in STRONG and b in STRONG) or a in "íú" or b in "íú"
            if hiatus:
                break
            i += 1
        spans.append((start, i))
    return spans


def syllables(word: str) -> int:
    return max(1, len(nuclei(word)))


def stressed_nucleus(word: str) -> int:
    """Index (into nuclei) of the stressed syllable, by Spanish spelling rules."""
    spans = nuclei(word)
    if not spans:
        return 0
    letters = _letters(word)
    for idx, (s, e) in enumerate(spans):
        if any(ch in ACCENTED for ch in letters[s:e]):
            return idx
    if len(spans) == 1:
        return 0
    last = word[-1]
    # llana: ends in a vowel, n or s → second to last; otherwise aguda ("hoy", "reloj")
    if last in VOWELS or last in "ns":
        return len(spans) - 2
    return len(spans) - 1


def _stressed_vowel_pos(word: str) -> int:
    """Position of the stressed vowel letter inside the stressed nucleus."""
    letters = _letters(word)
    spans = nuclei(word)
    if not spans:
        return 0
    s, e = spans[stressed_nucleus(word)]
    group = letters[s:e]
    for k, ch in enumerate(group):
        if ch in ACCENTED:
            return s + k
    for k, ch in enumerate(group):
        if ch in STRONG:
            return s + k
    # weak + weak (ui, iu): stress falls on the second
    return s + len(group) - 1


def _sound(text: str) -> str:
    """Spelling → rough sound, so 'b'/'v' or a silent 'h' don't break a rhyme."""
    text = text.translate(_PLAIN).replace("_", "")
    text = text.replace("h", "").replace("v", "b").replace("ll", "y")
    text = re.sub(r"c([ei])", r"z\1", text)
    text = re.sub(r"g([ei])", r"j\1", text)
    text = text.replace("qu", "k").replace("c", "k")
    return text


def rhyme_tail(line: str) -> str:
    """Sound of the line's last word from its stressed vowel to the end."""
    words = _words(line)
    if not words:
        return ""
    word = words[-1]
    letters = _letters(word)
    return _sound("".join(letters[_stressed_vowel_pos(word):]))


def vowel_tail(line: str) -> str:
    """Only the vowels of the rhyme tail, for assonance (weak vowels in diphthongs dropped)."""
    tail = rhyme_tail(line)
    vowels = [ch for ch in tail if ch in "aeiou"]
    if len(vowels) > 2:  # keep stressed vowel and the last one
        vowels = [vowels[0], vowels[-1]]
    return "".join(vowels)


def consonant_rhyme(a: str, b: str) -> bool:
    ta, tb = rhyme_tail(a), rhyme_tail(b)
    if not ta or not tb:
        return False
    # The same last word doesn't count as a rhyme.
    return ta == tb and _words(a)[-1] != _words(b)[-1]


def assonant_rhyme(a: str, b: str) -> bool:
    va, vb = vowel_tail(a), vowel_tail(b)
    return bool(va) and va == vb and _words(a)[-1] != _words(b)[-1]


def metric_syllables(line: str) -> int:
    """Metric syllables with synalepha and the end-of-line rule."""
    words = _words(line)
    if not words:
        return 0
    total = sum(syllables(w) for w in words)
    for prev, nxt in zip(words, words[1:]):
        ends_vowel = _letters(prev)[-1] in VOWELS
        bare = nxt.lstrip("h")  # silent h: "la hora" still joins
        starts_vowel = bool(bare) and _letters(bare)[0] in VOWELS  # covers the word "y"
        if ends_vowel and starts_vowel:
            total -= 1  # sinalefa
    last = words[-1]
    n = syllables(last)
    from_end = n - 1 - stressed_nucleus(last)
    if from_end == 0 and n >= 1:
        total += 1  # aguda
    elif from_end >= 2:
        total -= 1  # esdrújula
    return total


def check_stanza(lines: list[str]) -> dict:
    """Score a 4-line calavera stanza.

    Required: lines 2 and 4 rhyme (consonant). Bonus: lines 1 and 3 rhyme too.
    Meter is reported, not required: calaveras are traditionally octosyllabic.
    """
    lines = [line for line in lines if line.strip()]
    if len(lines) != 4:
        return {"ok": False, "reason": f"expected 4 lines, got {len(lines)}"}
    even = consonant_rhyme(lines[1], lines[3])
    odd = consonant_rhyme(lines[0], lines[2])
    meter = [metric_syllables(line) for line in lines]
    return {
        "ok": even,
        "rhyme_2_4": even,
        "rhyme_1_3": odd,
        "assonant_2_4": assonant_rhyme(lines[1], lines[3]),
        "tails": [rhyme_tail(line) for line in lines],
        "meter": meter,
        "octosyllabic": sum(1 for m in meter if 7 <= m <= 9),
    }
