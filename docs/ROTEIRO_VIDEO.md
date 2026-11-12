# Roteiro do vídeo (máximo 6 minutos — alvo: 4 a 5 min)

Pedido pelo professor: o vídeo precisa (1) apresentar o **problema no contexto CitizenTech**, (2) explicar **brevemente a solução**, (3) **demonstrar o robô funcionando**, (4) **evidenciar o sensor, a integração com a IA e as principais funcionalidades**. Mostre também **diferentes condições e situações de falha**. Publique no YouTube (pode ser "não listado") e cole o link no README. O vídeo deve estar público e funcionando na correção.

Filme com o robô e o notebook no mesmo quadro (ou alterne com gravação de tela). Todos falam, e os nomes e RMs aparecem na tela ou na fala.

| Tempo | Quem | O que falar e mostrar |
|---|---|---|
| 0:00–0:30 | Ricardo | "Somos Ricardo Matos (95906), Julio Zampieri (98772) e João Dias (99092). Esta é a evolução do robô da MakerLab para o desafio CitizenTech." **Problema:** 64 mortos na tragédia de São Sebastião em 2023; a Vila Sahy tinha risco conhecido e faltava um aviso local e barato. Cidadão: morador de encosta e Defesa Civil. |
| 0:30–1:15 | Julio | **Solução e hardware:** mostrar o robô de MDF (Fusion 360, corte a laser), ESP32, MPU6050 preso à estrutura, LEDs e buzzer. Explicar o que o **MPU6050** mede (inclinação e vibração) e como a calibração define a posição de referência. Mostrar o Monitor Serial com a calibração e `[MQTT] Publicacao OK`. |
| 1:15–1:45 | Julio | **Arquitetura:** desenhar ou mostrar o diagrama do README: ESP32 → MQTT → API (regras + IA) → SQLite → dashboard. |
| 1:45–2:45 | João | **Demonstração dos níveis:** robô nivelado (verde) → inclinar devagar (amarelo ≥ 3°) → vermelho (≥ 6°) → alerta máximo (≥ 10°, sirene) → voltar (histerese de 8 s). Em cada nível, apontar LED, painel e gráfico. Bater de leve na mesa para mostrar a vibração. |
| 2:45–3:30 | João | **IA integrada ao sensor:** inclinar de 0° a ~7° por pelo menos 20 s de leituras reais e mostrar o card da IA saindo de "Coletando" para "Tendência de alta", com taxa em °/min, projeção até 10° e o **PRÉ-ALERTA da IA**. Mostrar também o histórico e o gráfico. Explicar: regressão linear sobre as leituras reais, a IA só antecipa o aviso e **não muda o nível**, quem decide é a Defesa Civil. |
| 3:30–4:30 | Ricardo | **Situações de falha:** (a) desligar o Wi-Fi: o robô continua alertando e o painel mostra "Offline"; (b) soltar o fio SDA do MPU: amarelo de falha segura, nunca verde; religar e mostrar a recuperação; (c) fechar a API: o robô segue com as regras locais. |
| 4:30–5:15 | Ricardo | **Qualidade e impacto:** rodar `python -m unittest discover -v` (24 testes ok), mostrar `/docs`, o plano de testes e o repositório no GitHub. **ODS 11, 13 e 9.** Limitações (maquete, limiares não geotécnicos, broker público) e próximos passos (broker privado com TLS, mais sensores, alertas por WhatsApp). |

Dicas: deixe cada nível visível por 3 a 4 segundos, grave o áudio em lugar silencioso, mantenha o painel em tela cheia, use o Serial em fonte grande e faça um teste de 20 s antes de gravar tudo.
