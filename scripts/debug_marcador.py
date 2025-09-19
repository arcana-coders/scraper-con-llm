# scripts/debug_marcador.py
import pathlib

print("--- INICIANDO SCRIPT DE DEPURACIÓN DE MARCADORES ---")

# 1. Definir la ruta al archivo problemático
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
RUTA_ARCHIVO = BASE_DIR / "html" / "pedidos_limpio_20250722.txt"

print(f"Analizando el archivo: {RUTA_ARCHIVO}\n")

# 2. Definir los marcadores que buscamos
MARCADORES = ["hace ", "Hoy", "Ayer"]
print(f"Buscando líneas que cumplan alguna de estas condiciones:")
print(f"  - linea.strip().startswith('{MARCADORES[0]}')")
print(f"  - linea.strip() == '{MARCADORES[1]}'")
print(f"  - linea.strip() == '{MARCADORES[2]}'\n")


# 3. Leer el archivo y analizar línea por línea
try:
    # Usamos read().splitlines() para evitar problemas con finales de línea
    with open(RUTA_ARCHIVO, 'r', encoding='utf-8') as f:
        lineas = f.read().splitlines()
except FileNotFoundError:
    print(f"ERROR: No se pudo encontrar el archivo. Asegúrate de que la ruta es correcta.")
    exit()

encontrados = 0
# Analizamos las primeras 100 líneas, que es donde deberían estar los marcadores.
for i, linea in enumerate(lineas[:100]):
    linea_limpia = linea.strip()

    # Analizamos solo las líneas que podrían ser un marcador para mantener la salida limpia
    if "hace" in linea_limpia or "Hoy" in linea_limpia or "Ayer" in linea_limpia:
        print(f"--- Posible marcador encontrado en la línea #{i+1} ---")
        print(f"Texto de la línea: '{linea_limpia}'")
        # repr() nos mostrará caracteres invisibles o especiales
        print(f"Representación real (repr): {repr(linea)}")

        # Realizamos y reportamos cada una de las comprobaciones
        check1 = linea_limpia.startswith(MARCADORES[0])
        print(f"Resultado de .startswith('hace '): {check1}")

        check2 = linea_limpia == MARCADORES[1]
        print(f"Resultado de == 'Hoy': {check2}")

        check3 = linea_limpia == MARCADORES[2]
        print(f"Resultado de == 'Ayer': {check3}")

        if check1 or check2 or check3:
            print("✅ VEREDICTO: ¡COINCIDENCIA ENCONTRADA!\n")
            encontrados += 1
        else:
            print("❌ VEREDICTO: ¡NO HAY COINCIDENCIA!\n")


print("--- ANÁLISIS FINALIZADO ---")
if encontrados > 0:
    print(f"Se encontraron {encontrados} marcadores de inicio de pedido.")
else:
    print("No se encontró ningún marcador. Esto confirma el error del script principal.")
    print("Revisa la 'Representación real (repr)' de las líneas para ver si hay caracteres inesperados.")