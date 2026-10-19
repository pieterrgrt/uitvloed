"""Tests voor controle.py. Draaien: python3 -m unittest discover gereedschap"""

import io
import unittest

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject

from controle import MM, binnenwerk, lettertypes, omslag, rechten, tekst


def pdf(*maten, letter=None):
    """Een PDF met lege pagina's van de gegeven maten in mm, eventueel met een lettertype."""
    schrijver = PdfWriter()
    for breedte, hoogte in maten:
        pagina = schrijver.add_blank_page(breedte * MM, hoogte * MM)
        if letter:
            pagina[NameObject("/Resources")] = DictionaryObject({
                NameObject("/Font"): DictionaryObject({NameObject("/F1"): schrijver._add_object(letter)})})
    buffer = io.BytesIO()
    schrijver.write(buffer)
    return PdfReader(buffer)


def tekens(meldingen):
    return [teken for teken, _ in meldingen]


class Rechten(unittest.TestCase):
    def test_zeventig_jaar_na_het_sterfjaar(self):
        self.assertEqual(tekens(rechten({"sterfjaar": 1955}, jaar=2026)), ["✓"])
        self.assertEqual(tekens(rechten({"sterfjaar": 1956}, jaar=2026)), ["✗"])

    def test_laatste_sterfjaar_telt(self):
        self.assertEqual(tekens(rechten({"sterfjaar": [1887, 1970]}, jaar=2026)), ["✗"])

    def test_zonder_sterfjaar_geen_druk(self):
        self.assertEqual(tekens(rechten({}, jaar=2026)), ["✗"])
        self.assertEqual(tekens(rechten({"rechtenvrij": "eigen tekst"}, jaar=2026)), ["✓"])


class Maten(unittest.TestCase):
    def test_goed_binnenwerk(self):
        self.assertEqual(tekens(binnenwerk(pdf(*[(105, 148)] * 8))), ["✓", "✓"])

    def test_verkeerd_formaat_en_paginatal(self):
        self.assertEqual(tekens(binnenwerk(pdf((105, 148), (148, 210), (105, 148)))), ["✗", "✗"])

    def test_omslag_past_bij_rug(self):
        self.assertEqual(tekens(omslag(pdf((2 * 105 + 8 + 6, 154)), 8)), ["✓"])
        self.assertEqual(tekens(omslag(pdf((2 * 105 + 8 + 6, 154)), 10)), ["✗"])
        self.assertEqual(tekens(omslag(pdf((216, 154), (216, 154)), 0)), ["✗"])


class Lettertypes(unittest.TestCase):
    def test_niet_ingebed(self):
        helvetica = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                                      NameObject("/Subtype"): NameObject("/Type1"),
                                      NameObject("/BaseFont"): NameObject("/Helvetica")})
        self.assertEqual(lettertypes(pdf((105, 148), letter=helvetica)), {"Helvetica"})

    def test_zonder_lettertypes(self):
        self.assertEqual(lettertypes(pdf((105, 148))), set())


class Tekst(unittest.TestCase):
    def test_resten_van_opschonen(self):
        meldingen = tekst("Een zin.\n\n12\n\n'Ja,' zei hij.\n")
        self.assertEqual(len(meldingen), 2)

    def test_schone_tekst(self):
        self.assertEqual(tekst("# I\n\n‘Ja,’ zei hij.\n"), [])


if __name__ == "__main__":
    unittest.main()
