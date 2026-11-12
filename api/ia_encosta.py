# -*- coding: utf-8 -*-
"""Módulo de IA do Encosta Viva: regressão linear local + LLM opcional.

A regressão é recalculada com leituras reais do SQLite. Não decide o nível de risco.
"""
from __future__ import annotations
import json
import math
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

LIMITE_MAXIMO_GRAUS = 10.0
MIN_AMOSTRAS = 5
MIN_JANELA_SEGUNDOS = 20.0
JANELA_RECENTE_S = 90.0
PRE_ALERTA_MIN = 3.0  # pré-alerta se a projeção até 10° for de até 3 minutos


def analisar_tendencia(amostras: List[Dict[str, float]]) -> Dict[str, Any]:
    """Ajusta y=a+bx por mínimos quadrados e estima chegada a 10 graus.

    Exige pelo menos cinco leituras reais válidas e uma janela de 20 segundos.
    O eixo x é tempo em minutos desde a primeira amostra.
    """
    dados = [(float(p["ts"]), float(p["inclinacao_graus"])) for p in amostras if p.get("ts") is not None and p.get("inclinacao_graus") is not None]
    if len(dados) < MIN_AMOSTRAS:
        return {"ativa": True, "modelo": "Regressão linear incremental (offline)", "status": "coletando", "mensagem": "IA coletando leituras reais; são necessárias pelo menos 5 amostras válidas.", "amostras": len(dados), "taxa_graus_min": None, "previsao_minutos_limite": None, "limite_graus": LIMITE_MAXIMO_GRAUS}
    # Usa apenas a janela recente (últimos 90 s) para refletir a tendência atual;
    # se houver poucas amostras nela, recorre às 5 últimas leituras.
    recentes = [d for d in dados if d[0] >= dados[-1][0] - JANELA_RECENTE_S]
    dados = (recentes if len(recentes) >= MIN_AMOSTRAS else dados[-MIN_AMOSTRAS:])[-60:]
    t0 = dados[0][0]
    xs = [(t - t0) / 60.0 for t, _ in dados]
    ys = [y for _, y in dados]
    if (dados[-1][0] - t0) < MIN_JANELA_SEGUNDOS:
        return {"ativa": True, "modelo": "Regressão linear incremental (offline)", "status": "coletando", "mensagem": "IA aguardando uma janela temporal maior para estimar a tendência.", "amostras": len(dados), "taxa_graus_min": None, "previsao_minutos_limite": None, "limite_graus": LIMITE_MAXIMO_GRAUS}
    xm = sum(xs) / len(xs); ym = sum(ys) / len(ys)
    den = sum((x-xm)**2 for x in xs)
    slope = sum((x-xm)*(y-ym) for x,y in zip(xs,ys)) / den if den > 1e-12 else 0.0
    atual = ys[-1]
    if slope > 0.03:
        status = "subindo"
        previsao = max(0.0, (LIMITE_MAXIMO_GRAUS-atual)/slope) if atual < LIMITE_MAXIMO_GRAUS else 0.0
        mensagem = (f"Tendência de alta: inclinação cresce cerca de {slope:.3f}° por minuto. "
                    + (f"Projeção matemática de {previsao:.1f} min até {LIMITE_MAXIMO_GRAUS:.0f}° se a taxa continuar." if previsao > 0 else "O limite máximo já foi atingido."))
    elif slope < -0.03:
        status = "caindo"; previsao = None
        mensagem = f"Tendência de queda: inclinação diminui cerca de {abs(slope):.3f}° por minuto."
    else:
        status = "estavel"; previsao = None
        mensagem = "Tendência aproximadamente estável no intervalo analisado."
    return {"ativa": True, "modelo": "Regressão linear incremental (offline)", "status": status, "mensagem": mensagem, "amostras": len(dados), "taxa_graus_min": round(slope, 4), "previsao_minutos_limite": round(previsao, 1) if previsao is not None else None, "limite_graus": LIMITE_MAXIMO_GRAUS}


def avaliar_pre_alerta(ia: Dict[str, Any]) -> bool:
    """Pré-alerta da IA: tendência de alta com projeção de até 3 min para 10°.

    Só antecipa o aviso ao robô (sinal visual/sonoro diferente). Nunca altera nem
    reduz o nível de risco, que continua vindo das regras determinísticas.
    """
    if not ia or ia.get("status") != "subindo":
        return False
    previsao = ia.get("previsao_minutos_limite")
    return previsao is not None and previsao <= PRE_ALERTA_MIN


def gerar_orientacao_llm(api_key: str, model: str, leitura: Dict[str, Any], nivel_nome: str, orientacao_base: str, emergencia: str) -> Optional[str]:
    """Usa endpoint compatível com OpenAI da Groq. Retorna None em qualquer falha."""
    if not api_key:
        return None
    umidade = leitura.get("umidade_solo_pct")
    umidade_txt = f"Umidade do solo: {umidade} %. " if umidade is not None else ""
    prompt = (
        "Escreva uma orientação em português brasileiro, com no máximo 45 palavras, "
        "clara e prudente para um painel comunitário de demonstração. "
        "Não invente medições, não diagnostique deslizamento e não altere o nível de risco. "
        "Para nível Alerta ou Alerta máximo, oriente procurar a Defesa Civil; preserve o contato 199/193. "
        f"Nível calculado por regras: {nivel_nome}. Inclinação: {leitura.get('inclinacao_graus')} graus. "
        f"Vibração: {leitura.get('vibracao_g')} g. MPU válido: {leitura.get('mpu_ok')}. "
        f"{umidade_txt}"
        f"Orientação-base: {orientacao_base} {emergencia if nivel_nome in ('Alerta','Alerta máximo') else ''}"
    )
    body = json.dumps({"model": model, "temperature": 0.2, "max_tokens": 100, "messages": [
        {"role": "system", "content": "Você redige orientações de segurança conservadoras. Não decide nem reclassifica risco."},
        {"role": "user", "content": prompt}
    ]}).encode("utf-8")
    req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=4) as response:
            payload = json.loads(response.read().decode("utf-8"))
        texto = payload["choices"][0]["message"]["content"].strip()
        return texto[:500] if texto else None
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, KeyError, IndexError):
        return None
