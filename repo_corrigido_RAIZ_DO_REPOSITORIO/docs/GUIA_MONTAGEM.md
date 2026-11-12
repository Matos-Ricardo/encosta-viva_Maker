# Guia de montagem — Encosta Viva

## 1. Componentes

- ESP32 DevKit V1
- MPU6050 / GY-521
- 3 LEDs (verde, amarelo, vermelho) + 3 resistores de 220 ohms
- Buzzer ativo
- Servos SG90: previstos no modelo 3D, **não instalados** nesta montagem (opcionais)
- Jumpers e protoboard

O sensor de umidade do solo não é usado no firmware principal. Ele só faz parte do firmware experimental opcional (`firmware/experimental_ia_umidade/`).

## 2. Ligações

Consulte `hardware/LIGACOES.md` para a tabela completa. Resumo:

| Componente | ESP32 |
|---|---|
| MPU6050 SDA / SCL | GPIO21 / GPIO22 |
| MPU6050 VCC / GND | 3V3 / GND |
| LED verde / amarelo / vermelho | GPIO25 / GPIO26 / GPIO27 (cada um com resistor 220 ohms) |
| Buzzer ativo | GPIO33 |
| Servo 1 / Servo 2 (sinal), só se forem instalados | GPIO14 / GPIO13 |
| LED azul onboard | GPIO2 |

Se algum dia os servos forem instalados, use alimentação externa de 5 V, una o GND da fonte ao GND do ESP32 e não os alimente pelo 3V3.

O botão de simulação está desativado por padrão. GPIO34 não possui pull-up interno; para utilizar botão, instale resistor externo de 10k entre GPIO34 e 3V3 e ligue o botão entre GPIO34 e GND. Depois altere `USAR_BOTAO_SIMULACAO` para `true` no firmware.

## 3. Firmware

1. Instale as bibliotecas Adafruit MPU6050, Adafruit Unified Sensor, PubSubClient e ESP32Servo na Arduino IDE.
2. Abra `firmware/encosta_viva_esp32/encosta_viva_esp32.ino`.
3. Preencha o nome e a senha da rede Wi-Fi 2.4 GHz.
4. Confira o `SETOR_ID`: deve ser igual ao `.env` da API.
5. Selecione a placa ESP32 Dev Module e a porta correta e grave o firmware.
6. Mantenha o robô imóvel na posição de referência durante a calibração de dois segundos.
7. Abra o Monitor Serial em 115200 baud. Procure `[MPU] Sensor encontrado`, `[MPU] Referencia calibrada` e `[MQTT] Conectado`.

## 4. API e dashboard

No Windows, entre em `api/` e execute `iniciar.bat`. Na primeira execução, o script cria um ambiente virtual e instala as dependências. Depois acesse:

- Dashboard: `http://localhost:8000`
- Documentação da API: `http://localhost:8000/docs`
- Saúde da API/MQTT: `http://localhost:8000/saude`

A API roda no computador, não no ESP32. Ela se conecta ao mesmo broker MQTT HiveMQ e assina o tópico `encosta/<SETOR_ID>/leitura`.

## 5. Testes

1. Com API ligada, confira `/saude` e veja se `mqtt.conectado` fica `true`.
2. Com o ESP32 ligado, confira no Monitor Serial se aparece `[MQTT] Conectado` e se publica mensagens.
3. No dashboard, veja se o robô aparece online e os valores de inclinação/vibração são atualizados.
4. Use os botões de simulação do dashboard para testar os quatro níveis sem inclinar fisicamente o robô.
5. Incline o conjunto suavemente para conferir se o valor de graus muda. Não force os cabos.

## 6. Inteligência Artificial

O dashboard apresenta a análise de tendência da inclinação por regressão linear local. O modelo utiliza leituras reais válidas do SQLite, exige no mínimo cinco amostras e 20 segundos de janela, e mostra tendência e projeção matemática até 10° quando aplicável. Leituras simuladas e falhas do MPU não treinam o modelo. A IA é complementar e não altera o nível calculado pelas regras. Quando prevê subida rápida, o painel destaca o PRÉ-ALERTA da IA. O LLM Groq é opcional via `GROQ_API_KEY`; sem chave, o sistema continua funcionando com orientação local.

## 7. Interpretação

- Nível 0: verde fixo.
- Nível 1: Monitoramento (amarelo fixo) e bipe curto periódico.
- Nível 2: vermelho piscando lentamente e bipe.
- Nível 3: vermelho piscando rapidamente e sirene intermitente.

Aumentos de nível são imediatos; reduções aguardam oito segundos estáveis para evitar oscilação. Os limiares são demonstrativos e não devem ser usados como critério real de evacuação.
