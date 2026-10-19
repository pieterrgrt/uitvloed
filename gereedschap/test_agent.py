"""Tests voor de gereedschappen van agent.py (zonder API). Draaien: python3 -m unittest discover gereedschap"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agent import Werkbank, gereedschappen

PROEF = Path(__file__).resolve().parent.parent / "boeken/_proef"


class Gereedschappen(unittest.TestCase):
    def setUp(self):
        self.map = Path(tempfile.mkdtemp()) / "proef"
        shutil.copytree(PROEF, self.map, ignore=shutil.ignore_patterns("uit"))
        self.bank = Werkbank(self.map)

    def tearDown(self):
        shutil.rmtree(self.map.parent)

    def test_lees_met_regelnummers_en_alleen_boekbestanden(self):
        self.assertIn("1\t# HOOFDSTUK I", self.bank.lees("tekst.txt", 1, 1))
        with self.assertRaises(ValueError):
            self.bank.lees("../../README.md")

    def test_vervang_moet_eenduidig_zijn(self):
        self.assertEqual(self.bank.vervang("derde dag", "vierde dag"), "1 keer vervangen")
        with self.assertRaises(ValueError):
            self.bank.vervang("de", "het")
        with self.assertRaises(ValueError):
            self.bank.vervang("staat er niet in", "")

    def test_rechten_blijven_van_de_mens(self):
        for veld in ("sterfjaar", "rechtenvrij", "isbn", "nummer"):
            with self.subTest(veld=veld), self.assertRaises(ValueError):
                self.bank.instellen(veld, 1900)
        self.bank.instellen("hoofdstukpatroon", "^HOOFDSTUK [IVXLC]+$")
        self.assertEqual(json.loads((self.map / "boek.json").read_text())["hoofdstukpatroon"], "^HOOFDSTUK [IVXLC]+$")

    def test_ongeldige_reguliere_expressie(self):
        with self.assertRaises(Exception):
            self.bank.instellen("weg", ["(open"])

    def test_opschonen_beschermt_handwerk(self):
        self.bank.vervang("derde dag", "vierde dag")
        with self.assertRaises(ValueError):
            self.bank.opschonen()
        self.assertIn("(exitcode 0)", self.bank.opschonen(toch=True))

    def test_tools_geven_fouten_als_tekst_terug(self):
        lees = next(t for t in gereedschappen(self.bank) if t.name == "lees")
        self.assertTrue(lees.call({"bestand": "geheim.txt"}).startswith("Fout:"))


if __name__ == "__main__":
    unittest.main()
