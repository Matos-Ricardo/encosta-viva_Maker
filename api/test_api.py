"""Testes da classificação de risco e dos endpoints (sem MQTT e sem rede)."""
import os
import tempfile
import unittest

os.environ["MQTT_ATIVO"] = "0"
os.environ["DB_ARQUIVO"] = os.path.join(tempfile.mkdtemp(), "teste.db")

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402


def leitura(incl, vib=0.0, ok=True):
    return main.LeituraIn(setor_id=main.SETOR_ID, inclinacao_graus=incl, vibracao_g=vib, mpu_ok=ok)


class TesteClassificacao(unittest.TestCase):
    def test_limites_de_inclinacao(self):
        casos = [(2.99, 0), (3.0, 1), (5.99, 1), (6.0, 2), (9.99, 2), (10.0, 3)]
        for graus, esperado in casos:
            with self.subTest(graus=graus):
                self.assertEqual(main.avaliar(leitura(graus))["nivel"], esperado)

    def test_limites_de_vibracao(self):
        self.assertEqual(main.avaliar(leitura(0, 0.039))["nivel"], 0)
        self.assertEqual(main.avaliar(leitura(0, 0.04))["nivel"], 1)
        self.assertEqual(main.avaliar(leitura(0, 0.15))["nivel"], 2)

    def test_prevalece_o_pior_fator(self):
        self.assertEqual(main.avaliar(leitura(3.5, 0.2))["nivel"], 2)

    def test_falha_do_mpu_nunca_e_verde(self):
        self.assertEqual(main.avaliar(leitura(0, 0, ok=False))["nivel"], 1)


class TesteEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = TestClient(main.app)

    def test_saude(self):
        r = self.c.get("/saude")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "ok")

    def test_simulacao_dos_quatro_niveis(self):
        for n in range(4):
            r = self.c.post(f"/api/simular/{n}")
            self.assertEqual(r.json()["nivel"], n)
        self.assertEqual(self.c.post("/api/simular/9").status_code, 422)

    def test_post_leitura_e_estado(self):
        r = self.c.post("/leituras", json={"setor_id": main.SETOR_ID, "inclinacao_graus": 6.5, "vibracao_g": 0.01})
        self.assertEqual(r.json()["nivel"], 2)
        est = self.c.get("/api/estado").json()
        self.assertEqual(est["nivel"], 2)
        self.assertIn("ia", est)

    def test_leitura_invalida_rejeitada(self):
        r = self.c.post("/leituras", json={"setor_id": main.SETOR_ID, "inclinacao_graus": -5})
        self.assertEqual(r.status_code, 422)

    def test_simulacao_nao_alimenta_a_ia(self):
        self.c.post("/api/simular/3")
        ia = self.c.get("/api/ia/tendencia").json()
        self.assertTrue(ia["ativa"])

    def test_historico_e_alertas(self):
        self.assertEqual(self.c.get("/api/historico").status_code, 200)
        self.assertEqual(self.c.get("/api/alertas").status_code, 200)


class TesteSensorUmidadeOpcional(unittest.TestCase):
    def test_sem_umidade_nada_muda(self):
        self.assertEqual(main.avaliar(leitura(0.5))["nivel"], 0)
        self.assertEqual(main.nivel_umidade(None), 0)

    def test_limites_de_umidade(self):
        self.assertEqual(main.nivel_umidade(69.9), 0)
        self.assertEqual(main.nivel_umidade(70), 1)
        self.assertEqual(main.nivel_umidade(84.9), 1)
        self.assertEqual(main.nivel_umidade(85), 2)

    def test_solo_saturado_eleva_nivel(self):
        l = main.LeituraIn(setor_id=main.SETOR_ID, inclinacao_graus=1.0, vibracao_g=0.01, umidade_solo_pct=90)
        r = main.avaliar(l)
        self.assertEqual(r["nivel"], 2)
        self.assertTrue(any("umidade" in f["texto"].lower() for f in r["fatores"]))

    def test_umidade_invalida_rejeitada(self):
        c = TestClient(main.app)
        r = c.post("/leituras", json={"setor_id": main.SETOR_ID, "inclinacao_graus": 1, "umidade_solo_pct": 140})
        self.assertEqual(r.status_code, 422)

    def test_migracao_de_banco_antigo(self):
        import sqlite3
        arq = os.path.join(tempfile.mkdtemp(), "antigo.db")
        con = sqlite3.connect(arq)
        con.execute("CREATE TABLE leituras (id INTEGER PRIMARY KEY AUTOINCREMENT, setor_id TEXT NOT NULL, sensor_id TEXT NOT NULL, ts REAL NOT NULL, inclinacao REAL NOT NULL, vibracao REAL NOT NULL, nivel INTEGER NOT NULL, simulado INTEGER NOT NULL, mpu_ok INTEGER NOT NULL, origem TEXT NOT NULL)")
        con.execute("INSERT INTO leituras (setor_id,sensor_id,ts,inclinacao,vibracao,nivel,simulado,mpu_ok,origem) VALUES ('x','s',1700000000,1,0.01,0,0,1,'mqtt')")
        con.commit(); con.close()
        banco = main.Banco(arq)  # não pode quebrar com o banco antigo
        banco.inserir_leitura(main.LeituraIn(setor_id="x", inclinacao_graus=2, umidade_solo_pct=50), 1700000100, 0, "mqtt")
        h = banco.historico("x", 0, 10)
        self.assertEqual(len(h), 2)
        self.assertIsNone(h[0]["umidade_solo_pct"])
        self.assertEqual(h[1]["umidade_solo_pct"], 50)


class FalsoMQTT:
    def __init__(self):
        self.enviadas = []

    def publish(self, topico, carga, qos=0, retain=False):
        self.enviadas.append((topico, carga, retain))


class TesteIAFechandoLaco(unittest.TestCase):
    def test_pre_alerta(self):
        from ia_encosta import avaliar_pre_alerta
        self.assertTrue(avaliar_pre_alerta({"status": "subindo", "previsao_minutos_limite": 2.0}))
        self.assertFalse(avaliar_pre_alerta({"status": "subindo", "previsao_minutos_limite": 30.0}))
        self.assertFalse(avaliar_pre_alerta({"status": "caindo", "previsao_minutos_limite": None}))
        self.assertFalse(avaliar_pre_alerta({"status": "coletando"}))

    def test_api_devolve_ia_ao_robo_via_mqtt(self):
        falso = FalsoMQTT()
        antes = (main.CLIENTE_MQTT, main.MQTT_INFO["conectado"])
        main.CLIENTE_MQTT, main.MQTT_INFO["conectado"] = falso, True
        try:
            main.enviar_ia_ao_robo({"ia": {"pre_alerta": True, "status": "subindo", "taxa_graus_min": 2.0, "previsao_minutos_limite": 1.5}})
        finally:
            main.CLIENTE_MQTT, main.MQTT_INFO["conectado"] = antes
        self.assertEqual(len(falso.enviadas), 1)
        topico, carga, retain = falso.enviadas[0]
        self.assertEqual(topico, main.TOPICO_IA)
        self.assertIn('"pre_alerta":true', carga)  # formato exato que o firmware procura
        self.assertFalse(retain)

    def test_sem_mqtt_nao_quebra(self):
        main.enviar_ia_ao_robo({"ia": {"pre_alerta": True}})  # CLIENTE_MQTT None


if __name__ == "__main__":
    unittest.main()
