#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🧠 CEREBRO - Amazon Pedidos Automation Master
============================================

Script maestro que ejecuta todo el flujo del proyecto Amazon Pedidos de forma automática.
Maneja estados, recuperación de interrupciones y logging detallado.

Autor: Sistema Amazon Pedidos
Fecha: Octubre 2025
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
import requests
from typing import Dict, Any, List, Optional

# ============================================
# CONFIGURACIÓN GLOBAL
# ============================================

# Colores para terminal
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

# Configuración de rutas
BASE_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = BASE_DIR / "scripts"
COOKIES_DIR = BASE_DIR / "cookies"
HTML_DIR = BASE_DIR / "html"
HTML_PEDIDOS_DIR = BASE_DIR / "html_pedidos"
CSV_DIR = BASE_DIR / "csv"
STATE_FILE = BASE_DIR / "cerebro_estado.json"

# ============================================
# SISTEMA DE ESTADO
# ============================================

class EstadoSistema:
    """Maneja el estado del sistema para recuperación tras interrupciones"""
    
    def __init__(self):
        self.estado_actual = self.cargar_estado()
    
    def cargar_estado(self) -> Dict[str, Any]:
        """Carga el estado desde archivo"""
        if STATE_FILE.exists():
            try:
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return self.estado_inicial()
        return self.estado_inicial()
    
    def estado_inicial(self) -> Dict[str, Any]:
        """Estado inicial del sistema"""
        return {
            "ultimo_paso_completado": 0,
            "fecha_inicio": None,
            "archivos_generados": [],
            "logs": []
        }
    
    def guardar_estado(self, paso_completado: int, archivos: List[str] = None):
        """Guarda el estado actual"""
        self.estado_actual["ultimo_paso_completado"] = paso_completado
        self.estado_actual["fecha_actualizacion"] = datetime.now().isoformat()
        
        if archivos:
            self.estado_actual["archivos_generados"] = archivos
        
        try:
            with open(STATE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.estado_actual, f, indent=2, ensure_ascii=False)
        except Exception as e:
            Logger.error(f"Error guardando estado: {e}")
    
    def marcar_inicio(self):
        """Marca el inicio del proceso"""
        self.estado_actual["fecha_inicio"] = datetime.now().isoformat()
        self.guardar_estado(0)
    
    def obtener_ultimo_paso(self) -> int:
        """Obtiene el último paso completado"""
        return self.estado_actual.get("ultimo_paso_completado", 0)
    
    def limpiar_estado(self):
        """Limpia el estado para un nuevo inicio (preserva archivos CSV)"""
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        self.estado_actual = self.cargar_estado()
    
    def reset_completo(self):
        """Reset completo incluyendo archivos (PELIGROSO - no usar normalmente)"""
        # Este método existe pero no se usa en el flujo normal
        # Solo para casos excepcionales donde se quiere limpiar todo
        pass

# ============================================
# SISTEMA DE LOGGING
# ============================================

class Logger:
    """Sistema de logging con colores y timestamps"""
    
    @staticmethod
    def info(mensaje: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Colors.CYAN}[{timestamp}] ℹ️  {mensaje}{Colors.END}")
    
    @staticmethod
    def success(mensaje: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Colors.GREEN}[{timestamp}] ✅ {mensaje}{Colors.END}")
    
    @staticmethod
    def warning(mensaje: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Colors.YELLOW}[{timestamp}] ⚠️  {mensaje}{Colors.END}")
    
    @staticmethod
    def error(mensaje: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Colors.RED}[{timestamp}] ❌ {mensaje}{Colors.END}")
    
    @staticmethod
    def step(paso: int, titulo: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n{Colors.BOLD}{Colors.PURPLE}{'='*60}")
        print(f"[{timestamp}] 🎯 PASO {paso}: {titulo}")
        print(f"{'='*60}{Colors.END}\n")
    
    @staticmethod
    def substep(mensaje: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{Colors.WHITE}[{timestamp}]    ➤ {mensaje}{Colors.END}")

# ============================================
# VERIFICADORES DE PRERREQUISITOS
# ============================================

class Verificadores:
    """Verifica que todos los prerrequisitos estén cumplidos"""
    
    @staticmethod
    def verificar_ollama() -> bool:
        """Verifica que Ollama esté funcionando"""
        try:
            response = requests.get("http://localhost:11434/api/version", timeout=5)
            if response.status_code == 200:
                Logger.success("Ollama está funcionando correctamente")
                return True
            else:
                Logger.error("Ollama no responde correctamente")
                return False
        except Exception as e:
            Logger.error(f"Error conectando con Ollama: {e}")
            Logger.error("Asegúrate de que Ollama esté ejecutándose")
            return False
    
    @staticmethod
    def verificar_cookies() -> bool:
        """Verifica que existan las cookies de Amazon"""
        cookie_file = COOKIES_DIR / "session.json"
        if cookie_file.exists():
            try:
                with open(cookie_file, 'r') as f:
                    cookies = json.load(f)
                if len(cookies) > 0:
                    Logger.success("Cookies de Amazon encontradas")
                    return True
                else:
                    Logger.error("Archivo de cookies vacío")
                    return False
            except Exception as e:
                Logger.error(f"Error leyendo cookies: {e}")
                return False
        else:
            Logger.error("No se encontraron cookies de Amazon")
            return False
    
    @staticmethod
    def verificar_directorios():
        """Verifica y crea directorios necesarios"""
        Logger.substep("Verificando estructura de directorios...")
        directorios = [COOKIES_DIR, HTML_DIR, HTML_PEDIDOS_DIR, CSV_DIR, CSV_DIR / "backup"]
        
        for directorio in directorios:
            if not directorio.exists():
                directorio.mkdir(parents=True, exist_ok=True)
                Logger.info(f"Creado directorio: {directorio}")
            else:
                Logger.substep(f"Directorio existe: {directorio}")
    
    @staticmethod
    def verificar_dependencias():
        """Verifica que las dependencias estén instaladas"""
        Logger.substep("Verificando dependencias de Python...")
        try:
            import openai
            import pathlib
            from bs4 import BeautifulSoup
            Logger.success("Dependencias de Python verificadas")
        except ImportError as e:
            Logger.error(f"Dependencia faltante: {e}")
            Logger.info("Ejecuta: pip install openai pathlib beautifulsoup4")
            return False
        
        Logger.substep("Verificando Node.js...")
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                Logger.success(f"Node.js disponible: {result.stdout.strip()}")
                return True
            else:
                Logger.error("Node.js no está disponible")
                return False
        except FileNotFoundError:
            Logger.error("Node.js no está instalado")
            return False

# ============================================
# EJECUTOR DE PASOS
# ============================================

class EjecutorPasos:
    """Ejecuta cada paso del flujo del proyecto"""
    
    def __init__(self, estado: EstadoSistema, logger: Logger):
        self.estado = estado
        self.logger = logger
    
    def ejecutar_comando(self, comando: List[str], directorio: Path = BASE_DIR, timeout: int = 300) -> bool:
        """Ejecuta un comando y muestra output en tiempo real"""
        try:
            Logger.substep(f"Ejecutando: {' '.join(comando)}")
            
            # Configurar encoding para Windows
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUNBUFFERED'] = '1'  # Fuerza output inmediato
            
            # Ejecutar el comando con output en tiempo real
            process = subprocess.Popen(
                comando,
                cwd=directorio,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combinar stderr con stdout
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env,
                encoding='utf-8',
                errors='replace'  # Reemplazar caracteres problemáticos
            )
            
            # Leer output línea por línea en tiempo real
            output_lines = []
            while True:
                line = process.stdout.readline()
                if line == '' and process.poll() is not None:
                    break
                if line:
                    clean_line = line.strip()
                    output_lines.append(clean_line)
                    # Mostrar con indentación para distinguir del output de CEREBRO
                    print(f"{Colors.WHITE}   {clean_line}{Colors.END}")
            
            # Esperar a que termine completamente
            return_code = process.wait()
            
            if return_code == 0:
                Logger.success(f"Comando ejecutado exitosamente")
                return True
            else:
                Logger.error(f"Comando falló con código de salida: {return_code}")
                if output_lines:
                    Logger.error("Últimas líneas de output:")
                    for line in output_lines[-5:]:  # Mostrar últimas 5 líneas
                        Logger.error(f"   {line}")
                return False
                
        except Exception as e:
            Logger.error(f"Error ejecutando comando: {e}")
            return False

    def paso_1_login_manual(self) -> bool:
        """Paso 1: Login manual para generar cookies (SOLO INSTRUCCIONES)"""
        Logger.step(1, "Login Manual en Amazon Seller Central 🔐")
        
        print(f"\n{Colors.YELLOW}{'='*60}")
        print(f"🔐 ACCIÓN REQUERIDA: LOGIN MANUAL")
        print(f"{'='*60}{Colors.END}")
        
        print(f"{Colors.WHITE}CEREBRO NO ejecuta el login automáticamente por seguridad.{Colors.END}")
        print(f"{Colors.WHITE}Debes ejecutarlo manualmente en otra terminal.{Colors.END}")
        
        print(f"\n{Colors.CYAN}{Colors.BOLD}📍 EJECUTA EN OTRA TERMINAL:{Colors.END}")
        print(f"{Colors.CYAN}{Colors.BOLD}    node scripts/login_amazon.js{Colors.END}")
        
        print(f"\n{Colors.WHITE}📋 Proceso de login:{Colors.END}")
        print(f"  1️⃣  Abre una nueva terminal (PowerShell/CMD)")
        print(f"  2️⃣  Navega a: {BASE_DIR}")
        print(f"  3️⃣  Ejecuta: node scripts/login_amazon.js")
        print(f"  4️⃣  Completa el login en el navegador que se abre")
        print(f"  5️⃣  Espera a que el script termine y cierre el navegador")
        print(f"  6️⃣  Regresa aquí y presiona ENTER")
        
        print(f"\n{Colors.YELLOW}⚠️  Importante:{Colors.END}")
        print(f"  • Completa TODO el proceso de login (incluyendo 2FA)")
        print(f"  • NO cierres el navegador manualmente")
        print(f"  • Espera a que el script termine automáticamente")
        print(f"  • Las cookies se guardarán en: cookies/session.json")
        
        print(f"\n{Colors.RED}🛑 CEREBRO ESPERANDO TU CONFIRMACIÓN 🛑{Colors.END}")
        
        # Bucle hasta que las cookies estén disponibles
        while True:
            try:
                # Limpiar buffer de entrada
                import sys
                if hasattr(sys.stdin, 'flush'):
                    sys.stdin.flush()
                
                respuesta = input(f"\n{Colors.GREEN}{Colors.BOLD}>>> Presiona ENTER cuando hayas completado el login <<<{Colors.END}")
                
                # Verificar cookies después de cada confirmación
                if Verificadores.verificar_cookies():
                    Logger.success("✅ Cookies detectadas correctamente")
                    self.estado.guardar_estado(1, ["cookies/session.json"])
                    return True
                else:
                    print(f"\n{Colors.RED}❌ No se detectaron cookies válidas{Colors.END}")
                    print(f"{Colors.YELLOW}¿Completaste el proceso de login?{Colors.END}")
                    print(f"{Colors.WHITE}  • ¿Se cerró el navegador automáticamente?{Colors.END}")
                    print(f"{Colors.WHITE}  • ¿Aparece cookies/session.json en tu carpeta?{Colors.END}")
                    
                    continuar = input(f"\n{Colors.CYAN}¿Quieres intentar de nuevo? (ENTER=Sí, Ctrl+C=Cancelar): {Colors.END}")
                    continue
                    
            except KeyboardInterrupt:
                Logger.error("Proceso cancelado por el usuario")
                return False

    def paso_2_extraer_html(self) -> bool:
        """Paso 2: Extracción del HTML de la tabla de pedidos"""
        Logger.step(2, "Extracción del HTML de la tabla de pedidos 🕷️")
        
        # Verificar cookies
        if not Verificadores.verificar_cookies():
            return False
        
        # Ejecutar script de extracción
        comando = ["node", "scripts/extraer_html_tabla.js"]
        if not self.ejecutar_comando(comando):
            return False
        
        # Verificar que se creó el archivo HTML
        archivos_html = list(HTML_DIR.glob("pedidos_*.html"))
        if archivos_html:
            archivo_mas_reciente = max(archivos_html, key=lambda p: p.name)
            Logger.success(f"HTML generado: {archivo_mas_reciente.name}")
            self.estado.guardar_estado(2, [str(archivo_mas_reciente)])
            return True
        else:
            Logger.error("No se generó archivo HTML")
            return False
    
    def paso_3_procesar_ia(self) -> bool:
        """Paso 3: Procesamiento de Lista de Pedidos con IA"""
        Logger.step(3, "Procesamiento de Lista de Pedidos con IA 🤖")
        
        # Verificar Ollama
        if not Verificadores.verificar_ollama():
            return False
        
        # Verificar que existe HTML del paso anterior
        archivos_html = list(HTML_DIR.glob("pedidos_*.html"))
        if not archivos_html:
            Logger.error("No se encontró archivo HTML del paso 2")
            return False
        
        # Ejecutar parser con IA
        comando = ["python", "scripts/parser_tabla_llm.py"]
        if not self.ejecutar_comando(comando):
            return False
        
        # Verificar archivos generados
        archivos_generados = []
        json_file = CSV_DIR / "pedidos_consolidados.json"
        csv_file = CSV_DIR / "pedidos_consolidados.csv"
        
        if json_file.exists():
            archivos_generados.append(str(json_file))
            Logger.success(f"JSON generado: {json_file}")
        
        if csv_file.exists():
            archivos_generados.append(str(csv_file))
            Logger.success(f"CSV generado: {csv_file}")
        
        if archivos_generados:
            self.estado.guardar_estado(3, archivos_generados)
            return True
        else:
            Logger.error("No se generaron archivos consolidados")
            return False
    
    def paso_4_descargar_individuales(self) -> bool:
        """Paso 4: Descarga de HTML de pedidos individuales"""
        Logger.step(4, "Descarga de HTML de pedidos individuales 📥")
        
        # Verificar que existe el JSON con los pedidos
        json_file = CSV_DIR / "pedidos_consolidados.json"
        if not json_file.exists():
            Logger.error("No se encontró archivo JSON del paso 3")
            return False
        
        # Ejecutar descarga de pedidos individuales
        comando = ["node", "scripts/extraer_detalles_pedidos.js"]
        if not self.ejecutar_comando(comando, timeout=600):  # Timeout más largo para descargas
            return False
        
        # Verificar archivos descargados
        archivos_individuales = list(HTML_PEDIDOS_DIR.glob("*.html"))
        if archivos_individuales:
            Logger.success(f"Descargados {len(archivos_individuales)} archivos HTML individuales")
            self.estado.guardar_estado(4, [str(f) for f in archivos_individuales])
            return True
        else:
            Logger.error("No se descargaron archivos HTML individuales")
            return False
    
    def paso_5_extraer_detalles(self) -> bool:
        """Paso 5: Extracción de detalles completos con IA"""
        Logger.step(5, "Extracción de detalles completos con IA 🎯")
        
        # Verificar Ollama
        if not Verificadores.verificar_ollama():
            return False
        
        # Verificar archivos HTML individuales
        archivos_individuales = list(HTML_PEDIDOS_DIR.glob("*.html"))
        if not archivos_individuales:
            Logger.error("No se encontraron archivos HTML individuales del paso 4")
            return False
        
        Logger.info(f"Procesando {len(archivos_individuales)} archivos HTML individuales")
        
        # Ejecutar extracción de detalles
        comando = ["python", "scripts/parser_detalles_llm.py"]
        if not self.ejecutar_comando(comando, timeout=900):  # Timeout más largo para IA
            return False
        
        # Verificar actualización de archivos
        json_file = CSV_DIR / "pedidos_consolidados.json"
        csv_file = CSV_DIR / "pedidos_consolidados.csv"
        
        archivos_actualizados = []
        if json_file.exists():
            archivos_actualizados.append(str(json_file))
        if csv_file.exists():
            archivos_actualizados.append(str(csv_file))
        
        if archivos_actualizados:
            Logger.success("Archivos consolidados actualizados con detalles completos")
            self.estado.guardar_estado(5, archivos_actualizados)
            return True
        else:
            Logger.error("Error actualizando archivos consolidados")
            return False

# ============================================
# CEREBRO PRINCIPAL
# ============================================

class CerebroAmazonPedidos:
    """Clase principal que coordina todo el flujo"""
    
    def __init__(self):
        self.estado = EstadoSistema()
        self.ejecutor = EjecutorPasos(self.estado, Logger)
    
    def mostrar_banner(self):
        """Muestra el banner inicial"""
        print(f"{Colors.BOLD}{Colors.CYAN}")
        print("╔" + "═" * 58 + "╗")
        print("║" + " " * 58 + "║")
        print("║" + "🧠 CEREBRO - Amazon Pedidos Automation Master".center(58) + "║")
        print("║" + " " * 58 + "║")
        print("╚" + "═" * 58 + "╝")
        print(f"{Colors.END}")
        
        print(f"{Colors.WHITE}Sistema de automatización inteligente para pedidos de Amazon{Colors.END}")
        print(f"{Colors.YELLOW}Versión 1.0 - Octubre 2025{Colors.END}\n")
    
    def mostrar_resumen_estado(self):
        """Muestra el estado actual del sistema"""
        ultimo_paso = self.estado.obtener_ultimo_paso()
        
        print(f"{Colors.BOLD}📊 ESTADO DEL SISTEMA:{Colors.END}")
        
        if ultimo_paso == 0:
            print(f"{Colors.YELLOW}   🚀 Sistema listo para iniciar desde el principio{Colors.END}")
        else:
            print(f"{Colors.GREEN}   ✅ Último paso completado: {ultimo_paso}{Colors.END}")
            print(f"{Colors.CYAN}   🔄 El sistema continuará desde el paso {ultimo_paso + 1}{Colors.END}")
            
            if "archivos_generados" in self.estado.estado_actual:
                archivos = self.estado.estado_actual["archivos_generados"]
                print(f"{Colors.WHITE}   📁 Archivos generados: {len(archivos)}{Colors.END}")
        
        print()
    
    def verificar_prerrequisitos(self) -> bool:
        """Verifica todos los prerrequisitos del sistema"""
        Logger.step(0, "Verificación de Prerrequisitos 🔍")
        
        verificaciones = [
            ("Directorios", Verificadores.verificar_directorios),
            ("Dependencias", Verificadores.verificar_dependencias),
            ("Ollama", Verificadores.verificar_ollama),
        ]
        
        for nombre, verificador in verificaciones:
            Logger.substep(f"Verificando {nombre}...")
            if nombre == "Directorios":
                verificador()  # Este no retorna bool
                continue
            elif not verificador():
                Logger.error(f"Falló verificación: {nombre}")
                return False
        
        Logger.success("Todos los prerrequisitos están listos")
        return True
    
    def ejecutar_flujo_completo(self):
        """Ejecuta el flujo completo del proyecto"""
        self.mostrar_banner()
        self.mostrar_resumen_estado()
        
        # Verificar prerrequisitos
        if not self.verificar_prerrequisitos():
            Logger.error("No se pueden cumplir los prerrequisitos. Abortando.")
            return False
        
        # Determinar desde qué paso empezar
        ultimo_paso = self.estado.obtener_ultimo_paso()
        
        # Marcar inicio si es primera ejecución
        if ultimo_paso == 0:
            self.estado.marcar_inicio()
        
        # Definir pasos a ejecutar
        pasos = [
            (1, "Login Manual", self.ejecutor.paso_1_login_manual),
            (2, "Extracción HTML", self.ejecutor.paso_2_extraer_html),
            (3, "Procesamiento IA", self.ejecutor.paso_3_procesar_ia),
            (4, "Descarga Individual", self.ejecutor.paso_4_descargar_individuales),
            (5, "Extracción Detalles", self.ejecutor.paso_5_extraer_detalles),
        ]
        
        # Ejecutar pasos - algunos siempre se ejecutan, otros solo si es necesario
        for numero_paso, nombre_paso, funcion_paso in pasos:
            # Paso 1 (Login): Solo saltar si ya está hecho Y las cookies existen
            if numero_paso == 1 and ultimo_paso >= 1 and Verificadores.verificar_cookies():
                Logger.warning(f"Paso {numero_paso} (Login) ya completado - Saltando")
                continue
            
            # Paso 2 (Extraer HTML): SIEMPRE se ejecuta para detectar nuevas ventas
            if numero_paso == 2:
                Logger.info(f"Iniciando {nombre_paso} (siempre se ejecuta para detectar nuevas ventas)")
            
            # Pasos 3,4,5: Solo saltar si no es necesario (el script decide)
            elif numero_paso > 2 and ultimo_paso >= numero_paso:
                Logger.warning(f"Paso {numero_paso} ya completado en esta sesión - Saltando")
                continue
            else:
                Logger.info(f"Iniciando {nombre_paso}")
            
            if not funcion_paso():
                Logger.error(f"Error en paso {numero_paso}: {nombre_paso}")
                Logger.error("Ejecución abortada. El estado se guardó para recuperación.")
                return False
            
            Logger.success(f"Paso {numero_paso} completado exitosamente")
        
        # Flujo completado
        self.mostrar_resumen_final()
        return True
    
    def mostrar_resumen_final(self):
        """Muestra un resumen final del proceso"""
        print(f"\n{Colors.BOLD}{Colors.GREEN}")
        print("╔" + "═" * 58 + "╗")
        print("║" + " " * 58 + "║")
        print("║" + "🎉 PROCESO COMPLETADO EXITOSAMENTE 🎉".center(58) + "║")
        print("║" + " " * 58 + "║")
        print("╚" + "═" * 58 + "╝")
        print(f"{Colors.END}")
        
        # Mostrar archivos finales
        Logger.info("📊 ARCHIVOS FINALES GENERADOS:")
        
        json_file = CSV_DIR / "pedidos_consolidados.json"
        csv_file = CSV_DIR / "pedidos_consolidados.csv"
        
        if json_file.exists():
            size_mb = json_file.stat().st_size / (1024 * 1024)
            Logger.success(f"   📄 {json_file} ({size_mb:.2f} MB)")
        
        if csv_file.exists():
            size_mb = csv_file.stat().st_size / (1024 * 1024)
            Logger.success(f"   📊 {csv_file} ({size_mb:.2f} MB)")
        
        # Contar pedidos procesados
        try:
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    Logger.success(f"   🛒 Total de pedidos procesados: {len(data)}")
        except Exception as e:
            Logger.warning(f"No se pudo contar pedidos: {e}")
        
        # Crear backup automático de archivos finales
        self.crear_backup_automatico()
        
        # Limpiar estado al final (permite nueva ejecución sin reset manual)
        Logger.info("Limpiando estado del sistema para permitir próxima ejecución...")
        self.estado.limpiar_estado()
        Logger.success("Sistema listo para nueva ejecución automática")
        
        print(f"\n{Colors.CYAN}✨ ¡Todos los datos están listos para su análisis! ✨{Colors.END}")
        print(f"{Colors.YELLOW}💡 Tip: Puedes ejecutar 'python cerebro.py' nuevamente para buscar más ventas{Colors.END}")
    
    def crear_backup_automatico(self):
        """Crea backup automático de archivos finales con timestamp"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            json_file = CSV_DIR / "pedidos_consolidados.json"
            csv_file = CSV_DIR / "pedidos_consolidados.csv"
            backup_dir = CSV_DIR / "backup"
            
            if json_file.exists():
                backup_json = backup_dir / f"pedidos_consolidados_{timestamp}.json"
                json_file.replace(backup_json.parent / backup_json.name)
                backup_json.write_bytes(json_file.read_bytes())
                Logger.success(f"Backup JSON creado: {backup_json.name}")
            
            if csv_file.exists():
                backup_csv = backup_dir / f"pedidos_consolidados_{timestamp}.csv"
                csv_file.replace(backup_csv.parent / backup_csv.name)
                backup_csv.write_bytes(csv_file.read_bytes())
                Logger.success(f"Backup CSV creado: {backup_csv.name}")
                
        except Exception as e:
            Logger.warning(f"No se pudo crear backup automático: {e}")
            Logger.info("Los archivos principales siguen disponibles")

# ============================================
# PUNTO DE ENTRADA PRINCIPAL
# ============================================

def main():
    """Función principal"""
    try:
        # Verificar que estamos en el directorio correcto
        if not (BASE_DIR / "scripts").exists():
            print(f"{Colors.RED}❌ Error: Ejecuta este script desde la carpeta raíz del proyecto{Colors.END}")
            print(f"{Colors.WHITE}   Directorio actual: {BASE_DIR}{Colors.END}")
            print(f"{Colors.WHITE}   Directorio esperado debe contener: scripts/, cookies/, html/, etc.{Colors.END}")
            sys.exit(1)
        
        # Crear y ejecutar cerebro
        cerebro = CerebroAmazonPedidos()
        
        # Manejar argumentos de línea de comandos
        if len(sys.argv) > 1:
            if sys.argv[1] == "--reset":
                Logger.warning("Reiniciando estado del sistema...")
                cerebro.estado.limpiar_estado()
                Logger.success("Estado reiniciado")
                return
            elif sys.argv[1] == "--status":
                cerebro.mostrar_resumen_estado()
                return
            elif sys.argv[1] == "--help":
                print(f"{Colors.CYAN}🧠 CEREBRO - Amazon Pedidos Automation Master{Colors.END}")
                print(f"{Colors.WHITE}Uso: python cerebro.py [opciones]{Colors.END}")
                print(f"{Colors.WHITE}Opciones:{Colors.END}")
                print(f"  --reset   Reinicia el estado del sistema")
                print(f"  --status  Muestra el estado actual")
                print(f"  --help    Muestra esta ayuda")
                print(f"\n{Colors.YELLOW}El sistema te guiará paso a paso, empezando por el login manual{Colors.END}")
                return
        
        # Ejecutar flujo completo
        exito = cerebro.ejecutar_flujo_completo()
        
        if exito:
            sys.exit(0)
        else:
            sys.exit(1)
    
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️  Proceso interrumpido por el usuario{Colors.END}")
        print(f"{Colors.CYAN}💾 El estado se guardó automáticamente para recuperación{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}💥 Error inesperado: {e}{Colors.END}")
        sys.exit(1)

if __name__ == "__main__":
    main()