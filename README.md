# PROXON HESP für Home Assistant

Lokale Integration für PROXON-Anlagen der P-Serie über ein transparentes
RS485-zu-TCP-Gateway. Ohne Cloud, MQTT oder zusätzliche Anwendung.

## Voraussetzungen

- Home Assistant ab **2026.9**.
- Geprüfte Referenz: **LT-ZIM V1.6, PTC 4× V1.2, BDE Comfort**.
- Gateway im transparenten TCP-Modus mit **19200 Baud, 8N1**.
- Andere Hardwarevarianten sind nicht automatisch unterstützt.

## Was die Integration bietet

- Temperaturen, Luftstufen, Drehzahlen, Betriebsstunden und Filterrestlaufzeit.
- Verdichterrotation, Bypass-Schaltzustand und Intensivlüftung.
- Passive Diagnoseaufnahmen bei Bedarf oder bei Verdichterstarts und -stopps.
- In der Beta: Raumüberwachung mit vorhandenen HA-Sensoren, manueller
  Gerätezeitabgleich und optionale experimentelle Statusbits zum BDE-Vergleich.

Die vorhandene Anlagensteuerung und deine Thermostate bleiben verantwortlich.
Nur der ausdrücklich ausgelöste Gerätezeitabgleich schreibt einen Kalenderwert.
Allgemeine Heizungs-/Lüftersteuerung und eine bestätigte Unterscheidung von
Heizen, Kühlen und Abtauen sind nicht enthalten.

## Installation und Updates

1. Dieses Repository in HACS als benutzerdefinierte **Integration** hinzufügen.
2. PROXON HESP herunterladen und Home Assistant neu starten.
3. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen**
   PROXON HESP auswählen und Gateway-Adresse, Port und Profil eintragen.

**Stabil: 0.11.0. Beta: 0.12.0b6.** Für weitere Beta-Updates in HACS die
Vorabversionen für dieses Repository aktivieren. Eine einmalig manuell installierte
Beta aktiviert diese Einstellung nicht zwingend.

HACS prüft Updates regelmäßig; Veröffentlichungen werden nicht unmittelbar an
Home Assistant gepusht. Bei Bedarf in HACS **Informationen aktualisieren** verwenden.
Die Update-Entität meldet verfügbare Versionen. Installation und HA-Neustart sind
separate Schritte; eine Handy-Pushnachricht wird dadurch nicht automatisch eingerichtet.

Vor Updates ein Backup erstellen und benötigte Mitschnitte herunterladen.
Beim Wechsel von vor 0.12.0b3 wird das Konfigurationsformat migriert;
ein Zurückwechseln erfordert das vorherige Backup. Bestehende Einträge behalten.

## Dokumentation

- [Einrichtung und ausführliche Übersicht](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/docs/GETTING_STARTED.md)
- [Hardware und Kompatibilität](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/docs/COMPATIBILITY.md)
- [Heizräume einrichten](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/docs/ROOMS.md)
- [Diagnose und Aufnahmen](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/docs/DIAGNOSTICS.md)
- [Experimentelle Statusbits vergleichen](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/docs/EXPERIMENTAL.md)
- [Gerätezeit abgleichen](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/docs/CLOCK_SYNC.md)
- [Entitäten am Hauptgerät](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/docs/ENTITY_ORGANIZATION.md)
- [Versions- und Upgradehinweise](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/RELEASE_NOTES.md)
- [English overview](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/README.en.md)
- [Entwicklung – Englisch](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/CONTRIBUTING.md)

Unabhängiges Projekt ohne Verbindung zum Gerätehersteller.
Eigener Code: [MIT-Lizenz](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/LICENSE).
Protokollquellen, CC-BY-4.0-Zuordnung und Markenhinweise:
[Quellen und Rechte](https://github.com/DNier/proxon-hesp-homeassistant/blob/main/NOTICE.md).
