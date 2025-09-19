# scripts/parser_html_llm_v2.py

import json
import csv
from datetime import datetime
from openai import OpenAI
from pathlib import Path
import re

# === CONFIGURACIÓN ===
# Activa el modo de depuración para ver todo en consola
MODO_DEPURACION = True

LLM = "llama3.1:8b"
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

BASE_DIR = Path(__file__).resolve().parent.parent
HTML_DIR = BASE_DIR / "html"
CSV_DIR = BASE_DIR / "csv"
OUTPUT_JSON_CONSOLIDADO = CSV_DIR / "pedidos_consolidados.json"
OUTPUT_CSV_CONSOLIDADO = CSV_DIR / "pedidos_consolidados.csv"

# === PROMPTS PARA LA CADENA DE DOS PASOS ===

PROMPT_LIMPIEZA = """
Tu tarea es SOLAMENTE extraer y devolver el código HTML de la tabla que contiene los pedidos de Amazon Seller Central.

INSTRUCCIONES IMPORTANTES:
1. Busca en el HTML una tabla que contenga múltiples filas con datos de pedidos (ID de pedido, fechas, productos, ASIN, SKU, etc.)
2. Extrae ÚNICAMENTE esa tabla completa con sus tags <table>, <tr>, <td>, etc.
3. NO agregues explicaciones, comentarios ni texto adicional
4. NO digas "Aquí está el HTML" o similar
5. Devuelve SOLAMENTE el código HTML de la tabla, nada más

Si no encuentras una tabla clara, busca un div o contenedor que liste múltiples pedidos y devuelve ese HTML.

RESPONDE ÚNICAMENTE CON HTML VÁLIDO.
"""

PROMPT_EXTRACCION = """
Eres un experto en extracción de datos. El siguiente código HTML contiene una lista de pedidos de Amazon. Tu tarea es parsear este HTML y extraer la información de CADA pedido.

Devuelve una lista de objetos JSON, donde cada objeto representa un pedido. La estructura debe ser:

[
  {
    "fecha_pedido": "YYYY-MM-DD",
    "id_pedido": "000-0000000-0000000",
    "producto": "Nombre completo del producto",
    "asin": "B0XXXXXXXX",
    "sku": "SKU-DEL-PRODUCTO",
    "cantidad": 1,
    "subtotal": 1234.56,
    "estado_pedido": "No enviado"
  }
]

Reglas:
- Extrae la información para TODOS los pedidos que encuentres en el HTML.
- Convierte las fechas a formato ISO (YYYY-MM-DD).
- Limpia los valores numéricos, eliminando símbolos de moneda y usando un punto como separador decimal.
- Si un campo no se encuentra para un pedido, usa `null`.
- Tu respuesta debe ser ÚNICAMENTE la lista de objetos JSON. No incluyas explicaciones, texto introductorio ni la palabra "json" al principio.
"""

def encontrar_html_mas_reciente(directorio: Path) -> Path | None:
    print(f"🔎 Buscando archivos HTML en: {directorio}")
    archivos_html = list(directorio.glob("pedidos_*.html"))
    if not archivos_html:
        return None
    archivo_mas_reciente = max(archivos_html, key=lambda p: p.name)
    print(f"📄 Se usará el archivo más reciente: {archivo_mas_reciente.name}")
    return archivo_mas_reciente

def llm_limpiar_html(html_crudo: str) -> str | None:
    print("🤖 Paso 1: Pidiendo al LLM que aísle el HTML de la tabla de pedidos...")
    try:
        response = client.chat.completions.create(
            model=LLM,
            messages=[
                {"role": "system", "content": PROMPT_LIMPIEZA.strip()},
                {"role": "user", "content": html_crudo}
            ],
            temperature=0,
        )
        html_limpio = response.choices[0].message.content.strip()
        
        # *** AGREGANDO LOGS DETALLADOS ***
        if MODO_DEPURACION:
            print("\n" + "="*20 + " RESPUESTA CRUDA DEL LLM (PASO 1) " + "="*20)
            print(f"Longitud de respuesta: {len(html_limpio)} caracteres")
            print(f"Contiene '<': {'<' in html_limpio}")
            print(f"Primeros 500 caracteres:")
            print(repr(html_limpio[:500]))
            print("="*68 + "\n")
        
        return html_limpio
    except Exception as e:
        print(f"❌ Error en el Paso 1 (Limpieza con LLM): {e}")
        return None

def llm_extraer_datos(html_limpio: str) -> list[dict] | None:
    print("🤖 Paso 2: Pidiendo al LLM que extraiga los datos estructurados del HTML limpio...")
    try:
        response = client.chat.completions.create(
            model=LLM,
            messages=[
                {"role": "system", "content": PROMPT_EXTRACCION.strip()},
                {"role": "user", "content": html_limpio}
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        content = response.choices[0].message.content.strip()
        
        if MODO_DEPURACION:
            print("\n" + "="*20 + " RESPUESTA CRUDA DEL LLM (PASO 2) " + "="*20)
            print(content)
            print("="*68 + "\n")

        parsed_json = json.loads(content)
        if isinstance(parsed_json, list):
            return parsed_json
        elif isinstance(parsed_json, dict):
             # Si el LLM devuelve un solo objeto en lugar de una lista, lo envolvemos en una lista para poder procesarlo
             print("ℹ️  El LLM devolvió un solo objeto, se convertirá en una lista de un solo elemento.")
             return [parsed_json]
        else:
            print(f"⚠️ La respuesta del LLM no es una lista ni un diccionario. Tipo: {type(parsed_json)}")
            return None

    except Exception as e:
        print(f"❌ Error en el Paso 2 (Extracción con LLM): {e}")
        return None

def guardar_datos(datos: list[dict]):
    if not datos:
        print("ℹ️ No hay datos para guardar.")
        return

    CSV_DIR.mkdir(parents=True, exist_ok=True)

    # Guardar JSON
    with open(OUTPUT_JSON_CONSOLIDADO, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
    print(f"💾 JSON guardado en: {OUTPUT_JSON_CONSOLIDADO}")

    # Guardar CSV
    if datos:
        keys = datos[0].keys()
        with open(OUTPUT_CSV_CONSOLIDADO, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(datos)
        print(f"💾 CSV guardado en: {OUTPUT_CSV_CONSOLIDADO}")

def main():
    if MODO_DEPURACION:
        print("="*50)
        print("🕵️  SCRIPT EN MODO DEPURACIÓN 🕵️")
        print("Se mostrará información detallada en consola.")
        print("="*50)

    html_path = encontrar_html_mas_reciente(HTML_DIR)
    if not html_path:
        print("❌ No se encontraron archivos 'pedidos_*.html'. Saliendo.")
        return

    print(f"📖 Leyendo el contenido crudo de {html_path.name}...")
    html_crudo = html_path.read_text(encoding="utf-8")
    
    # *** AGREGANDO LOG DEL TAMAÑO DEL ARCHIVO ***
    print(f"📊 Archivo HTML cargado: {len(html_crudo)} caracteres, {len(html_crudo.splitlines())} líneas")

    # --- Inicia la Cadena de LLM ---
    html_limpio = llm_limpiar_html(html_crudo)
    
    if not html_limpio or "<" not in html_limpio:
        print("🛑 El LLM no devolvió un fragmento de HTML válido en el paso de limpieza. El proceso termina.")
        return
    
    print("✅ Paso 1 completado. HTML de la tabla aislado.")

    if MODO_DEPURACION:
        print("\n" + "="*20 + " HTML AISLADO ENVIADO AL PASO 2 " + "="*20)
        print(html_limpio)
        print("="*66 + "\n")

    pedidos_del_html = llm_extraer_datos(html_limpio)
    
    if not pedidos_del_html:
        print("🛑 El LLM no extrajo ningún pedido del HTML limpio. El proceso termina.")
        return

    # Si estamos en modo depuración, solo mostramos lo que se extrajo y terminamos.
    if MODO_DEPURACION:
        print("📦 Contenido extraído por el LLM en modo depuración:")
        print(json.dumps(pedidos_del_html, indent=2, ensure_ascii=False))
        print("\n🏁 Proceso de depuración completado. No se guardó nada.")
        return

    print(f"✅ Paso 2 completado. Se extrajeron {len(pedidos_del_html)} pedidos del HTML.\n")
    
    # --- Lógica de actualización (solo se ejecuta si MODO_DEPURACION es False) ---
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
    else:
        print("📋 No se encontró un archivo JSON previo.")

    nuevos_pedidos = []
    for pedido_html in pedidos_del_html:
        id_actual = pedido_html.get("id_pedido")
        if id_actual and id_actual not in ids_existentes:
            print(f"✨ Pedido nuevo encontrado: {id_actual}. Se agregará.")
            pedido_html["fecha_procesado"] = datetime.now().isoformat()
            nuevos_pedidos.append(pedido_html)

    if not nuevos_pedidos:
        print("\n🏁 No se encontraron pedidos nuevos para agregar. Los archivos están actualizados.")
    else:
        print(f"\n➕ Se agregarán {len(nuevos_pedidos)} pedidos nuevos a los archivos.")
        lista_final = sorted(pedidos_existentes + nuevos_pedidos, key=lambda p: p.get("fecha_procesado", ""))
        
        CSV_DIR.mkdir(parents=True, exist_ok=True)
        guardar_datos(lista_final)

    print("\n✅ Proceso completado.")

if __name__ == "__main__":
    main()
