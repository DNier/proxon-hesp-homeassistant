# Herstellerangaben und unabhängige Beobachtungen

## Quellen und Geltungsbereich

Die folgenden Angaben fassen eine Antwort von Zimmermann an das Projekt zusammen.
Sie beziehen sich auf die angefragte P-Serie der [Referenzgeneration](COMPATIBILITY.md).
Die Reichweite der Antwort ist auf diese Gerätegeneration begrenzt.

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

Der optionale [Gerätezeitabgleich](CLOCK_SYNC.md) korrigiert die Geräteuhr bei
laufender Verbindung. Nach einer vollständigen Spannungsunterbrechung kann die
Geräteuhr erneut zurückgesetzt werden. Beim Start löst Home Assistant keinen
Abgleich aus.

<a name="eigene-beobachtung-betrieb-ohne-bde-am-23-september-2026"></a>

## Unterstützter Betrieb mit BDE

Bei der Referenzanlage lieferte der PTC-X2–Hauptplatine-X5-Abgriff mit
angeschlossenem BDE in 60 Sekunden 1.200 gültige Telegramme mit 98 verschiedenen
Kombinationen aus Kennung, Datenpunkt und Länge. Bei einem passiven Vergleich
ohne BDE blieb die TCP-Verbindung zum Gateway offen, aber der Abgriff lieferte
keine Daten. Der Empfang mit BDE ließ sich wiederherstellen.

Der Vergleich stützt die Bedeutung des BDE für den Empfang. BDE-Trennung und
Neustart änderten gleichzeitig zwei Bedingungen. Die genaue Rolle des BDE
beim Sendetakt sowie die Steuerbarkeit ohne BDE bleiben offen. Die Installation
setzt ein angeschlossenes BDE voraus.
