// Huisstijl van uitvloed voor drukwerk: formaat, kleuren en lettertypes.
// De kleuren komen overeen met site/statisch/uitvloed.css; de kleur van een boek
// (bijvoorbeeld reeks-07) wordt door gereedschap/bouw.py uit die stylesheet gehaald.

// A6-pocket, bijgesneden formaat.
#let breedte = 105mm
#let hoogte = 148mm
#let afloop = 3mm

#let papier = rgb("#f6f2e9")
#let kaft = rgb("#efe7d6")
#let inkt = rgb("#2b2724")
#let gedempt = rgb("#6e655a")

// EB Garamond voor tekst, TeX Gyre Heros als vrije vervanger van Univers.
// Beide staan in sjablonen/letters/, zodat elke computer hetzelfde zet.
#let serif = "EB Garamond 12"
#let schreefloos = "TeX Gyre Heros"

// Het nummer in de reeks, zoals op de site: № 07.
#let nr(n) = "№ " + if n < 10 { "0" } + str(n)

// Gegevens van het boek, samengesteld door gereedschap/bouw.py.
#let boek = json(bytes(sys.inputs.at("boek", default: "{}")))
