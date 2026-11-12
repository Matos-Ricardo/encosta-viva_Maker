import unittest
from ia_encosta import analisar_tendencia

class TesteTendencia(unittest.TestCase):
    def test_coletando_com_poucas_amostras(self):
        r = analisar_tendencia([{"ts": 1000+i, "inclinacao_graus": 1.0} for i in range(4)])
        self.assertEqual(r["status"], "coletando")
    def test_tendencia_subindo(self):
        r = analisar_tendencia([{"ts": 1000+i*10, "inclinacao_graus": 1+i*0.2} for i in range(6)])
        self.assertEqual(r["status"], "subindo")
        self.assertGreater(r["taxa_graus_min"], 0)
    def test_tendencia_caindo(self):
        r = analisar_tendencia([{"ts": 1000+i*10, "inclinacao_graus": 5-i*0.2} for i in range(6)])
        self.assertEqual(r["status"], "caindo")

class TesteJanelaRecente(unittest.TestCase):
    def test_usa_somente_janela_recente(self):
        subida = [{"ts": 1000 + i * 5, "inclinacao_graus": i * 0.3} for i in range(20)]
        descida = [{"ts": 1100 + i * 5, "inclinacao_graus": 6 - i * 0.3} for i in range(20)]
        r = analisar_tendencia(subida + descida)
        self.assertEqual(r["status"], "caindo")

    def test_estavel(self):
        r = analisar_tendencia([{"ts": 1000 + i * 10, "inclinacao_graus": 1.0} for i in range(8)])
        self.assertEqual(r["status"], "estavel")

    def test_projecao_ate_10_graus(self):
        r = analisar_tendencia([{"ts": 1000 + i * 10, "inclinacao_graus": 1 + i * 0.5} for i in range(8)])
        self.assertIsNotNone(r["previsao_minutos_limite"])


if __name__ == "__main__":
    unittest.main()
