# Herstellerangaben und unabhängige Beobachtungen

## Quellen und Geltungsbereich

Die folgenden Herstellerangaben fassen eine private Antwort von Zimmermann
zusammen, die dem Projekt am **29. September 2026** mitgeteilt wurde. Das ist das
Datum der Mitteilung an das Projekt, nicht ein belegtes Versanddatum des Herstellers.
Die Korrespondenz wird nicht vollständig veröffentlicht. Sie bezieht sich auf die
angefragte P-Serie der [Referenzgeneration](COMPATIBILITY.md), nicht pauschal auf
alle heutigen oder zukünftigen PROXON-Produkte.

## Aussagen des Herstellers

- **Modbus:** Die angefragte P-Serie hat keine Modbus-Schnittstelle. Eine
  Nachrüstung ist für diese Gerätegeneration nicht möglich. Das seinerzeit
  angebotene Modbus-Modul war ausschließlich für die FWT-Serie 1.0 vorgesehen;
  das dafür erforderliche Bussystem ist bei dieser P-Serie nicht vorhanden.
- **HESP:** Externe Auswertung der internen Kommunikation ist vom Hersteller
  weder vorgesehen noch unterstützt. Protokollbeschreibungen, Datenpunktlisten
  und Angaben zu internen Statuswörtern oder Telegrammen werden nicht bereitgestellt.
- **T300:** Die Kommunikationsschnittstelle dient innerhalb der Systemarchitektur
  unter anderem der direkten Anbindung an entsprechende FWT-Systeme. Externe
  Auslesung durch Drittsysteme wird vom Hersteller nicht durchgeführt und kann
  von ihm nicht bewertet oder freigegeben werden. Daraus folgt keine bestätigte
  T300-Anbindung für diese Integration.
- **Öffentliche Modbus-Parameter:** Freigegebene Parameter stehen auf der
  [Hersteller-Downloadseite](https://www.zimmermann-lueftung.de/downloads/).
  Sie sind keine HESP-Datenpunktreferenz und kein Nachweis einer Modbus-Schnittstelle
  an der angefragten P-Serie.
- **Datum und Uhrzeit:** Das Zurücksetzen nach vollständiger Spannungsunterbrechung
  ist bei der angefragten P-Serie normal. Die Anlage ist für dauerhaften Betrieb
  und kontinuierlichen Luftaustausch ausgelegt. Nach einer Unterbrechung sollen
  Datum und Uhrzeit kontrolliert und gegebenenfalls neu eingestellt werden.
- **Logo:** Eine Freigabe zur Verwendung des PROXON-Logos in GitHub, Home Assistant,
  HACS oder vergleichbaren öffentlichen Projekten wurde nicht erteilt. Die Antwort
  enthält keine ausdrückliche Entfernungsaufforderung. Daraus wird weder eine
  Nutzungserlaubnis noch eine rechtliche Bewertung der konkreten Nutzung abgeleitet.
  Siehe [Rechtehinweise](../NOTICE.md#logo).

## Bedeutung für die Integration

PROXON HESP bleibt ein unabhängig entwickeltes Community-Projekt ohne Unterstützung
oder Freigabe durch den Hersteller. Die implementierten Zuordnungen beruhen auf
öffentlich zugänglicher Recherche, Mitschnitten und Vergleichen mit der Anzeige;
sie sind keine vom Hersteller bestätigte Protokollspezifikation.

Ein transparentes RS485-zu-TCP-Gateway transportiert vorhandene HESP-Daten. Es
rüstet keine Modbus-Schnittstelle nach. Die Integration ersetzt das BDE nicht und
benötigt für ihren passiven Empfang den bestehenden Busverkehr. Für Modell,
Firmware, T300, PTC- und Ventilzustände gelten weiterhin die jeweils dokumentierten
[Validierungsgrenzen](DATA_POINTS.md).

Der [manuelle Gerätezeitabgleich](CLOCK_SYNC.md) korrigiert die aktuelle Einstellung;
er verhindert keinen erneuten Zeitverlust nach einer Spannungsunterbrechung.
Es gibt keine automatische Synchronisation beim Start. Zusätzliche Stromunterbrechungen
allein zur Protokollsuche sind nicht Teil der normalen Einrichtung.

## Eigene Beobachtung: Betrieb ohne BDE am 23. September 2026

Dies ist ein Ergebnisbericht eines abgeschlossenen Versuchs an der Referenzanlage,
keine Anleitung zum Betrieb ohne BDE und keine Herstellerfreigabe.

| Abschnitt | Beobachtung |
|---|---|
| Mit BDE | 60 Sekunden passive Aufnahme am PTC-X2–Hauptplatine-X5-Abgriff: 1.200 gültige Telegramme, 98 Kennung/Datenpunkt/Längen-Kombinationen, keine unzugeordneten Bytes. Eco Sommer, Auto am BDE, angeforderte und gemeldete Luftstufe 1, Verdichter 0 rpm. |
| Nach Trennen des BDE und Neustart | Die TCP-Verbindung zum Gateway war offen, es wurden keine Datenbytes empfangen. Die gesamte Aufnahme dauerte etwa 82 Sekunden und begann bereits vor dem Einschalten; das ist nicht die gemessene Anlagenlaufzeit. Der Betreiber meldete laufende Lüfter und rotes Blinken. Ort und Fehlerbedeutung des Blinkens wurden nicht bestimmt. |
| Abbruch | Wegen fehlender Rückmeldungen und des gemeldeten Blinkens beendet. Keine aktiven Abfragen und kein Steuerbefehl gesendet. |
| Wiederherstellung | BDE wieder angeschlossen, Anlage neu gestartet, HA-Integration wieder aktiviert. Aktuelle BDE-/Reglerwerte kamen zurück. Der Betreiber bestätigte verschwundenes Blinken und Auto-Auswahl; die zurückgesetzte Gerätezeit wurde von ihm korrigiert. |

Das Ergebnis passt zur Hypothese, dass das BDE die zyklische Kommunikation
anstößt. Es beweist weder die genaue Rolle aller Teilnehmer noch die Ursache des
Blinkens. Neustart und BDE-Trennung änderten zwei Bedingungen zugleich. Eine
TCP-Verbindung belegt keine fehlerfreie elektrische Buskommunikation; laufende
Lüfter belegen keinen sicheren Ersatzbetrieb.

**Steuerbarkeit ohne BDE wurde weder bestätigt noch widerlegt**, da kein Befehl
gesendet wurde. Der unterstützte Integrationsbetrieb bleibt mit angeschlossenem
BDE. Weitere Kontrollversuche sind durch diesen Bericht nicht freigegeben.
