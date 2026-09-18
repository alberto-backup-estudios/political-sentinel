"""
models.py — Modelos de datos formales para Political Sentinel.
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class CamaraTipo(str, Enum):
    DIPUTADOS = "DIPUTADOS"
    SENADO = "SENADO"


class OpcionVoto(str, Enum):
    AFIRMATIVO = "AFIRMATIVO"
    EN_CONTRA = "EN CONTRA"
    ABSTENCION = "ABSTENCION"
    PAREO = "PAREO"
    DISPENSADO = "DISPENSADO"
    AUSENTE = "AUSENTE"


def parsear_opcion_voto(texto: str) -> OpcionVoto:
    """Normaliza variantes textuales de opciones de voto de las APIs."""
    t = texto.strip().upper()
    if "AFIRMATIVO" in t or "SI" in t or "A FAVOR" in t:
        return OpcionVoto.AFIRMATIVO
    if "CONTRA" in t or "NO" in t:
        return OpcionVoto.EN_CONTRA
    if "ABSTENC" in t:
        return OpcionVoto.ABSTENCION
    if "PAREO" in t:
        return OpcionVoto.PAREO
    if "DISPENS" in t:
        return OpcionVoto.DISPENSADO
    return OpcionVoto.AUSENTE


def valor_numerico_voto(opcion: OpcionVoto) -> Optional[float]:
    """
    Retorna v_{i, l} según metodologia_y_mapas.md:
    +1: AFIRMATIVO
    -1: EN CONTRA
     0: ABSTENCIÓN
    None: Ausente / Pareo / Dispensado (no computable)
    """
    if opcion == OpcionVoto.AFIRMATIVO:
        return 1.0
    elif opcion == OpcionVoto.EN_CONTRA:
        return -1.0
    elif opcion == OpcionVoto.ABSTENCION:
        return 0.0
    return None


class VectorImpacto(BaseModel):
    """Vector en R^6 de impacto socioeconómico y regulatorio de la ley."""
    d1_transferencias: float = Field(ge=-1.0, le=1.0, description="Transferencias y ayuda monetaria directa")
    d2_bienes_publicos: float = Field(ge=-1.0, le=1.0, description="Acceso a bienes públicos (salud, educación, vivienda)")
    d3_derechos_laborales: float = Field(ge=-1.0, le=1.0, description="Derechos laborales y protección al consumidor")
    d4_carga_fiscal: float = Field(ge=-1.0, le=1.0, description="Carga fiscal, deuda y nuevos impuestos")
    d5_costos_privados: float = Field(ge=-1.0, le=1.0, description="Costos de cumplimiento al sector privado")
    d6_burocracia: float = Field(ge=-1.0, le=1.0, description="Carga burocrática y regulatoria (permisología)")

    def componente_x_ley(self, w4: float = 1.0, w5: float = 1.0, w6: float = 1.0) -> float:
        """Ponderación de carga e intervención económica (Eje X)."""
        denominador = w4 + w5 + w6
        if denominador == 0:
            return 0.0
        return (w4 * self.d4_carga_fiscal + w5 * self.d5_costos_privados + w6 * self.d6_burocracia) / denominador

    def componente_y_ley(self, w1: float = 1.0, w2: float = 1.0, w3: float = 1.0) -> float:
        """Ponderación de bienestar y protección social (Eje Y)."""
        denominador = w1 + w2 + w3
        if denominador == 0:
            return 0.0
        return (w1 * self.d1_transferencias + w2 * self.d2_bienes_publicos + w3 * self.d3_derechos_laborales) / denominador


class LeyEvaluada(BaseModel):
    """Ficha estructurada de un proyecto de ley calificado con evidencia técnica."""
    boletin: str
    titulo: str
    sectores_afectados: List[str] = Field(default_factory=list)
    vector_impacto: VectorImpacto
    costo_fiscal_anual_clp: Optional[float] = None
    recaudacion_estimada_clp: Optional[float] = None
    beneficiarios_estimados: Optional[int] = None
    justificacion: str = ""


class Parlamentario(BaseModel):
    id: str
    nombre_completo: str
    camara: CamaraTipo
    partido: str = "Independiente"
    bancada: Optional[str] = None
    coalicion: Optional[str] = None
    distrito_o_circunscripcion: Optional[str] = None
    # Período legislativo al que corresponde este registro (ej. "2022-2026"). La
    # Cámara se renueva completa cada período; el Senado tiene términos de 8 años
    # escalonados, pero igual se etiqueta con el período en que se emitió cada voto
    # para poder filtrar candidatos de cruce por fecha.
    periodo: Optional[str] = None
    # Para Cámara, `id` es el Id oficial de opendata.camara.cl (cruce exacto, sin
    # ambigüedad). Para Senado, no hay Id oficial disponible vía datos abiertos;
    # `nombre` y `apellido_paterno` se usan para el cruce estructurado por nombre.
    nombre: Optional[str] = None
    apellido_paterno: Optional[str] = None


class VotoNominal(BaseModel):
    parlamentario_id: str
    nombre_completo: str
    opcion: OpcionVoto
    valor_numerico: Optional[float] = None


class Votacion(BaseModel):
    id: int
    camara: CamaraTipo
    fecha: str
    boletin: Optional[str] = None
    descripcion: str
    resultado: str
    votos: List[VotoNominal] = Field(default_factory=list)


class CuadranteInfo(str, Enum):
    CUADRANTE_I = "I. Socialdemocracia / Estado Social"
    CUADRANTE_II = "II. Populismo Fiscal"
    CUADRANTE_III = "III. Liberalismo Clásico / Pro-Mercado"
    CUADRANTE_IV = "IV. Estatismo Burocrático"


def clasificar_cuadrante(x: float, y: float) -> CuadranteInfo:
    """Determina el cuadrante cartesiano según los signos de X e Y."""
    if x > 0 and y > 0:
        return CuadranteInfo.CUADRANTE_I
    elif x <= 0 and y > 0:
        return CuadranteInfo.CUADRANTE_II
    elif x <= 0 and y <= 0:
        return CuadranteInfo.CUADRANTE_III
    else:
        return CuadranteInfo.CUADRANTE_IV


class PosicionamientoParlamentario(BaseModel):
    parlamentario: Parlamentario
    x: float
    y: float
    cuadrante: str
    nombre_cuadrante: str
    total_votaciones_computadas: int
    # Dispersión de los aportes individuales de cada voto a (x, y) — no la
    # dispersión entre personas de una bancada (esa es MetricasBancada).
    sigma_x: Optional[float] = None
    sigma_y: Optional[float] = None
    error_estandar: Optional[float] = None
    nivel_confianza: str = "Baja"
    razon_confianza: str = ""


class PerfilRadarParlamentario(BaseModel):
    """Perfil del parlamentario en las 6 dimensiones sin colapsar en X/Y, para
    comparar su radar directamente contra el radar de una ley o el promedio del corpus."""
    parlamentario: Parlamentario
    vector_promedio: VectorImpacto
    total_votaciones_computadas: int


class MetricasBancada(BaseModel):
    bancada: str
    x_centroide: float
    y_centroide: float
    sigma_x: float
    sigma_y: float
    sigma_xy: float
    disciplina_id: float
    total_miembros: int
    elipse_semieje_mayor: float
    elipse_semieje_menor: float
    elipse_angulo_grados: float
