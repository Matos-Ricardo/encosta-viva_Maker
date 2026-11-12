#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Encosta Viva - API FastAPI + ponte MQTT + dashboard (sensor de umidade opcional)."""

import asyncio
import json
import os
import sqlite3
import threading
import time
import uuid
from collections import deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import paho.mqtt.client as mqtt
import uvicorn
from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from ia_encosta import PRE_ALERTA_MIN, analisar_tendencia, avaliar_pre_alerta, gerar_orientacao_llm

BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_DASHBOARD = BASE_DIR / "dashboard.html"


def env(nome: str, padrao: str) -> str:
    valor = os.getenv(nome, "").strip()
    return valor if valor else padrao


def env_bool(nome: str, padrao: bool) -> bool:
    valor = os.getenv(nome)
    if valor is None or not valor.strip():
        return padrao
    return valor.strip().lower() in ("1", "true", "sim", "yes", "on")


SETOR_ID = env("SETOR_ID", "vilasahy-q4m8z2")
SETOR_NOME = env("SETOR_NOME", "Maquete - Vila Sahy (São Sebastião/SP)")
MQTT_ATIVO = env_bool("MQTT_ATIVO", True)
MQTT_HOST = env("MQTT_HOST", "broker.hivemq.com")
MQTT_PORT = int(env("MQTT_PORT", "1883"))
MQTT_USUARIO = env("MQTT_USUARIO", "")
MQTT_SENHA = env("MQTT_SENHA", "")
PORTA = int(env("PORTA", "8000"))
OFFLINE_APOS_S = 15
DB_ARQUIVO = env("DB_ARQUIVO", str(BASE_DIR / "encosta_viva_sem_umidade.db"))
GROQ_API_KEY = env("GROQ_API_KEY", "")
GROQ_MODEL = env("GROQ_MODEL", "llama-3.3-70b-versatile")

TOPICO_LEITURA = f"encosta/{SETOR_ID}/leitura"
TOPICO_STATUS = f"encosta/{SETOR_ID}/status"
TOPICO_IA = f"encosta/{SETOR_ID}/ia"  # a API devolve ao robô o pré-alerta calculado pela IA

# Limiares ilustrativos da maquete. Não são limites geotécnicos certificados.
INCL_ATENCAO = 3.0
INCL_ALERTA = 6.0
INCL_MAXIMO = 10.0
VIB_ATENCAO = 0.04
VIB_ALERTA = 0.15
# Umidade do solo: sensor adicional OPCIONAL (se não vier no payload, não influencia nada).
UMID_ATENCAO = 70.0
UMID_ALERTA = 85.0

NIVEIS = {
    0: {"nome": "Observação", "cor": "verde", "orientacao": "Sem inclinação ou vibração acima dos limites configurados. Continue acompanhando as condições do local."},
    1: {"nome": "Monitoramento", "cor": "amarelo", "orientacao": "Foi identificado movimento inicial ou uma falha no acelerômetro. Mantenha o monitoramento e verifique o equipamento."},
    2: {"nome": "Alerta", "cor": "vermelho", "orientacao": "Foi detectada inclinação ou vibração relevante. Verifique o local e siga as orientações da Defesa Civil."},
    3: {"nome": "Alerta máximo", "cor": "vermelho", "orientacao": "Foi detectada inclinação igual ou superior ao limite máximo configurado. A Defesa Civil deve avaliar a situação."},
}
EMERGENCIA = "Em emergência, ligue 199 (Defesa Civil) ou 193 (Bombeiros)."


class LeituraIn(BaseModel):
    """Contrato de dados publicado pelo ESP32 no tópico MQTT de leitura."""
    model_config = ConfigDict(extra="ignore")
    setor_id: str = Field(min_length=1, max_length=64)
    sensor_id: str = Field(default="robo-sentinela-01", max_length=64)
    ts: Optional[float] = None
    inclinacao_graus: float = Field(ge=0, le=180)
    vibracao_g: float = Field(default=0.0, ge=0, le=10)
    nivel: Optional[int] = Field(default=None, ge=0, le=3)
    simulado: bool = False
    mpu_ok: bool = True
    rssi: Optional[int] = None
    umidade_solo_pct: Optional[float] = Field(default=None, ge=0, le=100)


def nivel_inclinacao(graus: float) -> int:
    if graus >= INCL_MAXIMO:
        return 3
    if graus >= INCL_ALERTA:
        return 2
    if graus >= INCL_ATENCAO:
        return 1
    return 0


def nivel_vibracao(vibracao: float) -> int:
    if vibracao >= VIB_ALERTA:
        return 2
    if vibracao >= VIB_ATENCAO:
        return 1
    return 0


def nivel_umidade(umidade: Optional[float]) -> int:
    if umidade is None:
        return 0
    if umidade >= UMID_ALERTA:
        return 2
    if umidade >= UMID_ATENCAO:
        return 1
    return 0


def avaliar(leitura: LeituraIn) -> Dict[str, Any]:
    if not leitura.mpu_ok:
        nivel = 1  # falha segura: não apresentar verde quando o sensor falha
    else:
        ni = nivel_inclinacao(leitura.inclinacao_graus)
        nv = nivel_vibracao(leitura.vibracao_g)
        nivel = max(ni, nv, nivel_umidade(leitura.umidade_solo_pct))

    fatores = []
    if not leitura.mpu_ok:
        fatores.append({"texto": "MPU6050 sem leitura válida. O sistema entrou em monitoramento por segurança.", "grau": 1})
    else:
        ni = nivel_inclinacao(leitura.inclinacao_graus)
        nv = nivel_vibracao(leitura.vibracao_g)
        if ni:
            fatores.append({"texto": f"Inclinação de {leitura.inclinacao_graus:.2f}° em relação à posição de referência.", "grau": ni})
        else:
            fatores.append({"texto": f"Inclinação dentro do limite configurado ({leitura.inclinacao_graus:.2f}°).", "grau": 0})
        if nv:
            fatores.append({"texto": f"Vibração estimada de {leitura.vibracao_g:.3f} g acima do limite de monitoramento.", "grau": nv})
        else:
            fatores.append({"texto": f"Vibração estimada dentro do limite ({leitura.vibracao_g:.3f} g).", "grau": 0})
        if leitura.umidade_solo_pct is not None:
            nu = nivel_umidade(leitura.umidade_solo_pct)
            if nu:
                fatores.append({"texto": f"Solo com {leitura.umidade_solo_pct:.0f}% de umidade: terreno saturado aumenta o risco.", "grau": nu})
            else:
                fatores.append({"texto": f"Umidade do solo dentro do limite ({leitura.umidade_solo_pct:.0f}%).", "grau": 0})
    return {"nivel": nivel, "fatores": fatores}


class Banco:
    def __init__(self, arquivo: str):
        self.lock = threading.Lock()
        self.con = sqlite3.connect(arquivo, check_same_thread=False)
        with self.lock:
            self.con.executescript("""
                CREATE TABLE IF NOT EXISTS leituras (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setor_id TEXT NOT NULL,
                    sensor_id TEXT NOT NULL,
                    ts REAL NOT NULL,
                    inclinacao REAL NOT NULL,
                    vibracao REAL NOT NULL,
                    nivel INTEGER NOT NULL,
                    simulado INTEGER NOT NULL,
                    mpu_ok INTEGER NOT NULL,
                    origem TEXT NOT NULL,
                    umidade REAL
                );
                CREATE INDEX IF NOT EXISTS ix_leituras_setor_ts ON leituras(setor_id, ts);
                CREATE TABLE IF NOT EXISTS eventos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setor_id TEXT NOT NULL,
                    ts REAL NOT NULL,
                    de INTEGER,
                    para INTEGER NOT NULL,
                    motivo TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS ix_eventos_setor_ts ON eventos(setor_id, ts);
            """)
            # Migração: bancos criados antes do sensor opcional de umidade não têm a coluna.
            colunas = [r[1] for r in self.con.execute("PRAGMA table_info(leituras)").fetchall()]
            if "umidade" not in colunas:
                self.con.execute("ALTER TABLE leituras ADD COLUMN umidade REAL")
            self.con.commit()

    def inserir_leitura(self, l: LeituraIn, ts: float, nivel: int, origem: str):
        with self.lock:
            self.con.execute(
                "INSERT INTO leituras (setor_id,sensor_id,ts,inclinacao,vibracao,nivel,simulado,mpu_ok,origem,umidade) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (l.setor_id, l.sensor_id, ts, l.inclinacao_graus, l.vibracao_g, nivel,
                 int(l.simulado or origem == "simulado"), int(l.mpu_ok), origem, l.umidade_solo_pct),
            )
            self.con.commit()

    def inserir_evento(self, setor_id: str, ts: float, de: Optional[int], para: int, motivo: str):
        with self.lock:
            self.con.execute("INSERT INTO eventos (setor_id,ts,de,para,motivo) VALUES (?,?,?,?,?)", (setor_id, ts, de, para, motivo))
            self.con.commit()

    def historico(self, setor_id: str, desde: float, limite: int):
        with self.lock:
            rows = self.con.execute(
                "SELECT ts,inclinacao,vibracao,nivel,simulado,umidade FROM leituras WHERE setor_id=? AND ts>=? ORDER BY ts DESC LIMIT ?",
                (setor_id, desde, limite),
            ).fetchall()
        rows.reverse()
        return [{"ts": r[0], "inclinacao_graus": r[1], "vibracao_g": r[2], "nivel": r[3], "simulado": bool(r[4]), "umidade_solo_pct": r[5]} for r in rows]

    def leituras_reais_tendencia(self, setor_id: str, limite: int = 60):
        """Retorna leituras reais e válidas; simulações/falhas não treinam o modelo."""
        with self.lock:
            rows = self.con.execute(
                "SELECT ts,inclinacao FROM leituras WHERE setor_id=? AND simulado=0 AND mpu_ok=1 ORDER BY ts DESC LIMIT ?",
                (setor_id, limite),
            ).fetchall()
        rows.reverse()
        return [{"ts": float(r[0]), "inclinacao_graus": float(r[1])} for r in rows]

    def eventos(self, setor_id: str, limite: int):
        with self.lock:
            rows = self.con.execute("SELECT ts,de,para,motivo FROM eventos WHERE setor_id=? ORDER BY ts DESC LIMIT ?", (setor_id, limite)).fetchall()
        return [{"ts": r[0], "de": r[1], "para": r[2], "motivo": r[3]} for r in rows]


BANCO = Banco(DB_ARQUIVO)
LOCK = threading.RLock()
ESTADOS: Dict[str, Dict[str, Any]] = {}
ASSINANTES = set()
LOOP: Optional[asyncio.AbstractEventLoop] = None
MQTT_INFO: Dict[str, Any] = {"ativo": MQTT_ATIVO, "conectado": False, "mensagens": 0, "invalidas": 0, "erro": None}
CLIENTE_MQTT: Optional[mqtt.Client] = None


def novo_estado(setor_id: str) -> Dict[str, Any]:
    return {
        "setor_id": setor_id,
        "nome": SETOR_NOME if setor_id == SETOR_ID else setor_id,
        "nivel": None,
        "desde": None,
        "recebida_em": 0.0,
        "leitura": None,
        "fatores": [],
        "frase": "Aguardando a primeira leitura do robô.",
        "orientacao_fonte": "regras locais",
        "dispositivo_online": None,
        "alertas": deque(BANCO.eventos(setor_id, 8), maxlen=8),
        "total": 0,
    }


def analisar_com_pre_alerta(setor_id: str) -> Dict[str, Any]:
    ia = analisar_tendencia(BANCO.leituras_reais_tendencia(setor_id))
    ia["pre_alerta"] = avaliar_pre_alerta(ia)
    ia["pre_alerta_minutos"] = PRE_ALERTA_MIN
    return ia


def snapshot(setor_id: str) -> Dict[str, Any]:
    with LOCK:
        st = ESTADOS.get(setor_id) or novo_estado(setor_id)
        agora = time.time()
        idade = agora - st["recebida_em"] if st["recebida_em"] else None
        online = idade is not None and idade <= OFFLINE_APOS_S and st["dispositivo_online"] is not False
        nivel = st["nivel"]
        meta = NIVEIS.get(nivel) if nivel is not None else None
        return {
            "setor_id": setor_id,
            "nome": st["nome"],
            "agora": agora,
            "online": bool(online),
            "idade_s": idade,
            "nivel": nivel,
            "nivel_nome": meta["nome"] if meta else "Sem dados",
            "cor": meta["cor"] if meta else "cinza",
            "desde": st["desde"],
            "leitura": st["leitura"],
            "fatores": st["fatores"],
            "frase": st["frase"],
            "alertas": list(st["alertas"]),
            "total_leituras": st["total"],
            "ia": analisar_com_pre_alerta(setor_id),
            "orientacao_fonte": st.get("orientacao_fonte", "regras locais"),
            "limiares": {
                "inclinacao_atencao": INCL_ATENCAO,
                "inclinacao_alerta": INCL_ALERTA,
                "inclinacao_maximo": INCL_MAXIMO,
                "vibracao_atencao": VIB_ATENCAO,
                "vibracao_alerta": VIB_ALERTA,
                "umidade_atencao": UMID_ATENCAO,
                "umidade_alerta": UMID_ALERTA,
            },
            "mqtt": dict(MQTT_INFO),
        }


def publicar(tipo: str, dados: Dict[str, Any]):
    if LOOP is None:
        return
    msg = {"tipo": tipo, "dados": dados}
    def distribuir():
        for fila in list(ASSINANTES):
            try:
                fila.put_nowait(msg)
            except asyncio.QueueFull:
                pass
    try:
        LOOP.call_soon_threadsafe(distribuir)
    except RuntimeError:
        pass


def enviar_ia_ao_robo(quadro: Dict[str, Any]):
    """Fecha o laço sensor -> IA -> atuadores: devolve ao ESP32 o pré-alerta da IA.

    Mensagem não retida e sem efeito sobre o nível de risco. Se o robô ficar sem
    receber, ele simplesmente continua usando as regras locais (degradação elegante).
    """
    if CLIENTE_MQTT is None or not MQTT_INFO.get("conectado"):
        return
    ia = quadro.get("ia") or {}
    carga = {
        "pre_alerta": bool(ia.get("pre_alerta")),
        "status": ia.get("status"),
        "taxa_graus_min": ia.get("taxa_graus_min"),
        "previsao_min": ia.get("previsao_minutos_limite"),
    }
    try:
        CLIENTE_MQTT.publish(TOPICO_IA, json.dumps(carga, separators=(",", ":")), qos=0, retain=False)
    except Exception as erro:
        print(f"[MQTT] Falha ao devolver IA ao robô: {erro}")


def processar_leitura(leitura: LeituraIn, origem: str) -> Dict[str, Any]:
    agora = time.time()
    ts = leitura.ts if leitura.ts and 1_600_000_000 < leitura.ts <= agora + 300 else agora
    avaliacao = avaliar(leitura)
    nivel = avaliacao["nivel"]
    frase = NIVEIS[nivel]["orientacao"]
    if nivel >= 2:
        frase += " " + EMERGENCIA
    dados_leitura = {
        "ts": ts,
        "sensor_id": leitura.sensor_id,
        "inclinacao_graus": leitura.inclinacao_graus,
        "vibracao_g": leitura.vibracao_g,
        "nivel": nivel,
        "simulado": leitura.simulado or origem == "simulado",
        "mpu_ok": leitura.mpu_ok,
        "rssi": leitura.rssi,
        "umidade_solo_pct": leitura.umidade_solo_pct,
        "origem": origem,
    }
    solicitar_llm = False
    with LOCK:
        st = ESTADOS.setdefault(leitura.setor_id, novo_estado(leitura.setor_id))
        BANCO.inserir_leitura(leitura, ts, nivel, origem)
        st["total"] += 1
        st["recebida_em"] = agora
        st["dispositivo_online"] = True
        if not st["leitura"] or ts >= st["leitura"]["ts"]:
            anterior = st["nivel"]
            st["leitura"] = dados_leitura
            st["nivel"] = nivel
            st["fatores"] = avaliacao["fatores"]
            st["frase"] = frase
            st["orientacao_fonte"] = "regras locais + IA de tendência"
            if anterior != nivel:
                solicitar_llm = bool(GROQ_API_KEY)
                motivo = "; ".join(f["texto"] for f in avaliacao["fatores"] if f["grau"] > 0) or "Leitura dentro dos limites configurados"
                evento = {"ts": ts, "de": anterior, "para": nivel, "motivo": motivo}
                st["alertas"].appendleft(evento)
                BANCO.inserir_evento(leitura.setor_id, ts, anterior, nivel, motivo)
                st["desde"] = ts
        quadro = snapshot(leitura.setor_id)
    publicar("estado", quadro)
    if not dados_leitura["simulado"]:
        enviar_ia_ao_robo(quadro)
    if solicitar_llm:
        # A chamada externa roda em thread separada: nunca bloqueia MQTT/API.
        threading.Thread(target=atualizar_orientacao_llm, args=(leitura.setor_id, dados_leitura, nivel), daemon=True).start()
    return quadro


def atualizar_orientacao_llm(setor_id: str, leitura: Dict[str, Any], nivel: int):
    try:
        texto = gerar_orientacao_llm(
            api_key=GROQ_API_KEY, model=GROQ_MODEL, leitura=leitura,
            nivel_nome=NIVEIS[nivel]["nome"], orientacao_base=NIVEIS[nivel]["orientacao"],
            emergencia=EMERGENCIA,
        )
        if not texto:
            return
        with LOCK:
            st = ESTADOS.get(setor_id)
            # Não aplicar resposta atrasada a uma leitura de outro nível.
            if not st or st.get("nivel") != nivel:
                return
            st["frase"] = texto
            st["orientacao_fonte"] = "LLM Groq + IA de tendência"
            quadro = snapshot(setor_id)
        publicar("estado", quadro)
    except Exception as erro:
        print(f"[IA-LLM] Fallback para orientação local: {erro}")


def ao_conectar(cliente, userdata, flags, reason_code, properties):
    if reason_code == 0:
        MQTT_INFO["conectado"] = True
        MQTT_INFO["erro"] = None
        cliente.subscribe(TOPICO_LEITURA, qos=0)
        cliente.subscribe(TOPICO_STATUS, qos=0)
        print(f"[MQTT] Conectado a {MQTT_HOST}:{MQTT_PORT}; ouvindo {TOPICO_LEITURA}")
    else:
        MQTT_INFO["conectado"] = False
        MQTT_INFO["erro"] = f"conexao recusada: {reason_code}"
        print(f"[MQTT] Conexao recusada: {reason_code}")


def ao_desconectar(cliente, userdata, disconnect_flags, reason_code, properties):
    MQTT_INFO["conectado"] = False
    print("[MQTT] Desconectado; o cliente tentara reconectar.")


def ao_receber(cliente, userdata, msg):
    texto = msg.payload.decode("utf-8", errors="replace")
    if msg.topic == TOPICO_STATUS:
        estado = texto.strip().lower()
        with LOCK:
            st = ESTADOS.setdefault(SETOR_ID, novo_estado(SETOR_ID))
            st["dispositivo_online"] = estado == "online"
        publicar("estado", snapshot(SETOR_ID))
        print(f"[MQTT] Status do robo: {estado}")
        return
    try:
        payload = json.loads(texto)
        leitura = LeituraIn.model_validate(payload)
        if leitura.setor_id != SETOR_ID:
            print(f"[MQTT] Leitura ignorada: setor_id {leitura.setor_id} diferente de {SETOR_ID}")
            return
        MQTT_INFO["mensagens"] += 1
        processar_leitura(leitura, "mqtt")
    except Exception as erro:
        MQTT_INFO["invalidas"] += 1
        MQTT_INFO["erro"] = str(erro)
        print(f"[MQTT] Mensagem invalida: {erro}")


def iniciar_mqtt():
    global CLIENTE_MQTT
    if not MQTT_ATIVO:
        print("[MQTT] Desativado por MQTT_ATIVO=0")
        return
    try:
        cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"encosta-api-{uuid.uuid4().hex[:8]}")
        if MQTT_USUARIO:
            cliente.username_pw_set(MQTT_USUARIO, MQTT_SENHA)
        cliente.on_connect = ao_conectar
        cliente.on_disconnect = ao_desconectar
        cliente.on_message = ao_receber
        cliente.reconnect_delay_set(min_delay=1, max_delay=30)
        cliente.connect_async(MQTT_HOST, MQTT_PORT, keepalive=30)
        cliente.loop_start()
        CLIENTE_MQTT = cliente
        print(f"[MQTT] Iniciando conexao com {MQTT_HOST}:{MQTT_PORT}")
    except Exception as erro:
        MQTT_INFO["erro"] = str(erro)
        print(f"[MQTT] Nao foi possivel iniciar: {erro}")


def parar_mqtt():
    if CLIENTE_MQTT:
        CLIENTE_MQTT.loop_stop()
        CLIENTE_MQTT.disconnect()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global LOOP
    LOOP = asyncio.get_running_loop()
    iniciar_mqtt()
    try:
        yield
    finally:
        parar_mqtt()


app = FastAPI(
    title="Encosta Viva - API",
    description="Recebe por MQTT as leituras de inclinação e vibração do Robô Sentinela. Sensor de umidade do solo opcional.",
    version="2.0.0",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def pagina_inicial():
    if not ARQUIVO_DASHBOARD.exists():
        return HTMLResponse("dashboard.html nao encontrado", status_code=404)
    return HTMLResponse(ARQUIVO_DASHBOARD.read_text(encoding="utf-8"))


@app.get("/saude", tags=["Operacao"])
def saude():
    return {"status": "ok", "mqtt": dict(MQTT_INFO), "setor_principal": SETOR_ID, "topico_leitura": TOPICO_LEITURA}


@app.get("/api/config", tags=["Operacao"])
def configuracao():
    return {
        "setor_id": SETOR_ID,
        "setor_nome": SETOR_NOME,
        "mqtt_host": MQTT_HOST,
        "mqtt_porta": MQTT_PORT,
        "topico_leitura": TOPICO_LEITURA,
        "topico_status": TOPICO_STATUS,
        "topico_ia": TOPICO_IA,
        "mqtt_ativo": MQTT_ATIVO,
        "ia_tendencia_ativa": True,
        "llm_configurado": bool(GROQ_API_KEY),
        "limiares": {"inclinacao_atencao": INCL_ATENCAO, "inclinacao_alerta": INCL_ALERTA, "inclinacao_maximo": INCL_MAXIMO, "vibracao_atencao": VIB_ATENCAO, "vibracao_alerta": VIB_ALERTA, "umidade_atencao": UMID_ATENCAO, "umidade_alerta": UMID_ALERTA},
        "pre_alerta_ia_minutos": PRE_ALERTA_MIN,
    }


@app.get("/api/ia/tendencia", tags=["Inteligência Artificial"])
def ia_tendencia(setor_id: Optional[str] = None):
    alvo = setor_id or SETOR_ID
    return analisar_com_pre_alerta(alvo)


@app.get("/api/estado", tags=["Dashboard"])
def estado_atual(setor_id: Optional[str] = None):
    return snapshot(setor_id or SETOR_ID)


@app.get("/api/historico", tags=["Dashboard"])
def historico(setor_id: Optional[str] = None, minutos: int = Query(10, ge=1, le=1440), limite: int = Query(600, ge=10, le=5000)):
    return BANCO.historico(setor_id or SETOR_ID, time.time() - minutos * 60, limite)


@app.get("/api/alertas", tags=["Dashboard"])
def alertas(setor_id: Optional[str] = None, limite: int = Query(20, ge=1, le=200)):
    return BANCO.eventos(setor_id or SETOR_ID, limite)


@app.get("/setores/{setor_id}/risco", tags=["Contrato"])
def risco_setor(setor_id: str):
    q = snapshot(setor_id)
    return {"setor_id": setor_id, "nivel": q["nivel"], "nivel_nome": q["nivel_nome"], "porque": q["fatores"], "orientacao": q["frase"], "online": q["online"], "atualizado_em": q["leitura"]["ts"] if q["leitura"] else None}


@app.post("/leituras", tags=["Contrato"])
def receber_leituras(corpo: Union[LeituraIn, List[LeituraIn]] = Body(...)):
    lista = corpo if isinstance(corpo, list) else [corpo]
    if len(lista) > 500:
        raise HTTPException(status_code=413, detail="Lote grande demais; maximo 500 leituras.")
    quadro = None
    for item in lista:
        quadro = processar_leitura(item, "http")
    return {"aceitas": len(lista), "nivel": quadro["nivel"] if quadro else None}


@app.post("/api/simular/{nivel}", tags=["Demonstracao"])
def simular_nivel(nivel: int):
    perfis = {
        0: (0.5, 0.010),
        1: (4.0, 0.020),
        2: (7.0, 0.030),
        3: (10.5, 0.030),
    }
    if nivel not in perfis:
        raise HTTPException(status_code=422, detail="O nivel deve ser 0, 1, 2 ou 3.")
    incl, vib = perfis[nivel]
    leitura = LeituraIn(setor_id=SETOR_ID, sensor_id="simulador", inclinacao_graus=incl, vibracao_g=vib, simulado=True, mpu_ok=True)
    return processar_leitura(leitura, "simulado")


@app.get("/api/stream", tags=["Dashboard"])
async def fluxo_tempo_real(request: Request, setor_id: Optional[str] = None):
    fila: asyncio.Queue = asyncio.Queue(maxsize=100)
    ASSINANTES.add(fila)
    alvo = setor_id or SETOR_ID
    async def gerador():
        try:
            yield "retry: 3000\n\n"
            yield f"event: estado\ndata: {json.dumps(snapshot(alvo), ensure_ascii=False)}\n\n"
            while not await request.is_disconnected():
                try:
                    msg = await asyncio.wait_for(fila.get(), timeout=10)
                    if msg["dados"].get("setor_id") == alvo:
                        yield f"event: estado\ndata: {json.dumps(msg['dados'], ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield f"event: estado\ndata: {json.dumps(snapshot(alvo), ensure_ascii=False)}\n\n"
        finally:
            ASSINANTES.discard(fila)
    return StreamingResponse(gerador(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


if __name__ == "__main__":
    print("=" * 60)
    print("ENCOSTA VIVA - API + IA + dashboard")
    print(f"Dashboard : http://localhost:{PORTA}")
    print(f"API docs  : http://localhost:{PORTA}/docs")
    print(f"MQTT      : {MQTT_HOST}:{MQTT_PORT}")
    print(f"Topico    : {TOPICO_LEITURA}")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=PORTA, log_level="info")
