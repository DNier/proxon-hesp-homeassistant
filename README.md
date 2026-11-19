# PROXON HESP für Home Assistant

PROXON HESP bindet eine Lüftungs- und Heizungsanlage über ihren HESP-Bus lokal in
Home Assistant ein. Die Integration empfängt die vorhandenen Daten über ein
transparentes RS485-zu-TCP-Gateway. Die Anlage und vorhandene Thermostate regeln
weiter wie gewohnt.

Das Projekt wird unabhängig von Zimmermann entwickelt. [English overview](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/README.en.md)

## Voraussetzungen

- **Home Assistant ab 2026.9.**
- **PROXON P2** mit LT-ZIM V1.6, PTC 4× V1.2 und BDE Comfort als geprüfte
  Referenz. Für die **FWT 2-L** ist ein begrenzter lesender Umfang durch
  Community-Vergleiche belegt. Vergleiche deine Ausstattung mit der
  [Kompatibilitätsübersicht](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/docs/COMPATIBILITY.md).
- **Transparentes RS485-zu-TCP-Gateway** am unterstützten Busabschnitt, eingestellt
  auf **19200 Baud, 8N1**. Das Bedienteil (BDE) bleibt angeschlossen. HESP wird
  direkt übertragen und benötigt kein Modbus-Modul, MQTT oder Cloud-Konto.

## Was die Integration bietet

- Temperaturen, Luftstufen, Drehzahlen, Betriebsstunden und Filterrestlaufzeit.
- Optionale Diagnosen wie Verdichter-Stellgröße und BDE-Anzeigen. Der Status
  **Verdichter läuft** beschreibt die gemeldete Drehung. Die
  [BDE-Betriebsanzeige](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/docs/BDE_DISPLAY_EVIDENCE.md)
  zeigt **Heizbetrieb** und **Betriebsfeld leer** ausschließlich in belegten
  Eco-Winter-Konstellationen.
- Manuelle und automatische [Diagnoseaufnahmen](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/docs/DIAGNOSTICS.md)
  zur Fehlersuche und für Vergleiche mit dem BDE.
- Optionale [Heizraum-Überwachung](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/docs/ROOMS.md)
  mit vorhandenen Home-Assistant-Entitäten.
- Optionaler [Gerätezeitabgleich](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/docs/CLOCK_SYNC.md)
  per Schaltfläche oder über den standardmäßig ausgeschalteten Schalter für
  Sommer- und Winterzeit. Beim Einschalten kann der Schalter die Gerätezeit
  sofort korrigieren.

## Installation und Updates

[![Repository in HACS öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=DNier&repository=proxon-hesp-homeassistant&category=integration)

1. Dieses Repository in HACS als benutzerdefinierte **Integration** hinzufügen.
2. Die [aktuelle stabile Version](https://github.com/DNier/proxon-hesp-homeassistant/releases/latest)
   herunterladen und Home Assistant neu starten.
3. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen**
   **PROXON HESP** auswählen. Gateway-Adresse, TCP-Port und Anlagenprofil angeben.

Vor einem Update benötigte Mitschnitte herunterladen und die
[Hinweise für bestehende Installationen](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/docs/GETTING_STARTED.md#updates-und-bestehende-installationen)
lesen. Den bestehenden Integrationseintrag behalten.

## Austausch und Mithilfe

Fragen und Ideen gehören in die [GitHub-Discussions](https://github.com/DNier/proxon-hesp-homeassistant/discussions)
oder ins [Home-Assistant-Forum](https://community.home-assistant.io/t/proxon-p-series-via-hesp-local-integration-without-a-modbus-module-testers-and-contributors-welcome/1026553).
Für Fehler und Kompatibilitätsberichte gibt es [Meldeformulare](https://github.com/DNier/proxon-hesp-homeassistant/issues/new/choose).
Teile bei Bedarf einen kurzen, bereinigten Auszug. Vollständige Diagnoseexporte,
Mitschnitte und Fotos bleiben privat. Sicherheitslücken bitte
[vertraulich melden](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/SECURITY.md).

## Dokumentation

- [Einrichtung und Fehlerhilfe](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/docs/GETTING_STARTED.md)
- [Hardware und Kompatibilität](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/docs/COMPATIBILITY.md)
- [Entitäten am Hauptgerät](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/docs/ENTITY_ORGANIZATION.md)
- [Heizräume einrichten](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/docs/ROOMS.md)
- [Gerätezeit abgleichen](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/docs/CLOCK_SYNC.md)
- [Diagnose und Aufnahmen](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/docs/DIAGNOSTICS.md)
- [Gezielte BDE-Vergleiche](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/docs/REFERENCE_TESTS.md)
- [Experimentelle Statusbits vergleichen](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/docs/EXPERIMENTAL.md)
- [Versions- und Upgradehinweise](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/RELEASE_NOTES.md)
- [Entwicklung und Beiträge (Englisch)](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/CONTRIBUTING.md)

[MIT-Lizenz für den Projektcode](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/LICENSE)
· [Protokollquellen und Rechte](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/NOTICE.md)
· [Verhaltenskodex (Englisch)](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/CODE_OF_CONDUCT.md)
