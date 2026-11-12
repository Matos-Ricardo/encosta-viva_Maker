# Plano de testes e demonstração

Cobre diferentes condições de operação e situações de falha, como pede a avaliação de "Testes e demonstração". A coluna **Evidência** indica o tempo, no vídeo de demonstração (2 min 08 s), em que cada teste aparece; os testes marcados como "não gravado" não foram filmados.

## A. Testes automatizados (software)

`cd api && python -m unittest discover -v` → **24 testes**, sem MQTT e sem internet.

| Grupo | O que valida |
|---|---|
| Classificação | Limites 2,99° / 3° / 5,99° / 6° / 9,99° / 10°; vibração 0,04 g e 0,15 g; prevalece o pior fator; falha do MPU nunca é nível 0. |
| API | `/saude`, `/leituras`, `/api/estado`, `/api/historico`, `/api/alertas`, simulação dos 4 níveis, entrada inválida rejeitada (422). |
| IA | Poucas amostras ("coletando"), subindo, caindo, estável, janela recente de 90 s, projeção até 10°, pré-alerta. |
| Pré-alerta | A API publica `{"pre_alerta":true,...}` em `encosta/<setor>/ia`; sem MQTT nada quebra. |
| Sensor opcional | Limites 70% e 85%, solo saturado eleva o nível, umidade inválida rejeitada, migração de banco antigo. |

## B. Testes no robô (hardware)

| # | Condição | Procedimento | Resultado esperado | Evidência |
|---|---|---|---|---|
| 1 | Calibração | Ligar com o robô imóvel e nivelado | Serial: `[MPU] Referencia calibrada`; LED verde | Início do vídeo (0:00–0:04): LED verde e painel em nível 0 |
| 2 | Operação normal | Deixar parado 10 s | Inclinação < 3°, vibração baixa, nível 0 | 0:04 (0,55°) e 2:04 (0,24°): painel "Observação" |
| 3 | Nível 1 | Inclinar devagar até ≥ 3° | Amarelo fixo + bipe curto; painel "Monitoramento" | 0:12 e 0:24: painel "Monitoramento" |
| 4 | Nível 2 | Inclinar até ≥ 6° | Vermelho piscando + bipe | 0:16 (6,94°): painel "Alerta", LED vermelho |
| 5 | Nível 3 | Inclinar até ≥ 10° | Vermelho piscando rápido + sirene; painel "Alerta máximo" | 1:00 (10,32°) e 1:52 (21,79°): painel "Alerta máximo" |
| 6 | Histerese | Voltar ao nível | O nível só cai após 8 s estáveis | Não gravado |
| 7 | Vibração | Bater de leve na mesa ao lado | Vibração sobe; nível 1 ou 2 conforme a intensidade | Não gravado |
| 8 | **IA com leituras reais** | Inclinar de 0° a ~7° aos poucos, por pelo menos 20 s de leituras reais | Card da IA muda de "Coletando" para "Tendência de alta" com taxa em °/min, projeção até 10° e, se for rápida, **PRÉ-ALERTA da IA** | 0:04, 0:12 e 1:00: card "Tendência de alta" com taxa e projeção |
| 9 | **Falha: Wi-Fi/MQTT** | Desligar o hotspot/roteador | LEDs e buzzer continuam; painel mostra robô "Offline" em ~15 s; ao religar o robô reconecta sozinho | Não gravado |
| 10 | **Falha: MPU desconectado** | Soltar o fio SDA com o robô ligado | Amarelo, Serial `[ERRO] Falha ao ler o MPU6050`, painel "Falha" no MPU; nunca verde | Não gravado |
| 11 | Recuperação | Religar o fio SDA | Serial `[MPU] Reconectado`, nível volta ao normal após a histerese | Não gravado |
| 12 | **Sem IA/API** | Fechar a API | Robô segue alertando com as regras locais (LEDs e buzzer) | Não gravado |
| 13 | Firmware experimental (opcional) | Só se for gravado e testado | Pré-alerta pisca o amarelo no robô; sensor de umidade aparece no painel | Não aplicável (opcional, não testado) |

## C. Testes do painel

| # | Teste | Esperado |
|---|---|---|
| 1 | Botões "Nível 0 a 3" | O painel muda de nível sem mexer no robô; leitura marcada "SIMULADA" |
| 2 | Gráfico | Linha da inclinação com tracejados de 3°, 6° e 10° |
| 3 | `/docs` | Swagger lista todos os endpoints |
| 4 | Teclado e leitor de tela | Botões acessíveis por Tab; nível lido por `aria-live` |
