# Einmaliger Solltemperatur-Test

Stand: 14.09.2026. Ab Version **0.7.0** enthalten. Noch kein Live-Schreibversuch
an der Anlage; Installation und Neustart starten keinen Test. Version 0.6.0
enthält diese Aktionen nicht.

## Fragestellung

Reagiert die Steuerung auf einen einzelnen externen Solltemperatur-Befehl,
welcher Wert wird anschließend wieder auf dem Bus übertragen, und ändert sich
die Anzeige am BDE? Ein ACK oder erfolgreiches TCP-Senden beantwortet diese
drei Fragen nicht alleine. Grundlage ist die
[Analyse des BDE-Parallelbetriebs](BDE_PARALLELBETRIEB.md).

Das ist ein bewusst begrenzter Versuch mit angeschlossenem BDE, keine Freigabe
für eine dauerhafte Steuerung. Der Gateway kann auf RS485 mit dem vorhandenen
Sender kollidieren; die Integration kennt dessen Sendezeitpunkt nicht. Es gibt
keinen zweiten TCP-Client, keinen regelmäßigen Schreibauftrag und keinen Versuch,
das BDE durch häufigeres Senden zu überstimmen.

## Begrenzung

- Zwei getrennte HA-Aktionen, nur für einen angemeldeten Administrator.
  Vorbereitung sendet nichts und liefert einen kurz gültigen Freigabecode.
- Nur der beobachtete Solltemperatur-SET an DP `0x0227`, Float32 LE mit
  berechneter Prüfsumme. Keine frei wählbare Adresse, Rohbytes oder Gateway-IP.
- Nur Komfortbetrieb; Ist-Sollwert und Betriebsart müssen jünger als 10 Sekunden
  sein. Der am BDE abgelesene Sollwert muss exakt dem empfangenen Wert entsprechen.
- Änderung ausschließlich um −0,5 oder +0,5 °C; Ausgangs- und Testwert innerhalb
  der am lokalen BDE beobachteten 18–30 °C. Der halbe Grad ist die Begrenzung
  dieses Experiments, noch kein Nachweis der unterstützten BDE-Schrittweite.
- Mindestens 10 Sekunden Vorlauf; Freigabecode verfällt nach 60 Sekunden.
  Eine zwischenzeitlich beobachtete Änderung von Sollwert oder Betriebsart,
  veraltete Werte beim Senden, Verbindungswechsel oder gestoppte Testaufnahme
  verhindern das Senden.
- Ein einziger `write()`-Aufruf mit 14 Bytes je Laden der Integration.
  Der Versuch wird vor dem Aufruf verbraucht. Fehler, Abbruch und Timeout
  führen zu keiner Wiederholung. `drain()` wartet höchstens zwei Sekunden.
- Keine automatische Rückstellung. Eine benötigte Rückstellung erfolgt am BDE.
  Keine optimistische Änderung der HA-Sensorwerte.

## Installation und Durchführung

Zuerst in HACS **PROXON HESP → Aktualisieren / Erneut herunterladen → 0.7.0**
auswählen und Home Assistant neu starten. Die bestehenden Entitäten bleiben
erhalten. Die zwei Testaktionen erscheinen unter Entwicklerwerkzeuge → Aktionen.

1. Am BDE Komfortbetrieb und aktuelle Solltemperatur ablesen. Vor Ort bleiben
   und die Anzeige beobachten. Andere aktive Bus-Clients dürfen nicht zusätzlich
   senden. Den ursprünglichen Sollwert für die spätere Rückstellung notieren.
2. Als Administrator in **Entwicklerwerkzeuge → Aktionen** die Aktion
   `proxon_hesp.prepare_target_temperature_test` wählen. PROXON-Integration
   auswählen, `expected_temperature` mit dem abgelesenen Wert füllen und
   `delta` auf `0.5` oder `-0.5` stellen. Mit Antwortdaten ausführen.

   Beispiel für 21 → 21,5 °C:

   ```yaml
   action: proxon_hesp.prepare_target_temperature_test
   data:
     config_entry_id: "DEINE_PROXON_CONFIG_ENTRY_ID"
     expected_temperature: 21
     delta: 0.5
   ```

   Der Aufruf benötigt Antwortdaten (`return_response: true` bei einem
   API-Serviceaufruf; **kein** zusätzliches Feld unter `data`). Ohne angeforderte
   Antwort wird die Vorbereitung abgelehnt, damit kein Freigabecode verloren geht.
   Die Antwort enthält `original_temperature`, `test_temperature`,
   `confirmation_token`, `minimum_wait_seconds: 10` und `expires_in_seconds: 60`.
3. **10–59 Sekunden nach der Vorbereitung** die separate Aktion
   `proxon_hesp.send_target_temperature_test` ausführen. Dieselbe Integration
   und den gerade erhaltenen Freigabecode einsetzen:

   ```yaml
   action: proxon_hesp.send_target_temperature_test
   data:
     config_entry_id: "DEINE_PROXON_CONFIG_ENTRY_ID"
     confirmation_token: "CODE_AUS_DER_VORBEREITUNG"
   ```

   Vor dem Senden Ausgangs- und Testwert aus der Antwort prüfen. Nicht in eine
   Automation oder regelmäßig laufendes Skript übernehmen. Bei abgelaufenem
   Code kann ohne vorherigen Sendeversuch neu vorbereitet werden; damit beginnt
   auch die Testaufnahme neu. Ein alter Code funktioniert dann nicht mehr.
4. BDE-Sollwertanzeige, Betriebsanzeige und HA-Verlauf mit Uhrzeit dokumentieren.
   Nach dem Versuch 30–60 Sekunden beobachten. Ein ausbleibender sichtbarer Effekt
   ist ebenfalls ein Ergebnis. Bei unerwartetem Verhalten über das BDE zurückstellen.
   Den ursprünglichen Sollwert anschließend am BDE wiederherstellen, falls nötig.
5. Die separate Aufnahme endet spätestens **120 Sekunden nach Vorbereitung**.
   Danach unter Einstellungen → Geräte & Dienste → PROXON HESP die
   **Diagnosedaten herunterladen**. Der Download enthält Vorlauf, eigenen
   Sendeversuch und nachfolgend empfangene Telegramme. Für einen weiteren Versuch
   wäre ein bewusstes Neuladen der Integration nötig; zuerst die Diagnose sichern.

Nicht ausgeführte Freigaben verfallen ohne Schreibzugriff. Neustart oder Reload
löschen sie. Nach einem Sendeversuch keine erneuten Aufrufe zur vermeintlichen
Fehlerbehebung: auch bei unbekannter Zustellung bleibt der Versuch verbraucht.

## Auswertung der Diagnose

Unter `target_temperature_test` stehen:

| Feld / Zustand | Bedeutung |
|---|---|
| `original_temperature`, `test_temperature` | Vorbereiteter Ausgangs- und Testwert |
| `write_attempts` | 0 oder 1; auch ein fehlgeschlagener Aufruf zählt als Versuch |
| `application_bytes_offered` | Bytes, die dem TCP-Writer angeboten wurden; kein Empfangsnachweis |
| `transmission_attempt` | Eigener Sendeversuch, mit `direction: tx_attempt`, Rohtelegramm und Zeitpunkt relativ zum Aufnahmestart |
| `receive_capture` | Ausschließlich empfangene Rohbytes, maximal 120 Sekunden, 1 MiB bzw. 4096 Blöcke |
| `prepared` | Vorbereitung ohne Sendeversuch |
| `expired`, `panel_changed`, `connection_changed`, `state_unavailable_or_changed`, `capture_stopped` | Freigabe nicht mehr verwendbar; ohne Versuch kein Versand |
| `transport_flushed_unverified` | TCP-Writer und `drain()` erfolgreich, Zustellung und Übernahme unbestätigt |
| `delivery_unknown` | Sendeversuch begonnen, Abschluss nicht bestätigt; keine Wiederholung |
| `cleared` | Testaufnahme und vorbereitete Werte gelöscht; ein bereits verbrauchter Sendeversuch bleibt verbraucht |

Das bestehende oberste Feld `application_bytes_sent` zählt hier ebenfalls die
dem Writer angebotenen Bytes (normal 0, beim Versuch 14); es ist **keine** Messung
der tatsächlich auf RS485 gesendeten Bytes. Der Freigabecode wird nicht in
Integration-Diagnosen oder Integration-Logs aufgenommen. HA-Aktionsdaten und
Antworten können den Code enthalten; nicht in öffentliche Fehlerberichte kopieren.

Die bisherige, manuell gestartete Busaufnahme bleibt unabhängig bestehen und wird
durch diesen Versuch nicht gelöscht. Testdaten liegen nur im Arbeitsspeicher.
**Aufnahme stoppen** beendet auch die Testaufnahme und verwirft eine noch offene
Freigabe. **Aufnahme löschen** löscht beide Aufnahmen, Testwerte und das
aufgezeichnete Sendetelegramm. Der Versuchszähler wird dabei nicht zurückgesetzt.
Reload/Neustart löschen die Daten ebenfalls. Wie alle Rohaufnahmen können sie weitere Messwerte
der Anlage enthalten; vor Veröffentlichung prüfen.

Nach dem Senden auf den nächsten wiederkehrenden BDE/PTC-Sollwert-SET achten.
Ein zurückkehrender alter Sollwert spricht für erneutes Durchsetzen des bisherigen
Werts. Ein Echo des eigenen Telegramms kann auch den normalen Sollwertsensor
aktualisieren: das ist kein Beweis, dass das BDE seinen internen Sollwert übernommen
hat. Das leere ACK besitzt keine Transaktions-ID und kann nicht eindeutig dem
externen Versuch zugeordnet werden. Deshalb BDE-Foto/Video und Zeitangaben
gemeinsam mit der Aufnahme auswerten.
