# PROXON HESP für Home Assistant

[English overview](../README.en.md) · [Installation](#installation-mit-hacs) · [Fehlerhilfe](#fehlerhilfe)

PROXON HESP liest Betriebsdaten einer PROXON-Anlage über den vorhandenen HESP-Bus
und ein transparentes RS485-zu-TCP-Gateway. Die Integration nutzt eine bestehende
Verbindung für Messwerte und Aufnahmen. Die Anlagensteuerung und vorhandene
Thermostate bleiben für den Betrieb zuständig.

Die Integration sendet nur zur optionalen Korrektur der Gerätezeit. Dafür gibt es
die Schaltfläche **Gerätezeit abgleichen** und den standardmäßig ausgeschalteten
Schalter **Sommer-/Winterzeit automatisch abgleichen**. Beim Einschalten kann
der Schalter die frisch empfangene Gerätezeit sofort korrigieren. Einrichtung,
Wiederverbindung und Diagnoseaufnahmen arbeiten rein lesend.

## Versionsstand

Installiere die [aktuelle stabile Version](https://github.com/DNier/proxon-hesp-homeassistant/releases/latest).
Die [Versionshinweise](../RELEASE_NOTES.md) beschreiben Änderungen und
Migrationsschritte je Version.

## Voraussetzungen und Kompatibilität

- **Home Assistant ab 2026.9.**
- **PROXON P2** mit LT-ZIM V1.6, PTC 4× V1.2 und BDE Comfort als bestätigte
  Referenz. Für die **FWT 2-L** mit LT-ZIM V1.3 und BDE Comfort V03.7.9B00
  ist ein lesender Teilumfang geprüft. Angaben zu bestätigten Funktionen und
  Busabschnitten stehen unter [Hardware und Kompatibilität](COMPATIBILITY.md).
- **Transparentes RS485-zu-TCP-Gateway**, eingestellt auf **19200 Baud, 8N1**.
  Das Gateway reicht die HESP-Daten direkt weiter. Das Bedienteil (BDE) bleibt
  angeschlossen.

Wähle das dokumentierte Anlagenprofil `lt_zim_16_observed` bei der Einrichtung.
Die Integration erkennt Modell, Platinenrevision und Firmware nicht automatisch.
Belegungen unterscheiden sich je nach Platinenrevision. Richte den Zugang zum
Bus anhand der Dokumentation für deine Hardware ein.

Die Integration nutzt HESP unabhängig von Zimmermann und benötigt kein
Modbus-Modul, MQTT oder Cloud-Konto. Informationen zur genannten P-Serie und zum
Verhalten nach einem Stromausfall stehen unter [Herstellerangaben](MANUFACTURER_INFORMATION.md).

## Funktionen und Grenzen

| Funktion | Verfügbarer Umfang |
|---|---|
| Temperaturen, Lüftungsstufe, Lüfter- und Verdichterdrehzahlen | Lesende Betriebswerte |
| Bypass, Intensivlüftung, Filterrestlaufzeit und Betriebsstunden | Lesende Zustände und Zähler |
| Verdichter-Stellgröße, Lüfteransteuerung, Leistungsgrenzen und Wärmepumpen-Schwellen | Optionale Diagnose. Die Schwellen zeigen die von der Steuerung gemeldeten Einstellungen. |
| BDE-Betriebsanzeige sowie MV-Heizen/Kühlen und MV-Abtau | Optionale Anzeige ausgewählter, belegter BDE-Zustände |
| Manuelle und automatische Mitschnitte | Passive, zeitlich und im Speicher begrenzte [Aufnahmen](DIAGNOSTICS.md) |
| Gerätezeit | Optionale Anzeige und [manueller oder automatischer Abgleich](CLOCK_SYNC.md) |
| Heizräume | Optionale Überwachung anhand vorhandener Home-Assistant-Entitäten |

Betriebswerte sind bei frischem, gültigem Empfang verfügbar. Die meisten Werte
laufen nach 30 Sekunden ohne gültige Aktualisierung ab. Bei einem
Verbindungsabbruch werden sie sofort unverfügbar. Die
[Entitätsübersicht](ENTITY_ORGANIZATION.md) zeigt, welche Diagnosen du am Gerät
bei Bedarf aktivieren kannst.

**Verdichter läuft** beschreibt die gemeldete Rotation. **BDE-Betriebsanzeige**
meldet **Heizbetrieb** oder **Betriebsfeld leer** nur in den dafür belegten
Eco-Winter-Konstellationen. Für Aussagen über abgegebene Leistung, tatsächliche
Ventilpositionen und PTC-Aktivität sind eigene Messungen erforderlich. Die
[Protokollreferenz (Englisch)](DATA_POINTS.md) beschreibt die Zuordnungen.

## Installation mit HACS

[![Repository in HACS öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=DNier&repository=proxon-hesp-homeassistant&category=integration)

1. Das Gateway mit dem unterstützten Busabschnitt verbinden und als
   transparenten TCP-Server einstellen. Einen vorhandenen Modbus-Modus
   ausschalten. Andere Aufnahmeprogramme, die mit dem Gateway verbunden sind,
   vor der Einrichtung schließen.
2. In HACS [dieses Repository](https://github.com/DNier/proxon-hesp-homeassistant)
   als benutzerdefiniertes Repository der Kategorie **Integration** hinzufügen.
3. **PROXON HESP** herunterladen und Home Assistant neu starten.
4. **Einstellungen → Geräte & Dienste → Integration hinzufügen → PROXON HESP**
   öffnen. Gateway-Adresse, TCP-Port (Standard `4196`), Name und Anlagenprofil
   angeben.

Der Verbindungstest wartet bis zu 20 Sekunden auf gültige, unterstützte
Telegramme. Bei manueller Installation den Ordner `custom_components/proxon_hesp`
aus dem Release in den Ordner `custom_components` der HA-Konfiguration kopieren.
Danach Home Assistant neu starten und die Integration wie oben hinzufügen.

## Optionale Heizräume

Über **Heizraum hinzufügen** verknüpfst du vorhandene Heizschalter,
Leistungssensoren und optional Thermostate sowie Temperatur- oder
Feuchtesensoren. Jeder [Heizraum](ROOMS.md) erhält ein virtuelles Gerät mit
Erreichbarkeit, Schaltzustand, Leistung und erkanntem elektrischem Heizbetrieb.

## Updates und bestehende Installationen

Benötigte Mitschnitte vor einem Update herunterladen. Sie liegen im
Arbeitsspeicher und gehen beim Neustart verloren. Installiere das Update in HACS
und starte Home Assistant neu. Behalte den vorhandenen Integrationseintrag,
damit Namen und Aktivierungseinstellungen erhalten bleiben. Adresse, Port und
Name kannst du über **Neu konfigurieren** ändern.

| Ausgangsversion | Was du beim Update beachten musst |
|---|---|
| Vor 0.16.11 | Die konfigurierten Wärmepumpen-Schwellen ersetzen `raw_0115` und `raw_011c`. Passe Verweise und Vergleiche in Dashboards und Automationen an die neuen Entitäten mit K bzw. °C an. [Details (Englisch)](SERVICE_SETTINGS_EVIDENCE.md#configured-heat-pump-thresholds) |
| Vor 0.16.8 | Die optionale **Verdichter-Stellgröße** ersetzt `raw_0120`. Passe eigene Verweise und Vergleiche an die neue Entität und ihren numerischen Prozentwert an. [Details (Englisch)](DATA_POINTS.md#compressor-control-output-0168) |
| Vor 0.15.0 | Sieben Rohanzeigen werden durch verständlich benannte Sensoren ersetzt. Prüfe Dashboards, Automationen und Vorlagen auf Verweise zu entfernten IDs. Die neue Prozentanzeige hat eine eigene Zeitreihe. [Ersatzsensoren und Aktivierung (Englisch)](DATA_POINTS.md#readable-telemetry-and-entity-migration-0150) |
| Vor 0.12.0b3 | Erstelle vor dem Wechsel ein HA-Backup. Das Konfigurationsformat wird migriert. Für eine Rückkehr zu einer älteren Version brauchst du das Backup. |
| 0.7.x | Entferne gespeicherte Aufrufe der früheren Testaktionen `proxon_hesp.prepare_target_temperature_test` und `proxon_hesp.send_target_temperature_test`. |

## Fehlerhilfe

- Wenn die Einrichtung fehlschlägt, prüfe Gateway-Adresse, Port, serielle
  Einstellungen und den transparenten TCP-Modus. Trenne andere TCP-Clients.
- Wenn einzelne Werte fehlen, prüfe Hardwareprofil, Ausstattung und den Empfang
  der betroffenen Werte. Die optionale Entität **Gateway-Verbindung** zeigt
  den Zustand der TCP-Verbindung an.
- Für einen Mitschnitt wähle auf der Geräteseite **Aufnahme starten** und später
  **Mitschnitt stoppen**. Im Menü des Integrationseintrags kannst du die
  [Diagnosedaten](DIAGNOSTICS.md) herunterladen. Halte Originalexporte privat und
  teile bei Bedarf einen kurzen, bereinigten Auszug über das
  [Meldeformular](https://github.com/DNier/proxon-hesp-homeassistant/issues/new/choose).

## Dokumentation

- [Hardware und Kompatibilität](COMPATIBILITY.md)
- [Heizräume](ROOMS.md)
- [Gerätezeit abgleichen](CLOCK_SYNC.md)
- [Diagnose und Aufnahmen](DIAGNOSTICS.md)
- [Gezielte BDE-Vergleiche](REFERENCE_TESTS.md)
- [Entitäten am Hauptgerät](ENTITY_ORGANIZATION.md)
- [Versions- und Upgradehinweise](../RELEASE_NOTES.md)

Für die Entwicklung stehen [Beitragsleitfaden](../CONTRIBUTING.md),
[Datenpunktreferenz](DATA_POINTS.md), [Offline-Auswertung](OFFLINE_ANALYSIS.md),
[Belege zu Steuerbefehlen](CONTROL_EVIDENCE.md) und
[Prüfsummenherleitung](CHECKSUM_ALGORITHM.md) auf Englisch zur Verfügung.

## Lizenz und Quellen

[MIT-Lizenz für den Projektcode](../LICENSE) · [Protokollquellen und Rechte](../NOTICE.md)
