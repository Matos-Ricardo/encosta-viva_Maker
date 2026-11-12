/*
 * ENCOSTA VIVA - Robô Sentinela (ESP32 + MPU6050 + MQTT)
 * FIAP Global Solution 2026.2 - Ricardo Matos (RM 95906), Julio Zampieri (RM 98772), João Dias (RM 99092)
 * Sensor de umidade do solo opcional (USAR_SENSOR_UMIDADE).
 *
 * Bibliotecas (Arduino IDE > Gerenciar Bibliotecas):
 *   - Adafruit MPU6050
 *   - Adafruit Unified Sensor
 *   - PubSubClient
 *   - ESP32Servo
 *
 * IMPORTANTE:
 *   - Mantenha o robô imóvel na posição de referência durante a calibração.
 *   - Servos devem usar fonte externa regulada de 5 V; una o GND dessa fonte
 *     ao GND do ESP32. Não alimente servos pelo pino 3V3 do ESP32.
 *   - GPIO34 é somente entrada e NÃO tem pull-up interno. Use resistor externo
 *     de 10k entre GPIO34 e 3V3; botão entre GPIO34 e GND.
 */

#include <WiFi.h>
#include <Wire.h>
#include <math.h>
#include <time.h>
#include <PubSubClient.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <ESP32Servo.h>

// ===== REDE: PREENCHA COM SUA REDE WI-FI 2.4 GHz =====
const char* WIFI_SSID = "SEU_WIFI";
const char* WIFI_SENHA = "SUA_SENHA";
const char* MQTT_HOST = "broker.hivemq.com";
const uint16_t MQTT_PORTA = 1883;

// Estes IDs precisam ser iguais aos configurados na API (.env).
const char* SETOR_ID = "vilasahy-q4m8z2";
const char* SENSOR_ID = "robo-sentinela-01";

// ===== PINOS =====
const int PIN_LED_VERDE = 25;
const int PIN_LED_AMARELO = 26;
const int PIN_LED_VERMELHO = 27;
const int PIN_BUZZER = 33;       // buzzer ativo
const int PIN_BOTAO = 34;        // resistor externo de 10k para 3V3
const int PIN_LED_REDE = 2;      // LED onboard: aceso = MQTT conectado
const int PIN_SERVO1 = 14;
const int PIN_SERVO2 = 13;
const int PIN_SDA = 21;
const int PIN_SCL = 22;

// ===== SENSOR ADICIONAL OPCIONAL: UMIDADE DO SOLO (saída analógica AO) =====
// Desligado por padrão: o robô funciona normalmente sem ele. Para usar, ligue
// VCC no 3V3, GND no GND e AO no GPIO35 (ADC1, somente entrada) e mude para true.
// Calibre: valor ADC com o sensor no ar (seco) e dentro de água/solo encharcado.
const bool USAR_SENSOR_UMIDADE = false;
const int PIN_UMIDADE = 35;
const int UMIDADE_ADC_SECO = 3200;
const int UMIDADE_ADC_MOLHADO = 1300;
const float UMID_ATENCAO = 70.0f;  // % -> nível 1 (igual à API)
const float UMID_ALERTA = 85.0f;   // % -> nível 2 (igual à API)

// ===== LIMIARES DE DEMONSTRAÇÃO (VALIDAR PARA USO REAL) =====
const float INCL_ATENCAO = 3.0f;
const float INCL_ALERTA = 6.0f;
const float INCL_MAXIMO = 10.0f;
const float VIB_ATENCAO = 0.04f;
const float VIB_ALERTA = 0.15f;

// Amostragem do MPU: 50 Hz, consolidação a cada 1 segundo.
const uint32_t INTERVALO_AMOSTRA_MS = 20;
const uint32_t INTERVALO_PUBLICACAO_MS = 1000; // 1 Hz: dashboard acompanha o robô quase em tempo real
const uint32_t TEMPO_HISTERESE_MS = 8000;
const float GRAVIDADE = 9.80665f;
const int AMOSTRAS_CALIBRACAO = 100;
const int AMOSTRAS_JANELA = 50;

Adafruit_MPU6050 mpu;
WiFiClient clienteWifi;
PubSubClient mqtt(clienteWifi);
Servo servo1;
Servo servo2;

char topicoLeitura[96];
char topicoStatus[96];
char topicoIA[96];   // a API devolve aqui o pré-alerta calculado pela IA
char clientId[48];

bool mpuOk = false;
bool baseValida = false;
bool servosAnexados = false;
double baseX = 0, baseY = 0, baseZ = 1;

// Acumuladores da janela de 1 segundo.
double somaX = 0, somaY = 0, somaZ = 0;
double somaX2 = 0, somaY2 = 0, somaZ2 = 0;
int amostrasJanela = 0;

float inclinacaoGraus = 0.0f;
float vibracaoG = 0.0f;
float umidadePct = -1.0f;            // -1 = sensor desativado/sem leitura
uint32_t ultimaLeituraUmidadeMs = 0;
bool iaPreAlerta = false;            // recebido da API por MQTT (IA de tendência)
uint32_t iaUltimaMsgMs = 0;
uint8_t nivelAtual = 1; // estado inicial seguro: monitoramento até validar o MPU
uint8_t modoSimulacao = 0; // 0 = real; 1..4 = força nível 0..3
bool buzzerAtivo = true;
const bool USAR_BOTAO_SIMULACAO = false; // mude para true somente se instalar o resistor externo no GPIO34

uint32_t ultimaAmostraMs = 0;
uint32_t ultimaTentativaMPUMs = 0;
uint32_t ultimaPublicacaoMs = 0;
uint32_t ultimaTentativaWifi = 0;
uint32_t ultimaTentativaMqtt = 0;
uint32_t inicioCandidatoNivel = 0;
uint8_t nivelCandidato = 1;
int ultimoNivelAtuadores = -1;

// ---------------------------------------------------------------------------
// MPU6050
// ---------------------------------------------------------------------------
bool iniciarMPU(uint8_t tentativas) {
  for (uint8_t i = 0; i < tentativas; i++) {
    if (mpu.begin(0x68, &Wire) || mpu.begin(0x69, &Wire)) {
      mpu.setAccelerometerRange(MPU6050_RANGE_4_G);
      mpu.setGyroRange(MPU6050_RANGE_250_DEG);
      mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
      delay(100);
      return true;
    }
    delay(300);
  }
  return false;
}

bool calibrarReferencia() {
  Serial.println("[MPU] Calibrando por 2 segundos. NAO MOVA O ROBO.");
  double sx = 0, sy = 0, sz = 0;
  int validas = 0;
  for (int i = 0; i < AMOSTRAS_CALIBRACAO; i++) {
    sensors_event_t a, g, t;
    if (mpu.getEvent(&a, &g, &t)) {
      sx += a.acceleration.x;
      sy += a.acceleration.y;
      sz += a.acceleration.z;
      validas++;
    }
    delay(20);
  }
  if (validas < AMOSTRAS_CALIBRACAO * 0.8) {
    Serial.println("[ERRO] Nao foi possivel calibrar o MPU6050.");
    baseValida = false;
    return false;
  }
  baseX = sx / validas;
  baseY = sy / validas;
  baseZ = sz / validas;
  double norma = sqrt(baseX * baseX + baseY * baseY + baseZ * baseZ);
  if (norma < 7.0 || norma > 12.5) {
    Serial.println("[ERRO] Referencia do MPU fora da faixa esperada.");
    baseValida = false;
    return false;
  }
  baseValida = true;
  Serial.printf("[MPU] Referencia calibrada: X=%.2f Y=%.2f Z=%.2f m/s2\n", baseX, baseY, baseZ);
  return true;
}

void zerarJanela() {
  somaX = somaY = somaZ = 0;
  somaX2 = somaY2 = somaZ2 = 0;
  amostrasJanela = 0;
}

void acumularAmostraMPU() {
  sensors_event_t a, g, t;
  if (!mpu.getEvent(&a, &g, &t)) {
    mpuOk = false;
    Serial.println("[ERRO] Falha ao ler o MPU6050.");
    return;
  }
  const double x = a.acceleration.x;
  const double y = a.acceleration.y;
  const double z = a.acceleration.z;
  somaX += x; somaY += y; somaZ += z;
  somaX2 += x * x; somaY2 += y * y; somaZ2 += z * z;
  amostrasJanela++;

  if (amostrasJanela >= AMOSTRAS_JANELA) {
    const double mx = somaX / amostrasJanela;
    const double my = somaY / amostrasJanela;
    const double mz = somaZ / amostrasJanela;
    const double normaM = sqrt(mx * mx + my * my + mz * mz);
    const double normaB = sqrt(baseX * baseX + baseY * baseY + baseZ * baseZ);

    if (baseValida && normaM > 0.1 && normaB > 0.1) {
      double cosseno = (mx * baseX + my * baseY + mz * baseZ) / (normaM * normaB);
      cosseno = constrain(cosseno, -1.0, 1.0);
      inclinacaoGraus = acos(cosseno) * 180.0 / PI;
    }

    // RMS do componente AC (desvio padrão dos três eixos), em unidades de g.
    // Remove a componente média da gravidade e estima a vibração da janela.
    double vx = (somaX2 / amostrasJanela) - (mx * mx);
    double vy = (somaY2 / amostrasJanela) - (my * my);
    double vz = (somaZ2 / amostrasJanela) - (mz * mz);
    if (vx < 0) vx = 0; if (vy < 0) vy = 0; if (vz < 0) vz = 0;
    vibracaoG = sqrt(vx + vy + vz) / GRAVIDADE;

    zerarJanela();
    Serial.printf("[LEITURA] inclinacao=%.2f graus | vibracao=%.3f g | nivel=%u | MPU=%s\n",
                  inclinacaoGraus, vibracaoG, nivelAtual, mpuOk ? "OK" : "FALHA");
  }
}

// ---------------------------------------------------------------------------
// CLASSIFICACAO E ATUADORES
// ---------------------------------------------------------------------------
uint8_t calcularNivel() {
  if (!mpuOk || !baseValida) return 1; // falha segura: nunca indicar verde
  uint8_t nivelIncl = 0;
  if (inclinacaoGraus >= INCL_MAXIMO) nivelIncl = 3;
  else if (inclinacaoGraus >= INCL_ALERTA) nivelIncl = 2;
  else if (inclinacaoGraus >= INCL_ATENCAO) nivelIncl = 1;

  uint8_t nivelVib = 0;
  if (vibracaoG >= VIB_ALERTA) nivelVib = 2;
  else if (vibracaoG >= VIB_ATENCAO) nivelVib = 1;
  uint8_t nivelUmid = 0;
  if (USAR_SENSOR_UMIDADE && umidadePct >= 0.0f) {
    if (umidadePct >= UMID_ALERTA) nivelUmid = 2;
    else if (umidadePct >= UMID_ATENCAO) nivelUmid = 1;
  }
  uint8_t nivelFinal = max(nivelIncl, nivelVib);
  if (nivelUmid > nivelFinal) nivelFinal = nivelUmid;
  return nivelFinal;
}

// Umidade do solo (sensor adicional opcional): média de 16 leituras do ADC.
void lerUmidadeSolo() {
  if (!USAR_SENSOR_UMIDADE) return;
  long soma = 0;
  for (int i = 0; i < 16; i++) soma += analogRead(PIN_UMIDADE);
  float adc = soma / 16.0f;
  float pct = (UMIDADE_ADC_SECO - adc) * 100.0f / (float)(UMIDADE_ADC_SECO - UMIDADE_ADC_MOLHADO);
  if (pct < 0.0f) pct = 0.0f;
  if (pct > 100.0f) pct = 100.0f;
  umidadePct = pct;
}

// IA -> robô: a API publica em encosta/<SETOR_ID>/ia o pré-alerta calculado pela
// regressão linear. Só muda o aviso (LED amarelo piscando + bipe); o nível de risco
// continua vindo das regras locais, e sem mensagens por 10 s o robô ignora a IA.
void aoReceberMqtt(char* topico, byte* payload, unsigned int tamanho) {
  if (strcmp(topico, topicoIA) != 0) return;
  char msg[200];
  unsigned int n = tamanho < sizeof(msg) - 1 ? tamanho : sizeof(msg) - 1;
  memcpy(msg, payload, n);
  msg[n] = 0;
  bool novo = strstr(msg, "\"pre_alerta\":true") != NULL;
  if (novo != iaPreAlerta) {
    Serial.printf("[IA] Pre-alerta da IA: %s\n", novo ? "ATIVO (tendencia de alta)" : "desativado");
  }
  iaPreAlerta = novo;
  iaUltimaMsgMs = millis();
}

bool preAlertaIAAtivo(uint32_t agora) {
  return iaPreAlerta && (agora - iaUltimaMsgMs) < 10000;
}

void atualizarNivelComHisterese(uint32_t agora) {
  uint8_t desejado = calcularNivel();
  if (modoSimulacao > 0) desejado = modoSimulacao - 1;

  if (desejado > nivelAtual) {
    nivelAtual = desejado; // aumenta imediatamente
    nivelCandidato = desejado;
    inicioCandidatoNivel = agora;
  } else if (desejado < nivelAtual) {
    if (desejado != nivelCandidato) {
      nivelCandidato = desejado;
      inicioCandidatoNivel = agora;
    } else if (agora - inicioCandidatoNivel >= TEMPO_HISTERESE_MS) {
      nivelAtual = desejado; // reduz somente apos 8 segundos estaveis
    }
  } else {
    nivelCandidato = desejado;
    inicioCandidatoNivel = agora;
  }
}

void atualizarAtuadores(uint32_t agora) {
  bool verde = false, amarelo = false, vermelho = false, som = false;
  const bool preIA = preAlertaIAAtivo(agora) && nivelAtual < 2;
  switch (nivelAtual) {
    case 0:
      if (preIA) {            // IA prevê subida rápida: amarelo piscando + bipe curto
        amarelo = ((agora / 250) % 2) == 0;
        som = (agora % 1000) < 80;
      } else {
        verde = true;
      }
      break;
    case 1:
      if (preIA) {
        amarelo = ((agora / 250) % 2) == 0;
        som = (agora % 1000) < 80;
      } else {
        amarelo = true;
        som = (agora % 2000) < 180;
      }
      break;
    case 2:
      vermelho = ((agora / 500) % 2) == 0;
      som = (agora % 2000) < 120;
      break;
    default:
      vermelho = ((agora / 150) % 2) == 0;
      som = ((agora / 200) % 2) == 0;
      break;
  }
  digitalWrite(PIN_LED_VERDE, verde ? HIGH : LOW);
  digitalWrite(PIN_LED_AMARELO, amarelo ? HIGH : LOW);
  digitalWrite(PIN_LED_VERMELHO, vermelho ? HIGH : LOW);
  digitalWrite(PIN_BUZZER, (som && buzzerAtivo) ? HIGH : LOW);

  if (servosAnexados && ultimoNivelAtuadores != nivelAtual) {
    int posicao = (nivelAtual >= 2) ? 90 : 0;
    servo1.write(posicao);
    servo2.write(posicao);
    ultimoNivelAtuadores = nivelAtual;
  }
}

void autoTesteLEDs() {
  Serial.println("[BOOT] Testando LEDs e buzzer...");
  digitalWrite(PIN_LED_VERDE, HIGH); digitalWrite(PIN_BUZZER, HIGH); delay(180);
  digitalWrite(PIN_LED_VERDE, LOW); digitalWrite(PIN_BUZZER, LOW);
  digitalWrite(PIN_LED_AMARELO, HIGH); digitalWrite(PIN_BUZZER, HIGH); delay(180);
  digitalWrite(PIN_LED_AMARELO, LOW); digitalWrite(PIN_BUZZER, LOW);
  digitalWrite(PIN_LED_VERMELHO, HIGH); digitalWrite(PIN_BUZZER, HIGH); delay(180);
  digitalWrite(PIN_LED_VERMELHO, LOW); digitalWrite(PIN_BUZZER, LOW);
}

// ---------------------------------------------------------------------------
// WI-FI + MQTT
// ---------------------------------------------------------------------------
void gerenciarRede(uint32_t agora) {
  if (WiFi.status() != WL_CONNECTED && agora - ultimaTentativaWifi >= 10000) {
    ultimaTentativaWifi = agora;
    Serial.println("[WIFI] Tentando conectar...");
    WiFi.begin(WIFI_SSID, WIFI_SENHA);
  }

  if (WiFi.status() == WL_CONNECTED && !mqtt.connected() && agora - ultimaTentativaMqtt >= 5000) {
    ultimaTentativaMqtt = agora;
    Serial.printf("[MQTT] Conectando em %s:%u...\n", MQTT_HOST, MQTT_PORTA);
    if (mqtt.connect(clientId, topicoStatus, 0, true, "offline")) {
      mqtt.publish(topicoStatus, "online", true);
      mqtt.subscribe(topicoIA);
      Serial.printf("[MQTT] Conectado. Publicando em %s\n", topicoLeitura);
    } else {
      Serial.printf("[MQTT] Falha na conexao. Estado=%d\n", mqtt.state());
    }
  }
  digitalWrite(PIN_LED_REDE, mqtt.connected() ? HIGH : ((agora / 500) % 2));
}

void publicarLeitura() {
  if (!mqtt.connected()) return;
  char json[384];
  char extra[48] = "";
  if (USAR_SENSOR_UMIDADE && umidadePct >= 0.0f) snprintf(extra, sizeof(extra), ",\"umidade_solo_pct\":%.1f", umidadePct);
  const int rssi = (WiFi.status() == WL_CONNECTED) ? WiFi.RSSI() : 0;
  snprintf(json, sizeof(json),
    "{\"setor_id\":\"%s\",\"sensor_id\":\"%s\",\"inclinacao_graus\":%.2f,\"vibracao_g\":%.4f,\"nivel\":%u,\"simulado\":%s,\"mpu_ok\":%s,\"rssi\":%d%s}",
    SETOR_ID, SENSOR_ID, inclinacaoGraus, vibracaoG, nivelAtual,
    modoSimulacao > 0 ? "true" : "false", (mpuOk && baseValida) ? "true" : "false", rssi, extra);
  bool ok = mqtt.publish(topicoLeitura, json, false);
  Serial.printf("[MQTT] Publicacao %s: %s\n", ok ? "OK" : "FALHOU", json);
}

// ---------------------------------------------------------------------------
// SETUP / LOOP
// ---------------------------------------------------------------------------
void setup() {
  Serial.begin(115200);
  delay(300);

  pinMode(PIN_LED_VERDE, OUTPUT);
  pinMode(PIN_LED_AMARELO, OUTPUT);
  pinMode(PIN_LED_VERMELHO, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_LED_REDE, OUTPUT);
  pinMode(PIN_BOTAO, INPUT); // GPIO34 precisa de pull-up externo
  digitalWrite(PIN_LED_VERDE, LOW);
  digitalWrite(PIN_LED_AMARELO, HIGH); // atencao ate validar o sensor
  digitalWrite(PIN_LED_VERMELHO, LOW);

  snprintf(topicoLeitura, sizeof(topicoLeitura), "encosta/%s/leitura", SETOR_ID);
  snprintf(topicoStatus, sizeof(topicoStatus), "encosta/%s/status", SETOR_ID);
  snprintf(topicoIA, sizeof(topicoIA), "encosta/%s/ia", SETOR_ID);
  snprintf(clientId, sizeof(clientId), "robo-sentinela-%06X", (uint32_t)(ESP.getEfuseMac() & 0xFFFFFF));

  Wire.begin(PIN_SDA, PIN_SCL);
  mpuOk = iniciarMPU(5);
  if (mpuOk) {
    Serial.println("[MPU] Sensor encontrado.");
    baseValida = calibrarReferencia();
  } else {
    Serial.println("[ERRO] MPU6050 nao encontrado. LEDs permanecem em atencao.");
  }

  autoTesteLEDs();

  // Os servos sao conectados depois da calibracao para nao contaminar a referencia.
  servo1.setPeriodHertz(50);
  servo2.setPeriodHertz(50);
  servo1.attach(PIN_SERVO1, 500, 2400);
  servo2.attach(PIN_SERVO2, 500, 2400);
  servo1.write(0);
  servo2.write(0);
  servosAnexados = true;

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_SENHA);
  ultimaTentativaWifi = millis();
  mqtt.setServer(MQTT_HOST, MQTT_PORTA);
  mqtt.setKeepAlive(30);
  mqtt.setSocketTimeout(5);
  mqtt.setBufferSize(512);
  mqtt.setCallback(aoReceberMqtt);

  nivelAtual = (mpuOk && baseValida) ? 0 : 1;
  nivelCandidato = nivelAtual;
  inicioCandidatoNivel = millis();
  Serial.printf("[BOOT] Pronto. Topico: %s | Status: %s\n", topicoLeitura, topicoStatus);
}

void loop() {
  const uint32_t agora = millis();

  gerenciarRede(agora);
  if (mqtt.connected()) mqtt.loop();

  if (!mpuOk && agora - ultimaTentativaMPUMs >= 5000) {
    ultimaTentativaMPUMs = agora;
    Serial.println("[MPU] Tentando reconectar...");
    mpuOk = iniciarMPU(1);
    if (mpuOk && baseValida) Serial.println("[MPU] Reconectado; mantendo a referencia original.");
  }

  if (mpuOk && agora - ultimaAmostraMs >= INTERVALO_AMOSTRA_MS) {
    ultimaAmostraMs = agora;
    acumularAmostraMPU();
  }

  // Se o MPU falhar, nao recalibra automaticamente: evita aceitar uma nova
  // inclinacao como se fosse a posicao original. O operador deve reiniciar
  // o robo com ele nivelado depois de corrigir a falha.
  if (!mpuOk) {
    nivelAtual = 1;
  } else {
    atualizarNivelComHisterese(agora);
  }

  // Botao: um clique percorre modo real -> simula nivel 0 -> 1 -> 2 -> 3 -> real.
  static int leituraAnterior = HIGH;
  static uint32_t ultimaMudancaBotao = 0;
  int leituraBotao = USAR_BOTAO_SIMULACAO ? digitalRead(PIN_BOTAO) : HIGH;
  if (USAR_BOTAO_SIMULACAO && leituraAnterior == HIGH && leituraBotao == LOW && agora - ultimaMudancaBotao > 250) {
    ultimaMudancaBotao = agora;
    modoSimulacao = (modoSimulacao + 1) % 5;
    Serial.printf("[BOTAO] Simulacao=%u (0=real; 1..4= niveis 0..3)\n", modoSimulacao);
    if (modoSimulacao > 0) nivelAtual = modoSimulacao - 1;
    else { nivelAtual = calcularNivel(); nivelCandidato = nivelAtual; inicioCandidatoNivel = agora; }
  }
  leituraAnterior = leituraBotao;

  if (USAR_SENSOR_UMIDADE && agora - ultimaLeituraUmidadeMs >= 1000) {
    ultimaLeituraUmidadeMs = agora;
    lerUmidadeSolo();
  }

  atualizarAtuadores(agora);

  // Publica a cada 1 s e imediatamente quando o nível muda (LED e painel ficam sincronizados).
  static uint8_t nivelPublicado = 255;
  if (agora - ultimaPublicacaoMs >= INTERVALO_PUBLICACAO_MS || (nivelAtual != nivelPublicado && agora - ultimaPublicacaoMs >= 150)) {
    ultimaPublicacaoMs = agora;
    nivelPublicado = nivelAtual;
    publicarLeitura();
  }
  delay(1);
}
