const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const cookiePath = path.join(__dirname, '..','cookies', 'session.json');

  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  console.log('🔐 Abriendo página de login de Amazon Seller Central...');
  await page.goto('https://sellercentral.amazon.com');

  console.log('🧑‍💻 Espera a iniciar sesión manualmente...');
  console.log('✅ Cuando termines y veas el panel de Seller Central, cierra esta ventana o presiona ENTER aquí.');

  // Esperar hasta que el usuario presione ENTER en la terminal
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', async () => {
    console.log('💾 Guardando cookie...');
    await context.storageState({ path: cookiePath });
    console.log(`✅ Cookie guardada en: ${cookiePath}`);
    await browser.close();
    process.exit(0);
  });
})();
