// Titel en beschrijving van elke boekpagina, uit het gegevensbestand van het boek.
export default {
  eleventyComputed: {
    titel: ({ b }) => `${b.titel} — uitvloed`,
    beschrijving: ({ b }) => `${b.titel} door ${b.auteur} (${b.jaar}), № ${String(b.nummer).padStart(2, '0')} in de reeks van uitvloed. ${b.kort}`,
  },
};
