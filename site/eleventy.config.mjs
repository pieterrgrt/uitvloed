// Eleventy bouwt de site van uitvloed uit src/ naar _site/. Boeken staan in boeken/, één bestand per titel.
export default function (config) {
  config.addPassthroughCopy({ statisch: '/' });
  config.addWatchTarget('boeken/');
  config.addWatchTarget('reeks.json');
  config.addWatchTarget('reeks.mjs');

  config.addGlobalData('slogan', 'Nederlandse literatuur, opnieuw gedrukt — pas als jij het bestelt.');
  config.addGlobalData('bouwjaar', new Date().getFullYear());

  // № 07
  config.addFilter('nr', (n) => '№ ' + String(n).padStart(2, '0'));
  config.addFilter('pct', (aantal, doel) => Math.min(100, Math.round((aantal / doel) * 100)));
  config.addFilter('nummer', (lijst, n) => lijst.find((b) => b.nummer === n));

  return {
    dir: { input: 'src', includes: '_includes', data: '_data', output: '_site' },
    templateFormats: ['njk'],
    htmlTemplateEngine: 'njk',
  };
}
