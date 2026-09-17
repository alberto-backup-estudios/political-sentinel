"""
config.py — Parámetros globales y configuración del sistema Political Sentinel.
"""

from pathlib import Path

# Rutas del Sistema de Archivos
SRC_DIR = Path(__file__).resolve().parent
BASE_DIR = SRC_DIR.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SCHEMAS_DIR = BASE_DIR / "schemas"
VISUALIZADOR_DIR = SRC_DIR / "visualizador" / "dashboard"

# URLs de Datos Abiertos del Congreso de Chile
CAMARA_WS_URL = "https://opendata.camara.cl/camaradiputados/WServices/WSLegislativo.asmx"
CAMARA_NAMESPACES = {"ns": "http://opendata.camara.cl/camaradiputados/v1"}

SENADO_WS_BASE = "https://tramitacion.senado.cl/wspublico"
SENADO_TRAMITACION_URL = f"{SENADO_WS_BASE}/tramitacion.php"
SENADO_VOTACIONES_URL = f"{SENADO_WS_BASE}/votaciones.php"
SENADO_SESIONES_URL = f"{SENADO_WS_BASE}/sesiones.php"

# Ponderadores por Defecto para las 6 Dimensiones (metodologia_y_mapas.md)
DEFAULT_WEIGHTS = {
    "w1": 1.0,  # Transferencias y Ayuda Directa
    "w2": 1.0,  # Acceso a Bienes Públicos
    "w3": 1.0,  # Derechos y Protección Social/Laboral
    "w4": 1.0,  # Carga Fiscal y Tributaria
    "w5": 1.0,  # Costos de Cumplimiento al Privado
    "w6": 1.0,  # Carga Burocrática y Regulatoria
}

# Parámetros de Elipse de Dispersión Partidaria
# k=1.0 representa aproximadamente el 68% de confianza (1 desviación estándar)
DEFAULT_ELLIPSE_CONFIDENCE_K = 1.0

# Colores sugeridos para partidos y bancadas chilenas
COLORES_PARTIDOS = {
    "Partido Comunista": "#D32F2F",
    "Frente Amplio": "#E91E63",
    "Partido Socialista": "#C2185B",
    "Partido por la Democracia": "#FF9800",
    "Democracia Cristiana": "#009688",
    "Demócratas": "#00BCD4",
    "Amarillos por Chile": "#FFEB3B",
    "Renovación Nacional": "#1976D2",
    "Unión Demócrata Independiente": "#0D47A1",
    "Evópoli": "#00E676",
    "Partido Republicano": "#1A237E",
    "Partido de la Gente": "#795548",
    "Independientes": "#9E9E9E",
}
