# Firmware experimental (opcional, NÃO testado no robô)

O firmware principal está em `../encosta_viva_esp32/` e é o que foi testado e filmado no robô. **Use sempre o principal na entrega.**

Esta pasta guarda uma versão com extras, a ser usada só depois de um teste próprio no robô:

- **Pré-alerta da IA no robô:** a API publica em `encosta/<SETOR_ID>/ia` e o robô pisca amarelo e apita quando a IA prevê subida rápida (níveis 0 e 1). Sem mensagem por 10 s, ignora a IA.
- **Sensor de umidade do solo opcional** (AO no GPIO35), desligado por padrão em `USAR_SENSOR_UMIDADE`.
- Publicação a cada 1 s e na hora em que o nível muda.

Para testar: grave esta versão, confira no Serial `[MPU] Referencia calibrada` e `[MQTT] Conectado`, incline o robô e veja se os níveis mudam como no firmware principal. Se qualquer coisa estiver diferente, volte ao principal. A API e o dashboard funcionam com as duas versões.
