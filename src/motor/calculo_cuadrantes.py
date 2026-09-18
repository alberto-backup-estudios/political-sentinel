"""
calculo_cuadrantes.py — Motor analítico y matemático de Political Sentinel.
Implementa el marco de metodologia_y_mapas.md:
- Coordenadas individuales (X_i, Y_i)
- Asignación de cuadrantes
- Centroides de bancada
- Matriz de covarianza, elipses de cohesión e Índice de Disciplina Partidaria (ID_P)
"""

import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np

from src.config import (
    DEFAULT_ELLIPSE_CONFIDENCE_K,
    DEFAULT_WEIGHTS,
    PERIODOS_LEGISLATIVOS,
    UMBRAL_ERROR_ESTANDAR_CONFIANZA_ALTA,
    UMBRAL_VOTACIONES_CONFIANZA_ALTA,
    UMBRAL_VOTACIONES_CONFIANZA_MEDIA,
)
from src.models import (
    CuadranteInfo,
    LeyEvaluada,
    MetricasBancada,
    Parlamentario,
    PerfilRadarParlamentario,
    PosicionamientoParlamentario,
    VectorImpacto,
    Votacion,
    VotoNominal,
    clasificar_cuadrante,
    valor_numerico_voto,
)

EJES_VECTOR_IMPACTO = (
    "d1_transferencias",
    "d2_bienes_publicos",
    "d3_derechos_laborales",
    "d4_carga_fiscal",
    "d5_costos_privados",
    "d6_burocracia",
)


def fecha_a_periodo(fecha: str) -> Optional[str]:
    """Determina a qué período legislativo (PERIODOS_LEGISLATIVOS) corresponde una
    fecha de votación. Acepta ISO ('2022-01-26T14:55:15') o Senado ('24/01/2022')."""
    fecha = (fecha or "").strip()
    dt = None
    for parser in (
        lambda s: datetime.fromisoformat(s.split("T")[0]),
        lambda s: datetime.strptime(s, "%d/%m/%Y"),
    ):
        try:
            dt = parser(fecha)
            break
        except ValueError:
            continue
    if dt is None:
        return None

    for nombre_periodo, (ini, fin) in PERIODOS_LEGISLATIVOS.items():
        if datetime.fromisoformat(ini) <= dt <= datetime.fromisoformat(fin):
            return nombre_periodo
    return None


def _voto_es_del_periodo_del_parlamentario(votacion: Votacion, parlamentario: Parlamentario) -> bool:
    """Si el parlamentario tiene período asignado, la votación debe caer en ese mismo
    período (evita que un mismo Id oficial reelecto en otro período -Cámara- acumule
    votos de un período que no le corresponde a ese registro del catálogo)."""
    if not parlamentario.periodo:
        return True
    return fecha_a_periodo(votacion.fecha) == parlamentario.periodo


def calcular_posicionamiento_parlamentario(
    parlamentario: Parlamentario,
    votaciones: List[Votacion],
    leyes_map: Dict[str, LeyEvaluada],
    pesos: Optional[Dict[str, float]] = None,
) -> PosicionamientoParlamentario:
    """
    Calcula las coordenadas (X_i, Y_i) para un parlamentario 'i' evaluando
    todas las votaciones registradas en las que participó.
    """
    w = pesos or DEFAULT_WEIGHTS
    w1, w2, w3 = w["w1"], w["w2"], w["w3"]
    w4, w5, w6 = w["w4"], w["w5"], w["w6"]

    aportes_x: List[float] = []
    aportes_y: List[float] = []

    for votacion in votaciones:
        # Solo computamos si la votación está asociada a una ley evaluada
        if not votacion.boletin or votacion.boletin not in leyes_map:
            continue
        if not _voto_es_del_periodo_del_parlamentario(votacion, parlamentario):
            continue

        ley = leyes_map[votacion.boletin]
        impacto = ley.vector_impacto

        # Buscar el voto del parlamentario en esta votación
        voto = next((v for v in votacion.votos if v.parlamentario_id == parlamentario.id), None)
        if not voto:
            continue

        v_val = valor_numerico_voto(voto.opcion)
        if v_val is None:
            # Ausente, Pareo, Dispensado no computan en base activa
            continue

        c_x = impacto.componente_x_ley(w4, w5, w6)
        c_y = impacto.componente_y_ley(w1, w2, w3)

        aportes_x.append(v_val * c_x)
        aportes_y.append(v_val * c_y)

    votaciones_computadas = len(aportes_x)

    if votaciones_computadas > 0:
        x_final = max(-1.0, min(1.0, sum(aportes_x) / votaciones_computadas))
        y_final = max(-1.0, min(1.0, sum(aportes_y) / votaciones_computadas))
    else:
        x_final = 0.0
        y_final = 0.0

    cuad_enum = clasificar_cuadrante(x_final, y_final)
    nombre_cuad = cuad_enum.value
    cuad_code = cuad_enum.value.split(".")[0].strip()

    sigma_x, sigma_y, error_estandar, nivel_confianza, razon_confianza = (
        _calcular_confianza_posicionamiento(aportes_x, aportes_y, votaciones_computadas)
    )

    return PosicionamientoParlamentario(
        parlamentario=parlamentario,
        x=round(x_final, 4),
        y=round(y_final, 4),
        cuadrante=cuad_code,
        nombre_cuadrante=nombre_cuad,
        total_votaciones_computadas=votaciones_computadas,
        sigma_x=sigma_x,
        sigma_y=sigma_y,
        error_estandar=error_estandar,
        nivel_confianza=nivel_confianza,
        razon_confianza=razon_confianza,
    )


def _calcular_confianza_posicionamiento(
    aportes_x: List[float], aportes_y: List[float], n: int
) -> Tuple[Optional[float], Optional[float], Optional[float], str, str]:
    """
    Mide qué tan confiable es la posición (x, y) de UN parlamentario, a partir de
    la dispersión de sus aportes voto a voto (no de la dispersión entre personas
    de una bancada, que calcula calcular_metricas_bancada).
    """
    if n == 0:
        return None, None, None, "Baja", "Sin votaciones computadas."

    if n < 2:
        sigma_x, sigma_y = 0.0, 0.0
    else:
        sigma_x = float(np.std(aportes_x, ddof=1))
        sigma_y = float(np.std(aportes_y, ddof=1))

    error_estandar = math.sqrt(sigma_x**2 + sigma_y**2) / math.sqrt(n)

    if n < UMBRAL_VOTACIONES_CONFIANZA_MEDIA:
        nivel = "Baja"
        razon = f"Solo {n} votaciones computadas: posición no representativa."
    elif n < UMBRAL_VOTACIONES_CONFIANZA_ALTA or error_estandar > UMBRAL_ERROR_ESTANDAR_CONFIANZA_ALTA:
        nivel = "Media"
        razon = f"{n} votaciones computadas, error estándar {error_estandar:.4f}: posición razonable pero con margen de incertidumbre."
    else:
        nivel = "Alta"
        razon = f"{n} votaciones computadas, error estándar {error_estandar:.4f}: posición estadísticamente estable."

    return round(sigma_x, 4), round(sigma_y, 4), round(error_estandar, 4), nivel, razon


def calcular_perfil_radar_parlamentario(
    parlamentario: Parlamentario,
    votaciones: List[Votacion],
    leyes_map: Dict[str, LeyEvaluada],
) -> PerfilRadarParlamentario:
    """
    Calcula el promedio ponderado por voto de cada uno de los 6 ejes POR SEPARADO
    (sin agruparlos en X/Y), para poder comparar el radar de un parlamentario
    directamente contra el radar de una ley específica o contra el promedio del
    corpus de leyes evaluadas.
    """
    sumas = {eje: 0.0 for eje in EJES_VECTOR_IMPACTO}
    votaciones_computadas = 0

    for votacion in votaciones:
        if not votacion.boletin or votacion.boletin not in leyes_map:
            continue
        if not _voto_es_del_periodo_del_parlamentario(votacion, parlamentario):
            continue

        impacto = leyes_map[votacion.boletin].vector_impacto
        voto = next((v for v in votacion.votos if v.parlamentario_id == parlamentario.id), None)
        if not voto:
            continue

        v_val = valor_numerico_voto(voto.opcion)
        if v_val is None:
            continue

        for eje in EJES_VECTOR_IMPACTO:
            sumas[eje] += v_val * getattr(impacto, eje)
        votaciones_computadas += 1

    if votaciones_computadas > 0:
        promedio = {
            eje: round(max(-1.0, min(1.0, sumas[eje] / votaciones_computadas)), 4)
            for eje in EJES_VECTOR_IMPACTO
        }
    else:
        promedio = {eje: 0.0 for eje in EJES_VECTOR_IMPACTO}

    return PerfilRadarParlamentario(
        parlamentario=parlamentario,
        vector_promedio=VectorImpacto(**promedio),
        total_votaciones_computadas=votaciones_computadas,
    )


def calcular_perfil_radar_bancada(perfiles: List["PerfilRadarParlamentario"]) -> VectorImpacto:
    """Promedio simple (no ponderado) del perfil de radar de los parlamentarios de
    una bancada, en línea con cómo ya se calcula su centroide (X, Y)."""
    if not perfiles:
        return VectorImpacto(**{eje: 0.0 for eje in EJES_VECTOR_IMPACTO})

    promedio = {
        eje: round(sum(getattr(p.vector_promedio, eje) for p in perfiles) / len(perfiles), 4)
        for eje in EJES_VECTOR_IMPACTO
    }
    return VectorImpacto(**promedio)


def calcular_perfil_promedio_leyes(leyes_map: Dict[str, LeyEvaluada]) -> VectorImpacto:
    """Promedio simple del vector de impacto de todas las leyes evaluadas -
    el radar 'de referencia' contra el que se puede comparar a un parlamentario."""
    leyes = list(leyes_map.values())
    if not leyes:
        return VectorImpacto(**{eje: 0.0 for eje in EJES_VECTOR_IMPACTO})

    promedio = {
        eje: round(sum(getattr(ley.vector_impacto, eje) for ley in leyes) / len(leyes), 4)
        for eje in EJES_VECTOR_IMPACTO
    }
    return VectorImpacto(**promedio)


def calcular_metricas_bancada(
    bancada: str,
    posiciones: List[PosicionamientoParlamentario],
    k_confianza: float = DEFAULT_ELLIPSE_CONFIDENCE_K,
) -> MetricasBancada:
    """
    Calcula centroide, matriz de covarianza, elipse de dispersión
    e Índice de Disciplina Partidaria (ID_P) para un grupo de parlamentarios.
    """
    n = len(posiciones)
    if n == 0:
        return MetricasBancada(
            bancada=bancada,
            x_centroide=0.0,
            y_centroide=0.0,
            sigma_x=0.0,
            sigma_y=0.0,
            sigma_xy=0.0,
            disciplina_id=1.0,
            total_miembros=0,
            elipse_semieje_mayor=0.0,
            elipse_semieje_menor=0.0,
            elipse_angulo_grados=0.0,
        )

    xs = np.array([p.x for p in posiciones])
    ys = np.array([p.y for p in posiciones])

    x_mean = float(np.mean(xs))
    y_mean = float(np.mean(ys))

    if n == 1:
        # Con 1 miembro, la dispersión es 0 y la disciplina es 100%
        return MetricasBancada(
            bancada=bancada,
            x_centroide=round(x_mean, 4),
            y_centroide=round(y_mean, 4),
            sigma_x=0.0,
            sigma_y=0.0,
            sigma_xy=0.0,
            disciplina_id=1.0,
            total_miembros=1,
            elipse_semieje_mayor=0.02,
            elipse_semieje_menor=0.02,
            elipse_angulo_grados=0.0,
        )

    # Matriz de covarianza muestral (ddof=1)
    cov_matrix = np.cov(xs, ys, ddof=1)
    sigma_x2 = float(cov_matrix[0, 0])
    sigma_y2 = float(cov_matrix[1, 1])
    sigma_xy = float(cov_matrix[0, 1])

    sigma_x = math.sqrt(max(0.0, sigma_x2))
    sigma_y = math.sqrt(max(0.0, sigma_y2))

    # Índice de Disciplina Partidaria ID_P = 1 - sqrt(sigma_x^2 + sigma_y^2)
    dispersion_total = math.sqrt(sigma_x2 + sigma_y2)
    disciplina_id = max(0.0, min(1.0, 1.0 - dispersion_total))

    # Autovalores y autovectores para la elipse de covarianza
    eigvals, eigvecs = np.linalg.eigh(cov_matrix)
    order = eigvals.argsort()[::-1]
    eigvals = eigvals[order]
    eigvecs = eigvecs[:, order]

    # Radios escalados por factor de confianza k
    lambda_1 = max(0.0, float(eigvals[0]))
    lambda_2 = max(0.0, float(eigvals[1]))
    semieje_mayor = k_confianza * math.sqrt(lambda_1)
    semieje_menor = k_confianza * math.sqrt(lambda_2)

    # Ángulo del eje mayor en grados
    vx, vy = eigvecs[0, 0], eigvecs[1, 0]
    angulo_rad = math.atan2(vy, vx)
    angulo_grados = math.degrees(angulo_rad)

    return MetricasBancada(
        bancada=bancada,
        x_centroide=round(x_mean, 4),
        y_centroide=round(y_mean, 4),
        sigma_x=round(sigma_x, 4),
        sigma_y=round(sigma_y, 4),
        sigma_xy=round(sigma_xy, 4),
        disciplina_id=round(disciplina_id, 4),
        total_miembros=n,
        elipse_semieje_mayor=round(max(0.02, semieje_mayor), 4),
        elipse_semieje_menor=round(max(0.02, semieje_menor), 4),
        elipse_angulo_grados=round(angulo_grados, 2),
    )
