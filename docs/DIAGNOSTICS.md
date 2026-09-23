# Diagnose und Aufnahmen

Seit 0.9.0 sind Aufnahmedauer und Aufnahmestatus verfügbar. In 0.8.0 beträgt die
Dauer fest 120 Sekunden; eine Statusentität fehlt dort. Ältere Exporte werden
von den Offline-Werkzeugen weiterhin unterstützt.

## Diagnosedaten herunterladen

Die HA-Diagnose enthält Verbindungs- und Decoderzähler, Angaben zur Aktualität
und gegebenenfalls Mitschnitte. Seit 0.9.0 gehören auch Integrationsversion,
ausgewähltes Hardwareprofil und Zeitpunkt des letzten gültigen unterstützten
Messwerts dazu. Konfigurierte Netzwerkadressen und Identifikatoren werden von
der Integration ausgelassen. Den gesamten Export vor dem Teilen trotzdem prüfen:
HA-Metadaten und Busdaten können Angaben zur eigenen Anlage enthalten.

`application_bytes_sent` zählt die seit dem Laden der Integration an den TCP-
Schreiber übergebenen Bytes. Ohne notwendigen manuellen Zeitabgleich bleibt der
Wert null; er beweist keine physische Zustellung. `clock_sync_status` meldet
`idle`, `waiting`, `confirmed`, `already_current` oder `unconfirmed`.
`clock_sync_target` enthält die zuletzt angeforderte lokale Kalenderzeit.
Details: [Gerätezeit abgleichen](CLOCK_SYNC.md).

## Manuelle Aufnahme

1. Auf der Geräteseite **Aufnahme starten** wählen.
2. Bei einer gezielten Untersuchung Uhrzeit und zugehörige BDE-Anzeige notieren.
3. **Mitschnitt stoppen** wählen und anschließend Diagnosedaten herunterladen.

Die Aufnahme nutzt die vorhandene Verbindung und sendet keine Abfragen.
Unter **Einstellungen → Geräte & Dienste → PROXON HESP → Konfigurieren** am
Integrationseintrag lässt sich die Dauer auf **30 bis 600 Sekunden** einstellen
(Standard **120 Sekunden**). Gemeint ist nicht der Dialog **Systemoptionen**.

Eine Änderung gilt für die nächste manuelle Aufnahme. Sie verbindet das Gateway
nicht neu und löscht keinen Mitschnitt. Laufende Aufnahmen behalten ihr ursprüngliches
Limit. Die Aufnahme stoppt bei Zeitlimit, **1 MiB**, **16.384 Empfangsblöcken**,
manuellem Stopp oder Verbindungsabbruch. Mehr eingestellte Zeit garantiert daher
keine längere Aufnahme.

Erneutes Starten ersetzt die vorherige Aufnahme. **Mitschnitt löschen**, Neuladen
und HA-Neustart entfernen sie. Ein gestoppter Mitschnitt bleibt ansonsten im
Arbeitsspeicher und in späteren Diagnoseexporten enthalten. Vor einem Update
oder Neustart benötigte Aufnahmen herunterladen.

## Automatische Ereignisaufnahmen

Seit 0.10.0 kann unter **Konfigurieren** die automatische Ereignisaufnahme
aktiviert werden. Sie ist zunächst deaktiviert, bleibt vollständig passiv und
benötigt keinen manuellen Start im Moment eines Verdichterwechsels.

Seit **0.11.0** gilt:

- Ein fortlaufender Puffer hält bis zu **180 Sekunden Vorgeschichte**, begrenzt
  auf 512 KiB und 8.192 Empfangsblöcke.
- Eine frische, gültige Verdichterdrehzahl von null auf positiv oder umgekehrt
  startet eine Aufnahme mit Vorgeschichte und **180 Sekunden Nachlauf**.
  Erste Messwerte, mindestens 30 Sekunden alte Daten und Wiederverbindungen
  bilden nur eine neue Ausgangsbasis. Ungültige Telegramme lösen nichts aus.
- **Ereignisaufnahme** zeigt den Zustand deaktiviert, wartend, aufzeichnend oder
  bereit sinngemäß in der HA-Oberflächensprache. Sobald eine Aufnahme bereit ist,
  die gewöhnlichen Diagnosedaten herunterladen. Während der Aufnahme ist der
  Export nur ein Zwischenstand.
- Bis zu **vier Aufnahmen einschließlich einer laufenden** bleiben erhalten.
  Eine fünfte ersetzt die älteste; `overwritten_captures` zählt Ersetzungen.
  Weitere Übergänge innerhalb eines laufenden Fensters werden als Ereignisse
  vermerkt, ohne es zu verlängern. Maximal 32 Ereignisse werden einzeln gespeichert;
  weitere werden gezählt. „Bereit“ bedeutet nicht, dass die Automatik angehalten ist.
- **Ereignisaufnahmen löschen** entfernt alle gespeicherten Ereignisaufnahmen.
  Die nächste gültige Zustandsänderung kann erneut eine Aufnahme auslösen.
- Die jüngste Aufnahme steht in `event_capture.chunks` und `events`.
  Frühere liegen in `event_capture.previous_captures`, älteste zuerst, jeweils
  mit eigenen Zeitstempeln und Abschlussgründen. `capture_count` zählt auch
  eine laufende Aufnahme.
- Manuelle Aufnahmen sind unabhängig. Ihre Dauer verändert nicht die automatischen
  180/180-Sekunden-Fenster. Deaktivieren der Automatik verwirft den Vorlaufpuffer
  und beendet eine laufende Ereignisaufnahme mit `disabled`; das Teilergebnis
  bleibt herunterladbar. Erneutes Aktivieren erhält gespeicherte Aufnahmen und
  beginnt mit einer neuen Ausgangsbasis.
- Verbindungsabbruch beendet eine Aufnahme mit `disconnected` und verwirft
  Ausgangsbasis und Vorlaufpuffer. Neuladen oder Neustart verwirft alle Aufnahmen
  und Timer. Die Aktivierungseinstellung bleibt erhalten.

Jede Aufnahme einschließlich Vorgeschichte ist auf 1 MiB und 16.384 Blöcke
begrenzt. Tatsächlicher Vorlauf, Dauer, Zähler und Abschlussgrund sind sichtbar;
Speicherlimits können beide Zeitfenster verkürzen. Insgesamt sind höchstens
5,5 MiB Rohdaten vorgesehen: eine manuelle, vier automatische Aufnahmen und der
Vorlaufpuffer. Python-Objekte und Hex-Exporte benötigen zusätzlichen Speicher.

Ein Verdichterereignis belegt Rotation, nicht Heizen, Kühlen, Abtauen oder PTC-
Leistung. Der Zeitpunkt entspricht dem vollständig dekodierten TCP-Messwert,
nicht einem genauen elektrischen Schaltzeitpunkt. Pufferränder können Telegramme
teilen; der vorhandene Parser synchronisiert sich erneut. Für unbekannte Bits
kann weiterhin eine unabhängige Displaybeobachtung erforderlich sein.

## Status und Exportfelder

**Aufnahmestatus** ist standardmäßig aktiv. Attribute enthalten Start/Stopp,
tatsächliche Dauer, Größe, Anzahl der Blöcke und Grenzen, niemals rohe Nutzdaten.
Fortschritt wird ungefähr alle fünf Sekunden aktualisiert. Start, Stopp, Löschen,
Grenzen und Verbindungsabbruch werden unmittelbar gemeldet, auch wenn nach
Ablauf des Timers kein weiteres Telegramm eintrifft.

| Feld | Bedeutung |
|---|---|
| `started_utc` | Startzeit |
| `stopped_utc` | Stoppzeit; während Aufnahme oder im Leerlauf `null` |
| `status` | `idle`, `recording`, `manual`, `duration_limit`, `byte_limit`, `chunk_limit` oder `disconnected` |
| `actual_duration_seconds` | Tatsächliche Dauer einschließlich Zeiten ohne Empfang; nach Stopp eingefroren |
| `bytes`, `chunk_count` | Rohdatenmenge und Anzahl der Empfangsblöcke |
| `duration_seconds` | Für diese Aufnahme festgelegtes Zeitlimit |
| `configured_duration_seconds` | Aktuell eingestelltes Limit für die nächste Aufnahme |
| `integration_version`, `profile` | Kontext für die Interpretation |
| `max_bytes`, `max_chunks` | Speichergrenzen |
| `chunks` | Hexadezimale TCP-Blöcke mit relativem `elapsed_ms` |

Empfangsblöcke sind keine Telegrammgrenzen. Der letzte Blockzeitpunkt ist nicht
die genaue Stoppzeit. Die tatsächliche Dauer verwendet eine monotone Uhr und
ist unabhängig von Empfang und Systemzeitkorrekturen. Ein Export mit `recording`
ist ein Zwischenstand.

Aktuelle Exporte nutzen **Formatversion 2** mit unverändertem `chunks`-Format.
Ältere Exporte nutzen `size_limit` für beide Speichergrenzen und enthalten keine
genaue Stoppzeit oder tatsächliche Dauer. Werkzeuge erfinden diese fehlenden Werte nicht.
Auch unbekannte und verworfene Bytes werden aufgezeichnet. Rohdaten liegen nur
im Arbeitsspeicher, nicht in Entitätsattributen, Recorder oder Protokolldateien.

## Weitere Diagnoseentitäten

Zwei optionale Entitäten sind zunächst deaktiviert:

- **Gateway-Verbindung** beschreibt ausschließlich die TCP-Verbindung.
- **Letzter gültiger Datenempfang** zeigt den Zeitpunkt des jüngsten unterstützten,
  gültigen Decoderwerts. Unbekannte oder ungültige Daten aktualisieren ihn nicht.
  Er belegt nicht die Aktualität aller Kanäle. Bei Verbindungsabbruch bleibt der
  Zeitpunkt erhalten; nach Neuladen ist er bis zum ersten gültigen Wert unbekannt.
  Während des Empfangs erfolgt die HA-Aktualisierung ungefähr alle fünf Sekunden.

Status- und Verbindungsdiagnosen bleiben bei Verbindungsabbruch lesbar.
Messwerte werden nach ihren eigenen Aktualitätsregeln nicht verfügbar.
Neuladen/Entladen beendet Timer und entfernt Listener. Löschen setzt den
manuellen Aufnahmestatus auf Leerlauf zurück.

## Hinweise zum Update

Beim damaligen Update 0.8.0 → 0.9.0 blieben 54 Entitätsidentitäten, eigene Namen
und Aktivierungseinstellungen erhalten; drei Diagnosen kamen hinzu (57 insgesamt).
Ohne gesetzte Option gilt eine Aufnahmedauer von 120 Sekunden. Dafür war keine
Konfigurationsmigration oder zusätzliche Verbindung nötig. Für aktuelle Versionen
und die spätere Beta-Migration gelten die [Versionshinweise](../RELEASE_NOTES.md).

## Auswertung und Fehlermeldungen

Für die technische Analyse gibt es [Offline-Werkzeuge (Englisch)](OFFLINE_ANALYSIS.md).
Sie arbeiten ohne Geräteverbindung und unterstützen alte sowie neue Exportformate.
Die Inventarisierung erfasst auch unbekannte Telegrammkennungen; die Wiedergabe
zeigt nur vom Produktionsdecoder verstandene Werte.

Bei einer Fehlermeldung Integrations- und HA-Version, Hardwareprofil, betroffene
Entität sowie erwartetes und beobachtetes Verhalten nennen. Ein geprüftes minimales
Telegramm mit erwarteter Interpretation ist hilfreicher als ein ungefilterter Dump.
Adressen, Kennungen, Seriennummern, private Pfade und nicht benötigte Messwerte
entfernen. Keine Anlagenstörung absichtlich auslösen. Vollständige Aufnahmen,
Displayfotos und persönliche Notizen außerhalb des öffentlichen Repositorys aufbewahren.
