"""
generar_datos_dashboard.py — Pipeline de consolidación y generación de payload para el Dashboard.
1. Carga leyes evaluadas y parlamentarios.
2. Descarga o usa caché de las votaciones nominales clave de los 5 proyectos emblemáticos.
3. Ejecuta el motor matemático de cuadrantes, centroides y elipses.
4. Exporta data_dashboard.json para el visualizador interactivo.
"""

import json
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.config import COLORES_BANCADAS, PERIODOS_LEGISLATIVOS, PROCESSED_DATA_DIR, VISUALIZADOR_DIR
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
    calcular_perfil_promedio_leyes,
    calcular_perfil_radar_bancada,
    calcular_perfil_radar_parlamentario,
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


def _fecha_a_periodo(fecha: str) -> Optional[str]:
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


def _normalizar_texto(texto: str) -> str:
    """Minúsculas y sin tildes/diacríticos, para comparar nombres de forma robusta."""
    t = texto.strip().lower()
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def _parsear_nombre_voto_senado(nombre_voto: str) -> Tuple[str, str]:
    """
    El Senado entrega los votos como 'ApellidoPaterno InicialMaterno., Nombre(s)',
    ej. 'Insulza S., José Miguel'. Devuelve (apellido_paterno, nombre) normalizados.
    """
    if "," not in nombre_voto:
        return ("", _normalizar_texto(nombre_voto))
    apellidos_parte, nombre_parte = nombre_voto.split(",", 1)
    palabras_apellido = apellidos_parte.strip().split()
    apellido_paterno = palabras_apellido[0] if palabras_apellido else ""
    return (_normalizar_texto(apellido_paterno), _normalizar_texto(nombre_parte))


def asociar_votos_a_parlamentarios(
    parlamentarios: List[Parlamentario], votaciones: List[Votacion]
) -> List[Parlamentario]:
    """
    Cámara: no se toca nada. `camara.py` ya asigna el Id oficial de
    opendata.camara.cl a cada voto (`obtener_detalle_votacion`), y el catálogo
    usa ese mismo Id oficial — el cruce ya es exacto por construcción.

    Senado: la API pública no entrega un Id de parlamentario, solo el nombre en
    texto ('ApellidoPaterno Inicial., Nombre'). Se cruza por apellido paterno
    exacto + nombre exacto (normalizados, sin tildes), nunca por substring, y
    solo se asigna si hay EXACTAMENTE UN candidato del catálogo que calce — una
    coincidencia ambigua o nula se reporta y no se asigna, para no atribuirle a
    alguien un voto que no es suyo.

    Además, los candidatos se restringen al período legislativo vigente en la
    fecha de la votación (el Senado tiene términos de 8 años escalonados, así
    que quién ocupaba un escaño cambia entre períodos): un voto de 2022 nunca
    se cruza contra el catálogo de un período distinto.
    """
    senadores = [p for p in parlamentarios if p.camara == CamaraTipo.SENADO and p.apellido_paterno]

    for vot in votaciones:
        if vot.camara != CamaraTipo.SENADO:
            continue

        periodo_voto = _fecha_a_periodo(vot.fecha)
        senadores_del_periodo = (
            [p for p in senadores if p.periodo == periodo_voto] if periodo_voto else senadores
        )

        for v in vot.votos:
            apellido_v, nombre_v = _parsear_nombre_voto_senado(v.nombre_completo)
            if not apellido_v:
                continue

            candidatos = [
                p for p in senadores_del_periodo
                if _normalizar_texto(p.apellido_paterno) == apellido_v
                and (
                    _normalizar_texto(p.nombre) == nombre_v
                    or _normalizar_texto(p.nombre).split()[0] == nombre_v.split(" ")[0]
                )
            ]

            if len(candidatos) == 1:
                v.parlamentario_id = candidatos[0].id
            elif len(candidatos) > 1:
                print(
                    f"[Aviso] Voto de Senado ambiguo, no se asigna: '{v.nombre_completo}' "
                    f"calza con {len(candidatos)} parlamentarios del catálogo.",
                    file=sys.stderr,
                )
            # len(candidatos) == 0: no está en nuestro catálogo, se ignora sin aviso
            # (es el caso esperado para la mayoría de los ~50 senadores).

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

    # Calcular perfiles de radar (6 ejes sin colapsar) y el promedio del corpus de leyes
    perfiles_radar = [
        calcular_perfil_radar_parlamentario(p, votaciones, leyes_map) for p in parlamentarios
    ]
    perfil_promedio_leyes = calcular_perfil_promedio_leyes(leyes_map)

    # Detalle de voto por parlamentario y boletín, para el detalle de apoyo del radar
    votos_por_parlamentario: Dict[str, Dict[str, str]] = {p.id: {} for p in parlamentarios}
    ids_catalogo = set(votos_por_parlamentario.keys())
    for votacion in votaciones:
        if not votacion.boletin:
            continue
        for v in votacion.votos:
            if v.parlamentario_id in ids_catalogo:
                votos_por_parlamentario[v.parlamentario_id][votacion.boletin] = v.opcion.value

    # Agrupar por bancada (comité parlamentario) y calcular centroides y elipses.
    # Se agrupa por bancada -no por partido legal- porque con el catálogo completo
    # (155+50) el partido legal queda demasiado fragmentado (~23 partidos, varios
    # de 1-3 personas) para que la disciplina de bloque sea informativa.
    bancadas_map: Dict[str, List[PosicionamientoParlamentario]] = {}
    for pos in posiciones:
        bancada = pos.parlamentario.bancada or pos.parlamentario.partido
        bancadas_map.setdefault(bancada, []).append(pos)

    bancadas_metricas: List[MetricasBancada] = []
    for bancada, lista_pos in bancadas_map.items():
        mb = calcular_metricas_bancada(bancada, lista_pos)
        bancadas_metricas.append(mb)

    # Perfil de radar (6 ejes) agregado por bancada, para poder comparar dos
    # bancadas entre sí en el radar, igual que se compara a dos personas.
    perfiles_por_bancada_id: Dict[str, List] = {}
    for pf in perfiles_radar:
        bancada = pf.parlamentario.bancada or pf.parlamentario.partido
        perfiles_por_bancada_id.setdefault(bancada, []).append(pf)

    perfiles_radar_bancadas = [
        {
            "bancada": bancada,
            "vector_promedio": calcular_perfil_radar_bancada(lista_pf).model_dump(),
            "total_miembros": len(lista_pf),
        }
        for bancada, lista_pf in perfiles_por_bancada_id.items()
    ]

    # Formatear payload completo para el visualizador web
    payload = {
        "leyes": [ley.model_dump() for ley in leyes_map.values()],
        "parlamentarios_posicionados": [pos.model_dump() for pos in posiciones],
        "perfiles_radar_parlamentarios": [pf.model_dump() for pf in perfiles_radar],
        "perfiles_radar_bancadas": perfiles_radar_bancadas,
        "perfil_promedio_leyes": perfil_promedio_leyes.model_dump(),
        "votos_por_parlamentario": votos_por_parlamentario,
        "bancadas_metricas": [b.model_dump() for b in bancadas_metricas],
        "colores_bancadas": COLORES_BANCADAS,
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
