"""
validar_clasificador_leyes.py — Corre el clasificador de Claude sobre las 2 leyes que ya
clasificamos a mano con fuentes verificadas (PGU real y exenciones tributarias), para
comparar el resultado del modelo contra el criterio humano antes de confiar en el
pipeline para el resto de la biblioteca. No es un test automatizado (no hay assert):
imprime lado a lado para revisión manual, porque cada corrida gasta API real.
"""

import json

from src.motor.clasificador_leyes import clasificar_ley

CASOS = [
    {
        "boletin": "14763-05",
        "titulo": "Reduce o elimina exenciones tributarias que indica",
        "contenido": (
            "Promulgada como Ley 21.420, publicada el 4 de febrero de 2022. "
            "Ingresada por el Ministerio de Hacienda el 21 de diciembre de 2021. "
            "Elimina la tasa de impuesto único de 10% a las ganancias de capital del "
            "artículo 107 de la Ley de Impuesto a la Renta (ahora tributan con impuesto "
            "general). Reduce transitoriamente (2 años) y luego elimina el Crédito "
            "Especial a las Empresas Constructoras (CEEC) en el IVA. Elimina beneficios "
            "tributarios para la tercera vivienda en adelante para compradores de "
            "viviendas DFL 2 antes de 2011. Extiende el IVA a todos los servicios en "
            "general (antes exentos), excepto salud, educación, transporte y quienes "
            "emiten boleta de honorarios. Aplica impuesto a la herencia sobre los "
            "beneficios de seguros de vida (antes exentos). Propósito declarado por el "
            "Ejecutivo: aumentar la recaudación fiscal permanente para financiar la "
            "Pensión Garantizada Universal (PGU), que es OTRO proyecto de ley distinto "
            "(boletín 14588-13) votado por separado."
        ),
        "esperado_manual": {
            "d4_carga_fiscal": 1.0,
            "d5_costos_privados": 0.6,
            "d6_burocracia": 0.2,
            "d1_transferencias": 0.0,
        },
    },
    {
        "boletin": "14588-13",
        "titulo": "Crea la Pensión Garantizada Universal (PGU)",
        "contenido": (
            "Promulgada como Ley 21.419, publicada el 29 de enero de 2022. Ingresada por "
            "los Ministerios de Hacienda y del Trabajo y Previsión Social el 20 de "
            "septiembre de 2021. Crea un aporte monetario mensual universal (~$185.000 "
            "inicial) para el 90% más vulnerable de las personas mayores de 65 años, "
            "reemplazando el sistema de Pensión Básica Solidaria (PBS) y Aporte "
            "Previsional Solidario de Vejez (APS). Se estima beneficia a más de 2 "
            "millones de personas. Su financiamiento proviene de una ley separada "
            "(boletín 14763-05, que reduce exenciones tributarias), votada de forma "
            "independiente — esta ley en sí misma no crea ni sube ningún impuesto."
        ),
        "esperado_manual": {
            "d1_transferencias": 1.0,
            "d4_carga_fiscal": 0.6,
            "d5_costos_privados": 0.0,
            "d3_derechos_laborales": 0.4,
        },
    },
]


def main():
    for caso in CASOS:
        print(f"\n{'=' * 70}\nBoletín {caso['boletin']}: {caso['titulo']}\n{'=' * 70}")
        clasificacion, usage = clasificar_ley(
            boletin=caso["boletin"], titulo=caso["titulo"], contenido=caso["contenido"]
        )
        print("Vector Claude   :", clasificacion.vector_impacto.model_dump())
        print("Esperado (manual):", caso["esperado_manual"])
        print("Sectores:", clasificacion.sectores_afectados)
        print("Justificación:", clasificacion.justificacion)
        print(
            f"Tokens -> input={usage.input_tokens} output={usage.output_tokens} "
            f"cache_creation={usage.cache_creation_input_tokens} cache_read={usage.cache_read_input_tokens}"
        )


if __name__ == "__main__":
    main()
