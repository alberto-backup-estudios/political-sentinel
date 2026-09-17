"""
test_asociar_votos.py — Pruebas del cruce de identidad Cámara/Senado.
Cubre el bug original: cruce por substring de apellido asignaba votos a la
persona equivocada (ej. 'Insulza Salinas' capturaba votos de cualquiera con
'Salinas' en el nombre, como 'Durán Salinas' o 'Bravo Salinas').
"""

import unittest

from src.models import CamaraTipo, OpcionVoto, Parlamentario, Votacion, VotoNominal
from src.motor.generar_datos_dashboard import asociar_votos_a_parlamentarios


class TestAsociarVotosSenado(unittest.TestCase):

    def setUp(self):
        self.insulza = Parlamentario(
            id="103", nombre="José Miguel", apellido_paterno="Insulza",
            nombre_completo="José Miguel Insulza Salinas", camara=CamaraTipo.SENADO, partido="PS",
            periodo="2022-2026",
        )
        self.catalogo = [self.insulza]

    def _votacion_senado(self, votos_nombre_opcion):
        return Votacion(
            id=1, camara=CamaraTipo.SENADO, fecha="2024-01-01", boletin="0001-01",
            descripcion="test", resultado="Aprobado",
            votos=[
                VotoNominal(parlamentario_id=nombre, nombre_completo=nombre, opcion=opcion)
                for nombre, opcion in votos_nombre_opcion
            ],
        )

    def test_no_confunde_por_substring_de_apellido(self):
        """El bug original: 'Salinas' como substring capturaba a cualquiera con ese apellido."""
        vot = self._votacion_senado([
            ("Durán S., Eduardo", OpcionVoto.EN_CONTRA),
            ("Bravo S., Marta", OpcionVoto.AFIRMATIVO),
            ("Insulza S., José Miguel", OpcionVoto.ABSTENCION),
        ])
        asociar_votos_a_parlamentarios(self.catalogo, [vot])

        voto_insulza = next(v for v in vot.votos if v.nombre_completo == "Insulza S., José Miguel")
        self.assertEqual(voto_insulza.parlamentario_id, "103")

        # Los otros dos NO deben terminar apuntando al id de Insulza
        otros = [v for v in vot.votos if v.nombre_completo != "Insulza S., José Miguel"]
        for v in otros:
            self.assertNotEqual(v.parlamentario_id, "103")

    def test_match_exacto_asigna_id(self):
        vot = self._votacion_senado([("Insulza S., José Miguel", OpcionVoto.AFIRMATIVO)])
        asociar_votos_a_parlamentarios(self.catalogo, [vot])
        self.assertEqual(vot.votos[0].parlamentario_id, "103")

    def test_no_asigna_si_no_hay_match(self):
        vot = self._votacion_senado([("Perez G., Ana", OpcionVoto.AFIRMATIVO)])
        asociar_votos_a_parlamentarios(self.catalogo, [vot])
        self.assertEqual(vot.votos[0].parlamentario_id, "Perez G., Ana")

    def test_ambiguedad_no_asigna(self):
        """Dos senadores del catálogo con el mismo apellido paterno Y mismo nombre
        (distinto apellido materno, que el Senado no reporta): no se debe adivinar."""
        insulza_2 = Parlamentario(
            id="199", nombre="José Miguel", apellido_paterno="Insulza",
            nombre_completo="José Miguel Insulza Rojas", camara=CamaraTipo.SENADO, partido="PS",
            periodo="2022-2026",
        )
        catalogo = [self.insulza, insulza_2]
        vot = self._votacion_senado([("Insulza S., José Miguel", OpcionVoto.AFIRMATIVO)])
        asociar_votos_a_parlamentarios(catalogo, [vot])
        self.assertEqual(vot.votos[0].parlamentario_id, "Insulza S., José Miguel")

    def test_no_cruza_con_otro_periodo(self):
        """Un senador de un período distinto al de la votación no debe calzar,
        aunque el nombre coincida exactamente (el Senado tiene términos de 8 años
        escalonados: quién ocupaba un escaño en 2022 puede no ser quien lo ocupa
        en otro período)."""
        insulza_periodo_anterior = Parlamentario(
            id="203", nombre="José Miguel", apellido_paterno="Insulza",
            nombre_completo="José Miguel Insulza Salinas", camara=CamaraTipo.SENADO,
            partido="PS", periodo="2018-2022",
        )
        vot = self._votacion_senado([("Insulza S., José Miguel", OpcionVoto.AFIRMATIVO)])
        # fecha por defecto de _votacion_senado ("2024-01-01") cae en el período 2022-2026
        asociar_votos_a_parlamentarios([insulza_periodo_anterior], [vot])
        self.assertEqual(vot.votos[0].parlamentario_id, "Insulza S., José Miguel")

    def test_no_toca_votos_de_camara(self):
        """La Cámara ya trae el Id oficial correcto; esta función no debe tocarlo."""
        vot = Votacion(
            id=2, camara=CamaraTipo.DIPUTADOS, fecha="2024-01-01", boletin="0001-01",
            descripcion="test", resultado="Aprobado",
            votos=[VotoNominal(parlamentario_id="973", nombre_completo="Karol Cariola Oliva", opcion=OpcionVoto.AFIRMATIVO)],
        )
        asociar_votos_a_parlamentarios(self.catalogo, [vot])
        self.assertEqual(vot.votos[0].parlamentario_id, "973")


if __name__ == "__main__":
    unittest.main()
