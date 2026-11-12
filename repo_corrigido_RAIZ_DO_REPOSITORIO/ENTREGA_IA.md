# Entrega Encosta Viva com IA

## O que foi adicionado

- `api/ia_encosta.py`: modelo local de regressão linear por mínimos quadrados para estimar tendência da inclinação.
- `api/main.py`: integração da IA no estado da API e endpoint `GET /api/ia/tendencia`.
- `api/dashboard.html`: painel com status, taxa e projeção da IA.
- LLM Groq opcional para redação de orientação, sem bloquear a API e com fallback local.
- Testes automatizados em `api/test_ia_encosta.py`.

## Como funciona

A regressão usa leituras reais válidas do SQLite, excluindo simulações e falhas do MPU. Exige pelo menos cinco amostras e 20 segundos de janela. Estima a tendência linear da inclinação em graus por minuto e, quando positiva, projeta matematicamente o tempo até 10 graus.

A IA não determina, aumenta ou reduz o nível de risco. A classificação de segurança permanece nas regras da API e no firmware: 0-3 graus (nível 0), a partir de 3 (nível 1), 6 (nível 2), 10 (nível 3), com vibração a partir de 0,04 g e 0,15 g elevando os níveis conforme a regra existente.

## LLM opcional

Para habilitar orientações redigidas por LLM, configure `GROQ_API_KEY` e opcionalmente `GROQ_MODEL` no arquivo `api/.env`. Sem chave, internet ou em caso de falha, o sistema usa as orientações locais. A chave não deve ser enviada ao GitHub.

## Validação executada nesta entrega

- Compilação sintática Python de `main.py` e `ia_encosta.py`.
- Três testes unitários da regressão: coleta insuficiente, tendência crescente e tendência decrescente.
- Verificação de importação/configuração da API com MQTT simulado no ambiente de validação.
- Verificação dos limites de classificação em 2,99°, 3°, 5,99°, 6°, 9,99° e 10°.

A comunicação real com ESP32/MQTT e o LLM com chave válida ainda precisam ser demonstrados no computador/hardware do grupo.

## Revisão final da entrega

- Equipe, RMs e ficha técnica adicionados (README, `docs/FICHA_TECNICA.md`, rodapé do dashboard e cabeçalho do firmware).
- Dashboard: novo gráfico de inclinação dos últimos 5 minutos com linhas de limiar.
- IA: a regressão passou a usar a janela recente (90 s), refletindo a tendência atual.
- Firmware: mantida a versão testada (publicação a cada 2 s); as melhorias ficaram só na versão experimental opcional.
- Testes: de 3 para 16 (classificação, endpoints, validação, IA).
- Roteiro de vídeo com divisão de falas em `docs/ROTEIRO_VIDEO.md`.

## Atualização conforme o enunciado da MakerLab

- **Firmware principal inalterado:** `firmware/encosta_viva_esp32/` é a versão testada no robô. Nada nele foi modificado.
- **IA com pré-alerta:** o painel mostra taxa, projeção até 10° e PRÉ-ALERTA; a API também publica o pré-alerta em `encosta/<setor>/ia`.
- **Versão experimental opcional** (`firmware/experimental_ia_umidade/`, não testada no robô): recebe o pré-alerta e pisca amarelo; sensor de umidade opcional. A API aceita leituras com ou sem umidade e migra bancos antigos.
- **Testes:** 24 automatizados + plano de testes com situações de falha (`docs/PLANO_DE_TESTES.md`).
- **Documentação:** README com mapa dos critérios, ODS com metas, LGPD, ficha técnica no modelo do desafio, guia de publicação no GitHub e workflow de CI.
- **Painel:** gráfico dos últimos 5 minutos, selo de pré-alerta da IA e melhorias de acessibilidade.
