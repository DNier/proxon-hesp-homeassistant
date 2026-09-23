<p align="center">
  <img src="https://raw.githubusercontent.com/DNier/proxon-hesp-homeassistant/main/custom_components/proxon_hesp/brand/logo.png" alt="PROXON HESP" width="160" height="160">
</p>

# PROXON HESP für Home Assistant

[English overview](README.en.md) · [Installation](#installation-mit-hacs) · [Dokumentation](#dokumentation)

Lokale Integration für PROXON-Anlagen der P-Serie mit einem transparenten
RS485-zu-TCP-Gateway am HESP-Bus. MQTT, Cloud oder eine zusätzliche Anwendung
sind nicht erforderlich. Die vorhandene Anlagensteuerung bleibt verantwortlich.

Die Integration empfängt den bestehenden Busverkehr ohne eigene Abfragen.
Die optionale Schaltfläche **Gerätezeit abgleichen** ist die einzige
Schreibfunktion: Auf Tastendruck sendet sie einmalig eine Kalenderkorrektur.
Einrichtung, Wiederverbindung und Aufnahmen senden keine Steuerbefehle.

## Versionsstand

- **0.11.0** ist die stabile Version. Sie enthält automatische Aufnahmen bei
  Verdichterstarts und -stopps mit bis zu 180 Sekunden Vor- und Nachlauf und
  bewahrt die vier jüngsten Ereignisaufnahmen auf.
- **0.12.0b4** ist eine Vorabversion. Sie ergänzt optionale Heizräume als native
  HA-Untereinträge sowie Gerätezeit-Anzeige und manuellen Zeitabgleich.
  Die praktische Abnahme der Raumüberwachung ist noch offen.
- **0.12.0b4** überarbeitet außerdem die [Einteilung der Entitäten](docs/ENTITY_ORGANIZATION.md)
  und vereinheitlicht die Nutzerdokumentation auf Deutsch.

Vor dem Wechsel auf 0.12.0b4 ein HA-Backup erstellen: Das Konfigurationsformat
steigt auf Version 2. Ältere Integrationsversionen können es nicht laden;
für ein Zurückwechseln ist das vorherige Backup erforderlich.
Details stehen in den [Versionshinweisen](RELEASE_NOTES.md).

## Voraussetzungen und Kompatibilität

0.11.0 und 0.12.0b4 benötigen **Home Assistant ab 2026.9**.
Das bestätigte Hardwareprofil ist **LT-ZIM V1.6 mit PTC 4× V1.2 und BDE Comfort**.
Die Unterstützung beruht auf Mitschnitten und Displayvergleichen dieser
Konfiguration. Andere Revisionen sind damit nicht automatisch unterstützt.
Das Profil wird bei der Einrichtung ausgewählt, nicht vom Gateway erkannt.

Bitte vor der Installation die [Kompatibilität](docs/COMPATIBILITY.md) prüfen.
Dieses unabhängige Projekt steht in keiner Verbindung zum Gerätehersteller.

## Funktionen und Grenzen

| Funktion | Umfang |
|---|---|
| Betriebsart, angeforderte Luftstufe, Raum- und Solltemperatur | Lesend |
| Zehn Anlagentemperaturen sowie Lüfter- und Verdichterdrehzahlen | Lesend |
| Verdichter läuft, Bypass-Schaltzustand, Intensivlüftung | Lesend; kein Nachweis von Heiz-/Kühlbetrieb |
| Filterrestlaufzeit und acht Betriebsstundenzähler | Lesend |
| Regler-Luftstufe, rohe Stellwerte und Hex-Datenpunkte | Optionale Diagnose |
| Manuelle und automatische Mitschnitte | Passiv, zeitlich und im Speicher begrenzt |
| Gerätedatum/-uhrzeit und manueller Zeitabgleich | Optional, ab 0.12.0b1 |
| Heizräume mit vorhandenen HA-Entitäten | Herstellerunabhängige Überwachung, ab 0.12.0b1 |

Nach 30 Sekunden ohne gültige Aktualisierung wird der jeweilige Messwert nicht
verfügbar; bei Verbindungsabbruch sofort. Fehlende Daten bedeuten nicht null,
„aus“ oder „störungsfrei“. Die angeforderte Luftstufe kann von der Reglerstufe
abweichen. Ein gemeldeter Schaltzustand ist keine Messung der mechanischen Position.

Es gibt keine allgemeine Heizungs- oder Lüftersteuerung, keinen bestätigten
Heizen/Kühlen/Abtauen-Sensor, keinen Fehlertextsensor, keinen Countdown für
Intensivlüftung und keine Warmwasserintegration. Die technische
[Datenpunktreferenz (Englisch)](docs/DATA_POINTS.md) beschreibt die Beleglage.

## Installation mit HACS

[![Repository in HACS öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=DNier&repository=proxon-hesp-homeassistant&category=integration)

1. In HACS `https://github.com/DNier/proxon-hesp-homeassistant` als
   benutzerdefiniertes Repository der Kategorie **Integration** hinzufügen
   oder die Schaltfläche oben verwenden.
2. **PROXON HESP** herunterladen und Home Assistant neu starten.
3. **Einstellungen → Geräte & Dienste → Integration hinzufügen → PROXON HESP** öffnen.
4. Gateway-Adresse, TCP-Port (Standard `4196`), Namen und Hardwareprofil eintragen.

Für eine Beta in HACS gegebenenfalls Vorabversionen zulassen und über
**Erneut herunterladen** die gewünschte Version wählen.

Bei manueller Installation den Ordner `custom_components/proxon_hesp` in den
Ordner `custom_components` der HA-Konfiguration kopieren. Danach HA neu starten
und die Integration wie oben hinzufügen.

Das Gateway separat als transparenten TCP-Server mit **19200 Baud, 8N1** für den
unterstützten Busabschnitt konfigurieren. Keine Modbus-Konvertierung aktivieren.
Die Integration konfiguriert das Gateway nicht. Anschlussbezeichnungen und
Belegungen unterscheiden sich je nach Platinenrevision; es gibt hier keine
universelle Verdrahtungsanleitung.

Die Einrichtung wartet bis zu 20 Sekunden auf unterstützte, prüfsummengültige
Daten. Ein erreichbarer TCP-Port allein reicht nicht. Andere Aufnahmeprogramme
vorher beenden: Das Gateway unterstützt möglicherweise nur eine Verbindung.
Auch während Aufnahmen nutzt die Integration nur ihre bestehende Verbindung.

## Optionale Heizräume

Mit **Heizraum hinzufügen** lassen sich vorhandene Heizschalter, Leistungssensoren
und optional Thermostate sowie Temperatur-/Feuchtesensoren zu Räumen verknüpfen.
Jeder Raum erhält ein virtuelles Gerät mit Erreichbarkeit, Schaltzustand,
Leistung und erkanntem elektrischem Heizbetrieb. Mehrere Heizelemente je Raum
sind möglich. Die vorhandenen Thermostate regeln weiter; die Raumüberwachung
schaltet nichts. Es sind keine bestimmten Hersteller vorausgesetzt.

Einrichtung und Verhalten bei fehlenden Werten: [Heizräume](docs/ROOMS.md).
Aufnahmeoptionen bleiben am übergeordneten Integrationseintrag unter **Konfigurieren**.

## Updates und bestehende Installationen

Updates über HACS installieren und HA neu starten. Benötigte Mitschnitte zuvor
herunterladen: Sie liegen nur im Arbeitsspeicher. Den bestehenden Eintrag behalten,
damit Entitätsidentitäten, eigene Namen und Einstellungen erhalten bleiben.

Gateway-Adresse, Port oder Namen über **Neu konfigurieren** ändern. Löschen und
Neuanlegen erzeugt eine neue Identität. Verschiedene Hostnamen für dasselbe
Gateway können derzeit nicht als Duplikat erkannt werden.

Beim Update von 0.8.0 auf 0.11.0 bleiben die 54 bisherigen Entitätsidentitäten
erhalten; sechs kommen hinzu (60 insgesamt). Automatische Ereignisaufnahmen
sind zunächst deaktiviert. Die manuelle Aufnahmedauer bleibt ohne Änderung
bei 120 Sekunden. Die Beta ergänzt zwei Gerätezeit-Entitäten (62 am Hauptgerät)
und die jeweils eingerichteten Raum-Entitäten.

Seit 0.8.0 sind `proxon_hesp.prepare_target_temperature_test` und
`proxon_hesp.send_target_temperature_test` entfernt. Gespeicherte Aufrufe aus
0.7.x entfernen; es gibt keine Ersatzaktion für die Solltemperatur. Der frühere
Diagnoseabschnitt `target_temperature_test` entfällt ebenfalls.

## Fehlerhilfe

Bei fehlgeschlagener Einrichtung Gateway-Modus, serielle Einstellungen und
konkurrierende TCP-Verbindungen prüfen. Sind nur einzelne Werte nicht verfügbar,
fehlen möglicherweise unterstützte gültige Telegramme für diese Datenpunkte.
Eine bestehende TCP-Verbindung belegt keine aktuellen Messwerte.

Für Untersuchungen auf der Geräteseite **Aufnahme starten**, anschließend
**Mitschnitt stoppen** und Diagnosedaten herunterladen. Dauer und automatische
Ereignisaufnahmen werden am Integrationseintrag unter **Konfigurieren** eingestellt.
Diagnosedateien vor dem Teilen auf private Angaben prüfen.

## Dokumentation

**Für die Einrichtung und Nutzung (Deutsch):**

- [Hardware und Kompatibilität](docs/COMPATIBILITY.md)
- [Heizräume](docs/ROOMS.md)
- [Gerätezeit abgleichen](docs/CLOCK_SYNC.md)
- [Diagnose und Aufnahmen](docs/DIAGNOSTICS.md)
- [Entitäten am Hauptgerät](docs/ENTITY_ORGANIZATION.md)
- [Versions- und Upgradehinweise](RELEASE_NOTES.md)

**Für Entwicklung und Protokollanalyse (Englisch):**

- [Mitwirken und Prüfungen](CONTRIBUTING.md)
- [Datenpunkte und Validierungsgrenzen](docs/DATA_POINTS.md)
- [Offline-Auswertung](docs/OFFLINE_ANALYSIS.md)
- [Belege zu Steuerbefehlen](docs/CONTROL_EVIDENCE.md)
- [Herleitung der Prüfsumme](docs/CHECKSUM_ALGORITHM.md)

Nutzerdokumentation und Versionshinweise werden auf Deutsch gepflegt;
[README.en.md](README.en.md) bietet einen kompakten englischen Einstieg.
Code, Codekommentare und Entwicklerreferenzen bleiben englisch.
Die HA-Oberfläche unterstützt Deutsch und Englisch.

## Lizenz und Quellen

Eigener Code steht unter der [MIT-Lizenz](LICENSE). Protokollinterpretation und
Prüfsummenherleitung bauen auf [Markus Mauchs HESP-Dokumentation](https://markusmauch.github.io/proxon-hesp/)
unter CC BY 4.0 auf. Für übernommenes bzw. angepasstes Material bleiben
Quellenangabe und Lizenz erhalten; siehe [NOTICE.md](NOTICE.md).
Das PROXON-Logo ist von der MIT-Lizenz ausgenommen und gehört den jeweiligen Rechteinhabern.
