// scripts/extraer_detalles_pedidos.js

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// --- Configuración ---
const BASE_DIR = path.resolve(__dirname, '..'); // Sube un nivel a la carpeta raíz del proyecto
const CONSOLIDATED_JSON_PATH = path.join(BASE_DIR, 'csv', 'pedidos_consolidados.json');
const HTML_PEDIDOS_DIR = path.join(BASE_DIR, 'html_pedidos');
const COOKIES_PATH = path.join(BASE_DIR, 'cookies', 'session.json');
// --------------------

/**
 * Función para crear una pausa con un tiempo aleatorio.
 * @param {number} min_ms - Tiempo mínimo de espera en milisegundos.
 * @param {number} max_ms - Tiempo máximo de espera en milisegundos.
 */
function sleep(min_ms, max_ms) {
    const ms = Math.random() * (max_ms - min_ms) + min_ms;
    return new Promise(resolve => setTimeout(resolve, ms));
}

(async () => {
    // 1. Verificar que los archivos y carpetas necesarios existan
    if (!fs.existsSync(CONSOLIDATED_JSON_PATH)) {
        console.error(`❌ Error: No se encuentra el archivo JSON consolidado en: ${CONSOLIDATED_JSON_PATH}`);
        return;
    }
    if (!fs.existsSync(COOKIES_PATH)) {
        console.error(`❌ Error: El archivo de sesión no se encuentra en la ruta: ${COOKIES_PATH}`);
        return;
    }

    // Crear la carpeta de destino si no existe
    if (!fs.existsSync(HTML_PEDIDOS_DIR)) {
        console.log(`📂 Creando directorio de destino: ${HTML_PEDIDOS_DIR}`);
        fs.mkdirSync(HTML_PEDIDOS_DIR, { recursive: true });
    }

    // 2. Leer los pedidos del archivo JSON
    const pedidos = JSON.parse(fs.readFileSync(CONSOLIDATED_JSON_PATH, 'utf-8'));
    if (!pedidos || pedidos.length === 0) {
        console.log('ℹ️ No hay pedidos en el archivo JSON para procesar. Saliendo.');
        return;
    }
    
    console.log(`🔍 Se encontraron ${pedidos.length} pedidos en el archivo consolidado.`);

    // 3. Filtrar los pedidos que necesitan ser descargados
    const pedidos_a_descargar = pedidos.filter(pedido => {
        const html_path = path.join(HTML_PEDIDOS_DIR, `${pedido.id_pedido}.html`);
        return !fs.existsSync(html_path);
    });

    if (pedidos_a_descargar.length === 0) {
        console.log('✅ ¡Excelente! Todos los pedidos ya tienen su HTML descargado.');
        return;
    }

    console.log(`📥 Se descargarán los detalles de ${pedidos_a_descargar.length} pedidos nuevos.`);

    // 4. Iniciar el navegador
    console.log('🚀 Iniciando navegador...');
    const browser = await chromium.launch({ headless: false }); // Cambiar a true para modo silencioso
    const context = await browser.newContext({ storageState: COOKIES_PATH });

    // 5. Iterar y descargar cada página
    for (let i = 0; i < pedidos_a_descargar.length; i++) {
        const pedido = pedidos_a_descargar[i];
        const page = await context.newPage();
        const url = `https://sellercentral.amazon.com/orders-v3/order/${pedido.id_pedido}`;
        const outputPath = path.join(HTML_PEDIDOS_DIR, `${pedido.id_pedido}.html`);

        try {
            console.log(`\n[${i + 1}/${pedidos_a_descargar.length}] Navegando a: ${url}`);
            await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 90000 });
            
            console.log('- Esperando 5 segundos para carga de elementos dinámicos...');
            await page.waitForTimeout(5000);

            const htmlContent = await page.content();
            fs.writeFileSync(outputPath, htmlContent, 'utf-8');
            console.log(`✅ HTML guardado en: ${outputPath}`);

        } catch (error) {
            console.error(`❌ Ocurrió un error al descargar el pedido ${pedido.id_pedido}:`, error);
        } finally {
            await page.close();
            // Pausa entre peticiones para no sobrecargar el servidor
            if (i < pedidos_a_descargar.length - 1) {
                const delay = Math.random() * (5000 - 2000) + 2000; // Pausa entre 2 y 5 segundos
                console.log(`⏳ Pausa de ${(delay / 1000).toFixed(1)} segundos...`);
                await sleep(2000, 5000);
            }
        }
    }

    await browser.close();
    console.log('\n🎉 Proceso de descarga finalizado.');
})();