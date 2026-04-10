#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// =========================
// Hardware
// =========================
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define OLED_ADDR 0x3C

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

const int POT_PIN = A0;
const int BUTTON_PIN = D2;

// =========================
// Serial / Pi 5 protocol
// =========================
const unsigned long DEFAULT_TIMEOUT_MS = 30000;

// =========================
// Menu system
// =========================
enum MenuState {
  MENU_MAIN,
  MENU_GAMES,
  SCREEN_WAIT
};

MenuState currentMenu = MENU_MAIN;

struct MenuItem {
  const char* name;
  void (*run)();
};

void actionTakePicture();
void actionMakeGcode();
void actionStartCut();
void actionStopCut();
void actionSendGcodeUsb();
void openGamesMenu();
void backToMainMenu();

void gameFangBall();
void gameTreff();

MenuItem mainMenu[] = {
  {"BILDE", actionTakePicture},
  {"LAGE KODE", actionMakeGcode},
  {"START KUTT", actionStartCut},
  {"SEND TIL USB", actionSendGcodeUsb},
  {"STOPP", actionStopCut},
  {"GAMES >", openGamesMenu}
};

MenuItem gamesMenu[] = {
  {"FANG BALL", gameFangBall},
  {"TREFF", gameTreff},
  {"< TILBAKE", backToMainMenu}
};

const int mainMenuCount = sizeof(mainMenu) / sizeof(mainMenu[0]);
const int gamesMenuCount = sizeof(gamesMenu) / sizeof(gamesMenu[0]);

int lastButtonState = HIGH;

// =========================
// Helpers
// =========================
String wrapLine1 = "";
String wrapLine2 = "";
String wrapLine3 = "";

void splitText(const String& text, int maxChars = 16) {
  wrapLine1 = "";
  wrapLine2 = "";
  wrapLine3 = "";

  String remaining = text;
  String* lines[3] = {&wrapLine1, &wrapLine2, &wrapLine3};

  for (int i = 0; i < 3; i++) {
    if (remaining.length() <= maxChars) {
      *lines[i] = remaining;
      remaining = "";
      break;
    }

    int splitPos = maxChars;
    if (splitPos >= remaining.length()) splitPos = remaining.length() - 1;

    while (splitPos > 0 && remaining[splitPos] != ' ') {
      splitPos--;
    }

    if (splitPos == 0) {
      splitPos = maxChars;
      if (splitPos > remaining.length()) splitPos = remaining.length();
    }

    *lines[i] = remaining.substring(0, splitPos);
    remaining = remaining.substring(splitPos);
    remaining.trim();
  }
}

void drawScrollbar(int topIndex, int totalItems, int visibleCount) {
  int x = 122;
  int y = 0;
  int w = 6;
  int h = 64;

  display.drawRect(x, y, w, h, SSD1306_WHITE);

  int trackH = h - 2;

  if (totalItems <= visibleCount) {
    display.fillRect(x + 1, y + 1, 4, trackH, SSD1306_WHITE);
    return;
  }

  int thumbH = (trackH * visibleCount) / totalItems;
  if (thumbH < 8) thumbH = 8;

  int maxTopIndex = totalItems - visibleCount;
  int maxThumbMove = trackH - thumbH;
  int thumbY = y + 1 + (topIndex * maxThumbMove) / maxTopIndex;

  display.fillRect(x + 1, thumbY, 4, thumbH, SSD1306_WHITE);
}

String cropText(String text, int maxChars) {
  if ((int)text.length() <= maxChars) return text;
  if (maxChars <= 1) return text.substring(0, maxChars);
  return text.substring(0, maxChars - 1) + ">";
}

void drawMenu(MenuItem* menu, int menuCount, int selectedIndex) {
  display.clearDisplay();

  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.print("MENY");
  display.drawLine(0, 10, 120, 10, SSD1306_WHITE);

  const int visibleCount = 4;
  int topIndex = selectedIndex - (visibleCount / 2);
  if (topIndex < 0) topIndex = 0;
  int maxTopIndex = menuCount - visibleCount;
  if (maxTopIndex < 0) maxTopIndex = 0;
  if (topIndex > maxTopIndex) topIndex = maxTopIndex;

  int startY = 14;
  int lineHeight = 12;

  for (int row = 0; row < visibleCount; row++) {
    int itemIndex = topIndex + row;
    if (itemIndex >= menuCount) break;

    int y = startY + row * lineHeight;
    String text = cropText(String(menu[itemIndex].name), 14);

    if (itemIndex == selectedIndex) {
      display.fillRect(0, y - 1, 118, 10, SSD1306_WHITE);
      display.setTextColor(SSD1306_BLACK);
      display.setCursor(2, y);
      display.print(">");
      display.print(cropText(text, 13));
      display.setTextColor(SSD1306_WHITE);
    } else {
      display.setCursor(6, y);
      display.print(text);
    }
  }

  drawScrollbar(topIndex, menuCount, visibleCount);
  display.display();
}

void showMessage(const String& title, const String& msg1 = "", const String& msg2 = "") {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);

  display.setCursor(0, 0);
  display.print(cropText(title, 16));

  if (msg1.length() > 0) {
    display.setCursor(0, 18);
    display.print(cropText(msg1, 16));
  }

  if (msg2.length() > 0) {
    display.setCursor(0, 30);
    display.print(cropText(msg2, 16));
  }

  display.display();
}

void showWrappedStatus(const String& title, const String& status) {
  splitText(status, 16);

  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);

  display.setCursor(0, 0);
  display.print(cropText(title, 16));

  if (wrapLine1.length()) {
    display.setCursor(0, 18);
    display.print(wrapLine1);
  }
  if (wrapLine2.length()) {
    display.setCursor(0, 30);
    display.print(wrapLine2);
  }
  if (wrapLine3.length()) {
    display.setCursor(0, 42);
    display.print(wrapLine3);
  }

  display.display();
}

// =========================
// Pakning-animasjon
// =========================
void drawGasketAnimationFrame(const String& title, int step, const String& status) {
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);

  // Overskrift
  display.setCursor(0, 0);
  display.print(cropText(title, 16));
  display.drawLine(0, 10, 127, 10, SSD1306_WHITE);

  // Midtpunkt for pakning
  const int cx = 64;
  const int cy = 30;

  // Ytre ring
  display.drawCircle(cx, cy, 18, SSD1306_WHITE);

  // Innerhol
  display.drawCircle(cx, cy, 8, SSD1306_WHITE);

  // Fem små hol
  int hx[5] = {cx, cx + 13, cx + 8, cx - 8, cx - 13};
  int hy[5] = {cy - 13, cy - 4, cy + 11, cy + 11, cy - 4};

  for (int i = 0; i < 5; i++) {
    display.drawCircle(hx[i], hy[i], 2, SSD1306_WHITE);
  }

  // "Arbeidsprikk" som går rundt ytterkanten
  switch (step % 8) {
    case 0: display.fillCircle(cx,      cy - 18, 2, SSD1306_WHITE); break;
    case 1: display.fillCircle(cx + 13, cy - 13, 2, SSD1306_WHITE); break;
    case 2: display.fillCircle(cx + 18, cy,      2, SSD1306_WHITE); break;
    case 3: display.fillCircle(cx + 13, cy + 13, 2, SSD1306_WHITE); break;
    case 4: display.fillCircle(cx,      cy + 18, 2, SSD1306_WHITE); break;
    case 5: display.fillCircle(cx - 13, cy + 13, 2, SSD1306_WHITE); break;
    case 6: display.fillCircle(cx - 18, cy,      2, SSD1306_WHITE); break;
    case 7: display.fillCircle(cx - 13, cy - 13, 2, SSD1306_WHITE); break;
  }

  // Lat som pakninga blir "bygd opp"
  int stage = step % 6;
  if (stage >= 1) {
    display.drawLine(cx - 5, cy - 1, cx + 5, cy - 1, SSD1306_WHITE);
  }
  if (stage >= 2) {
    display.drawLine(cx - 5, cy + 1, cx + 5, cy + 1, SSD1306_WHITE);
  }
  if (stage >= 3) {
    display.fillCircle(hx[0], hy[0], 1, SSD1306_WHITE);
  }
  if (stage >= 4) {
    display.fillCircle(hx[1], hy[1], 1, SSD1306_WHITE);
    display.fillCircle(hx[4], hy[4], 1, SSD1306_WHITE);
  }
  if (stage >= 5) {
    display.fillCircle(hx[2], hy[2], 1, SSD1306_WHITE);
    display.fillCircle(hx[3], hy[3], 1, SSD1306_WHITE);
  }

  // Status nederst
  String txt = cropText(status, 20);
  display.setCursor(0, 54);
  display.print(txt);

  display.display();
}

int getSelectedIndex(int menuCount) {
  int raw = analogRead(POT_PIN);

  // Arduino on STM32 is often 12-bit ADC (0-4095)
  int maxAdc = 4095;
  int index = (raw * menuCount) / (maxAdc + 1);
  if (index >= menuCount) index = menuCount - 1;
  if (index < 0) index = 0;
  return index;
}

void waitForButtonRelease() {
  while (digitalRead(BUTTON_PIN) == LOW) {
    delay(10);
  }
}

bool buttonPressedNow() {
  int currentState = digitalRead(BUTTON_PIN);
  bool pressed = (lastButtonState == HIGH && currentState == LOW);
  lastButtonState = currentState;
  return pressed;
}

// =========================
// Serial comm helpers
// =========================
void flushSerialInput() {
  while (Serial.available()) {
    Serial.read();
  }
}

void sendCommandToPi5(const String& command) {
  Serial.print("CMD:");
  Serial.println(command);
}

String readLineFromPi5(unsigned long timeoutMs) {
  unsigned long start = millis();
  String line = "";

  while (millis() - start < timeoutMs) {
    while (Serial.available()) {
      char c = (char)Serial.read();

      if (c == '\r') continue;

      if (c == '\n') {
        line.trim();
        if (line.length() > 0) return line;
        line = "";
      } else {
        line += c;
      }
    }
    delay(5);
  }

  return "";
}

bool runPi5Job(const String& command, const String& title, unsigned long timeoutMs) {
  flushSerialInput();
  sendCommandToPi5(command);

  unsigned long start = millis();
  unsigned long lastAnim = millis();
  int animStep = 0;
  String currentStatus = "ARBEIDAR";

  while (millis() - start < timeoutMs) {
    String line = readLineFromPi5(50);

    if (line.length() > 0) {
      if (line.startsWith("STATUS:")) {
        currentStatus = line.substring(7);
        drawGasketAnimationFrame(title, animStep, currentStatus);

      } else if (line == ("DONE:" + command)) {
        drawGasketAnimationFrame(title, animStep, "FERDIG");
        delay(700);
        return true;

      } else if (line.startsWith("ERROR:" + command + ":")) {
        String prefix = "ERROR:" + command + ":";
        String msg = line.substring(prefix.length());
        drawGasketAnimationFrame(title, animStep, "FEIL");
        showWrappedStatus("FEIL", msg);
        delay(2000);
        return false;
      }
    }

    if (millis() - lastAnim > 180) {
      animStep++;
      drawGasketAnimationFrame(title, animStep, currentStatus);
      lastAnim = millis();
    }
  }

  drawGasketAnimationFrame(title, animStep, "TIMEOUT");
  delay(1500);
  return false;
}

// =========================
// Pi 5 actions
// =========================
void actionTakePicture() {
  runPi5Job("TAKE_PICTURE", "BILDE", 30000);
}

void actionMakeGcode() {
  runPi5Job("MAKE_GCODE", "G-KODE", 60000);
}

void actionStartCut() {
  runPi5Job("START_CUT", "KUTT", 30000);
}

void actionSendGcodeUsb() {
  runPi5Job("SEND_GCODE_USB", "SEND TIL USB", 30000);
}

void actionStopCut() {
  runPi5Job("STOP_CUT", "STOPP", 10000);
}

void openGamesMenu() {
  currentMenu = MENU_GAMES;
}

void backToMainMenu() {
  currentMenu = MENU_MAIN;
}

// =========================
// Games
// =========================
long rngState = 12345;

int randRangeCustom(int maxValue) {
  rngState = (1103515245L * rngState + 12345L) & 0x7fffffff;
  if (maxValue <= 0) return 0;
  return rngState % maxValue;
}

void gameFangBall() {
  waitForButtonRelease();

  const int playerW = 20;
  const int playerH = 4;
  const int playerY = 58;
  const int ballSize = 4;

  int ballX = randRangeCustom(128 - ballSize);
  int ballY = 0;
  int score = 0;
  int lives = 3;
  int ballSpeed = 2;
  int frameDelay = 30;

  unsigned long lastMove = millis();

  while (true) {
    int raw = analogRead(POT_PIN);
    int playerX = map(raw, 0, 4095, 0, 128 - playerW);

    if (millis() - lastMove >= (unsigned long)frameDelay) {
      ballY += ballSpeed;
      lastMove = millis();
    }

    if (ballY + ballSize >= playerY) {
      if ((ballX + ballSize >= playerX) && (ballX <= playerX + playerW)) {
        score++;
        if (score % 3 == 0 && ballSpeed < 6) ballSpeed++;
        ballX = randRangeCustom(128 - ballSize);
        ballY = 0;
      } else {
        lives--;
        ballX = randRangeCustom(128 - ballSize);
        ballY = 0;
        if (lives <= 0) break;
      }
    }

    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);

    display.setCursor(18, 0);
    display.print("FANG BALL");

    display.setCursor(0, 12);
    display.print("S:");
    display.print(score);

    display.setCursor(88, 12);
    display.print("L:");
    display.print(lives);

    display.drawLine(0, 20, 127, 20, SSD1306_WHITE);
    display.fillRect(ballX, ballY, ballSize, ballSize, SSD1306_WHITE);
    display.fillRect(playerX, playerY, playerW, playerH, SSD1306_WHITE);
    display.display();

    delay(frameDelay);
  }

  showMessage("GAME OVER", "TRYKK KNAPP");
  waitForButtonRelease();
  while (digitalRead(BUTTON_PIN) == HIGH) delay(10);
  waitForButtonRelease();
}

void gameTreff() {
  waitForButtonRelease();

  int roundNo = 1;
  const int roundsTotal = 10;
  int score = 0;
  const int targetW = 18;

  while (roundNo <= roundsTotal) {
    int targetX = randRangeCustom(128 - targetW);

    while (true) {
      int raw = analogRead(POT_PIN);
      int cursorX = map(raw, 0, 4095, 0, 127);

      display.clearDisplay();
      display.setTextSize(1);
      display.setTextColor(SSD1306_WHITE);

      display.setCursor(40, 0);
      display.print("TREFF");

      display.setCursor(0, 12);
      display.print(roundNo);
      display.print("/");
      display.print(roundsTotal);

      display.setCursor(88, 12);
      display.print("S:");
      display.print(score);

      display.drawLine(0, 20, 127, 20, SSD1306_WHITE);
      display.fillRect(targetX, 28, targetW, 6, SSD1306_WHITE);

      for (int y = 42; y < 60; y++) {
        display.drawPixel(cursorX, y, SSD1306_WHITE);
      }

      display.display();

      if (digitalRead(BUTTON_PIN) == LOW) {
        waitForButtonRelease();

        if (cursorX >= targetX && cursorX <= targetX + targetW) {
          score++;
          showMessage("TREFF!");
          delay(500);
        } else {
          showMessage("BOM!");
          delay(500);
        }

        roundNo++;
        break;
      }

      delay(20);
    }
  }

  showMessage("FERDIG", "SCORE: " + String(score), "TRYKK KNAPP");
  while (digitalRead(BUTTON_PIN) == HIGH) delay(10);
  waitForButtonRelease();
}

// =========================
// Arduino setup / loop
// =========================
void setup() {
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  analogReadResolution(12);

  Serial.begin(115200);
  Wire.begin();

  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    while (true) {
      // stop if OLED init fails
    }
  }

  display.clearDisplay();
  display.display();
  showMessage("STM NUCLEO", "STARTAR...");
  delay(800);
}

void loop() {
  MenuItem* activeMenu;
  int activeCount;

  if (currentMenu == MENU_MAIN) {
    activeMenu = mainMenu;
    activeCount = mainMenuCount;
  } else {
    activeMenu = gamesMenu;
    activeCount = gamesMenuCount;
  }

  int selectedIndex = getSelectedIndex(activeCount);
  drawMenu(activeMenu, activeCount, selectedIndex);

  if (buttonPressedNow()) {
    activeMenu[selectedIndex].run();
    waitForButtonRelease();
  }

  delay(40);
}