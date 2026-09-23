# Hardware und Kompatibilität

## Bestätigtes Profil

Das Profil `lt_zim_16_observed` beruht auf passiven Mitschnitten und
BDE-Displayvergleichen mit dieser Hardware:

| Bestandteil | Beobachtete Ausführung |
|---|---|
| Hauptplatine | Hermes LT-ZIM V1.6 |
| PTC-Platine | PTC-Modul 4× V1.2 |
| Bedienteil | BDE Comfort, angezeigte Version V03.6.07A0 |
| Verbindung | Transparentes RS485-zu-TCP-Gateway |
| Serielle Einstellungen | 19200 Baud, 8N1 |

Diese Angaben beschreiben die Referenzkonfiguration. Sie sind keine automatisch
erkannten Geräteattribute. Ein gleicher Produktname allein belegt keine
Kompatibilität. Verfügbare Messwerte hängen auch von Ausstattung und Busverkehr ab.

## Busabschnitt

In der geprüften Konfiguration ist das BDE mit PTC-X1 verbunden. Der passive
HESP-Abgriff liegt zwischen **PTC-X2 und Hauptplatine-X5**. Dieser Abschnitt ist
vom direkten BDE-PTC-Anschluss zu unterscheiden. Ergebnisse eines Abschnitts
belegen nicht automatisch Protokoll und elektrische Eigenschaften eines anderen.

Steckerbezeichnungen unterscheiden sich je nach Revision. Belegungen nicht aus
Kabelfarben, Steckerbezeichnungen oder Fotos anderer Anlagen ableiten.
Diese Dokumentation ist keine Verdrahtungsanleitung. Das Gateway muss rohe
serielle Daten weiterreichen und darf sie nicht in Modbus umwandeln.

## Grenzen

- Unterstützt wird die Lüftungs-/Heizungssteuerung der P-Serie, keine T300-
  Warmwassertelemetrie und keine FWT-/Modbus-Anlage.
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
