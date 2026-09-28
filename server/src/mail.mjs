// Verstuurt de inlogmail. Zonder SMTP_URL wordt de link alleen in het logboek gezet (voor lokaal testen).
import nodemailer from 'nodemailer';

export function maakMailer({ smtpUrl, afzender }) {
  if (!smtpUrl) {
    return {
      async stuur({ aan, onderwerp, tekst }) {
        console.log(`[mail naar ${aan}] ${onderwerp}\n${tekst}`);
      },
    };
  }
  const transport = nodemailer.createTransport(smtpUrl);
  return {
    async stuur({ aan, onderwerp, tekst, html }) {
      await transport.sendMail({ from: afzender, to: aan, subject: onderwerp, text: tekst, html });
    },
  };
}

export function inlogmail(link) {
  const tekst = `Hallo,

Klik op deze link om in te loggen bij uitvloed:
${link}

De link werkt één keer en vervalt na 15 minuten. Heb je dit niet aangevraagd? Dan kun je deze mail negeren.

uitvloed — Nederlandse literatuur, opnieuw gedrukt.`;
  const html = `<div style="font-family: Georgia, serif; font-size: 17px; line-height: 1.6; color: #2b2724; max-width: 520px">
<p style="font-family: Helvetica, Arial, sans-serif; font-weight: 700; font-size: 22px; letter-spacing: -1px; margin: 0 0 24px">uitvloed</p>
<p>Klik op de knop om in te loggen.</p>
<p><a href="${link}" style="display: inline-block; background: #4a6fa5; color: #fff; font-family: Helvetica, Arial, sans-serif; font-weight: 700; font-size: 16px; padding: 14px 26px; border-radius: 11px; text-decoration: none">Inloggen</a></p>
<p style="font-size: 14px; color: #6e655a">De link werkt één keer en vervalt na 15 minuten. Heb je dit niet aangevraagd? Dan kun je deze mail negeren.</p>
</div>`;
  return { onderwerp: 'Je inloglink voor uitvloed', tekst, html };
}
