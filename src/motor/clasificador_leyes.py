"""
clasificador_leyes.py — Clasifica un proyecto de ley en el vector de impacto de 6D.
Capa 3 del pipeline (Python determinista -> Ollama local -> Claude API): se usa para
construir el gold-set inicial, arbitrar casos de baja confianza y clasificar el volumen
con Claude Haiku. Las cifras fiscales (costo, recaudación) NO se le piden al modelo:
deben venir de un parseo determinista del Informe Financiero DIPRES (Capa 1) para evitar
que el LLM las invente.
"""

from typing import List, Optional

import anthropic
from pydantic import BaseModel, Field

from src.models import VectorImpacto

MODEL_CLASIFICADOR = "claude-haiku-4-5-20251001"

INSTRUCCIONES_METODOLOGIA = """Eres un analista legislativo. Clasificas proyectos de ley chilenos en un vector de 6 dimensiones, cada una en el rango [-1.0, 1.0], según el efecto DIRECTO del texto de la ley.

DIMENSIONES:
d1_transferencias: +1 crea/amplía bonos o subsidios monetarios directos a personas; -1 los reduce o elimina.
d2_bienes_publicos: +1 expande cobertura o gratuidad en salud, educación o vivienda pública; -1 restringe acceso.
d3_derechos_laborales: +1 amplía derechos laborales o protección social/consumidor; -1 flexibiliza o desregula.
d4_carga_fiscal: +1 crea o sube impuestos/tasas, o aumenta el gasto/deuda pública permanente; -1 reduce tributos o gasto.
d5_costos_privados: +1 genera nuevos costos u obligaciones operacionales a empresas o personas; -1 alivia costos.
d6_burocracia: +1 crea nuevos permisos, registros o trámites obligatorios; -1 simplifica trámites.

REGLAS IMPORTANTES:
1. Clasifica SOLO el efecto directo del texto de ESTA ley. Si esta ley se financia con otra
   ley votada por separado (ej. un beneficio social financiado por una reforma tributaria en
   otro boletín), NO le asignes a esta ley el MECANISMO de esa otra ley (no le pongas a un
   beneficio social los impuestos que otro boletín creó para financiarlo, ni viceversa). Esto
   NO significa ignorar el efecto fiscal propio de esta ley: si ESTA ley por sí misma genera un
   gasto público nuevo y permanente (ej. crea un beneficio o transferencia recurrente), eso SÍ
   cuenta como carga fiscal (d4) de esta ley, aunque el financiamiento venga de otro boletín.
2. Cuando una ley ELIMINA o REDUCE una exención, beneficio o crédito tributario, eso
   AUMENTA la recaudación fiscal (d4 positivo), no la reduce — razona explícitamente
   este paso antes de fijar el signo.
3. No inventes cifras exactas de costo fiscal o recaudación: si no te las doy como
   evidencia verificada, no las menciones en la justificación.
4. La justificación debe citar mecanismos o artículos concretos de la ley, no opiniones
   generales.
5. Distingue dos tipos de ley que buscan aumentar la recaudación del Estado, aunque el
   Ejecutivo declare la misma intención de fondo para ambas:
   (a) Aumento DIRECTO: sube tasas, crea impuestos, elimina exenciones o créditos
       tributarios. Tiene un efecto cierto e inmediato -> d4 positivo.
   (b) Crecimiento económico INDIRECTO: reduce trámites, simplifica regulación o
       incentiva inversión/formalización esperando que la mayor actividad económica
       aumente la recaudación a futuro. NO sube ninguna tasa ni impuesto de forma
       directa -> d4 se mantiene neutro o incluso negativo si reduce algún tributo, y el
       efecto real de esta ley aparece en d5/d6 (probablemente negativos, porque alivia
       costos y burocracia). El aumento de recaudación esperado es un efecto indirecto y
       especulativo: no lo uses para justificar un d4 positivo (misma lógica de la regla 1:
       no le atribuyas a esta ley un efecto que depende de dinámicas económicas futuras,
       no del mecanismo directo de su texto).
"""


class ClasificacionLey(BaseModel):
    sectores_afectados: List[str] = Field(
        description="Sectores, industrias o grupos de personas directamente afectados por el texto de la ley."
    )
    vector_impacto: VectorImpacto
    justificacion: str = Field(
        description="Justificación breve citando mecanismos o artículos concretos de la ley para cada eje relevante."
    )


def clasificar_ley(
    *,
    boletin: str,
    titulo: str,
    contenido: str,
    evidencia_dipres: Optional[str] = None,
    client: Optional[anthropic.Anthropic] = None,
) -> tuple[ClasificacionLey, anthropic.types.Usage]:
    """Clasifica una ley con Claude Haiku y devuelve la clasificación y el uso de tokens/caché."""
    client = client or anthropic.Anthropic()

    mensaje_usuario = f"Boletín: {boletin}\nTítulo oficial: {titulo}\n\nContenido verificado:\n{contenido}"
    if evidencia_dipres:
        mensaje_usuario += f"\n\nEvidencia financiera (DIPRES/CNEP):\n{evidencia_dipres}"

    response = client.messages.parse(
        model=MODEL_CLASIFICADOR,
        max_tokens=1500,
        system=[
            {
                "type": "text",
                "text": INSTRUCCIONES_METODOLOGIA,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": mensaje_usuario}],
        output_format=ClasificacionLey,
    )
    return response.parsed_output, response.usage
