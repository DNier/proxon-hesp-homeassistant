# Entitäten am Hauptgerät

Home Assistant ordnet die Werte auf der Geräteseite nach ihrem Verwendungszweck.
In den Entitätseinstellungen kannst du zusätzliche Anzeigen für deine Anlage
aktivieren.

| Kategorie | Entitäten | Bei Neueinrichtung |
|---|---|---|
| Gerätewerte | Betriebsart, angeforderte Luftstufe, Raum- und Solltemperatur, Zu-/Ab-/Fort-/Frischlufttemperatur, Verdichter läuft, Bypass und Intensivlüftung | Aktiviert |
| Diagnose | Filterrestlaufzeit, Betriebsstunden, Aufnahmestatus, Ereignisaufnahmestatus und Aufnahmeaktionen | Aktiviert |
| Optionale Diagnose | Interne Temperaturen, Drehzahlen, Verdichter-Stellgröße, Gerätezeit und -datum, Regler-Luftstufe, Lüfterkennlinien und -ansteuerung, Leistungsgrenzen sowie konfigurierte Kühl- und Wärmepumpen-Schwellen | Deaktiviert |
| Optionale Diagnose | BDE-Betriebsanzeige, MV-Heizen/Kühlen, MV-Abtau, experimentelle Statusbits, Rohwerte, Gateway-Verbindung und letzter gültiger Empfang | Deaktiviert |
| Konfiguration | Schaltfläche **Gerätezeit abgleichen** | Entität deaktiviert |
| Konfiguration | Schalter **Sommer-/Winterzeit automatisch abgleichen** | Entität aktiviert, Schalter aus |

**Verdichter läuft** erhält seine Drehzahldaten auch bei deaktivierter
Drehzahlanzeige. **Ereignisaufnahme** zeigt den Aufnahmestatus an. Die
[automatische Aufzeichnung](DIAGNOSTICS.md#automatische-ereignisaufnahmen)
aktivierst du bei Bedarf am Integrationseintrag.
Die [BDE-Betriebsanzeige (Englisch)](BDE_DISPLAY_EVIDENCE.md)
und die Ventilanzeigen stehen nur in den jeweils dokumentierten Situationen zur
Verfügung. [Gerätezeit abgleichen](CLOCK_SYNC.md) erklärt, wann die Schaltfläche
und der Schalter die Uhr korrigieren.

Der HA-Gerätebereich verwendet feste Kategorien. Für eigene Gruppen kannst du
ein Dashboard anlegen. [Optionale Heizräume](ROOMS.md) erscheinen als virtuelle
Geräte.

## Bestehende Installationen

Behalte beim Update den vorhandenen Integrationseintrag. Bei den meisten
Entitäten bleiben IDs, eigene Namen und Aktivierung erhalten. Die
[Upgradehinweise](GETTING_STARTED.md#updates-und-bestehende-installationen)
beschreiben die Ausnahmen bei ersetzten Rohsensoren.

Prüfe vor dem Deaktivieren einer Entität, ob ein Dashboard, eine Automation
oder ein Verlauf sie verwendet. Bei den optionalen Hex-Diagnosesensoren für
`118000/01F8`, `118000/03B6`, `118007/0191`, `224000/0208` und
`224000/006C` erneuert auch unveränderter Empfang das Zeitstempelattribut.
Verwende für eine Zustandsbenachrichtigung den Wechsel des Hex-Werts.
