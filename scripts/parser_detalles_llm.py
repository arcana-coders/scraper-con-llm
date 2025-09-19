# scripts/parser_detalles_llm.py

import re
import json
import csv
from datetime import datetime
from openai import OpenAI
from pathlib import Path
from bs4 import BeautifulSoup

# === CONFIGURACIÓN ===
LLM = "llama3.1:8b"
client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

BASE_DIR = Path(__file__).resolve().parent.parent
HTML_PEDIDOS_DIR = BASE_DIR / "html_pedidos"
CSV_DIR = BASE_DIR / "csv"

OUTPUT_JSON_CONSOLIDADO = CSV_DIR / "pedidos_consolidados.json"
OUTPUT_CSV_CONSOLIDADO = CSV_DIR / "pedidos_consolidados.csv"

# --- PROMPT MEJORADO PARA DETALLES ---
PROMPT = """
Extrae la información detallada del siguiente pedido de Amazon Seller Central.

Devuelve solo un JSON válido con esta estructura:

{
  "direccion_envio": "Nombre del comprador\\nCalle y número\\nColonia\\nCiudad, Estado, Código Postal\\nPaís",
  "telefono_comprador": "555-123-4567",
  "subtotal_productos": 1500.00,
  "costo_envio": 100.00,
  "total_antes_impuestos": 1600.00,
  "impuestos": 256.00,
  "total_pedido": 1856.00
}

Reglas:
- La dirección de envío debe ser un solo string con saltos de línea (\\n).
- Si un dato numérico no está presente, usa 0.00.
- Si un dato de texto (como el teléfono) no está, usa null.
- Limpia los símbolos de moneda (MXN, $, etc.) de los valores numéricos.
- No inventes nada.
- No expliques nada.
- Devuelve solo el JSON y nada más.
"""

def limpiar_html(ruta_html: Path) -> str:
    """Limpia el HTML de scripts y estilos, devolviendo el texto plano."""
    with open(ruta_html, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)

def pedir_llm(texto: str, id_pedido: str) -> dict | None:
    """Envía un bloque de texto al LLM para extraer detalles."""
    try:
        print(f"\n🤖 Procesando detalles del pedido {id_pedido} con LLM...")
        response = client.chat.completions.create(
            model=LLM,
            messages=[
                {"role": "system", "content": PROMPT.strip()},
                {"role": "user", "content": texto}
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        content = response.choices[0].message.content.strip()
        return json.loads(content)
    except Exception as e:
        print(f"❌ Error al procesar detalles de {id_pedido} con LLM: {e}")
        return None

def guardar_datos(datos: list[dict]):
    """Guarda la lista de datos en los archivos JSON y CSV."""
    if not datos:
        return
    
    # Guardar JSON
    with open(OUTPUT_JSON_CONSOLIDADO, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
    print(f"💾 Archivo JSON actualizado en: {OUTPUT_JSON_CONSOLIDADO.resolve()}")
    
    # Guardar CSV
    headers = datos[0].keys()
    with open(OUTPUT_CSV_CONSOLIDADO, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(datos)
    print(f"🧾 Archivo CSV guardado en: {OUTPUT_CSV_CONSOLIDADO.resolve()}")

def main():
    if not OUTPUT_JSON_CONSOLIDADO.exists():
        print(f"❌ No se encuentra el archivo base {OUTPUT_JSON_CONSOLIDADO}. Ejecuta primero el parser principal.")
        return

    with open(OUTPUT_JSON_CONSOLIDADO, "r", encoding="utf-8") as f:
        pedidos = json.load(f)

    # Convertir a diccionario para fácil acceso y actualización
    pedidos_dict = {p["id_pedido"]: p for p in pedidos}
    
    # Identificar pedidos a los que les faltan detalles (usando 'direccion_envio' como indicador)
    pedidos_a_procesar = [p for p in pedidos if "direccion_envio" not in p]

    if not pedidos_a_procesar:
        print("✅ ¡Excelente! Todos los pedidos en la base de datos ya tienen sus detalles completos.")
        return

    print(f"🔍 Se encontraron {len(pedidos_a_procesar)} pedidos que necesitan ser enriquecidos con detalles.")
    
    pedidos_actualizados = 0
    for pedido_base in pedidos_a_procesar:
        id_pedido = pedido_base["id_pedido"]
        html_path = HTML_PEDIDOS_DIR / f"{id_pedido}.html"
        
        if not html_path.exists():
            print(f"⚠️ No se encontró el archivo HTML para el pedido {id_pedido}. Ejecuta primero el script de descarga.")
            continue
            
        texto_limpio = limpiar_html(html_path)
        detalles_extraidos = pedir_llm(texto_limpio, id_pedido)

        if detalles_extraidos:
            # Actualizar el diccionario del pedido con los nuevos datos
            pedidos_dict[id_pedido].update(detalles_extraidos)
            pedidos_actualizados += 1
            print(f"✨ Detalles de {id_pedido} extraídos y añadidos.")

    if pedidos_actualizados > 0:
        print(f"\n🔄 Se actualizaron {pedidos_actualizados} pedidos. Guardando archivos...")
        # Convertir el diccionario de nuevo a una lista para guardar
        lista_final_pedidos = list(pedidos_dict.values())
        guardar_datos(lista_final_pedidos)
    else:
        print("\n🏁 No se actualizaron pedidos en esta ejecución.")
        
    print("\n✅ Proceso de enriquecimiento de datos finalizado.")

if __name__ == "__main__":
    main()