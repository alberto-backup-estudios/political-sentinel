"""
test_calculo_cuadrantes.py — Pruebas unitarias para el motor analítico de Political Sentinel.
Compatible con unittest estándar y pytest.
"""

import unittest
from src.models import (
    CamaraTipo,
    CuadranteInfo,
    LeyEvaluada,
    OpcionVoto,
    Parlamentario,
    VectorImpacto,
    Votacion,
    VotoNominal,
    PosicionamientoParlamentario,
    clasificar_cuadrante,
)
from src.motor.calculo_cuadrantes import (
    calcular_metricas_bancada,
    calcular_posicionamiento_parlamentario,
)


class TestCalculoCuadrantes(unittest.TestCase):

    def setUp(self):
        self.ley_pensiones = LeyEvaluada(
            boletin="0001-01",
            titulo="Ley de Pensiones Solidarias e Impuestos",
            vector_impacto=VectorImpacto(
                d1_transferencias=1.0,     # Alto bono / subsidio
                d2_bienes_publicos=0.8,
                d3_derechos_laborales=0.5,
                d4_carga_fiscal=1.0,       # Sube impuestos
                d5_costos_privados=0.6,
                d6_burocracia=0.4,
            ),
        )
        self.leyes_map = {"0001-01": self.ley_pensiones}

    def test_clasificacion_cuadrantes(self):
        self.assertEqual(clasificar_cuadrante(0.5, 0.5), CuadranteInfo.CUADRANTE_I)
        self.assertEqual(clasificar_cuadrante(-0.5, 0.5), CuadranteInfo.CUADRANTE_II)
        self.assertEqual(clasificar_cuadrante(-0.5, -0.5), CuadranteInfo.CUADRANTE_III)
        self.assertEqual(clasificar_cuadrante(0.5, -0.5), CuadranteInfo.CUADRANTE_IV)

    def test_posicionamiento_socialdemocrata(self):
        """Vota a favor de impuestos y subsidios -> Cuadrante I."""
        parl = Parlamentario(id="1", nombre_completo="Diputado Socialdemócrata", camara=CamaraTipo.DIPUTADOS)
        votacion = Votacion(
            id=101,
            camara=CamaraTipo.DIPUTADOS,
            fecha="2026-03-01",
            boletin="0001-01",
            descripcion="Votación general ley pensiones",
            resultado="APROBADO",
            votos=[VotoNominal(parlamentario_id="1", nombre_completo=parl.nombre_completo, opcion=OpcionVoto.AFIRMATIVO)],
        )

        pos = calcular_posicionamiento_parlamentario(parl, [votacion], self.leyes_map)
        self.assertGreater(pos.x, 0)
        self.assertGreater(pos.y, 0)
        self.assertEqual(pos.cuadrante, "I")

    def test_posicionamiento_populista(self):
        """Aprueba subsidios y rechaza impuestos -> Cuadrante II."""
        parl = Parlamentario(id="2", nombre_completo="Diputado Populista Fiscal", camara=CamaraTipo.DIPUTADOS)
        leyes = {
            "subsidios": LeyEvaluada(
                boletin="subsidios",
                titulo="Bono Directo",
                vector_impacto=VectorImpacto(
                    d1_transferencias=1.0, d2_bienes_publicos=0.5, d3_derechos_laborales=0.0,
                    d4_carga_fiscal=0.0, d5_costos_privados=0.0, d6_burocracia=0.0
                )
            ),
            "impuestos": LeyEvaluada(
                boletin="impuestos",
                titulo="Aumento Impuestos",
                vector_impacto=VectorImpacto(
                    d1_transferencias=0.0, d2_bienes_publicos=0.0, d3_derechos_laborales=0.0,
                    d4_carga_fiscal=1.0, d5_costos_privados=0.5, d6_burocracia=0.5
                )
            )
        }

        votaciones = [
            Votacion(
                id=1, camara=CamaraTipo.DIPUTADOS, fecha="2026-01-01", boletin="subsidios",
                descripcion="Bono", resultado="APROBADO",
                votos=[VotoNominal(parlamentario_id="2", nombre_completo="Dip 2", opcion=OpcionVoto.AFIRMATIVO)]
            ),
            Votacion(
                id=2, camara=CamaraTipo.DIPUTADOS, fecha="2026-01-02", boletin="impuestos",
                descripcion="Impuesto", resultado="RECHAZADO",
                votos=[VotoNominal(parlamentario_id="2", nombre_completo="Dip 2", opcion=OpcionVoto.EN_CONTRA)]
            ),
        ]

        pos = calcular_posicionamiento_parlamentario(parl, votaciones, leyes)
        self.assertLess(pos.x, 0)
        self.assertGreater(pos.y, 0)
        self.assertEqual(pos.cuadrante, "II")

    def test_exclusion_pareo_y_ausencia(self):
        """Un parlamentario con solo PAREO o AUSENCIA no computa votos activos."""
        parl = Parlamentario(id="3", nombre_completo="Diputado Ausente", camara=CamaraTipo.DIPUTADOS)
        votacion = Votacion(
            id=102,
            camara=CamaraTipo.DIPUTADOS,
            fecha="2026-03-01",
            boletin="0001-01",
            descripcion="Votación general",
            resultado="APROBADO",
            votos=[VotoNominal(parlamentario_id="3", nombre_completo=parl.nombre_completo, opcion=OpcionVoto.AUSENTE)],
        )

        pos = calcular_posicionamiento_parlamentario(parl, [votacion], self.leyes_map)
        self.assertEqual(pos.total_votaciones_computadas, 0)
        self.assertEqual(pos.x, 0.0)
        self.assertEqual(pos.y, 0.0)

    def test_metricas_bancada_cohesion(self):
        """Una bancada con votos idénticos debe tener disciplina máxima (ID_P = 1.0)."""
        p1 = Parlamentario(id="1", nombre_completo="A", camara=CamaraTipo.DIPUTADOS, partido="Partido A")
        p2 = Parlamentario(id="2", nombre_completo="B", camara=CamaraTipo.DIPUTADOS, partido="Partido A")

        pos1 = PosicionamientoParlamentario(
            parlamentario=p1, x=0.4, y=0.6, cuadrante="I", nombre_cuadrante="I", total_votaciones_computadas=5
        )
        pos2 = PosicionamientoParlamentario(
            parlamentario=p2, x=0.4, y=0.6, cuadrante="I", nombre_cuadrante="I", total_votaciones_computadas=5
        )

        metricas = calcular_metricas_bancada("Partido A", [pos1, pos2])
        self.assertEqual(metricas.x_centroide, 0.4)
        self.assertEqual(metricas.y_centroide, 0.6)
        self.assertEqual(metricas.disciplina_id, 1.0)
        self.assertEqual(metricas.sigma_x, 0.0)
        self.assertEqual(metricas.sigma_y, 0.0)


if __name__ == "__main__":
    unittest.main()
