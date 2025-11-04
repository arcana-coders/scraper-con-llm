# 📋 Instrucciones de Uso - Proyecto Amazon Pedidos

## 🎯 Objetivo del Proyecto
Este proyecto automatiza la extracción y procesamiento de pedidos desde Amazon Seller Central mediante un flujo de 5 pasos que incluye autenticación, scraping web, y procesamiento de datos con IA.

## 📁 Estructura del Proyecto
```
amazon_pedidos/
├── scripts/              # Scripts de automatización
├── cookies/              # Archivos de sesión (session.json)
├── html/                 # HTML de páginas de pedidos descargadas
├── html_pedidos/         # HTML individual de cada pedido
├── csv/                  # Archivos consolidados finales
└── csv/backup/           # Respaldos automáticos
```

## 🔄 Flujo de Trabajo Completo

**🎯 CONCEPTO CLAVE:** El proyecto mantiene un **CSV acumulativo** que nunca se borra. Cada ejecución:
1. **SIEMPRE** extrae HTML fresco para detectar nuevas ventas
2. **SOLO** procesa pedidos que NO están en el CSV existente
3. **AGREGA** nuevos pedidos al CSV sin eliminar histórico

### 📝 Prerrequisitos
1. **Node.js** instalado con las dependencias del proyecto:
   ```powershell
   npm install
   ```

2. **Python** con las siguientes librerías:
   ```powershell
   pip install openai pathlib beautifulsoup4
   ```

3. **Servidor Ollama** ejecutándose en `http://localhost:11434` con el modelo `llama3.1:8b`

---

## 🧠 **RECOMENDACIÓN: USA CEREBRO**

En lugar de ejecutar cada paso manualmente, usa el script maestro:

```powershell
python cerebro.py
```

**Ventajas de CEREBRO:**
- ✅ **Un solo comando** en lugar de 5 pasos separados
- ✅ **Login guiado** y seguro (no automatizado)
- ✅ **Detección inteligente** de solo pedidos nuevos
- ✅ **Recuperación automática** de errores e interrupciones
- ✅ **Backup automático** con timestamp
- ✅ **Logging detallado** con colores y timestamps
- ✅ **Auto-reset** para próximas ejecuciones

**Los pasos manuales siguientes son solo para debugging o casos especiales.**

---

## 🚀 Pasos de Ejecución Manual

### Paso 1: Autenticación en Amazon 🔐

#### **🧠 Con CEREBRO (RECOMENDADO)**
```powershell
python cerebro.py
```
- CEREBRO te guiará paso a paso
- Te pedirá ejecutar el login en otra terminal
- Esperará tu confirmación antes de continuar
- **MÁS SEGURO**: No automatiza la autenticación

#### **📋 Manual (para debugging)**
```powershell
node scripts/login_amazon.js
```

**¿Qué hace?**
- Abre una ventana de navegador en Amazon Seller Central
- Te permite iniciar sesión manualmente
- Guarda las cookies de sesión para uso posterior

**¿Qué genera?**
- `cookies/session.json` - Archivo con las cookies de autenticación

**🔒 Proceso de Login Seguro:**
1. Abre el navegador automáticamente
2. Navega a Amazon Seller Central
3. **TÚ** completas el login manualmente (incluyendo 2FA)
4. El script detecta cuando terminas y guarda las cookies
5. Cierra el navegador automáticamente

**¿Qué necesita?**
- Conexión a internet
- Credenciales válidas de Amazon Seller Central

**✅ Indicador de éxito:** Se crea el archivo `session.json` en la carpeta `cookies/`

---

### Paso 2: Extracción de HTML de Lista de Pedidos 📄
**Script:** `extraer_html_tabla.js`
```powershell
node scripts/extraer_html_tabla.js
```

**¿Qué hace?**
- Navega automáticamente a la página de pedidos usando las cookies guardadas
- Descarga el HTML completo de la tabla de pedidos
- **IMPORTANTE:** Este paso SIEMPRE se ejecuta para detectar nuevas ventas
- Espera 10 segundos para asegurar la carga de elementos dinámicos

**¿Qué genera?**
- `html/pedidos_YYYYMMDD.html` - HTML fresco con TODOS los pedidos actuales

**¿Qué necesita?**
- `cookies/session.json` (del Paso 1)
- Sesión válida (no expirada)

**📊 Resultado esperado:**
- HTML actualizado que contiene nuevos pedidos + pedidos ya procesados

**✅ Indicador de éxito:** Se crea un archivo HTML en la carpeta `html/`

---

### Paso 3: Procesamiento de Lista de Pedidos con IA 🤖
**Script:** `parser_tabla_llm.py`
```powershell
python scripts/parser_tabla_llm.py
```

**¿Qué hace?**
- Encuentra el archivo HTML más reciente en la carpeta `html/`
- Limpia el HTML a texto plano usando BeautifulSoup
- Divide el texto en bloques individuales usando marcadores como "hace X días"
- Usa IA para extraer datos estructurados de cada pedido individualmente
- Consolida toda la información en archivos JSON y CSV

**¿Qué genera?**
- `csv/pedidos_consolidados.json` - Datos estructurados en formato JSON
- `csv/pedidos_consolidados.csv` - Datos estructurados en formato CSV
- `html/pedidos_limpio_YYYYMMDD.txt` - Texto limpio para depuración

**¿Qué necesita?**
- Archivo HTML del Paso 2
- Servidor Ollama ejecutándose con modelo `llama3.1:8b`

**✅ Indicador de éxito:** Se crean archivos consolidados en la carpeta `csv/`

---

### Paso 4: Descarga de Detalles Individuales de Pedidos 📥
**Script:** `extraer_detalles_pedidos.js`
```powershell
node scripts/extraer_detalles_pedidos.js
```

**¿Qué hace?**
- Lee el archivo `pedidos_consolidados.json`
- Identifica qué pedidos necesitan descargarse (los que no tienen HTML)
- Visita cada página individual de pedido y descarga su HTML
- Incluye pausas aleatorias entre descargas para evitar sobrecargar el servidor

**¿Qué genera?**
- `html_pedidos/[ID_PEDIDO].html` - Un archivo por cada pedido individual

**¿Qué necesita?**
- `csv/pedidos_consolidados.json` (del Paso 3)
- `cookies/session.json` (del Paso 1, sesión válida)

**✅ Indicador de éxito:** Se crean archivos HTML individuales en `html_pedidos/`

---

### Paso 5: Extracción de Detalles con IA 🧠
**Script:** `parser_detalles_llm.py`
```powershell
python scripts/parser_detalles_llm.py
```

**¿Qué hace?**
- Procesa cada archivo HTML individual de la carpeta `html_pedidos/`
- Extrae información detallada de cada pedido (dirección, teléfono, costos, impuestos)
- Limpia y estructura los datos usando IA
- Consolida todo en archivos finales actualizados

**¿Qué genera?**
- Actualiza `csv/pedidos_consolidados.json` con información detallada
- Actualiza `csv/pedidos_consolidados.csv` con información detallada

**¿Qué necesita?**
- Archivos HTML del Paso 4
- Servidor Ollama ejecutándose con modelo `llama3.1:8b`

**✅ Indicador de éxito:** Los archivos consolidados se actualizan con información detallada

---

## 🛠️ Scripts de Utilidad

### `parser_tabla_llm.py`
Script principal para procesar la tabla de pedidos. Limpia el HTML a texto plano y procesa cada pedido individualmente con IA.

### `parser_html_llm_v2.py` 
Script alternativo que intenta procesar todo el HTML de una vez usando IA en 2 pasos. **Nota:** Puede tener problemas con archivos HTML muy grandes o complejos.

### `debug_lector.py`
Herramienta de diagnóstico que analiza archivos de texto para encontrar caracteres invisibles que puedan causar problemas de parsing.

### `debug_marcador.py`
Herramienta específica para diagnosticar problemas con marcadores de tiempo en los archivos de texto.

---

## 🔧 Configuración

### Configuración de Ollama
- **URL:** `http://localhost:11434/v1`
- **Modelo requerido:** `llama3.1:8b`

### Configuración de URL de Amazon
```javascript
const URL_PEDIDOS = 'https://sellercentral.amazon.com/orders-v3/mfn/unshipped/?page=1';
```

---

## ⚠️ Notas Importantes

1. **Orden de Ejecución:** Los pasos deben ejecutarse en el orden especificado (1→2→3→4→5)

2. **Sesión de Cookies:** La sesión puede expirar. Si los scripts fallan por autenticación, ejecuta nuevamente el Paso 1.

3. **Modo Depuración:** Los scripts de Python incluyen flags `MODO_DEPURACION` para ver output detallado.

4. **Pausas Automáticas:** Los scripts incluyen pausas para evitar ser bloqueados por Amazon.

5. **Respaldos:** Los archivos importantes se respaldan automáticamente en `csv/backup/`

---

## 🚨 Solución de Problemas

### Error: "No se encuentra session.json"
- **Solución:** Ejecutar primero `login_amazon.js`

### Error: "Archivo HTML no encontrado"
- **Solución:** Verificar que el paso anterior se ejecutó correctamente

### Error: "Conexión a Ollama fallida"
- **Solución:** Verificar que el servidor Ollama esté ejecutándose y accesible

### Error: "Sesión expirada"
- **Solución:** Re-ejecutar `login_amazon.js` para renovar cookies

---

## 📊 Archivos de Salida Final

Al completar todo el flujo, tendrás:
- **`csv/pedidos_consolidados.json`** - Datos completos en formato JSON (acumulativo)
- **`csv/pedidos_consolidados.csv`** - Datos completos en formato CSV (acumulativo)
- **`html_pedidos/`** - Respaldo HTML de cada pedido individual
- **`csv/backup/`** - Respaldos automáticos con timestamp

### 💾 **Sistema de Backup Inteligente:**
- **CEREBRO**: Crea backups automáticos con timestamp al final de cada ejecución
- **Manual**: Debes crear backups manualmente antes de ejecutar
- **Formato**: `pedidos_consolidados_YYYYMMDD_HHMMSS.csv/json`
- **Ubicación**: `csv/backup/`

### 📈 **CSV Acumulativo:**
- **Nunca se borra**: Solo se agregan nuevos pedidos
- **Histórico completo**: Perfecto para análisis de tendencias
- **Detección inteligente**: Solo procesa pedidos que no están en el archivo

---

## 🎯 Estructura de Datos Final

Los archivos consolidados contienen:
```json
{
  "fecha_pedido": "2025-07-17",
  "id_pedido": "701-1234567-8901234",
  "producto": "Nombre del producto",
  "asin": "B0XXX1234",
  "sku": "SKU del producto",
  "cantidad": 1,
  "subtotal": 599.00,
  "fecha_limite_envio": "2025-07-20",
  "estado_pedido": "Pendiente",
  "direccion_envio": "Dirección completa",
  "telefono_comprador": "555-123-4567",
  "costo_envio": 100.00,
  "impuestos": 95.84,
  "total_pedido": 794.84
}
```
