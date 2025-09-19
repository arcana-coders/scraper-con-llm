# parser_tabla_llm.py

import re
import json
import csv
from datetime import datetime
from openai import OpenAI
from pathlib import Path
from bs4 import BeautifulSoup

# === CONFIGURACIÓN ===
# --- MODO DEPURACIÓN ---
# Se desactiva para que el script guarde los archivos JSON y CSV.
MODO_DEPURACION = False

LLM = "llama3.1:8b"
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

# --- Rutas de directorios ---
BASE_DIR = Path(__file__).resolve().parent.parent
HTML_DIR = BASE_DIR / "html"
CLEAN_TXT_DIR = BASE_DIR / "html"
CSV_DIR = BASE_DIR / "csv"

# --- Nombres de los archivos de salida consolidados ---
OUTPUT_JSON_CONSOLIDADO = CSV_DIR / "pedidos_consolidados.json"
OUTPUT_CSV_CONSOLIDADO = CSV_DIR / "pedidos_consolidados.csv"

# --- Prompts ---
PROMPT_EXTRACCION = """
Extrae la información del siguiente pedido de Amazon.

Devuelve solo un JSON válido con esta estructura:

{
  "fecha_pedido": "2025-07-17",
  "id_pedido": "701-1234567-8901234",
  "producto": "Nombre del producto",
  "asin": "B0XXX1234",
  "sku": "SKU del producto",
  "cantidad": 1,
  "costo_unitario": null,
  "subtotal": 599.00,
  "fecha_limite_envio": "2025-07-20",
  "estado_pedido": "Pendiente"
}

Reglas:
- La "fecha_pedido" ES SIEMPRE la fecha en formato dd/mm/yyyy que aparece al principio del texto, justo después de una línea que dice "hace X tiempo". Este dato es obligatorio y no puede ser nulo si está presente en el texto.
- Si falta un dato (excepto la fecha del pedido si es visible), colócalo como null.
- Usa formato de fecha ISO (aaaa-mm-dd).
- No inventes nada.
- No expliques nada.
- Devuelve solo el JSON y nada más.
"""

PROMPT_DEPURACION = """
Eres un experto en extracción de datos. Analiza el siguiente bloque de texto de un pedido de Amazon y describe en detalle las diferentes secciones de información que contiene. Sé muy específico sobre las fechas que encuentres y a qué crees que se refieren. Estructura tu respuesta claramente.
"""

REGEX_ID_PEDIDO = re.compile(r"^\d{3}-\d{7}-\d{7}$")


def encontrar_html_mas_reciente(directorio: Path) -> Path | None:
    print(f"🔎 Buscando archivos HTML en: {directorio}")
    archivos_html = list(directorio.glob("pedidos_*.html"))
    if not archivos_html:
        return None
    archivo_mas_reciente = max(archivos_html, key=lambda p: p.name)
    print(f"📄 Se usará el archivo más reciente: {archivo_mas_reciente.name}")
    return archivo_mas_reciente

def limpiar_html_y_guardar(ruta_html: Path, destino_txt: Path) -> str:
    if not ruta_html.exists():
        print(f"❌ No se encuentra el archivo HTML original: {ruta_html}")
        exit(1)
    with open(ruta_html, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    texto_limpio = soup.get_text(separator="\n", strip=True)
    destino_txt.write_text(texto_limpio, encoding="utf-8")
    print(f"🧼 HTML limpio guardado en: {destino_txt}")
    return texto_limpio

def dividir_en_pedidos(texto: str) -> list[str]:
    lineas = texto.splitlines()
    bloques = []
    indices_inicio = [i for i, linea in enumerate(lineas) if linea.startswith("hace ")]

    if not indices_inicio:
        print("⚠️ No se encontraron marcadores de inicio de pedido ('hace...').")
        return []

    for i, start_index in enumerate(indices_inicio):
        end_index = -1
        for j in range(start_index + 1, len(lineas)):
            if lineas[j].strip() == "«" and lineas[j-1].strip() == "Más información":
                end_index = j
                break
        
        if end_index == -1:
            end_index = indices_inicio[i+1] -1 if i + 1 < len(indices_inicio) else len(lineas) -1
        
        bloque = "\n".join(lineas[start_index : end_index + 1]).strip()
        if bloque:
            bloques.append(bloque)
            
    return bloques

def extraer_id_del_bloque(bloque: str) -> str | None:
    for linea in bloque.splitlines():
        if REGEX_ID_PEDIDO.match(linea):
            return linea
    return None

def pedir_llm_extraccion(texto: str, id_pedido: str) -> dict | None:
    try:
        response = client.chat.completions.create(
            model=LLM,
            messages=[
                {"role": "system", "content": PROMPT_EXTRACCION.strip()},
                {"role": "user", "content": texto.strip()}
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        content = response.choices[0].message.content.strip()
        return json.loads(content)
    except Exception as e:
        print(f"❌ Error al procesar el pedido {id_pedido} con LLM: {e}")
        return None

def depurar_bloque_con_llm(texto: str) -> str:
    try:
        response = client.chat.completions.create(
            model=LLM,
            messages=[
                {"role": "system", "content": PROMPT_DEPURACION.strip()},
                {"role": "user", "content": texto.strip()}
            ],
            temperature=0,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❌ Error durante la depuración con LLM: {e}"


def guardar_csv(ruta_csv: Path, datos: list[dict]):
    if not datos: return
    headers = datos[0].keys()
    with open(ruta_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(datos)
    print(f"🧾 Archivo CSV guardado en: {ruta_csv.resolve()}")

def main():
    if MODO_DEPURACION:
        print("="*50)
        print("🕵️  SCRIPT EN MODO DEPURACIÓN 🕵️")
        print("Se analizarán los pedidos nuevos pero no se guardará nada.")
        print("="*50)

    html_original = encontrar_html_mas_reciente(HTML_DIR)
    if not html_original:
        print("❌ No se encontraron archivos 'pedidos_*.html'. Saliendo.")
        return

    match = re.search(r"pedidos_(\d{8})", html_original.name)
    if not match: return
    fecha_archivo = match.group(1)
    
    html_limpio_path = CLEAN_TXT_DIR / f"pedidos_limpio_{fecha_archivo}.txt"
    texto_limpio = limpiar_html_y_guardar(html_original, html_limpio_path)
    
    print("\n📦 Dividiendo el texto en pedidos...")
    bloques = dividir_en_pedidos(texto_limpio)
    
    if not bloques:
        print("🛑 No se procesarán pedidos.")
        return

    print(f"📦 Detectados {len(bloques)} bloques de pedidos en el archivo HTML.\n")

    pedidos_existentes = []
    ids_existentes = set()
    if OUTPUT_JSON_CONSOLIDADO.exists():
        print(f"📂 Leyendo archivo JSON existente: {OUTPUT_JSON_CONSOLIDADO}")
        try:
            with open(OUTPUT_JSON_CONSOLIDADO, "r", encoding="utf-8") as f:
                contenido = f.read()
                if contenido:
                    pedidos_existentes = json.loads(contenido)
                    ids_existentes = {p.get("id_pedido") for p in pedidos_existentes if p.get("id_pedido")}
            print(f"🔍 Encontrados {len(pedidos_existentes)} pedidos existentes.")
        except json.JSONDecodeError:
             print("⚠️ El archivo JSON existe pero está vacío o corrupto.")
             pedidos_existentes = []
             ids_existentes = set()
    else:
        print("📋 No se encontró un archivo JSON previo.")

    nuevos_pedidos = []
    for i, bloque in enumerate(bloques, 1):
        id_candidato = extraer_id_del_bloque(bloque)
        
        if not id_candidato:
            print(f"⚠️ Bloque #{i} no contiene un ID de pedido válido. Se omite.")
            continue

        if id_candidato in ids_existentes:
            print(f"🔄 Pedido {id_candidato} ya existe en el JSON. Se omite.")
            continue
        
        if MODO_DEPURACION:
            print(f"\n--- 🕵️ Analizando bloque para el pedido: {id_candidato} 🕵️ ---")
            print("Texto enviado:")
            print(bloque)
            print("-" * 20)
            explicacion = depurar_bloque_con_llm(bloque)
            print("\n📝 Explicación del LLM:")
            print("-" * 20)
            print(explicacion)
            print("-" * 20)
            continue
        else:
            print(f"🤖 Procesando pedido potencial nuevo ({id_candidato})...")
            pedido_extraido = pedir_llm_extraccion(bloque, id_candidato)
            if pedido_extraido:
                id_actual = pedido_extraido.get("id_pedido")
                if id_actual:
                    print(f"✨ Pedido nuevo procesado: {id_actual}. Se agregará.")
                    pedido_extraido["fecha_procesado"] = datetime.now().isoformat()
                    nuevos_pedidos.append(pedido_extraido)
                    ids_existentes.add(id_actual)
    
    if MODO_DEPURACION:
        print("\n🏁 Proceso de depuración completado.")
        return

    if not nuevos_pedidos:
        print("\n🏁 No se encontraron pedidos nuevos para agregar. Los archivos están actualizados.")
    else:
        print(f"\n➕ Se agregarán {len(nuevos_pedidos)} pedidos nuevos a los archivos.")
        lista_final = sorted(pedidos_existentes + nuevos_pedidos, key=lambda p: p.get("fecha_procesado", ""))
        
        CSV_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(OUTPUT_JSON_CONSOLIDADO, "w", encoding="utf-8") as f:
            json.dump(lista_final, f, indent=2, ensure_ascii=False)
        print(f"💾 Archivo JSON actualizado en: {OUTPUT_JSON_CONSOLIDADO.resolve()}")
        
        guardar_csv(OUTPUT_CSV_CONSOLIDADO, lista_final)

    print("\n✅ Proceso completado.")

if __name__ == "__main__":
    main()