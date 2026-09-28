"""Tests voor opschonen.py. Draaien: python3 -m unittest discover gereedschap"""

import unittest

from opschonen import opschonen


def schoon(ruw, **instellingen):
    return opschonen(ruw, instellingen)[0]


class Opschonen(unittest.TestCase):
    def test_regels_worden_alineas(self):
        self.assertEqual(schoon("Het was stil\nop de kade.\n\nAnne wachtte.\n"),
                         "Het was stil op de kade.\n\nAnne wachtte.\n")

    def test_paginanummers_verdwijnen(self):
        for nummer in ("12", "- 12 -", "— 12 —", "[12]", "  7  "):
            with self.subTest(nummer=nummer):
                self.assertEqual(schoon(f"Een zin.\n\n{nummer}\n\nNog een zin.\n"),
                                 "Een zin.\n\nNog een zin.\n")

    def test_jaartal_in_een_zin_blijft(self):
        self.assertEqual(schoon("Het was 1887\nen koud.\n"), "Het was 1887 en koud.\n")

    def test_afgebroken_woord_wordt_heel(self):
        tekst, verslag, woorden = opschonen("Hij liep lang-\nzaam weg.\n")
        self.assertEqual(tekst, "Hij liep langzaam weg.\n")
        self.assertEqual(woorden, ["langzaam"])
        self.assertEqual(verslag["afbrekingen"], 1)

    def test_samenstelling_houdt_streepje(self):
        self.assertEqual(schoon("Ze reisde naar Noord-\nHolland.\n"), "Ze reisde naar Noord-Holland.\n")

    def test_gedachtestreepje_blijft(self):
        self.assertEqual(schoon("Hij zweeg —\nen ging.\n"), "Hij zweeg — en ging.\n")

    def test_alinea_over_paginawissel(self):
        ruw = "De brief kwam\nniet, en zij\n\n\n14\n\n\nwachtte nog een dag.\n"
        self.assertEqual(schoon(ruw), "De brief kwam niet, en zij wachtte nog een dag.\n")

    def test_afbreking_over_paginawissel(self):
        ruw = "Het water ver-\n\n15\n\nroerde zich niet.\n"
        self.assertEqual(schoon(ruw), "Het water verroerde zich niet.\n")

    def test_afgeronde_alinea_blijft_los(self):
        self.assertEqual(schoon("Zij sliep.\n\nen de nacht viel.\n"), "Zij sliep.\n\nen de nacht viel.\n")

    def test_hoofdstukken_en_scenewissels(self):
        ruw = "HOOFDSTUK I\n\nBegin.\n\n* * *\n\nVerder.\n\nII.\n\nEinde.\n"
        self.assertEqual(schoon(ruw), "# HOOFDSTUK I\n\nBegin.\n\n***\n\nVerder.\n\n# II.\n\nEinde.\n")

    def test_eigen_hoofdstukpatroon(self):
        ruw = "Eerste deel\n\nTekst.\n"
        self.assertEqual(schoon(ruw, hoofdstukpatroon=r"^\w+ deel$"), "# Eerste deel\n\nTekst.\n")

    def test_kopregels_via_weg(self):
        ruw = "Een zin die\n\nDE STILLE KADE\n\n12\n\ndoorloopt.\n"
        self.assertEqual(schoon(ruw, weg=[r"^DE STILLE KADE$"]), "Een zin die doorloopt.\n")

    def test_aanhalingstekens_krullen(self):
        self.assertEqual(schoon("'Wie?' vroeg Anne. \"Nee,\" zei hij.\n"),
                         "‘Wie?’ vroeg Anne. “Nee,” zei hij.\n")

    def test_apostroffen(self):
        self.assertEqual(schoon("Het is Anne's brief, zei 'k, en 't regent.\n"),
                         "Het is Anne’s brief, zei ’k, en ’t regent.\n")

    def test_krullen_uit_te_zetten(self):
        self.assertEqual(schoon("'Ja.'\n", aanhalingstekens_krullen=False), "'Ja.'\n")

    def test_windows_regeleinden_en_formfeed(self):
        self.assertEqual(schoon("Een\r\nzin.\f2\fNieuw.\r\n"), "Een zin.\n\nNieuw.\n")


if __name__ == "__main__":
    unittest.main()
