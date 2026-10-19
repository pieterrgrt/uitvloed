"""Tests voor ophalen.py. Draaien: python3 -m unittest discover gereedschap"""

import unittest

from ophalen import uit_gutenberg, zelfde_auteur

GUTENBERG = """﻿The Project Gutenberg eBook of Eline Vere\r
\r
Title: Eline Vere\r
        Een Haagsche roman\r
\r
Author: Louis Couperus\r
\r
Language: Dutch\r
\r
*** START OF THE PROJECT GUTENBERG EBOOK ELINE VERE ***\r
Produced by Jeroen Hellingman and the Online Distributed\r
Proofreading Team at http://www.pgdp.net/\r
\r
\r
Hoofdstuk I.\r
\r
Men verdrong zich.\r
\r
End of Project Gutenberg's Eline Vere, by Louis Couperus\r
\r
*** END OF THE PROJECT GUTENBERG EBOOK ELINE VERE ***\r
Updated editions will replace the previous one.\r
"""


class Ophalen(unittest.TestCase):
    def test_kop_en_licentie_gaan_eraf(self):
        kop, tekst = uit_gutenberg(GUTENBERG)
        self.assertEqual(tekst, "Hoofdstuk I.\n\nMen verdrong zich.\n")
        self.assertEqual(kop["title"], "Eline Vere Een Haagsche roman")
        self.assertEqual(kop["author"], "Louis Couperus")

    def test_zonder_markeringen_geen_tekst(self):
        with self.assertRaises(ValueError):
            uit_gutenberg("Gewoon een tekst.\n")

    def test_auteur_vergelijken(self):
        self.assertTrue(zelfde_auteur("Frederik van Eeden", "Eeden, Frederik van"))
        self.assertTrue(zelfde_auteur("Louis Couperus", "Couperus, Louis"))
        self.assertFalse(zelfde_auteur("Multatuli", "Couperus, Louis"))


if __name__ == "__main__":
    unittest.main()
