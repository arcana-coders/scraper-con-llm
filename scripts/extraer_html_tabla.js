// scripts/extraer_html_tabla.js

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// --- Configuración ---
const URL_PEDIDOS = 'https://sellercentral.amazon.com/orders-v3/mfn/unshipped/?page=1';
const COOKIES_PATH = path.join(__dirname, '../cookies/session.json');
// --------------------

/**
 * Genera un string con la fecha actual en formato YYYYMMDD.
 * @returns {string} La fecha formateada.
 */
function getFormattedDate() {
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    return `${year}${month}${day}`;
}

const HTML_OUTPUT_PATH = path.join(__dirname, `../html/pedidos_${getFormattedDate()}.html`);

(async () => {
    if (!fs.existsSync(COOKIES_PATH)) {
        console.error(`❌ Error: El archivo de sesión no se encuentra en la ruta: ${COOKIES_PATH}`);
        console.error('Asegúrate de haber generado primero el archivo "session.json" con tu script de login.');
        return;
    }

    console.log('🚀 Iniciando proceso de extracción de HTML...');
    // Puedes cambiar headless a false para ver el proceso en pantalla
    const browser = await chromium.launch({ headless: false }); 

    try {
        console.log('- Cargando contexto del navegador con la sesión guardada...');
        const context = await browser.newContext({ storageState: COOKIES_PATH });
        const page = await context.newPage();

        console.log(`- Navegando a la página de pedidos: ${URL_PEDIDOS}`);
        await page.goto(URL_PEDIDOS, { waitUntil: 'domcontentloaded', timeout: 90000 });

        // --- CAMBIO REALIZADO ---
        // Se elimina la espera por un selector específico que puede cambiar.
        // En su lugar, se usa una espera de tiempo fijo para que carguen los elementos dinámicos.
        console.log('- Esperando 10 segundos para asegurar la carga completa de la página...');
        await page.waitForTimeout(10000); // 10,000 milisegundos = 10 segundos

        console.log('- Tiempo de espera finalizado. Extrayendo el contenido HTML...');
        const htmlContent = await page.content();

        const htmlDir = path.dirname(HTML_OUTPUT_PATH);
        if (!fs.existsSync(htmlDir)) {
            fs.mkdirSync(htmlDir, { recursive: true });
        }
        
        fs.writeFileSync(HTML_OUTPUT_PATH, htmlContent, 'utf-8');
        console.log(`✅ ¡Éxito! HTML guardado en: ${HTML_OUTPUT_PATH}`);

    } catch (error) {
        console.error('❌ Ocurrió un error durante la automatización:', error);
        const screenshotPath = path.join(__dirname, '../html/error_screenshot.png');
        if (typeof page !== 'undefined') {
            await page.screenshot({ path: screenshotPath, fullPage: true });
            console.log(`📸 Se guardó una captura de pantalla del error en: ${screenshotPath}`);
        }
    } finally {
        await browser.close();
        console.log('🎉 Proceso finalizado. Navegador cerrado.');
    }
})();