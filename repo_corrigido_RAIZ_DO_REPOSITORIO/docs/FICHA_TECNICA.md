# Ficha Técnica do MVP — Encosta Viva

Preenchida conforme o modelo do Desafio FIAP CitizenTech (Global Solution 2026.2).

| Campo | Conteúdo |
|---|---|
| **Nome do produto** | Encosta Viva — Robô Sentinela |
| **Equipe** | Ricardo Matos (RM 95906) · Julio Zampieri (RM 98772) · João Dias (RM 99092) |
| **Cidadão e território** | Moradores de encostas de baixa renda no litoral norte paulista (maquete baseada na Vila Sahy, São Sebastião/SP) e agentes da Defesa Civil municipal. |
| **Problema, em uma frase** | Deslizamentos de terra matam famílias porque o risco é conhecido, mas não existe um aviso local, barato e contínuo que antecipe o movimento da encosta. |
| **Proposta de valor** | Um robô de baixo custo vigia a inclinação e a vibração do terreno, alerta no próprio local mesmo sem internet e entrega à Defesa Civil um painel em tempo real com tendência calculada por IA. |
| **Arquitetura: componentes** | MPU6050 → ESP32 (decide o risco; LEDs, buzzer) → MQTT (HiveMQ) → API FastAPI (regras + IA) → SQLite → dashboard (SSE). |
| **Fontes de dados** | Leituras reais do MPU6050 do robô (inclinação, vibração, RSSI). Dados simulados (botões do painel) ficam marcados como "simulação" e não treinam a IA. Evidências do problema: reportagens públicas sobre a tragédia de 2023 (links no README). |
| **Modelos de IA utilizados** | Regressão linear por mínimos quadrados (tendência da inclinação, offline) e LLM Llama 3.3 70B via Groq, opcional, só para redigir a orientação ao cidadão. |
| **URL do MVP e repositório** | Repositório: [https://github.com/Matos-Ricardo/encosta-viva_Maker](https://github.com/Matos-Ricardo/encosta-viva_Maker) · Vídeo: [https://www.youtube.com/watch?v=MCsqGxadtGM](https://www.youtube.com/watch?v=MCsqGxadtGM) · MVP: dashboard em `http://localhost:8000` (rodando junto com o robô) |
| **Indicadores de impacto** | Antecedência do pré-alerta (min) · alertas por mês e falsos positivos · % de tempo online · custo por encosta monitorada · famílias cobertas por sentinela. |
| **ODS conectados** | ODS 11 (metas 11.5 e 11.b), ODS 13 (meta 13.1) e ODS 9 (meta 9.1). Detalhes no README. |

## As seis perguntas do briefing

1. **Quem é o cidadão beneficiado?** O morador de encosta e o agente de Defesa Civil.
2. **Qual problema será resolvido?** Falta de aviso antecipado e local de movimentação do terreno.
3. **Como a solução funcionará?** O robô mede, classifica o risco em 4 níveis, alerta localmente e publica; a API calcula a tendência com IA e mostra no painel a taxa, a projeção até 10° e o pré-alerta.
4. **Quais tecnologias?** ESP32, MPU6050, MQTT, FastAPI, SQLite, SSE, regressão linear, LLM opcional, MDF cortado a laser (Fusion 360).
5. **Quem participa do ecossistema?** Moradores (usuários), Defesa Civil e prefeitura (operação e resposta), escolas e associações de bairro (instalação e conscientização), e a equipe como mantenedora.
6. **Como medir e ampliar o impacto?** Pelos indicadores acima; para ampliar, basta replicar o robô (hardware aberto de baixo custo) e trocar o broker público por um privado com TLS.

## Modelo de negócio (hipótese)

Pagador: prefeituras e fundos de defesa civil, com instalação por kit. Receita: venda do kit e assinatura do painel e dos alertas por SMS/WhatsApp. Escala: cada novo setor é só um `SETOR_ID` novo.

## Princípios de engenharia aplicados

Segurança e LGPD (sem dados pessoais, credenciais fora do código) · IA responsável (modelo explicável, limites declarados, pessoa no circuito) · resiliência (alerta local offline, falha segura do sensor) · acessibilidade (texto além da cor, `aria-live`, teclado) · reprodutibilidade (README, `requirements.txt`, 24 testes e CI no GitHub Actions).
