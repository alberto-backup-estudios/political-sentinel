"""
camara.py — Extractor oficial de datos abiertos de la Cámara de Diputadas y Diputados de Chile.
Fuente: https://opendata.camara.cl/camaradiputados/WServices/WSLegislativo.asmx
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional
import requests

from src.config import CAMARA_NAMESPACES, CAMARA_WS_URL, RAW_DATA_DIR
from src.models import CamaraTipo, OpcionVoto, Votacion, VotoNominal, parsear_opcion_voto, valor_numerico_voto


def obtener_votaciones_anno(anno: int) -> List[Dict]:
    """
    Obtiene la lista de votaciones de Sala de la Cámara para un año determinado.
    """
    url = f"{CAMARA_WS_URL}/retornarVotacionesXAnno?prmAnno={anno}"
    try:
        response = requests.get(url, timeout=25)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[Error] Fallo al consultar votaciones para el año {anno}: {e}", file=sys.stderr)
        return []

    root = ET.fromstring(response.content)
    lista = []
    for nodo in root.findall(".//ns:Votacion", CAMARA_NAMESPACES):
        v_id = nodo.findtext("ns:Id", default="", namespaces=CAMARA_NAMESPACES)
        desc = nodo.findtext("ns:Descripcion", default="", namespaces=CAMARA_NAMESPACES)
        fecha = nodo.findtext("ns:Fecha", default="", namespaces=CAMARA_NAMESPACES)
        tipo = nodo.findtext("ns:Tipo", default="", namespaces=CAMARA_NAMESPACES)
        resultado = nodo.findtext("ns:Resultado", default="", namespaces=CAMARA_NAMESPACES)

        if v_id:
            lista.append({
                "id": int(v_id),
                "descripcion": desc.strip(),
                "fecha": fecha.strip(),
                "tipo": tipo.strip(),
                "resultado": resultado.strip()
            })

    return lista


def obtener_detalle_votacion(votacion_id: int, guardar_cache: bool = True) -> Optional[Votacion]:
    """
    Descarga y procesa el detalle nominal de una votación específica de la Cámara.
    Retorna una instancia validada del modelo Votacion.
    """
    cache_path = RAW_DATA_DIR / f"camara_votacion_{votacion_id}.xml"
    content = None

    if cache_path.exists():
        try:
            content = cache_path.read_bytes()
        except OSError:
            content = None

    if not content:
        url = f"{CAMARA_WS_URL}/retornarVotacionDetalle?prmVotacionId={votacion_id}"
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            content = response.content
            if guardar_cache:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_bytes(content)
        except requests.RequestException as e:
            print(f"[Error] No se pudo obtener detalle de votación {votacion_id}: {e}", file=sys.stderr)
            return None

    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        print(f"[Error] XML inválido en votación {votacion_id}: {e}", file=sys.stderr)
        return None

    desc = root.findtext("ns:Descripcion", default="", namespaces=CAMARA_NAMESPACES).strip()
    fecha = root.findtext("ns:Fecha", default="", namespaces=CAMARA_NAMESPACES).strip()
    resultado = root.findtext("ns:Resultado", default="", namespaces=CAMARA_NAMESPACES).strip()
    boletin = root.findtext("ns:Boletin", default=None, namespaces=CAMARA_NAMESPACES)
    if boletin:
        boletin = boletin.strip()

    votos: List[VotoNominal] = []
    for nodo_voto in root.findall(".//ns:Voto", CAMARA_NAMESPACES):
        diputado = nodo_voto.find("ns:Diputado", CAMARA_NAMESPACES)
        dip_id = diputado.findtext("ns:Id", default="", namespaces=CAMARA_NAMESPACES) if diputado is not None else ""
        nombre = diputado.findtext("ns:Nombre", default="", namespaces=CAMARA_NAMESPACES) if diputado is not None else ""
        apellido_p = diputado.findtext("ns:ApellidoPaterno", default="", namespaces=CAMARA_NAMESPACES) if diputado is not None else ""
        apellido_m = diputado.findtext("ns:ApellidoMaterno", default="", namespaces=CAMARA_NAMESPACES) if diputado is not None else ""

        opcion_raw = nodo_voto.findtext("ns:OpcionVoto", default="", namespaces=CAMARA_NAMESPACES)
        opcion_enum = parsear_opcion_voto(opcion_raw)
        val_num = valor_numerico_voto(opcion_enum)

        votos.append(VotoNominal(
            parlamentario_id=str(dip_id).strip(),
            nombre_completo=f"{nombre} {apellido_p} {apellido_m}".strip(),
            opcion=opcion_enum,
            valor_numerico=val_num,
        ))

    return Votacion(
        id=votacion_id,
        camara=CamaraTipo.DIPUTADOS,
        fecha=fecha,
        boletin=boletin,
        descripcion=desc,
        resultado=resultado,
        votos=votos,
    )


def obtener_votaciones_por_boletin(boletin: str) -> List[Dict]:
    """
    Retorna la lista de votaciones asociadas a un número de boletín legislativo.
    """
    num_limpio = boletin.strip()
    url = f"{CAMARA_WS_URL}/retornarVotacionesXProyectoLey?prmNumeroBoletin={num_limpio}"
    try:
        response = requests.get(url, timeout=25)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[Error] Fallo al consultar votaciones para boletín {boletin}: {e}", file=sys.stderr)
        return []

    root = ET.fromstring(response.content)
    lista = []
    nodos = root.findall(".//ns:VotacionProyectoLey", CAMARA_NAMESPACES) or root.findall(".//ns:Votacion", CAMARA_NAMESPACES)
    for nodo in nodos:
        v_id = nodo.findtext("ns:Id", default="", namespaces=CAMARA_NAMESPACES)
        desc = nodo.findtext("ns:Descripcion", default="", namespaces=CAMARA_NAMESPACES)
        fecha = nodo.findtext("ns:Fecha", default="", namespaces=CAMARA_NAMESPACES)
        resultado = nodo.findtext("ns:Resultado", default="", namespaces=CAMARA_NAMESPACES)

        if v_id:
            lista.append({
                "id": int(v_id),
                "descripcion": desc.strip(),
                "fecha": fecha.strip(),
                "resultado": resultado.strip()
            })

    return lista


if __name__ == "__main__":
    print("Probando extractor de la Cámara...")
    vots = obtener_votaciones_anno(2024)
    print(f"Total votaciones en 2024: {len(vots)}")
    if vots:
        m = vots[0]
        det = obtener_detalle_votacion(m["id"])
        if det:
            print(f"Votación ID={det.id}: {det.descripcion[:70]}")
            print(f"Total votos nominales: {len(det.votos)}")
            print("Primeros 3 votos:")
            for v in det.votos[:3]:
                print(f"  - {v.nombre_completo}: {v.opcion.value} ({v.valor_numerico})")
