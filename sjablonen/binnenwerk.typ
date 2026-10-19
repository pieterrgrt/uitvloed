// Binnenwerk van een uitvloed-pocket (A6).
// Bouwen: python3 gereedschap/bouw.py boeken/<titel>
//
// De tekst komt uit tekst.txt: alinea's gescheiden door een witregel.
//   # Kop         hoofdstuk, begint op een nieuwe pagina
//   ## Kop        onderdeel binnen een hoofdstuk
//   ***           scènewissel
//   > tekst       motto, opdracht of citaat: ingesprongen en kleiner;
//                 vóór het eerste hoofdstuk krijgen ze een eigen pagina in het voorwerk;
//                 meer regels in één blok (elk met "> ") blijven onder elkaar staan
//   _cursief_     cursief, binnen één alinea
//   [12]          verwijzing naar een noot, verhoogd gezet

#import "uitvloed.typ": *

#set document(title: boek.titel, author: boek.auteur)
#set page(
  width: breedte,
  height: hoogte,
  margin: (inside: 15mm, outside: 12mm, top: 15mm, bottom: 17mm),
  binding: left,
)
#set text(font: serif, size: 9.5pt, fill: black, lang: "nl", hyphenate: true, number-type: "old-style")
#set par(justify: true, leading: 0.6em, spacing: 0.6em, first-line-indent: 1.1em)

#let klein(body) = text(size: 7.5pt, tracking: 0.08em, body)

// — Voorwerk: franjetitel, titelpagina en colofon, zonder paginanummers —

#page[
  #v(30%)
  #align(center, text(style: "italic", size: 13pt, boek.titel))
]
#page[]
#page[
  #set align(center)
  #v(18%)
  #text(font: schreefloos, weight: "bold", size: 8.5pt, tracking: 0.1em, upper(boek.auteur))
  #v(6mm)
  #par(justify: false, leading: 0.5em, text(style: "italic", size: 20pt, boek.titel))
  #v(1fr)
  #text(font: schreefloos, weight: "bold", size: 10pt, tracking: -0.02em)[uitvloed]
  #h(0.6em)
  #text(font: schreefloos, size: 8pt, fill: gedempt, nr(boek.nummer))
]
#page[
  #set text(size: 7.5pt)
  #set par(justify: false, first-line-indent: 0pt, spacing: 0.9em)
  #v(1fr)
  #boek.titel — #boek.auteur

  #if boek.at("oorspronkelijk", default: none) != none { boek.oorspronkelijk }

  Deze uitgave: uitvloed #nr(boek.nummer), #boek.jaar. \
  Gezet in EB Garamond. \
  Gedrukt omdat genoeg lezers erom vroegen.

  #if boek.at("isbn", default: none) != none [ISBN #boek.isbn]
]

// _cursief_: de stukken tussen twee lage streepjes worden cursief.
#let opmaak(tekst) = tekst.split("_").enumerate().map(((i, deel)) => if calc.odd(i) { emph(deel) } else { deel }).join()

// — Opdracht en motto's: de >-alinea's vóór het eerste hoofdstuk, op een eigen pagina —

#let blokken = read(sys.inputs.tekst).split(regex("\n\s*\n")).map(b => b.trim()).filter(b => b != "")
#let voorwerk = ()
#while blokken.len() > 0 and blokken.first().starts-with("> ") {
  voorwerk.push(blokken.remove(0))
}
#if voorwerk.len() > 0 {
  page({
    v(25%)
    set par(first-line-indent: 0pt)
    set text(style: "italic", size: 9pt)
    for b in voorwerk {
      // Korte regels en verzen gecentreerd, proza (een motto van een alinea) uitgevuld.
      let proza = b.len() > 120 and not b.contains("\n")
      set align(if proza { left } else { center })
      set par(justify: proza)
      block(below: 1.6em, width: 100%, opmaak(b.slice(2).replace(regex("\n> ?"), "\n")))
    }
  })
  // De tekst begint altijd op een rechterpagina.
  pagebreak(weak: true, to: "odd")
}

// — Romp —

#show heading.where(level: 1): it => {
  pagebreak(weak: true)
  v(22mm)
  align(center, text(size: 12pt, style: "italic", weight: "regular", it.body))
  v(9mm)
}
#show heading.where(level: 2): it => block(above: 1.6em, below: 1.1em, width: 100%,
  align(center, text(size: 9.5pt, weight: "regular", it.body)))
#show regex("\[\d+\]"): it => super(it.text.slice(1, -1))


#set page(
  header: context {
    // Geen kop op een pagina waar een hoofdstuk begint.
    let hier = here().page()
    if query(heading.where(level: 1)).any(h => h.location().page() == hier) { return }
    let links = calc.even(hier)
    set align(if links { left } else { right })
    klein(text(style: "italic", if links { boek.auteur } else { boek.titel }))
  },
  footer: context align(center, klein(counter(page).display())),
)
#counter(page).update(1)

#for blok in blokken {
  if blok.starts-with("# ") {
    heading(level: 1, outlined: true, opmaak(blok.slice(2)))
  } else if blok.starts-with("## ") {
    heading(level: 2, outlined: false, opmaak(blok.slice(3)))
  } else if blok == "***" {
    block(above: 1.2em, below: 1.2em, width: 100%, align(center, text(tracking: 0.4em)[\* \* \*]))
  } else if blok.starts-with("> ") {
    block(above: 1em, below: 1em, inset: (x: 6mm), {
      set text(size: 8.5pt)
      set par(first-line-indent: 0pt, justify: false)
      opmaak(blok.slice(2).replace(regex("\n> ?"), "\n"))
    })
  } else {
    opmaak(blok)
    parbreak()
  }
}

// — Slot: aanvullen tot een veelvoud van vier pagina's, met een laatste woord —

#let slotpagina = page.with(header: none, footer: none)
#metadata(none) <tekst-einde>
#context {
  // Na de laatste tekstpagina komen de lege pagina's en dan nog de slotpagina.
  let laatste = query(<tekst-einde>).first().location().page()
  let vul = calc.rem(4 - calc.rem(laatste + 1, 4), 4)
  for _ in range(vul) { slotpagina[] }
}
#slotpagina[
  #v(1fr)
  #align(center, {
    text(font: schreefloos, weight: "bold", size: 10pt, tracking: -0.02em)[uitvloed]
    linebreak()
    v(1mm)
    text(style: "italic", size: 8pt, fill: gedempt)[Nederlandse literatuur, opnieuw gedrukt — \ pas als jij het bestelt.]
  })
  #v(12mm)
  #context [#metadata(here().page()) <paginas>]
]
