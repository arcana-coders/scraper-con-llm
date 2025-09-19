# scripts/debug_lector.py
import pathlib

print("--- INICIANDO SCRIPT DE DEPURACIÓN (MODO LECTOR) ---")
print("Este script leerá las primeras 50 líneas del archivo de texto limpio")
print("y mostrará la representación real de cada una para encontrar caracteres invisibles.")

# 1. Definir la ruta al archivo problemático
BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
RUTA_ARCHIVO = BASE_DIR / "html" / "pedidos_limpio_20250722.txt"

print(f"\nAnalizando el archivo: {RUTA_ARCHIVO}\n")

# 2. Leer el archivo y analizar línea por línea
try:
    with open(RUTA_ARCHIVO, 'r', encoding='utf-8') as f:
        # Usamos read().splitlines() para evitar problemas con finales de línea
        lineas = f.read().splitlines()
except FileNotFoundError:
    print(f"ERROR: No se pudo encontrar el archivo. Asegúrate de que la ruta es correcta.")
    exit()

print("--- ANÁLISIS DE LAS PRIMERAS 50 LÍNEAS ---")
if not lineas:
    print("El archivo está vacío.")
else:
    for i, linea in enumerate(lineas[:50]):
        # Imprimimos el número de línea, el texto visible, y su representación real
        print(f"Línea #{i+1:02d} | Texto: '{linea}'")
        print(f"Línea #{i+1:02d} | Repr:  {repr(linea)}")
        print("-" * 40)

print("\n--- ANÁLISIS FINALIZADO ---")
print("Busca en la salida anterior las líneas que deberían ser marcadores (ej. 'hace 4 horas').")
print("Compara la 'Representación real (repr)' con el texto. Si ves '\\xa0' u otros '\\x..',")
print("esos son los caracteres invisibles que causan el problema.")