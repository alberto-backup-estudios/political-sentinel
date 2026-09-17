"""
calculo_cuadrantes.py — Motor analítico y matemático de Political Sentinel.
Implementa el marco de metodologia_y_mapas.md:
- Coordenadas individuales (X_i, Y_i)
- Asignación de cuadrantes
- Centroides de bancada
- Matriz de covarianza, elipses de cohesión e Índice de Disciplina Partidaria (ID_P)
"""

import math
from typing import Dict, List, Optional, Tuple
import numpy as np

from src.config import DEFAULT_ELLIPSE_CONFIDENCE_K, DEFAULT_WEIGHTS
from src.models import (
    CuadranteInfo,
    LeyEvaluada,
    MetricasBancada,
    Parlamentario,
    PosicionamientoParlamentario,
    Votacion,
    VotoNominal,
    clasificar_cuadrante,
    valor_numerico_voto,
)


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

    suma_x = 0.0
    suma_y = 0.0
    votaciones_computadas = 0

    for votacion in votaciones:
        # Solo computamos si la votación está asociada a una ley evaluada
        if not votacion.boletin or votacion.boletin not in leyes_map:
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

        suma_x += v_val * c_x
        suma_y += v_val * c_y
        votaciones_computadas += 1

    if votaciones_computadas > 0:
        x_final = max(-1.0, min(1.0, suma_x / votaciones_computadas))
        y_final = max(-1.0, min(1.0, suma_y / votaciones_computadas))
    else:
        x_final = 0.0
        y_final = 0.0

    cuad_enum = clasificar_cuadrante(x_final, y_final)
    nombre_cuad = cuad_enum.value
    cuad_code = cuad_enum.value.split(".")[0].strip()

    return PosicionamientoParlamentario(
        parlamentario=parlamentario,
        x=round(x_final, 4),
        y=round(y_final, 4),
        cuadrante=cuad_code,
        nombre_cuadrante=nombre_cuad,
        total_votaciones_computadas=votaciones_computadas,
    )


def calcular_metricas_bancada(
    partido: str,
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
            partido=partido,
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
            partido=partido,
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
        partido=partido,
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
