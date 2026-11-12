# Ligações do Robô Sentinela

Placa: ESP32 DevKit V1. Sensor de movimento: MPU6050 (GY-521).

## Componentes utilizados

- 1 ESP32 DevKit V1
- 1 MPU6050 (GY-521)
- 3 LEDs (verde, amarelo e vermelho), cada um com resistor de 220 ohms
- 1 buzzer ativo compatível com a tensão/corrente do circuito
- 2 servomotores SG90: previstos no modelo 3D, **não instalados** na montagem final (opcionais)
- 1 botão opcional para simulação (desativado por padrão no firmware)
- 1 sensor de umidade do solo com saída analógica (somente para o firmware experimental, opcional)
- Protoboard e jumpers

O sensor de umidade do solo **não é usado** no firmware principal. Ele só existe no firmware experimental opcional (`firmware/experimental_ia_umidade/`). Não o ligue se estiver usando o firmware principal.

## Tabela de ligações

> Servos: a tabela abaixo vale apenas se forem instalados. Sem eles, o robô funciona normalmente.

| Componente | Pino | ESP32 |
|---|---|---|
| MPU6050 | VCC | 3V3 |
| MPU6050 | GND | GND |
| MPU6050 | SDA | GPIO21 |
| MPU6050 | SCL | GPIO22 |
| LED verde | ânodo via resistor 220 ohms | GPIO25 |
| LED amarelo | ânodo via resistor 220 ohms | GPIO26 |
| LED vermelho | ânodo via resistor 220 ohms | GPIO27 |
| LEDs | cátodos | GND |
| Buzzer ativo | sinal (+) | GPIO33 (usar transistor se necessário) |
| Servo 1 | sinal | GPIO14 |
| Servo 2 | sinal | GPIO13 |
| Servos | alimentação | fonte externa regulada de 5 V |
| Servos | GND | GND comum com ESP32 |
| Botão opcional | sinal | GPIO34 (ver observação abaixo) |
| LED azul onboard | onboard | GPIO2 |
| Sensor de umidade (só firmware experimental) | VCC / GND / AO | 3V3 / GND / GPIO35 |

## Cuidados elétricos importantes

- Os servos NÃO devem ser alimentados pelo pino 3V3 do ESP32. Use fonte externa de 5 V dimensionada para os servos e una o GND da fonte ao GND do ESP32.
- Se os servos provocarem reinicializações, ruído ou falhas no MPU6050, adicione capacitor eletrolítico de 470 a 1000 uF próximo à alimentação dos servos e revise a fonte.
- GPIO34 é somente entrada e não possui pull-up/pull-down interno. O botão está desativado por padrão no firmware para evitar leituras aleatórias. Para ativá-lo, instale resistor de 10k entre GPIO34 e 3V3, botão entre GPIO34 e GND, e altere `USAR_BOTAO_SIMULACAO` para `true` no firmware.
- O MPU6050 deve ficar firmemente preso à estrutura, sem folga.
- Ligue SDA/SCL conforme a tabela e mantenha os fios I2C curtos.
- O robô deve permanecer imóvel na posição que será a referência durante os dois segundos de calibração após ligar.

## Pré-alerta da IA

Quando a API detecta tendência de alta rápida (projeção de até 3 minutos para 10°), o painel destaca o pré-alerta e a API publica em `encosta/<SETOR_ID>/ia`. Apenas o firmware experimental usa essa mensagem (LED amarelo piscando e bipe).

## LEDs

| Nível | Condição | Indicação |
|---|---|---|
| 0 | Inclinação abaixo de 3 graus e vibração abaixo do limite | Verde fixo |
| 1 | Inclinação a partir de 3 graus, vibração a partir de 0,04 g ou falha do MPU | Amarelo fixo + bipe curto periódico |
| 2 | Inclinação a partir de 6 graus ou vibração a partir de 0,15 g | Vermelho piscando lentamente + bipe |
| 3 | Inclinação a partir de 10 graus | Vermelho piscando rapidamente + sirene intermitente |

Os limites são apenas parâmetros de demonstração da maquete e precisam de validação técnica antes de qualquer uso real.
