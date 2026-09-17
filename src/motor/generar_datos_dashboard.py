"""
generar_datos_dashboard.py — Pipeline de consolidación y generación de payload para el Dashboard.
1. Carga leyes evaluadas y parlamentarios.
2. Descarga o usa caché de las votaciones nominales clave de los 5 proyectos emblemáticos.
3. Ejecuta el motor matemático de cuadrantes, centroides y elipses.
4. Exporta data_dashboard.json para el visualizador interactivo.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from src.config import COLORES_PARTIDOS, PROCESSED_DATA_DIR, VISUALIZADOR_DIR
from src.extractores.camara import obtener_detalle_votacion, obtener_votaciones_por_boletin
from src.extractores.senado import obtener_votaciones_senado
from src.models import (
    CamaraTipo,
    LeyEvaluada,
    MetricasBancada,
    Parlamentario,
    PosicionamientoParlamentario,
    Votacion,
    VotoNominal,
)
from src.motor.calculo_cuadrantes import (
    calcular_metricas_bancada,
    calcular_posicionamiento_parlamentario,
)


def cargar_leyes_evaluadas() -> Dict[str, LeyEvaluada]:
    ruta = PROCESSED_DATA_DIR / "leyes_evaluadas.json"
    with open(ruta, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    return {item["boletin"]: LeyEvaluada(**item) for item in data}


def cargar_parlamentarios() -> List[Parlamentario]:
    ruta = PROCESSED_DATA_DIR / "parlamentarios.json"
    with open(ruta, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    return [Parlamentario(**item) for item in data]


def _fecha_senado_a_orden(fecha: str) -> datetime:
    """Convierte una fecha 'DD/MM/YYYY' del Senado a datetime ordenable; sin fecha va al inicio."""
    try:
        return datetime.strptime(fecha.strip(), "%d/%m/%Y")
    except (ValueError, AttributeError):
        return datetime.min


def recolectar_votaciones_emblematicas(leyes: Dict[str, LeyEvaluada]) -> List[Votacion]:
    """
    Recopila las votaciones nominales de Sala para cada boletín en ambas cámaras.
    """
    votaciones_totales: List[Votacion] = []

    for boletin in leyes.keys():
        print(f"\n--> Procesando boletín {boletin} ({leyes[boletin].titulo})...")

        # 1. Cámara de Diputados
        vots_camara_meta = obtener_votaciones_por_boletin(boletin)
        if vots_camara_meta:
            # La API no garantiza orden cronológico en la lista; se elige la
            # votación con fecha ISO más reciente como la más representativa
            # del resultado final de la Cámara sobre este boletín.
            vot_final = max(vots_camara_meta, key=lambda v: v["fecha"])
            print(f"   [Cámara] Descargando votación nominal ID={vot_final['id']}: {vot_final['descripcion'][:60]}...")
            det_c = obtener_detalle_votacion(vot_final["id"])
            if det_c:
                det_c.boletin = boletin
                votaciones_totales.append(det_c)

        # 2. Senado
        vots_senado = obtener_votaciones_senado(boletin)
        if vots_senado:
            vot_s = max(vots_senado, key=lambda v: _fecha_senado_a_orden(v.fecha))
            print(f"   [Senado] Obtenida votación nominal con {len(vot_s.votos)} votos: {vot_s.descripcion[:60]}...")
            votaciones_totales.append(vot_s)

    return votaciones_totales


def asociar_votos_a_parlamentarios(
    parlamentarios: List[Parlamentario], votaciones: List[Votacion]
) -> List[Parlamentario]:
    """
    Empareja los nombres registrados en las votaciones oficiales con los IDs de nuestro catálogo.
    Si un parlamentario oficial votó, actualizamos su ID en la votación para el cruce.
    """
    # Mapeo de nombres normalizados
    for vot in votaciones:
        for v in vot.votos:
            # Buscar coincidencia difusa en parlamentarios
            for p in parlamentarios:
                # Comparamos apellidos principales
                apellidos_p = p.nombre_completo.lower().split()[1:]
                apellidos_v = v.nombre_completo.lower()
                if any(ap in apellidos_v for ap in apellidos_p if len(ap) > 3):
                    v.parlamentario_id = p.id
                    break

    return parlamentarios


def compilar_dashboard():
    print("=== Generando datos consolidados para el Dashboard Political Sentinel ===")
    leyes_map = cargar_leyes_evaluadas()
    parlamentarios = cargar_parlamentarios()

    print(f"Leyes evaluadas cargadas: {len(leyes_map)}")
    print(f"Parlamentarios en catálogo: {len(parlamentarios)}")

    votaciones = recolectar_votaciones_emblematicas(leyes_map)
    print(f"\nTotal votaciones consolidadas: {len(votaciones)}")

    asociar_votos_a_parlamentarios(parlamentarios, votaciones)

    # Calcular coordenadas individuales
    posiciones: List[PosicionamientoParlamentario] = []
    for p in parlamentarios:
        pos = calcular_posicionamiento_parlamentario(p, votaciones, leyes_map)
        posiciones.append(pos)

    # Agrupar por partido y calcular centroides y elipses
    partidos_map: Dict[str, List[PosicionamientoParlamentario]] = {}
    for pos in posiciones:
        partido = pos.parlamentario.partido
        partidos_map.setdefault(partido, []).append(pos)

    bancadas_metricas: List[MetricasBancada] = []
    for partido, lista_pos in partidos_map.items():
        mb = calcular_metricas_bancada(partido, lista_pos)
        bancadas_metricas.append(mb)

    # Formatear payload completo para el visualizador web
    payload = {
        "leyes": [ley.model_dump() for ley in leyes_map.values()],
        "parlamentarios_posicionados": [pos.model_dump() for pos in posiciones],
        "bancadas_metricas": [b.model_dump() for b in bancadas_metricas],
        "colores_partidos": COLORES_PARTIDOS,
        "resumen": {
            "total_leyes": len(leyes_map),
            "total_parlamentarios": len(posiciones),
            "total_bancadas": len(bancadas_metricas),
            "votaciones_procesadas": len(votaciones),
        }
    }

    VISUALIZADOR_DIR.mkdir(parents=True, exist_ok=True)
    salida_path = VISUALIZADOR_DIR / "data_dashboard.json"
    with open(salida_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"\n[Éxito] Dataset compilado y guardado en: {salida_path}")
    print(f"Tamaño del archivo generado: {salida_path.stat().st_size} bytes")


if __name__ == "__main__":
    compilar_dashboard()
