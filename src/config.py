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

# Umbrales de Confianza del Posicionamiento Individual de un Parlamentario
# (según cantidad de votaciones computadas y error estándar de su posición (x,y))
UMBRAL_VOTACIONES_CONFIANZA_MEDIA = 5
UMBRAL_VOTACIONES_CONFIANZA_ALTA = 20
UMBRAL_ERROR_ESTANDAR_CONFIANZA_ALTA = 0.15

# Períodos legislativos (fecha inicio, fecha término) - Cámara de Diputadas y Diputados.
# Fuente: retornarPeriodosLegislativos de opendata.camara.cl (Confianza Alta).
# El Senado NO se renueva por período completo (términos de 8 años escalonados);
# esta tabla se usa igual como referencia temporal para ambas cámaras.
PERIODOS_LEGISLATIVOS = {
    "2018-2022": ("2018-03-11", "2022-03-10"),
    "2022-2026": ("2022-03-11", "2026-03-10"),
    "2026-2030": ("2026-03-11", "2030-03-10"),
}

# Partido legal (Militancias, opendata.camara.cl - Confianza Alta) -> Bancada / Comité
# Parlamentario de la Cámara. Reconstruido desde prensa (camara.cl no expone esto vía
# datos abiertos; la página con el detalle de integrantes requiere JS) - Confianza Media.
PARTIDO_A_BANCADA = {
    "Partido Convergencia Social": "Frente Amplio",
    "Revolución Democrática": "Frente Amplio",
    "Partido Comunes": "Frente Amplio",
    "Frente Amplio": "Frente Amplio",
    "Partido Comunista": "Comunista e Independientes",
    "Partido Acción Humanista": "Comunista e Independientes",
    "Federación Regionalista Verde Social": "Comunista e Independientes",
    "Partido Socialista": "Socialismo Democrático e Independientes",
    "Partido Por la Democracia": "Socialismo Democrático e Independientes",
    "Partido Radical de Chile": "Socialismo Democrático e Independientes",
    "Partido Liberal de Chile": "Socialismo Democrático e Independientes",
    "Partido Demócrata Cristiano": "DC, FRVS e Independientes",
    "Partido Demócratas Chile": "Socialismo Democrático e Independientes",
    "Renovación Nacional": "RN, Evópoli e Independientes",
    "Evolución Política": "RN, Evópoli e Independientes",
    "Partido Regionalista Independiente": "RN, Evópoli e Independientes",
    "Unión Demócrata Independiente": "Unión Demócrata Independiente",
    "Partido Republicano": "Partido Republicano",
    "Partido Social Cristiano": "Partido Republicano",
    "Partido de la Gente": "Partido de la Gente",
    "Partido Nacional Libertario": "Partido Nacional Libertario",
    # Alias "viejo estilo" (catálogo original de 21 parlamentarios, antes de tener
    # el nombre legal exacto vía opendata.camara.cl) - mismo partido, otro nombre.
    "Partido por la Democracia": "Socialismo Democrático e Independientes",
    "Demócratas": "Socialismo Democrático e Independientes",
    "Evópoli": "RN, Evópoli e Independientes",
}

# Partido legal -> Coalición / pacto electoral (Confianza Media-Baja: aproximación por
# partido, no verificada persona por persona; varios partidos se formaron o cambiaron de
# nombre después de la elección parlamentaria de 2021).
PARTIDO_A_COALICION = {
    "Partido Convergencia Social": "Apruebo Dignidad",
    "Revolución Democrática": "Apruebo Dignidad",
    "Partido Comunes": "Apruebo Dignidad",
    "Frente Amplio": "Apruebo Dignidad",
    "Partido Comunista": "Apruebo Dignidad",
    "Partido Acción Humanista": "Apruebo Dignidad",
    "Federación Regionalista Verde Social": "Apruebo Dignidad",
    "Partido Socialista": "Nuevo Pacto Social",
    "Partido Por la Democracia": "Nuevo Pacto Social",
    "Partido Radical de Chile": "Nuevo Pacto Social",
    "Partido Liberal de Chile": "Nuevo Pacto Social",
    "Partido Demócrata Cristiano": "Nuevo Pacto Social",
    "Renovación Nacional": "Chile Podemos+",
    "Evolución Política": "Chile Podemos+",
    "Unión Demócrata Independiente": "Chile Podemos+",
    "Partido Regionalista Independiente": "Chile Podemos+",
    "Partido Republicano": "Frente Social Cristiano",
    "Partido Social Cristiano": "Frente Social Cristiano",
    # Alias "viejo estilo" (ver PARTIDO_A_BANCADA)
    "Partido por la Democracia": "Nuevo Pacto Social",
    "Evópoli": "Chile Podemos+",
}

# Colores por Bancada (Comité Parlamentario) - reemplaza el antiguo esquema por partido,
# que con el catálogo completo (155+50) queda demasiado fragmentado para visualizar.
COLORES_BANCADAS = {
    "Frente Amplio": "#E91E63",
    "Comunista e Independientes": "#D32F2F",
    "Socialismo Democrático e Independientes": "#FF9800",
    "DC, FRVS e Independientes": "#009688",
    "RN, Evópoli e Independientes": "#1976D2",
    "Unión Demócrata Independiente": "#0D47A1",
    "Partido Republicano": "#1A237E",
    "Partido de la Gente": "#795548",
    "Partido Nacional Libertario": "#6D4C41",
    "Independientes": "#9E9E9E",
}
