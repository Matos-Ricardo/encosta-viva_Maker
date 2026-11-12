# Robô Modelo 02 — Patins, dois SG90, encaixes em MDF

Projeto independente do primeiro robô, em MDF nominal de 3 mm.

## Arquivos

- `Robo_Modelo_02.py` e `Robo_Modelo_02.manifest`: script e manifesto que geram o modelo 3D (50 placas, cada uma com esboço e extrusão) quando executados no Fusion 360.
- `MODELO_02_MONTADO.png`: imagem da montagem do modelo.
- `DXF_nominal`: as 50 peças nominais em mm, escala 1:1, em arquivos individuais por tipo de peça, sem compensação de kerf.
- `../T01_FRENTE_LED_3LEDS.dxf`: frente do tronco com furos para os 3 LEDs, usada na montagem física.
- `TESTE_ENCAIXE`: cupom e lingueta para acertar espessura/kerf antes do lote.
- `Lista_de_pecas.csv`: códigos, grupos e orientações das 50 peças.

## Medidas principais

| Item | Medida nominal |
|---|---|
| Altura | 252 mm |
| Largura total com braços abaixados | 178 mm |
| Cabeça, largura × altura × profundidade | 146 × 84 × 72 mm |
| Tronco, cintura / ombros | 100 / 132 mm |
| Tronco, altura × profundidade | 112 × 68 mm |
| Pé: plataforma | 42 × 84 mm |
| Pé: longarina em patim | 98 mm de comprimento |
| Espessura das placas | 3 mm |

Cabeça com fachada octogonal e miolo retangular menor, olhos em losango e boca vazada em zigue-zague. Corpo trapezoidal, braços terminados em pá e pés apoiados em duas longarinas inclinadas. São 50 placas; 12 delas são pequenas lâminas dos quatro blocos para a tampa M3.

## Encaixes e montagem

Os encaixes têm folga nominal total de 0,15 mm nos rasgos. A folga é um ponto de partida: MDF real e largura de corte variam. Cortar o cupom primeiro, medir o MDF e ajustar a compensação na máquina. O desenho não garante encaixe por pressão em qualquer laser. A prancha é uma organização virtual, não o aproveitamento final de uma chapa específica.

1. Separar e identificar as peças conforme os códigos do CSV. Fazer uma montagem a seco antes de colar.
2. Montar cada pé com dois `PATIM` e uma `PLATAFORMA`. Colar as longarinas sob a plataforma.
3. Encaixar as quatro paredes de cada perna nos rasgos da plataforma. Aplicar pouca cola nas juntas.
4. Apoiar e colar o piso `T05` sobre as pernas. Encaixar as duas laterais e a frente do tronco no piso; as abas guiam a posição. As laterais inclinadas recebem as abas nas faces frontal e traseira. As pequenas diferenças de esquadro nas bordas inclinadas são fechadas com cola, sem forçar o MDF.
5. Encaixar as pontes superior/inferior dos ombros nas faces frontal/traseira e nos suportes `SUPORTE_SG90`. As pontes têm extensões internas que se prendem ao tronco. Montar os servos antes de fechar a caixa.
6. Encaixar o teto do tronco e o pescoço. Encaixar a base da cabeça no alto do pescoço.
7. Montar a cabeça: laterais, base e topo se encaixam nas duas fachadas. O ressalto octogonal ao redor do miolo menor faz parte do desenho.
8. Laminar três peças de cada `BLOCO_M3`, com os furos alinhados. Colar os dois blocos inferiores no piso e os dois superiores no teto, usando a tampa para alinhar os furos. **Não colar a tampa.** Prender a tampa com quatro parafusos M3 e porcas, escolhendo comprimento que atravesse tampa, bloco e porca.
9. Centralizar eletricamente cada servo antes de fixar as cruzetas e os braços. Fixar as placas `BRACO_PA` nas cruzetas plásticas fornecidas com os servos; não diretamente no eixo. Usar o parafuso central original do servo e parafusos adequados à cruzeta.
10. Conferir a folga dos dois braços, passagem dos cabos e acesso à eletrônica antes da colagem definitiva.

## Suportes de servo

Há um suporte SG90 em cada ombro: abertura nominal de 23,5 × 12,8 mm, furos piloto de 2,2 mm separados por 28 mm. Essas medidas são provisórias e precisam ser conferidas nos seus dois motores. SG90 de fabricantes diferentes e cruzetas diferentes podem exigir ajuste. O arquivo modela a estrutura e os espaços; os motores, cruzetas e parafusos não são sólidos de precisão incluídos na montagem.

Os braços têm furo central de 3,2 mm e rasgos auxiliares para adaptar a fixação à cruzeta real. Conferir o alcance do eixo/cruzeta em relação ao afastamento entre suporte e braço. A análise estática de placas não valida o movimento completo, o torque, a estabilidade com carga nem a montagem motorizada.

## Alterações no Fusion

Cada placa é um componente com esboço e extrusão. A espessura usa o parâmetro `mdf`. Os demais parâmetros do documento são referências: os contornos não se redimensionam automaticamente por esses parâmetros. Para mudanças globais, alterar o script `Robo_Modelo_02.py` e executá-lo de novo no Fusion; ele cria documentos novos.

O software e o firmware do Roberto anterior continuam em sua pasta original. Este projeto mecânico reserva **dois** motores; controlar ambos exige um firmware com dois sinais de servo.

**Na montagem física final os dois servos SG90 não foram instalados**; o robô alerta por LEDs e buzzer. O modelo 3D mantém os suportes dos servos como previsão de evolução.
