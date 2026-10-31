import unittest

from rima import (
    assonant_rhyme,
    check_stanza,
    consonant_rhyme,
    metric_syllables,
    rhyme_tail,
    syllables,
)


class Syllables(unittest.TestCase):
    def test_words(self):
        cases = {
            "muerte": 2, "calavera": 4, "día": 2, "huesos": 2, "poeta": 3,
            "ciudad": 2, "guitarra": 3, "querida": 3, "pingüino": 3, "rey": 1,
            "país": 2, "aire": 2, "buitre": 2, "oído": 3, "catrina": 3,
        }
        for word, n in cases.items():
            with self.subTest(word=word):
                self.assertEqual(syllables(word), n)


class Rhyme(unittest.TestCase):
    def test_tails(self):
        self.assertEqual(rhyme_tail("ya llegó la muerte"), "erte")
        self.assertEqual(rhyme_tail("con su corazón"), "on")
        self.assertEqual(rhyme_tail("en el panteón"), "on")
        self.assertEqual(rhyme_tail("la gente de la ciudad"), "ad")

    def test_consonant(self):
        self.assertTrue(consonant_rhyme("La flaca llegó a su puerta", "y la dejó bien abierta"))
        self.assertTrue(consonant_rhyme("ya llegó la muerte", "qué mala suerte"))
        self.assertTrue(consonant_rhyme("se fue al panteón", "con todo y millón"))
        self.assertTrue(consonant_rhyme("bebía vino", "por el camino"))
        self.assertFalse(consonant_rhyme("ya llegó la muerte", "y nadie lo duele"))
        self.assertFalse(consonant_rhyme("la muerte", "la muerte"))  # same word
        self.assertTrue(consonant_rhyme("en la nube", "el precio sube"))
        self.assertTrue(consonant_rhyme("cavaba", "llevaba"))  # b / v sound alike

    def test_assonant(self):
        self.assertTrue(assonant_rhyme("ya llegó la muerte", "nadie la detiene"))
        self.assertFalse(assonant_rhyme("ya llegó la muerte", "con todo y millón"))


class Meter(unittest.TestCase):
    def test_octosyllables(self):
        # Classic octosyllabic lines
        for line in [
            "La muerte calaca y flaca",  # sinalefa: calaca y
            "se llevó al gran empresario",
            "que no le alcanzó el dinero",
        ]:
            with self.subTest(line=line):
                self.assertEqual(metric_syllables(line), 8)

    def test_aguda_adds_one(self):
        self.assertEqual(metric_syllables("se fue para el panteón"), 8)


class Stanza(unittest.TestCase):
    def test_good_stanza(self):
        r = check_stanza([
            "Estaba el gran empresario",
            "contando su capital,",
            "llegó la flaca a su lado",
            "y lo mandó al hospital.",
        ])
        self.assertTrue(r["ok"])
        self.assertFalse(r["rhyme_1_3"])

    def test_bad_stanza(self):
        r = check_stanza([
            "La empresa ganó millones",
            "y despidió a la gente",
            "la muerte vino a verla",
            "y se la llevó al panteón",
        ])
        self.assertFalse(r["ok"])

    def test_wrong_length(self):
        self.assertFalse(check_stanza(["uno", "dos"])["ok"])


if __name__ == "__main__":
    unittest.main()
