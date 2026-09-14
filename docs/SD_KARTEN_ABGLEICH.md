# BDE-SD-Metadaten und Busdaten

Stand: 14.09.2026. Offline-Auswertung der vom Betreiber bereitgestellten
BDE-SD-Karte sowie der Busaufzeichnungen 1–18. Der historische SD-Vergleich
unten entstand zunächst mit den Aufzeichnungen 13–18.
Originaldateien, lokale Sicherung und Auswertung bleiben im ignorierten `tmp/`.
Die Dateiauswertung und Integration arbeiten rein lesend. Die separate
Bedienung des Service-Menüs am BDE ist am Ende dieses Dokuments festgehalten.

## Quellen und Abdeckung

Die 26 Anlagendateien wurden mit SHA-256 gegen die lokale Kopie geprüft.
20 Trace-CSV-Dateien enthalten 110.140 Datenzeilen; 704 Zeilen mit ungültigen
Datumswerten wurden vom Wertevergleich ausgeschlossen. Die verbleibenden
109.436 Zeitstempel sind syntaktisch gültig, nicht extern zeitlich verifiziert.
Der jüngste lautet 07.09.2024 19:14:49. Die Daten stammen überwiegend aus
Dezember 2015, also aus der Zeit vor der dokumentierten Kühlnachrüstung 2026.

Drei Event-XML-Dateien enthalten identische Metadatenlisten: 76 Einträge,
35 unterschiedliche Kombinationen aus Gruppe, Parameter-ID und Name.
Die Values-Elemente sind leer. Das ist kein vollständiger Parametersatz.

Die sechs Businventare umfassen 13.319 strukturell und per Prüfsumme erfasste
Frames bzw. 194.314 Bytes, ohne verbleibende ungeparste Bytes. Diese Abdeckung
belegt die Erfassung der Frames, nicht ihre semantische Interpretation.
SD- und Busaufnahmen sind zeitlich getrennt: Es handelt sich um den Vergleich
von Namen, Datentypen und Wertebereichen, nicht um synchronisierte Messpaare.

## Zuordnungen und Grenzen

| SD-Metadatum | Kandidat im heutigen Bus | Befund |
| --- | --- | --- |
| AktVentilatorSpannung [928], „Aktueller Stellwert der Ventilatorspannung“, mV | Controller 0x00D7, zwei float32 LE | SD enthält u.a. 2500, 5200, 7000 und 10000. Bus enthält diese Werte sowie 4000, darunter das Paar 10000/7000. Starker Hinweis auf Stellspannung in mV; kein zeitgleicher Nachweis und keine elektrische Messung. |
| DrehzahlZuAbluft [911], Zu(0)/Ab(1), rpm | Controller 0x00C9 | SD beschreibt Drehzahl ausdrücklich getrennt von Stellspannung. Bestehende Drehzahlzuordnung wird dadurch gestützt. |
| ProxonLTStatusword [417], System statusword32 | Controller 0x0208 | Gemeinsame Werte 0x8000100a, 0x8000101a und 0x80001022. Bus zusätzlich 0x80001012 und 0x80001522. Kandidat für dasselbe Statuskonzept; XML enthält keine Bitdefinitionen. |
| BypassZustand [352] | Controller 0x0160 | ID identisch, SD und Bus jeweils 0/1. XML nennt „Aktuelle Stellung der Bypassklappe“, erklärt aber keine mechanische Rückmeldung oder Endschalter. Bestehender Schaltzustand bleibt konservativ benannt. |
| SchieberPosition [360] | Controller 0x0168 | ID identisch. SD-Werte 0/2/4, Bus in Aufzeichnungen 13–18 konstant 2. Bedeutung der einzelnen Werte nicht belegt; Rohsensor bleibt erhalten. |
| BDE_StatusWord [415] | Panel 0x01F8 | SD enthält 0 und 0x800; Bus 13–18 enthält 0 und 0x40. Namen und Bitfeldstruktur allein reichen nicht für eine gesicherte Gleichsetzung. |
| BSTD_FL/RL/NL/IL [720–723], Stunden | Controller 0x02D0–0x02D3 | IDs stimmen überein. XML bestätigt Betriebsstundenzähler und Einheit h; ausgeschriebene Bedeutung der Abkürzungen nicht enthalten. |
| BSTD_WP_H/K [724/725], BSTD_LT [727], BSTD_Vorwaerme [729] | Controller 0x02D4/0x02D5/0x02D7/0x02D9 | IDs, explizite Namen und Einheit h stützen bestehende Zählerzuordnungen. |

Die XML-IDs dürfen nicht allgemein als Bus-Adressen verwendet werden:
TRaumsoll ist dort 124 (0x007C), im beobachteten Panel-Bus 0x0227.
Auch Betriebsart (401 gegenüber 0x020A), Drehzahl (911 gegenüber 0x00C9)
und Stellspannung (928 gegenüber 0x00D7) unterscheiden sich.

## Lüftungsstufe ist keine feste Stellspannung

Der Kandidat `(Statuswort & 0x38) >> 3` passt zu den manuell belegten
Stufen 1–4 in Busaufnahme 16 und bleibt bei Kühlung nach Intensivende auf 4
(Aufnahme 18), während die Panel-Anforderung auf 3 zurückgeht.

Die historische SD-Auswertung zeigt zusätzlich:

- 49.543 Zeilen: Status 0x8000131a, Stufenmuster 3, Stellwerte 5200/5200 mV.
- 3.712 Zeilen: derselbe Status, Stellwerte 2000/5200 mV.
- 260 Zeilen: Status 0x8000135a, weiterhin Stufenmuster 3, Stellwerte 7000/7000 mV.
- 16 Zeilen: derselbe Status 0x8000135a, Stellwerte 2000/7000 mV.

Damit darf weder aus der Stufe eine feste Spannung noch aus einer Spannung
eine eindeutige Stufe abgeleitet werden. Ursache der Abweichungen und Bedeutung
der weiteren Statusbits sind nicht bewiesen. Die vorhandene angeforderte
Luftstufe bleibt als eigene Entität mit unveränderter ID erhalten.

## Begrenzte Diagnose-Erweiterung in 0.6.0

Die zusätzliche Offline-Prüfung aller 18 Mitschnitte enthält acht verschiedene
Controller-Statuswörter bei `0x0208` (4 Bytes, uint32 LE):

Das vollständige Inventar umfasst 35.829 Frames und 522.226 Bytes; keine Bytes
bleiben strukturell ungeparst. Das Inventar erfasst auch semantisch unbekannte
Frames und ist daher umfangreicher als die produktive Sensor-Decodierung.

| Statuswort | Ausgegebene Stufe | Erster Mitschnitt |
| --- | ---: | ---: |
| 0x8000101A | 3 | 1 |
| 0x8000100A | 1 | 5 |
| 0x80001422 | 4 | 7 |
| 0x80001522 | 4 | 7 |
| 0x80001122 | 4 | 9 |
| 0x8000131A | 3 | 10 |
| 0x80001022 | 4 | 14 |
| 0x80001012 | 2 | 16 |

Die Zuordnung entspricht `(Wort & 0x38) >> 3`, wird im Decoder aber ausdrücklich
auf diese acht vollständigen Wörter beschränkt. Das verhindert, dass unbekannte
Sonder-/Fehlerzustände mit zufällig passendem Stufenmuster als bekannte Stufe
ausgegeben werden. Auch historische SD-Wörter wie 0x8000931A und 0x8000135A
werden nicht allein aufgrund der Maske übernommen.

Aufnahme 16 mit manuellen Stufen 1–4 und Aufnahme 18 mit automatischem
Intensivende bei weiterlaufender Kühlung sind die wesentlichen BDE-Gegenproben.
Aufnahme 18: Panel-Anforderung 4 → 3, Intensivbit Ein → Aus, Controllerwort
weiterhin 0x80001522 (Stufe 4), BDE-Anzeige weiterhin Stufe 4.
Die übrigen Mitschnitte liefern zusätzliche konsistente Werte; sie ersetzen
keine Prüfung aller möglichen Sonderzustände.

Bei `0x00D7` wurden die Paare 2500/2500, 4000/4000, 5200/5200,
10000/10000 und 10000/7000 erfasst. Slot 0 wird vorläufig als Zuluft-Stellwert,
Slot 1 als Abluft-Stellwert geführt, entsprechend der Lüfterkanalreihenfolge.
Die SD-Metadaten stützen das Stellwertkonzept; die physikalische Einheit bleibt
offen. Keine Gleichsetzung mit gemessener Spannung, Luftmenge oder Drehzahl.

Die drei Sensoren „Luftstufe laut Steuerung“, „Zuluft-Stellwert (roh)“ und
„Abluft-Stellwert (roh)“ sind standardmäßig deaktivierte Diagnose-Entitäten,
ohne Statistikklasse. Stellwerte bleiben ohne Einheit. Endliche Werte von
0–10000 werden einzeln akzeptiert (Empfangsgrenze, keine Herstellergrenze).
Ungültige Daten erneuern die Frische nicht: Ein vorheriger gültiger Wert kann
noch bis zu 30 Sekunden bestehen, danach wird der Sensor unavailable.
Verbindungsabbruch macht ihn sofort unavailable. Es gibt keine aktive Abfrage.

Prüfung am 14.09.2026: 148 Tests bestanden, Ruff-Lint/Format und
`git diff --check` erfolgreich. Alle 18 Aufzeichnungen wurden mit ihren
Original-Chunks, als Gesamtstrom und mit Chunkgrößen 1/37/127 wiedergegeben:
identische Ergebnisse, keine abgewiesenen Prüfsummen. Alle 366 Statusantworten
und 367 Stellwertpaare des vollständigen Inventars wurden erkannt.
Die HA-Tests prüfen Standard-Deaktivierung, bestehende aktivierte Einträge,
fehlende/ungültige Werte, Ablauf der Frische, Wiederherstellung und Disconnect.
Das automatische Intensivende bei weiterlaufender Kühlung ist separat geprüft.
Dies ist eine Offline- und Testumgebungsprüfung, keine Live-Installation.

## Installateur-Kennwort und Schreibzugriff

Eine Textsuche über alle 26 gesicherten Anlagendateien nach Passwort-, Kennwort-,
Installateur-, Zugang-, Servicecode- und Login-Begriffen ergab keine Treffer.
Das schließt codierte oder nicht in diesen Dateien gespeicherte Informationen
nicht aus. Es wurde weder nach gelöschten Dateien gesucht noch Firmware extrahiert.

Die offizielle Zimmermann-PROXON-FAQ nennt öffentlich das Installateur-Passwort
**2011** unter „Einstellungen“ → „Installateur“. Die Quelle beschreibt diesen
Zugang im Zusammenhang mit Notbetrieb; Notbetrieb ist keine Maßnahme dieser
Untersuchung. Der Betreiber konnte anschließend das Service-Hauptmenü öffnen;
das tatsächlich eingegebene Kennwort wurde nicht ausdrücklich bestätigt.

Quelle, abgerufen 14.09.2026:
[Zimmermann: Fehlercode am Hauptbedienteil](https://www.zimmermann-lueftung.de/faq/hilfe/lueftung/auf-dem-hauptbedienteil-steht-ein-fehlercode-was-ist-zu-tun-1).

AccessModes 64/85/255 und numerische DataType-Kennungen in den XML-Dateien
werden ohne zugehörige Definition nicht als Schreibrechte oder vollständiges
Protokoll interpretiert. Ein BDE-Zugangscode belegt keinen USB-Schreibweg.

## Service-Menü und verbleibende Prüfung

Das fotografierte Service-Hauptmenü enthält laut Betreiber nur Sprache,
Einregulierung, Temperaturabgleich und Wärmeelementverriegelung.
Das Öffnen von **Einregulierung aktiviert die Funktion sofort**; es ist keine
reine Parameteransicht. Die Annahme einer vorgeschalteten Bestätigung war falsch.
Nach dem Hinweis zum Beenden zeigt das nächste Foto wieder das Hauptbild:
Komfort, Luftstufe 4, 23,5 °C, Kühlbetrieb. Das bestätigt die Rückkehr zur
Hauptanzeige, nicht die Unverändertheit sämtlicher interner Einstellungen.
Weitere unbekannte Service-Einträge nicht als reine Ansichten behandeln.

USB ist mangels passendem Kabel zurückgestellt. Später zunächst nur
Gerätekennung und Geräteklasse identifizieren. Vor einer physikalischen
Einheit für `0x00D7` oder einer Erweiterung auf neue Statuswörter werden
zusätzliche eindeutige Belege benötigt. Die neuen Diagnosen gehören zu Version 0.6.0. Der Live-Abgleich am BDE nach
Installation dieser Version steht noch aus.
