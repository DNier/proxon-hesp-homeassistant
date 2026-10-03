# Hardware und Kompatibilität

## Referenzkonfiguration: P2

Das Profil `lt_zim_16_observed` beruht auf passiven Mitschnitten und
BDE-Displayvergleichen mit dieser Hardware:

| Bestandteil | Beobachtete Ausführung |
|---|---|
| Hauptplatine | Hermes LT-ZIM V1.6 |
| PTC-Platine | PTC-Modul 4× V1.2 |
| Bedienteil | BDE Comfort, angezeigte Version V03.6.07A0 |
| Gateway | Waveshare RS232/485/422 TO POE ETH (B) |
| Verbindung | RS485, transparent über TCP |
| Serielle Einstellungen | 19200 Baud, 8N1 |

Diese Angaben beschreiben die Referenzkonfiguration. Sie sind keine automatisch
erkannten Geräteattribute. Ein gleicher Produktname allein belegt keine
Kompatibilität. Verfügbare Messwerte hängen auch von Ausstattung und Busverkehr ab.

Das Waveshare-Modell ist die eingesetzte Referenzhardware, keine Voraussetzung
der Integration. Andere Gateways müssen rohe serielle Daten unverändert über TCP
übertragen können. Eine pauschale Kompatibilität aller Waveshare-Modelle ist damit
nicht bestätigt.

## Community-getestet: FWT 2-L

Die **PROXON FWT 2-L mit LT-ZIM V1.3** ist für den unten beschriebenen lesenden
Umfang als kompatibel gemeldet. Grundlage sind ein BDE-Vergleich durch einen
Nutzer und die Offlineprüfung seines Diagnoseexports mit dem unveränderten
Decoder aus **0.12.0**. Dies ist keine Herstellerfreigabe und keine pauschale
Bestätigung aller FWT-Modelle oder Funktionen.

| Bestandteil | Gemeldete Ausführung |
|---|---|
| Anlage | PROXON FWT 2-L |
| Steuerplatine | LT-ZIM V1.3 |
| Bedienteil | BDE Comfort V03.7.9B00 |
| Gateway | Waveshare RS485 TO POE ETH (B) |
| Verbindung | Interner RS485-Bus, transparent über TCP, Port 4196 |
| Serielle Einstellungen | 19200 Baud, 8N1 |
| Integration und Profil | 0.12.0, unverändert mit `lt_zim_16_observed` |

**Mit dem BDE verglichen:** alle zehn Temperaturen, Raumtemperatur und Sollwert,
Betriebsarten Eco Sommer und Komfort, Bypass, Lüfterstufe, Zu-/Abluftdrehzahlen,
Betriebsstundenzähler und Filterrestlaufzeit. Die Bezeichnungen der internen
Temperaturen passen laut Rückmeldung ebenfalls zur FWT.

Die 120-Sekunden-Aufnahme vom 01.10.2026 enthält 2.400 prüfsummengültige
Telegramme ohne unaufgelöste Bytes. Der Produktionsdecoder liest daraus 53
unterschiedliche Leseschlüssel; zusätzliche gültige Telegramme bleiben
uninterpretiert. Die Aufnahme entstand im **Komfortbetrieb bei stehendem
Verdichter**, nach einem Wechsel von Eco Sommer. Beide Betriebsarten werden
laut Nutzer korrekt angezeigt. Im Diagnoseexport sind keine gesendeten
Anwendungsbytes verzeichnet.

**Noch nicht bestätigt:** Betrieb bei laufender Wärmepumpe, Heiz-/Kühl- und
Abtauzuordnungen, Ventilindikatoren, aktive Vorheizung sowie der Gerätezeitabgleich.
Ein Betriebsstundenzähler für eine Funktion ist kein Nachweis ihres aktuellen
Schaltzustands. Kalenderwerte sind dekodierbar, wurden aber nicht durch einen
Schreibtest geprüft.

Der Nutzer liest parallel am internen Anschluss der Steuerplatine mit.
Die Steckerbezeichnung ist unbekannt; der Anschluss wird hier ausdrücklich
nicht als X6 oder offizieller GLT-Port bezeichnet. Die P2-Belegung ist keine
Verdrahtungsvorgabe für die FWT. Eine PTC-Platinenrevision wurde nicht angegeben.

Quelle: [Community-Testbericht und Rückmeldungen, Diskussion #2](https://github.com/DNier/proxon-hesp-homeassistant/discussions/2).
Modell und Versionsangaben stammen vom Nutzer, nicht aus automatischer Erkennung.

## Herstellerangaben für diese Generation

Laut der dem Projekt am 29.09.2026 mitgeteilten Herstellerantwort besitzt die
angefragte P-Serie keine Modbus-Schnittstelle und kann nicht nachgerüstet werden.
Das frühere Modul war für FWT 1.0 vorgesehen. Externe HESP-Auswertung wird nicht
unterstützt; öffentliche Modbus-Listen sind nicht auf HESP übertragbar.
Die erwähnte T300-Anbindung an FWT-Systeme erweitert den Integrationsumfang nicht.
[Quelle, Geltungsbereich und Einzelheiten](MANUFACTURER_INFORMATION.md).

Das BDE bleibt im unterstützten Betrieb angeschlossen. Im dokumentierten Versuch
ohne BDE wurden trotz offener TCP-Verbindung keine Bytes empfangen; nach dem
Wiederanschließen kehrte der Verkehr zurück. Ein Steuerungstest fand nicht statt.

## Busabschnitt

In der P2-Referenzkonfiguration ist das BDE mit PTC-X1 verbunden. Der passive
HESP-Abgriff liegt zwischen **PTC-X2 und Hauptplatine-X5**. Dieser Abschnitt ist
vom direkten BDE-PTC-Anschluss zu unterscheiden. Ergebnisse eines Abschnitts
belegen nicht automatisch Protokoll und elektrische Eigenschaften eines anderen.

Steckerbezeichnungen unterscheiden sich je nach Revision. Belegungen nicht aus
Kabelfarben, Steckerbezeichnungen oder Fotos anderer Anlagen ableiten.
Diese Dokumentation ist keine Verdrahtungsanleitung. Das Gateway muss rohe
serielle Daten weiterreichen und darf sie nicht in Modbus umwandeln.

## Grenzen

- Die Integration liest HESP auf der P2-Referenzkonfiguration und der oben
  beschriebenen Community-getesteten FWT 2-L. Sie implementiert weder Modbus
  noch T300-Warmwassertelemetrie. Andere FWT-Generationen sind nicht bestätigt.
- Beobachteter Kühlbetrieb belegt keine Kühlfunktion jeder Anlage.
- Firmware von Steuerung, BDE und weiteren Komponenten ist getrennt zu betrachten.
- Das Profil wird ausdrücklich ausgewählt. Modell, Seriennummer und Firmware
  werden nicht aus der Gateway-Adresse abgeleitet.
- Bestätigte und offene Zuordnungen stehen in der [Datenpunktreferenz (Englisch)](DATA_POINTS.md).

## Andere Konfiguration melden

Platinenrevisionen, BDE-Version, Ausstattung, Integrationsversion und die mit dem
Display verglichenen Werte angeben. Den beobachteten Busabschnitt beschreiben.
Keine Seriennummern, privaten Serviceunterlagen, Adressen oder Zugangsdaten
öffentlich einstellen. Eine kurze Beschreibung und geprüfte Diagnosedaten genügen
zunächst; vollständige Aufnahmen sind nicht grundsätzlich erforderlich.

## Stand der Geräteerkennung

In 32 untersuchten Aufnahmen wurden 95.885 prüfsummengültige Telegramme mit
100 Kombinationen aus Telegrammkennung, Datenpunkt und Nutzdatenlänge gefunden.
Die Suche in einzelnen gültigen Nutzdaten nach der angezeigten BDE-Bezeichnung,
Version sowie Hersteller-/Platinennamen ergab keine Treffer in ASCII oder UTF-16
(beide Byte-Reihenfolgen). Drei mögliche binäre Anordnungen der Versionsbestandteile
blieben ebenfalls ohne Treffer.

Das ist eine begrenzte Mustersuche, keine vollständige Entschlüsselung unbekannter
Daten. Über mehrere Telegramme verteilte Angaben oder ausschließlich beim Start
übertragene Informationen sind damit nicht ausgeschlossen. Beim Öffnen der
Systeminformationen erschienen im untersuchten Mitschnitt keine neuen Kennungen.
Die BDE-Version beschreibt das Bedienteil, nicht zwingend die Gesamtanlage.

Eine automatische Modell-, Seriennummern- oder Firmwareerkennung ist daher nicht
implementiert. Die Referenzversion wird nicht als vermeintlich erkannte Firmware
in die HA-Geräteinformationen eingetragen.
