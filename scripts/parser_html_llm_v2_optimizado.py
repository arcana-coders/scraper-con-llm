# scripts/parser_html_llm_v2_optimizado.py

import json
import csv
from datetime import datetime
from openai import OpenAI
from pathlib import Path
import re
from bs4 import BeautifulSoup

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

# === PROMPTS OPTIMIZADOS ===

PROMPT_EXTRACCION = """
INSTRUCCIONES ESPECÍFICAS:
1. El HTML contiene una tabla de pedidos de Amazon Seller Central
2. Extrae CADA pedido individual que encuentres  
3. Busca patrones como "701-XXXXXXX-XXXXXXX" o "702-XXXXXXX-XXXXXXX" para los IDs de pedido
4. Busca fechas en formato DD/MM/YYYY o fechas relativas como "hace X días"
5. Busca ASINs (códigos que empiezan con B seguidos de números/letras)
6. Busca SKUs y precios en formato $X,XXX.XX

FORMATO DE RESPUESTA:
Devuelve ÚNICAMENTE un objeto JSON con la clave "pedidos" y una lista de pedidos:

{
  "pedidos": [
    {
      "fecha_pedido": "2025-08-20",
      "id_pedido": "701-3601196-7811403",
      "producto": "Loctite Naval Jelly - Disolvente de óxido, 8 onzas, botella",
      "asin": "B000C014ZI",
      "sku": "1C0H-RLEO-QIPK",
      "cantidad": 1,
      "subtotal": 699.00,
      "estado_pedido": "No enviado"
    }
  ]
}

REGLAS ESTRICTAS:
- NO agregues explicaciones
- NO uses ```json al inicio
- Extrae TODOS los pedidos que veas
- Convierte fechas relativas como "hace 6 días" a fecha real (resta días desde hoy que es 2025-08-26)
- Los precios como "$699.00" conviértelos a números: 699.00
- Si no encuentras un dato, usa null
"""

def encontrar_html_mas_reciente(directorio: Path) -> Path | None:
    print(f"🔎 Buscando archivos HTML en: {directorio}")
    archivos_html = list(directorio.glob("pedidos_*.html"))
    if not archivos_html:
        return None
    archivo_mas_reciente = max(archivos_html, key=lambda p: p.name)
    print(f"📄 Se usará el archivo más reciente: {archivo_mas_reciente.name}")
    return archivo_mas_reciente

def encontrar_seccion_pedidos(html_crudo: str) -> str | None:
    """
    Usa BeautifulSoup para encontrar la sección de pedidos antes de enviar al LLM
    """
    print("🔍 Buscando sección de pedidos con BeautifulSoup...")
    
    try:
        soup = BeautifulSoup(html_crudo, 'html.parser')
        
        # Buscar por diferentes patrones comunes en Amazon
        candidatos = []
        
        # 1. Buscar tablas que podrían contener pedidos
        tablas = soup.find_all('table')
        for tabla in tablas:
            texto_tabla = tabla.get_text(strip=True).lower()
            if any(palabra in texto_tabla for palabra in ['pedido', 'order', 'asin', 'sku']):
                candidatos.append(('tabla', tabla, len(str(tabla))))
                
        # 2. Buscar divs que podrían contener listas de pedidos
        divs = soup.find_all('div', class_=re.compile(r'order|pedido|item|product', re.I))
        for div in divs:
            if len(div.find_all(['div', 'span', 'p'])) > 5:  # Tiene estructura compleja
                candidatos.append(('div', div, len(str(div))))
                
        # 3. Buscar por IDs o clases específicas
        secciones_especificas = soup.find_all(['div', 'section'], 
                                            id=re.compile(r'order|pedido|content|main', re.I))
        for seccion in secciones_especificas:
            candidatos.append(('seccion', seccion, len(str(seccion))))
            
        if candidatos:
            # Ordenar por tamaño (los más grandes probablemente tienen más contenido)
            candidatos.sort(key=lambda x: x[2], reverse=True)
            
            print(f"🎯 Encontrados {len(candidatos)} candidatos:")
            for i, (tipo, elemento, tamaño) in enumerate(candidatos[:3]):
                print(f"   {i+1}. {tipo}: {tamaño} caracteres")
            
            # Retornar el primer candidato (más grande)
            return str(candidatos[0][1])
        else:
            print("⚠️ No se encontraron secciones relevantes, usando una porción del HTML original...")
            # Si no encontramos nada específico, tomar la parte media del HTML
            # (donde usualmente está el contenido principal)
            lineas = html_crudo.split('\n')
            inicio = len(lineas) // 4
            fin = 3 * len(lineas) // 4
            return '\n'.join(lineas[inicio:fin])
            
    except Exception as e:
        print(f"❌ Error procesando con BeautifulSoup: {e}")
        return None

def llm_extraer_datos(html_limpio: str) -> list[dict] | None:
    print("🤖 Pidiendo al LLM que extraiga los datos estructurados del HTML...")
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
            print("\n" + "="*20 + " RESPUESTA CRUDA DEL LLM " + "="*20)
            print(content[:1000] + "..." if len(content) > 1000 else content)
            print("="*58 + "\n")

        parsed_json = json.loads(content)
        if "pedidos" in parsed_json and isinstance(parsed_json["pedidos"], list):
            return parsed_json["pedidos"]
        elif isinstance(parsed_json, list):
            return parsed_json
        elif isinstance(parsed_json, dict):
             # Si el LLM devuelve un solo objeto en lugar de una lista, lo envolvemos en una lista para poder procesarlo
             print("ℹ️  El LLM devolvió un solo objeto, se convertirá en una lista de un solo elemento.")
             return [parsed_json]
        else:
            print(f"⚠️ La respuesta del LLM no es una lista ni un diccionario. Tipo: {type(parsed_json)}")
            return None

    except Exception as e:
        print(f"❌ Error extrayendo con LLM: {e}")
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
        print("🕵️  SCRIPT EN MODO DEPURACIÓN (OPTIMIZADO) 🕵️")
        print("Se mostrará información detallada en consola.")
        print("="*50)

    html_path = encontrar_html_mas_reciente(HTML_DIR)
    if not html_path:
        print("❌ No se encontraron archivos 'pedidos_*.html'. Saliendo.")
        return

    print(f"📖 Leyendo el contenido crudo de {html_path.name}...")
    html_crudo = html_path.read_text(encoding="utf-8")
    
    print(f"📊 Archivo HTML cargado: {len(html_crudo)} caracteres, {len(html_crudo.splitlines())} líneas")

    # --- Buscar sección relevante con BeautifulSoup ---
    html_seccion = encontrar_seccion_pedidos(html_crudo)
    
    if not html_seccion:
        print("🛑 No se pudo encontrar una sección relevante de pedidos. El proceso termina.")
        return
    
    print(f"✅ Sección encontrada: {len(html_seccion)} caracteres")

    if MODO_DEPURACION:
        print("\n" + "="*20 + " HTML DE LA SECCIÓN ENCONTRADA " + "="*20)
        print(html_seccion[:2000] + "..." if len(html_seccion) > 2000 else html_seccion)
        print("="*66 + "\n")

    # --- Extraer datos con LLM ---
    pedidos_del_html = llm_extraer_datos(html_seccion)
    
    if not pedidos_del_html:
        print("🛑 El LLM no extrajo ningún pedido del HTML. El proceso termina.")
        return

    # Si estamos en modo depuración, solo mostramos lo que se extrajo y terminamos.
    if MODO_DEPURACION:
        print("📦 Contenido extraído por el LLM en modo depuración:")
        print(json.dumps(pedidos_del_html, indent=2, ensure_ascii=False))
        print("\n🏁 Proceso de depuración completado. No se guardó nada.")
        return

    print(f"✅ Extracción completada. Se extrajeron {len(pedidos_del_html)} pedidos del HTML.\n")
    
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
