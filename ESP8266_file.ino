#include <ESP8266WiFi.h>

WiFiClient client;
WiFiServer server(80);

const char* ssid = "node_mcu";

void setup() {
  WiFi.softAP(ssid);
  Serial.begin(9600);

  Serial.println();
  Serial.print("Access Point \"");
  Serial.print(ssid);
  Serial.print("\" IP Address: ");
  Serial.println(WiFi.softAPIP());
  server.begin();

  pinMode(D3, OUTPUT);  // GPIO0
  pinMode(D4, OUTPUT);  // GPIO2
  pinMode(D5, OUTPUT);  // GPIO14
  pinMode(D6, OUTPUT);  // GPIO12
}

void loop() {
  client = server.available();
  if (client) {
    String request = client.readStringUntil('\r');
    Serial.println(request);
    request.toLowerCase();

    // FORWARD
    if (request.indexOf("get /forward") >= 0) {
      digitalWrite(D3, HIGH);
      digitalWrite(D4, LOW);
      digitalWrite(D5, HIGH);
      digitalWrite(D6, LOW);
    }
    // BACKWARD
    else if (request.indexOf("get /backward") >= 0) {
      digitalWrite(D3, LOW);
      digitalWrite(D4, HIGH);
      digitalWrite(D5, LOW);
      digitalWrite(D6, HIGH);
    }
    // LEFT
    else if (request.indexOf("get /left") >= 0) {
      digitalWrite(D3, LOW);
      digitalWrite(D4, HIGH);
      digitalWrite(D5, HIGH);
      digitalWrite(D6, LOW);
    }
    // RIGHT
    else if (request.indexOf("get /right") >= 0) {
      digitalWrite(D3, HIGH);
      digitalWrite(D4, LOW);
      digitalWrite(D5, LOW);
      digitalWrite(D6, HIGH);
    }
    // STOP
    else if (request.indexOf("get /stop") >= 0) {
      digitalWrite(D3, LOW);
      digitalWrite(D4, LOW);
      digitalWrite(D5, LOW);
      digitalWrite(D6, LOW);
    }

    // Send HTTP response (but minimal, no HTML)
    client.println("HTTP/1.1 200 OK");
    client.println("Content-Type: text/plain");
    client.println("Connection: close");
    client.println();
    client.println("Command Received");

    delay(1);
    client.stop();
  }
}
