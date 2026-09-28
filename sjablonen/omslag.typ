// Omslag van een uitvloed-pocket: achterkant, rug en voorkant op één vel, met afloop.
// Bouwen: python3 gereedschap/bouw.py boeken/<titel>
// De rugdikte berekent bouw.py uit het aantal pagina's van het binnenwerk.
// Met de invoer hulplijnen=ja komen snijlijnen en de rug in beeld (niet voor de drukker).

#import "uitvloed.typ": *

#let rug = float(boek.rug_mm) * 1mm
#let reeks = rgb(boek.kleurcode)
#let hulplijnen = sys.inputs.at("hulplijnen", default: "nee") == "ja"

// Verhoudingen van de kaft op de site (300 × 480 px), omgerekend naar 105 mm breed.
#let px = breedte / 300
#let strook = 46 * px

#set document(title: boek.titel + " — omslag", author: boek.auteur)
#set page(width: 2 * breedte + rug + 2 * afloop, height: hoogte + 2 * afloop, margin: 0pt, fill: kaft)
#set text(font: serif, fill: inkt, lang: "nl", hyphenate: false)
#set par(justify: false)

// Linkerkant van achterkant, rug en voorkant, gemeten vanaf de rand van het vel.
#let achter-x = afloop
#let rug-x = afloop + breedte
#let voor-x = afloop + breedte + rug

#let woordmerk(maat) = text(font: schreefloos, weight: "bold", size: maat, tracking: -0.05em)[uitvloed]
#let strooktekst(body) = text(font: schreefloos, weight: "bold", size: 11 * px, fill: papier, body)

// De gekleurde strook loopt over het hele omslag, tot in de afloop.
#place(top + left, rect(width: 100%, height: afloop + strook, fill: reeks))

// — Voorkant —
#place(top + left, dx: voor-x + 18 * px, dy: afloop, box(width: breedte - 36 * px, height: strook,
  align(horizon, strooktekst[uitvloed #h(1fr) #text(tracking: 0.08em, nr(boek.nummer))])))
#place(top + left, dx: voor-x, dy: afloop + strook, box(width: breedte, height: hoogte - strook,
  inset: (x: 26 * px, y: 40 * px), {
    set align(center)
    rect(width: 46 * px, height: 1.5 * px, fill: reeks)
    v(22 * px - 0.65em)
    par(leading: 0.5em, text(style: "italic", size: 27pt, boek.titel))
    v(1fr)
    text(font: schreefloos, weight: "bold", size: 11pt, tracking: 0.07em, upper(boek.auteur))
  }))

// — Rug —
#if rug >= 5mm {
  place(top + left, dx: rug-x, dy: afloop + strook, box(width: rug, height: hoogte - strook,
    align(center + horizon, rotate(90deg, reflow: true, box(width: hoogte - strook - 12mm, {
      set text(size: calc.min(9pt, rug * 0.55))
      text(font: schreefloos, weight: "bold", tracking: 0.06em, upper(boek.auteur))
      h(1fr)
      text(style: "italic", boek.titel)
    })))))
  place(top + left, dx: rug-x, dy: afloop, box(width: rug, height: strook,
    align(center + horizon, text(font: schreefloos, weight: "bold", size: calc.min(7pt, rug * 0.4), fill: papier, str(boek.nummer)))))
}

// — Achterkant —
#place(top + left, dx: achter-x + 18 * px, dy: afloop, box(width: breedte - 36 * px, height: strook,
  align(horizon, strooktekst[#boek.auteur #h(1fr) #text(style: "italic", font: serif, weight: "regular", boek.titel)])))
#place(top + left, dx: achter-x, dy: afloop + strook, box(width: breedte, height: hoogte - strook,
  inset: (left: 12mm, right: 12mm, top: 14mm, bottom: 12mm), {
    set text(size: 10pt)
    set par(leading: 0.55em, spacing: 0.9em, justify: false)
    for alinea in boek.achterflap { par(alinea) }
    v(1fr)
    grid(columns: (1fr, auto), align: (left + bottom, right + bottom),
      {
        text(style: "italic", size: 8.5pt, fill: gedempt)[Nederlandse literatuur, opnieuw gedrukt — pas als jij het bestelt.]
        v(3mm)
        woordmerk(12pt)
      },
      // Ruimte voor de ISBN-streepjescode; de drukker of bouw.py vult die later in.
      rect(width: 36mm, height: 22mm, fill: white, stroke: none,
        align(center + horizon, text(font: schreefloos, size: 6.5pt, fill: gedempt,
          if boek.at("isbn", default: none) != none [ISBN #boek.isbn] else [ruimte voor ISBN-code]))),
    )
  }))

// — Hulplijnen: snijrand, rug en veilige zone —
#if hulplijnen {
  let lijn = (paint: rgb("#e0197d"), thickness: 0.3pt)
  place(top + left, dx: afloop, dy: afloop, rect(width: 2 * breedte + rug, height: hoogte, stroke: lijn))
  for x in (rug-x, voor-x) { place(top + left, dx: x, line(angle: 90deg, length: 100%, stroke: lijn)) }
  let veilig = (paint: rgb("#1f8fd0"), thickness: 0.3pt, dash: "dashed")
  for x in (achter-x, voor-x) {
    place(top + left, dx: x + 5mm, dy: afloop + 5mm, rect(width: breedte - 10mm, height: hoogte - 10mm, stroke: veilig))
  }
}
