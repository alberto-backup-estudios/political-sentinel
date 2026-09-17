"""
senado.py — Extractor de datos de votaciones de Sala del Senado de la República de Chile.
Fuente: https://tramitacion.senado.cl/wspublico/
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional
import requests

from src.config import RAW_DATA_DIR, SENADO_TRAMITACION_URL, SENADO_VOTACIONES_URL
from src.models import CamaraTipo, OpcionVoto, Votacion, VotoNominal, parsear_opcion_voto, valor_numerico_voto


def _normalizar_boletin(boletin: str) -> str:
    """Extrae el número base antes del guión (ej: '11179-13' -> '11179')."""
    limpio = boletin.strip()
    if "-" in limpio:
        return limpio.split("-")[0].strip()
    return limpio


def obtener_votaciones_senado(boletin: str, guardar_cache: bool = True) -> List[Votacion]:
    """
    Obtiene todas las votaciones nominales registradas en Sala del Senado para un proyecto de ley.
    """
    num_base = _normalizar_boletin(boletin)
    cache_path = RAW_DATA_DIR / f"senado_votaciones_{num_base}.xml"
    content = None

    if cache_path.exists():
        try:
            content = cache_path.read_bytes()
        except OSError:
            content = None

    if not content:
        url = f"{SENADO_VOTACIONES_URL}?boletin={num_base}"
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            content = response.content
            if guardar_cache:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_bytes(content)
        except requests.RequestException as e:
            print(f"[Error] Fallo al consultar votaciones del Senado para boletín {boletin}: {e}", file=sys.stderr)
            return []

    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        print(f"[Error] XML inválido en respuesta del Senado para boletín {boletin}: {e}", file=sys.stderr)
        return []

    votaciones: List[Votacion] = []
    idx = 1
    for nodo in root.findall(".//votacion"):
        sesion = nodo.findtext("SESION", default="").strip()
        fecha = nodo.findtext("FECHA", default="").strip()
        tema = nodo.findtext("TEMA", default="").strip()
        si = nodo.findtext("SI", default="0").strip()
        no = nodo.findtext("NO", default="0").strip()
        abst = nodo.findtext("ABSTENCION", default="0").strip()
        etapa = nodo.findtext("ETAPA", default="").strip()

        resultado = f"SI: {si}, NO: {no}, ABST: {abst}"

        votos: List[VotoNominal] = []
        for v_elem in nodo.findall(".//VOTO"):
            nombre_senador = v_elem.findtext("PARLAMENTARIO", default="").strip()
            seleccion = v_elem.findtext("SELECCION", default="").strip()
            opcion_enum = parsear_opcion_voto(seleccion)
            val_num = valor_numerico_voto(opcion_enum)

            votos.append(VotoNominal(
                parlamentario_id=nombre_senador,  # En el Senado, el nombre es la clave nominal
                nombre_completo=nombre_senador,
                opcion=opcion_enum,
                valor_numerico=val_num,
            ))

        votaciones.append(Votacion(
            id=int(f"{num_base}{idx}"),
            camara=CamaraTipo.SENADO,
            fecha=fecha,
            boletin=boletin,
            descripcion=f"[{etapa}] {tema}".strip(),
            resultado=resultado,
            votos=votos,
        ))
        idx += 1

    return votaciones


if __name__ == "__main__":
    print("Probando extractor del Senado...")
    boletin_test = "11179-13"  # Ley de 40 Horas
    vots = obtener_votaciones_senado(boletin_test)
    print(f"Total votaciones encontradas en el Senado para boletín {boletin_test}: {len(vots)}")
    for v in vots:
        print(f"\nFecha: {v.fecha} | Votos registrados: {len(v.votos)}")
        print(f"Descripción: {v.descripcion[:100]}...")
        print("Muestra de 3 senadores:")
        for voto in v.votos[:3]:
            print(f"  - {voto.nombre_completo}: {voto.opcion.value} ({voto.valor_numerico})")
