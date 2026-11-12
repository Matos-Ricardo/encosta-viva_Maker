# Checklist e roteiro de demonstração — Encosta Viva

> O roteiro completo do vídeo (até 6 min) está em `docs/ROTEIRO_VIDEO.md` e a lista de testes em `docs/PLANO_DE_TESTES.md`.

## Antes de ligar

- [ ] MPU6050 firme e conectado: VCC=3V3, GND=GND, SDA=GPIO21, SCL=GPIO22.
- [ ] LEDs com resistores de 220 ohms em GPIO25, GPIO26 e GPIO27.
- [ ] Buzzer ativo ligado ao GPIO33 (com transistor se a corrente exigir).
- [ ] Servos não instalados nesta montagem (o firmware ignora a ausência deles).
- [ ] Wi-Fi 2.4 GHz configurado no firmware.
- [ ] `SETOR_ID` igual no firmware e no arquivo `.env` da API.
- [ ] Sensor de umidade não é usado no firmware principal (só no experimental).

## Teste do firmware

- [ ] Gravar o firmware na placa ESP32.
- [ ] Abrir Monitor Serial em 115200 baud.
- [ ] Reiniciar o ESP32 mantendo o robô imóvel por pelo menos dois segundos.
- [ ] Confirmar `[MPU] Sensor encontrado`.
- [ ] Confirmar `[MPU] Referencia calibrada`.
- [ ] Confirmar leituras de inclinação e vibração no Serial.
- [ ] Confirmar `[MQTT] Conectado` e publicações `OK`.
- [ ] Inclinar suavemente o robô e verificar se os graus mudam.

Se o MPU não for encontrado, verificar alimentação 3V3, GND, SDA GPIO21 e SCL GPIO22. Se o valor oscilar muito, conferir se o módulo está bem preso e se a fonte e os cabos não estão causando ruído elétrico.

## Teste da API

- [ ] Executar `api/iniciar.bat`.
- [ ] Abrir `http://localhost:8000/saude` e conferir `status: ok`.
- [ ] Conferir `mqtt.conectado: true`.
- [ ] Abrir `http://localhost:8000/docs`.
- [ ] Abrir `http://localhost:8000` e confirmar dashboard.
- [ ] Verificar se a inclinação e a vibração recebidas aparecem no painel.
- [ ] Usar os botões de simulação dos níveis 0, 1, 2 e 3.

## Níveis configurados na demonstração

| Nível | Regra | Indicação local |
|---|---|---|
| 0 — Observação | inclinação < 3° e vibração < 0,04 g | Verde fixo |
| 1 — Monitoramento | inclinação ≥ 3°, vibração ≥ 0,04 g ou falha do MPU | Amarelo |
| 2 — Alerta | inclinação ≥ 6° ou vibração ≥ 0,15 g | Vermelho piscando |
| 3 — Alerta máximo | inclinação ≥ 10° | Vermelho piscando rápido |

## Demonstração da IA

- [ ] Gerar pelo menos cinco leituras reais válidas durante 20 segundos ou mais.
- [ ] Confirmar no dashboard o estado da IA local e a quantidade de amostras.
- [ ] Demonstrar tendência subindo/estável/caindo com leituras reais; simulações não entram no modelo.
- [ ] Explicar que a regressão estima uma tendência matemática e não prevê deslizamentos.
- [ ] Se `GROQ_API_KEY` estiver configurada, demonstrar a orientação LLM; caso contrário, demonstrar o fallback local.
- [ ] Confirmar que o nível de risco continua vindo das regras e não é alterado pela IA.
- [ ] Mostrar no painel a tendência da IA com leituras reais e o PRÉ-ALERTA quando a inclinação sobe rápido.

## Roteiro curto para apresentação

1. Apresente o MPU6050 preso à estrutura e explique que ele mede a aceleração nos três eixos.
2. Explique que o ESP32 registra a posição inicial como referência e calcula a variação angular.
3. Mostre o semáforo físico: verde, amarelo e vermelho conforme os limites configurados.
4. Mostre no Monitor Serial os graus, a vibração estimada e o estado da conexão MQTT.
5. Mostre o caminho dos dados: ESP32 → Wi-Fi → broker HiveMQ → API FastAPI → SQLite/dashboard.
6. Incline suavemente o robô e mostre a atualização do LED e do dashboard.
7. Use os botões de simulação do painel para demonstrar todos os níveis sem forçar a estrutura.
8. Mostre a IA local após acumular cinco ou mais leituras reais e explique a projeção de tendência.

## Limitações importantes

- A vibração é estimada pelo desvio padrão da magnitude da aceleração do MPU6050 em uma janela de aproximadamente um segundo.
- Os limites angulares e de vibração são valores de demonstração da maquete, não limites geotécnicos certificados.
- O sistema não prevê deslizamentos sozinho e não substitui sensores profissionais, vistoria ou orientação da Defesa Civil.
