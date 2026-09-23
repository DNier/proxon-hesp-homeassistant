# Versionshinweise

Die Abschnitte beschreiben jeweils den Stand bei Veröffentlichung. Für einen
GitHub-Release wird ausschließlich der Abschnitt seiner Version verwendet.

## 0.12.0b4 — Übersichtliche Gerätediagnose und deutsche Dokumentation (Beta)

- Interne Temperaturen, Lüfter-/Verdichterdrehzahlen und Filterrestlaufzeit der
  Diagnose zuordnen. Interne Temperaturen, Drehzahlen und rohen Kalender bei
  Neueinrichtungen zunächst deaktivieren; weiterhin einzeln aktivierbar.
- Deutsche Drehzahlbezeichnungen vereinheitlichen. Bestehende Entitäts-IDs,
  eigene Namen und Aktivierungseinstellungen bleiben erhalten. Der Sensor
  „Verdichter läuft“ arbeitet auch bei deaktivierter Drehzahlentität weiter.
- README, Nutzeranleitungen und Versionshinweise auf Deutsch vereinheitlichen.
  Englischen Einstieg ergänzen und englische Entwicklerreferenzen klar trennen.
- Ergebnis der Suche nach Geräte-/Firmwarekennungen dokumentieren. Es wird keine
  unbestätigte automatische Geräteerkennung ergänzt.

### Update und Prüfung

Vor dem Update ein HA-Backup erstellen und benötigte Mitschnitte exportieren.
In HACS **0.12.0b4** auswählen, installieren und Home Assistant neu starten.
Bestehende Einträge und Räume behalten. Bisher aktive Detailwerte bleiben aktiv;
bei Bedarf nach Prüfung ihrer Verwendung manuell deaktivieren.

Beim Wechsel von Versionen vor 0.12.0b3 gilt weiterhin die Migration auf
Konfigurationsformat 2; ein Zurückwechseln benötigt das Backup vor der Migration.

260 automatisierte Tests einschließlich Update ab 0.8.0 bestanden; Ruff-Code-
und Formatprüfung ebenfalls. Die praktische Raumabnahme bleibt offen.
Dies ist eine Vorabversion; **0.11.0 bleibt die stabile Version**.

## 0.12.0b3 — Native Einrichtung von Heizräumen (Beta)

- Jeder Heizraum erscheint als nativer HA-Untereintrag mit eigenen Aktionen zum
  Hinzufügen, Konfigurieren und Löschen. Aufnahmeoptionen bleiben getrennt.
- Die Einrichtung besteht aus drei Schritten: Raum/Heizelemente, optionale
  Verknüpfungen und Messwerteinstellungen. Erst der letzte Schritt speichert.
- Vorhandene Beta-Räume werden automatisch migriert. Geräte-/Entitäts-IDs,
  Namen, Bereiche, Quellenverknüpfungen, deaktivierte Entitäten und Aufnahmeoptionen bleiben erhalten.
- Raumänderungen bleiben lesend und unabhängig von Gateway-Verbindung und
  laufenden Aufnahmen. Bestehende Thermostate schalten weiterhin selbst.

### Update

Vorher ein HA-Backup erstellen. **0.12.0b3** über HACS installieren und HA neu
starten. Benötigte Mitschnitte vorher exportieren; sie liegen nur im Arbeitsspeicher.
Vorhandene Räume müssen nicht neu angelegt werden.

Neue Räume unter **Einstellungen → Geräte & Dienste → PROXON HESP → Heizraum
hinzufügen** anlegen. Bestehende Räume direkt am Untereintrag konfigurieren.
**Konfigurieren** am übergeordneten Eintrag enthält nur noch Aufnahmeoptionen.

Das gespeicherte Konfigurationsformat steigt von Version 1 auf 2. Ältere
Integrationsversionen können es nicht laden; ein Zurückwechseln erfordert das Backup vor der Migration.

260 automatisierte Tests bestanden, einschließlich Registry-Migration,
Hinzufügen/Bearbeiten/Löschen, Abbruch und Erhalt von Aufnahmen.
Dies bleibt eine Vorabversion; **0.11.0 bleibt die stabile Version**.

## 0.12.0b2 — Bereichszuordnung der Heizräume korrigiert (Beta)

- Den ausgewählten HA-Bereich auch dann zuweisen, wenn HA das virtuelle Gerät
  bereits vor der Synchronisierung der Raumoptionen registriert.
- Gespeicherte Bereiche bei bisher nicht zugeordneten Geräten wiederherstellen.
  Abweichende manuelle Zuordnungen bleiben erhalten. Zum dauerhaften Entfernen
  auch die Bereichsauswahl in der Raumkonfiguration löschen.
- Raumidentitäten, verknüpfte Quellgeräte, Thermostatregelung und Aufnahmen erhalten.

### Update

**0.12.0b2** über HACS installieren und HA neu starten. Benötigte Mitschnitte
zuvor exportieren. Räume müssen nicht neu angelegt werden; gespeicherte
Bereichsauswahlen werden automatisch angewendet.

Zwei Regressionstests prüfen die Registrierungsreihenfolge und Wiederherstellung.
Dies bleibt eine Vorabversion; **0.11.0 bleibt die stabile Version**.

## 0.12.0b1 — Heizräume und optionaler Gerätezeitabgleich (Beta)

Vorabversion für erste Installationstests. **0.11.0 bleibt die stabile Version.**

### Heizräume

- Optionale Räume über die Integrationsoptionen einrichten, jeweils mit virtuellem
  HA-Gerät und optionaler Bereichszuordnung.
- Vorhandene Schalter, Leistungssensoren, Thermostate und Temperatur-/Feuchtesensoren
  beliebiger Hersteller verknüpfen. Mehrere Heizelemente pro Raum sind möglich.
- Erreichbarkeit, Schaltzustand, vollständige Heizleistung und elektrischen
  Heizbetrieb oberhalb einer einstellbaren Schwelle anzeigen. Fehlende, ungültige,
  wiederhergestellte oder veraltete Messwerte bleiben unbekannt, niemals pauschal 0 W.
- Bestehende Thermostate regeln weiter; die Überwachung schaltet nichts.
  Raumänderungen erhalten Quellgeräte und laufende Aufnahmen. Umbenannte
  registrierte Quellen behalten ihre Verknüpfungen.

### Gerätezeit

- Optionalen lokalen Kalendersensor und zunächst deaktivierte Schaltfläche für
  manuellen Zeitabgleich in der HA-Zeitzone ergänzen. Die einzige HESP-Schreibaktion
  sendet ein Kalendertelegramm und wartet auf Rückmeldung der Steuerung.
  Keine automatische Wiederholung und kein Zeitabgleich beim Start.
- An einer LT-ZIM V1.6 / PTC 4× V1.2 / BDE Comfort am Display bestätigt.
  Andere Revisionen und Speicherung nach Stromausfall sind unbestätigt.
  Die Kalenderkorrektur kann die aktive Phase eines bestehenden Zeitprogramms ändern.

### Kompatibilität und Installation

Benötigt **HA ab 2026.9**. Bestehende Identitäten, Einstellungen und Thermostatregelung
bleiben erhalten. Neue Räume sind optional.

In HACS über **Erneut herunterladen** die Version **0.12.0b1** wählen und
gegebenenfalls Vorabversionen zulassen. Vor HA-Neustart benötigte Mitschnitte
exportieren. In dieser Version zunächst einen Raum über **Konfigurieren →
Heizräume verwalten → Raum hinzufügen** einrichten.

Automatisiert geprüft: Raumlebenszyklus, fehlende/veraltete Werte, Quellenumbenennung,
Update ab 0.8.0 und begrenzte Kalenderschreibzugriffe. Die praktische Abnahme der
Raumüberwachung steht aus. Erreichbarkeit beweist keine zentrale Heizfreigabe;
Raumverbrauch klassifiziert weder zentralen Heiz-/Kühlbetrieb noch Abtauen.

Siehe [Heizräume](https://github.com/DNier/proxon-hesp-homeassistant/blob/v0.12.0b1/docs/ROOMS.md)
und [Zeitabgleich](https://github.com/DNier/proxon-hesp-homeassistant/blob/v0.12.0b1/docs/CLOCK_SYNC.md).
Die verlinkten Dateien zeigen den damaligen Dokumentationsstand.

## 0.11.0 — Fortlaufende Ereignisaufnahmen

- Automatischen Vorlauf bei Verdichterereignissen auf 180 Sekunden erweitern;
  Nachlauf bleibt 180 Sekunden. Speichergrenzen gelten weiterhin.
- Die vier jüngsten Ereignisaufnahmen behalten, beim nächsten Fenster die älteste
  ersetzen und Aufnahme-/Ersetzungszähler anzeigen. Vorhandene Löschaktion löscht
  alle Ereignisse; manuelle Mitschnitte bleiben unabhängig.
- Grenze je Aufnahme auf 16.384 Blöcke, Vorlaufpuffer auf 512 KiB / 8.192 Blöcke
  erhöhen, damit kleine TCP-Blöcke besser aufgenommen werden können.
- Frühere Aufnahmen mit exportieren. Inventarisierung, Wiedergabe und Vergleich
  unterstützen `--event --event-index 0` für das älteste Fenster;
  `--event` allein wählt weiterhin das jüngste.
- Alle 60 Entitätsidentitäten und Einstellungen erhalten. Rotation klassifiziert
  weiterhin keinen Heiz-/Kühl-/Abtau- oder PTC-Zustand.

### Update und Prüfung

0.11.0 über HACS installieren, bestehenden Eintrag behalten und HA neu starten.
Benötigte Mitschnitte vorher herunterladen. Die automatische Aufnahmeoption
bleibt erhalten; gegebenenfalls unter **Einstellungen → Geräte & Dienste →
PROXON HESP → Konfigurieren** aktivieren. Nach den Übergängen Diagnosedaten
herunterladen; Löschen zwischen Ereignissen ist nicht mehr nötig.

197 Tests sowie Ruff-Code- und Formatprüfung bestanden. Geprüft wurden Update
ab 0.8.0, Ersetzen alter Fenster, fortlaufender Vorlauf, kleine TCP-Blöcke,
unabhängige manuelle Aufnahmen und Offline-Auswahl. Praktische Geräteabnahme steht aus.

## 0.10.0 — Automatische Aufnahme von Verdichterereignissen

- Standardmäßig aktiven Sensor für Verdichterrotation aus gültiger Drehzahl
  ergänzen: über 0 rpm ein, bei 0 rpm aus. Fehlende, veraltete oder getrennte
  Telemetrie bleibt nicht verfügbar; ungültige Telegramme aktualisieren nichts.
- Optionale passive Ereignisaufnahme mit bis zu 60 Sekunden Vorlauf und
  180 Sekunden Nachlauf bei frischem Start-/Stoppübergang ergänzen.
  Erste Aufnahme bis zum ausdrücklichen Löschen behalten; Status und
  Lösch-/Bereitschaftsaktion bereitstellen.
- Manuelle Aufnahme unabhängig halten; separater Diagnoseexport und
  `--event` für Inventarisierung, Wiedergabe und Vergleich. Beide Aufnahmen sind begrenzt.
- 57 bestehende Identitäten und Einstellungen erhalten, drei Entitäten ergänzen (60 insgesamt).
- Keine Heizen/Kühlen/Abtauen/PTC-Klassifikation aus Rotation, Betriebsart oder Temperaturdifferenzen.

### Update und Prüfung

0.10.0 über HACS installieren, Eintrag behalten und HA neu starten. Aufnahmen
vorher exportieren. Unter **Konfigurieren** die automatische Ereignisaufnahme
aktivieren. Bei fertiger Aufnahme Diagnose herunterladen, anschließend löschen
und erneut für das nächste Ereignis bereitstellen.

185 Tests bestanden: Update ab 0.8.0, begrenzter Vor-/Nachlauf, ungültige und
fragmentierte Telegramme, Verbindungsabbruch, unabhängige manuelle Aufnahme und
Offline-Auswahl. Ruff-Code- und Formatprüfung bestanden. Offline-Wiedergabe von
23 Aufnahmen erkannte den enthaltenen Verdichterstopp. Praktische Abnahme dieser Version steht aus.

## 0.9.1 — Regler-Luftstufe im Ofenbetrieb

- Die am Display mit Stufe 3 verglichenen Statuswörter `8000921A` und `8000931A`
  erkennen. Zuvor verwarf die optionale Diagnose diese Wörter und wurde nach
  Ablauf der Aktualitätsfrist nicht verfügbar.
- Nur vollständige bestätigte Wörter zulassen. Keine PTC-, Ventil- oder Heizinterpretation ergänzen.
- Alle 57 Identitäten, Einstellungen und passiven Betrieb erhalten.

### Update und Prüfung

0.9.1 über HACS installieren, Eintrag behalten und HA neu starten. Mitschnitte
vorher exportieren. 174 Tests bestanden, darunter Fragmentierung an jeder
Streamposition, Ablehnung unbekannter Wörter, HA-Aktualisierung und bestehende
Upgrade-/Lebenszyklusprüfungen. Ruff-Code- und Formatprüfung bestanden.
Offline-Wiedergabe erkennt beide neuen Wörter; andere unbekannte bleiben abgelehnt.

## 0.9.0 — Aufnahme- und Verbindungsdiagnose

- Aktiven Aufnahmestatus mit tatsächlicher Dauer, Start/Stopp, Größe und getrennten
  Abschlussgründen für Zeit-, Byte-, Blocklimit und Verbindungsabbruch ergänzen.
- Dauer auf 30–600 Sekunden einstellbar machen (Standard 120). Änderungen gelten
  für die nächste Aufnahme ohne Neuladen, Verbindungswechsel oder Datenverlust.
- Optionale TCP-Verbindungsdiagnose und Zeitpunkt des letzten gültigen unterstützten Werts ergänzen.
- Exportformat 2 mit tatsächlicher Dauer, Stoppzeit, Version und Profil ergänzen.
  Blockformat bleibt gleich; alte Exporte bleiben offline auswertbar.
- 54 bisherige Identitäten und Einstellungen erhalten, drei Diagnosen ergänzen.
  Aufnahme bleibt passiv und auf 1 MiB / 4.096 Blöcke begrenzt.

### Update und Prüfung

Mitschnitte vorher herunterladen, 0.9.0 über HACS installieren und HA neu starten.
Eintrag behalten. Ohne Änderung gilt weiterhin 120 Sekunden.

170 Tests bestanden, darunter Update ab 0.8.0, Timerabschluss ohne Busverkehr,
Erhalt von Optionen und Ressourcenfreigabe. Ruff-Code- und Formatprüfung bestanden.
Simulierte Prüfungen belegen keine Kompatibilität mit jeder Hardwarevariante.

## 0.8.0 — Lesende Telemetrie und passive Diagnose

Diese Version entfernt die experimentellen Solltemperatur-Schreibaktionen.
Die Integration empfängt bestehenden Busverkehr ohne HESP-Abfragen oder Steuerbefehle.

- Alle 54 Sensor-, Binärsensor- und Aufnahmeentitäten mit Identitäten,
  Nutzereinstellungen und bisheriger Dekodierung erhalten.
- Passives Starten, Stoppen und Löschen von Aufnahmen sowie gewöhnliche Diagnose erhalten.
- Experimentellen Sender, Vorbereitungs-/Bestätigungszustand und spezielle Schreibtest-Diagnose entfernen.

### Update von 0.7.x

Benötigte Mitschnitte herunterladen, über HACS auf **0.8.0** aktualisieren und HA
neu starten. Bestehenden PROXON-Eintrag behalten; kein Neuanlegen erforderlich.

`proxon_hesp.prepare_target_temperature_test` und
`proxon_hesp.send_target_temperature_test` sind entfernt; gespeicherte Aufrufe
löschen. Der Diagnoseabschnitt `target_temperature_test` entfällt ebenfalls.
`application_bytes_sent` bleibt vorhanden und null. Diese Version enthält keine
Ersatz-Schreibaktion und keine Heizungs-/Lüftersteuerung.

### Prüfung

Zur Veröffentlichung bestanden 150 Tests sowie Ruff-Code- und Formatprüfung.
Geprüft wurden Aufnahmetasten, Wiederverbindung, Neuladen/Entladen, Identitäten,
eigene Namen, entfernte Testaktionen und das Ausbleiben von Nutzdaten-Schreibzugriffen.
Simulierte Datenströme belegen keine Kompatibilität mit jeder Hardwarevariante.
Aktuelle Entwicklungsprüfungen: [CONTRIBUTING.md (Englisch)](CONTRIBUTING.md).
