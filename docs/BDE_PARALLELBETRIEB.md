# BDE und externe Steuerung: Ergebnis der Vorprüfung

Stand: 14.09.2026, nach Veröffentlichung von 0.6.0. Untersuchung ausschließlich
offline anhand der Aufzeichnungen (1)–(18) und öffentlich verfügbarer Quellen.
Kein zusätzlicher TCP-Client, kein eigenes QUERY/SET, keine Anlagenänderung.

## Entscheidung

Ein kooperativer Schreibweg, der externe Einstellungen auch im BDE übernimmt,
ist für die Referenzanlage bislang **nicht nachgewiesen**. Ein einzelnes
nachgebildetes SET mit anschließendem ACK genügt dafür nicht. Schnelleres
Gegenschreiben über den bestehenden parallelen Gateway wird nicht implementiert.

Das ist keine Aussage, dass Synchronisierung technisch unmöglich wäre. Die
vorliegenden Daten enthalten keinen extern ausgelösten Schreibversuch und
keinen Mitschnitt der separaten BDE/PTC-Verbindung. Sie zeigen die wiederholte
Übertragung des vom BDE vorgegebenen Zustands auf der HESP-Seite.

## Eigene Aufzeichnungen: Wiederholung und Rückmeldung

Die 18 Exporte umfassen 522.226 Bytes und 35.829 strukturell gültige Frames.
Das vollständige Inventar und das SET/ACK-Audit lassen keine exportierten Bytes
ungeparst. Die vier untersuchten Einstellungs-Datenpunkte ergeben:

| Datenpunkt | Bedeutung | SETs / passende ACKs | Unveränderte Wiederholungen | Median der Wiederholungsabstände je Mitschnitt |
| --- | --- | ---: | ---: | ---: |
| 0x00E1 | angeforderte Luftstufe | 377 / 377 | 345 | 4.899–5.321 ms |
| 0x01F8 | BDE-Bitfeld einschließlich Intensivbit | 366 / 366 | 341 | 4.900–5.321 ms |
| 0x020A | Betriebsart | 366 / 366 | 345 | 4.899,5–5.321 ms |
| 0x0227 | Solltemperatur | 369 / 369 | 349 | 4.900–5.321 ms |

Insgesamt 1.478 SETs/ACKs und 1.380 unveränderte Wiederholungen. Die restlichen
SETs sind 72 Ausgangswerte (vier pro Mitschnitt) und 26 Wertänderungen.
Keine mehrdeutigen Zuordnungen, offenen SETs oder ACKs ohne passendes SET im
gewählten 1.000-ms-Fenster. Größte SET/ACK-Differenz: 142 ms.

Die Wiederholungsstatistik berücksichtigt nur aufeinanderfolgende SETs desselben
Datenpunkts mit identischer Payload innerhalb desselben Exports. Änderungen und
Grenzen zwischen Dateien werden nicht als periodische Wiederholung gezählt.
Die Tabellenwerte sind der kleinste und größte **Mitschnitt-Median**, kein
zusammengefasster Median und kein garantiertes Busintervall. Einzelabstände
weichen ab: beispielsweise 306 ms für eine unveränderte Luftstufen-Wiederholung.
Die Zeitstempel stammen vom abschließenden TCP-Chunk, nicht von einer Messung
der elektrischen Busbelegung. Empfangspausen begründen kein Senderecht.

Für jeden dieser vier Datenpunkte enthält das vollständige Inventar genau
die Identitäten `11 80 00` (SET, passende Nutzdatenlänge) und `23 40 00`
(ACK, null Nutzbytes). Es gibt hier **keine zusätzliche Antwort mit dem
übernommenen Wert**. Ein ACK trägt auch keine Transaktionsnummer.
Damit bleiben Annahme, dauerhafter Zustand und BDE-Anzeige getrennte Prüfungen.

Die Bezeichnung „Panel-SET“ beschreibt die Herkunft des Sollzustands. Sie
identifiziert nicht allein den elektrisch sendenden Prozessor: Nach der
Architekturdokumentation vermittelt der PTC-Master zwischen BDE und Hauptplatine.
Das wurde auf unserer Anlage nicht durch gleichzeitige Messung beider Busseiten
erneut bestimmt.

Weitere SETs sind vorhanden, darunter 0x0226 (Raumtemperatur) und die nicht als
Steuerfunktionen zugeordneten 0x0229, 0x022A, 0x022C, 0x032E, 0x03B6 sowie
Subadresse 7 / 0x0191. 0x0229 und 0x022A enthalten in dieser Stichprobe jeweils
konstant `0000a841` (als float32 LE: 21). Das macht sie weder zu bestätigten
alternativen Sollwerten noch zu einem Override. Unbekannte DPs werden nicht
versuchsweise beschrieben. Die Untersuchung beweist nicht, dass es außerhalb
dieses Verkehrs keine weiteren Bedienfunktionen gibt.

## Abgleich mit öffentlich verfügbaren Projekten

### HESP-Dokumentation von Markus Mauch

Geprüfter Stand: `0c5151342299084db0f57836f5bbd140822e7e33` (13.09.2026).
Die Referenz beschreibt einen PTC-Master, der den Panelzustand etwa alle fünf
Sekunden erneut überträgt. Ein fremdes einmaliges SET wird dort wieder verdrängt;
häufigere Wiederholung konnte eine Wirkung erzielen. Unsere passiven Daten
bestätigen den Wiederholungstakt, nicht bereits das Verhalten nach Fremd-SETs.

Die Dokumentation enthält kein hier verwendbares Verfahren für mehrere Master,
keine bestätigte Rückschreibfunktion in den BDE-Speicher und keinen belegten
Vorrangmechanismus für externe Sollwerte. Die Zustandsübertragung auf dem
separaten 9600-Baud-Bus ist nicht vollständig erklärt. Die vermutete analoge
Ursache für dort ignorierte Fremdframes wird nicht als bewiesene Ursache übernommen.

Quellen:
[Protokoll](https://github.com/markusmauch/proxon-hesp/blob/0c5151342299084db0f57836f5bbd140822e7e33/docs/protokoll.md),
[Schreibbeobachtungen](https://github.com/markusmauch/proxon-hesp/blob/0c5151342299084db0f57836f5bbd140822e7e33/docs/dp-referenz.md),
[offene Punkte](https://github.com/markusmauch/proxon-hesp/blob/0c5151342299084db0f57836f5bbd140822e7e33/docs/offene-punkte.md).

### FWT1-Bericht von highcool

Der relevante Erfahrungsbericht ist Beitrag **21**, obwohl der ursprünglich
geteilte Link auf Beitrag 20 zeigt. Am 14.09.2026 berichtet der Autor über
Drehzahlschwankungen bei parallel alle 1,5 Sekunden gesendeten Vorgaben. Seine
neue Lösung vermittelt mit einem ESP32 und zwei RS485-Modulen und ersetzt
Bedienteil-Befehle durch HA-Vorgaben. Er begrenzt die Aussage ausdrücklich auf FWT1.

Das ist ein Beleg für die berichtete Strategie an einer anderen Anlage, kein
Nachweis der Kompatibilität mit LT-ZIM V1.6/PTC 4× V1.2. Weder die Übernahme
der Werte in die BDE-Anzeige noch Details zu Bussegmenten, Firmware und
Ausfallverhalten sind in diesem Beitrag belegt. Eine Bridge kann Befehle
vermitteln, ohne den gespeicherten BDE-Sollwert zu ändern. Diese beiden Ziele
dürfen nicht gleichgesetzt werden.

Quelle: [Beitrag 21](https://community.simon42.com/t/proxon-p2-anschluss-modbus/65378/21).
Die bereits vorhandene Nachfrage in Beitrag 22 bittet um Code, Module,
Vorrangregeln und Ausfallverhalten. Beim Abruf endet das Thema mit Beitrag 22;
keine zusätzliche Nachricht wurde gesendet.

### Modbus-Projekte

`steuerlexi/proxon-t300-esphome` verwendet Modbus-Controller und Holding-Register;
`charma/proxon-homeassistant` verwendet die native HA-Modbus-Anbindung.
Das sind keine HESP-BDE-Synchronisierungsverfahren. Registeradressen und
Schreibfreigaben werden nicht auf die P-Serie übertragen. T300 bleibt nachrangig.

Quellen:
[T300-Konfiguration](https://github.com/steuerlexi/proxon-t300-esphome/blob/main/proxon-t300.yaml),
[HA-Modbus-Konfiguration](https://github.com/charma/proxon-homeassistant/blob/main/modbus.yml).

## Nächste konkrete Voraussetzung

Vor einer Hardwareentscheidung fehlt die Antwort auf die schon gestellten
Fragen in [Upstream-Issue 1](https://github.com/markusmauch/proxon-hesp/issues/1#issuecomment-5659731209)
und [Forumsbeitrag 22](https://community.simon42.com/t/proxon-p2-anschluss-modbus/65378/22).
Beim aktuellen Abruf hat Issue 1 nur unsere vorhandene Nachfrage als Kommentar.
Ein fehlender Antwortbeleg ist kein Nachweis, dass der Autor keine Lösung hat.

Ein angebotener Schreib-/Bridge-Weg ist anhand folgender Punkte zu prüfen:

1. Welches Bussegment und welche Rolle übernimmt er? Pinbelegung und elektrische
   Ausführung für unsere Platinen müssen belegt sein; keine Ableitung aus Fotos
   oder FWT1-Steckernummern.
2. Ändert er den BDE-Sollwert tatsächlich oder nur die weitergeleitete Vorgabe?
   Für echte Synchronisierung: externer Sollwert → BDE-Anzeige → spätere
   BDE/PTC-SETs desselben Werts. Eine solche Übernahme wurde bislang nicht beobachtet.
3. Wie gewinnt eine anschließende manuelle BDE-Änderung Vorrang? Ein transparent
   weitergereichtes periodisches SET unterscheidet sich nicht automatisch von
   einer neuen Nutzerentscheidung. Programme und Zeitsteuerung müssen einbezogen sein.
4. Was passiert bei Verlust von HA/WLAN, Neustart, Prozessstillstand und
   Stromausfall der Bridge? Eine Software-Rückkehr zur Durchleitung hilft nicht
   automatisch bei ausgefallener Hardware. Ein Rückfallweg muss konkret geprüft sein.
5. Welche unabhängige Rückmeldung bestätigt die Wirkung? Controller-Luftstufe und
   Ist-Drehzahlen helfen bei Lüftung, ersetzen aber keine BDE-Sollwertübernahme.

Diese Voraussetzungen gelten für die Entscheidung über eine dauerhafte Steuerung.
Auf gesonderten Nutzerwunsch ist inzwischen ein
[einmaliger Solltemperatur-Test](SOLLTEMPERATUR_TEST.md) in Version 0.7.0 enthalten.
Er untersucht die Reaktion auf einen einzelnen Befehl und setzt keinen kooperativen
Buszugriff voraus; eine Kollision bleibt möglich. Ein Live-Versuch steht aus.
Keine Wiederholung der bisherigen Intensivversuche allein für mehr
gleichartige Daten nötig. USB kann später über Geräteklasse/Identifikation geprüft
werden; ein passendes Kabel allein erschließt noch keinen Steuerzugriff.

## Reproduzierbarkeit und Softwareumfang

`tools.audit_panel_writes` gibt zusätzlich `unchanged_set_interval_ms` mit Anzahl,
Minimum, Median und Maximum aus. Bestehende SET-/ACK-Zuordnungen bleiben erhalten.
Das Werkzeug arbeitet auf Dateien und enthält keinen Sender. Originalexporte,
gespeicherte Quellen und Detailberichte bleiben im ignorierten `tmp/`.

```sh
uv run python -m tools.audit_panel_writes diagnose-01.json diagnose-02.json --output /tmp/set-ack.json
uv run python -m tools.inventory_capture diagnose-01.json diagnose-02.json --output /tmp/gesamtinventar.json
uv run pytest -q tests/test_audit_panel_writes.py
```

Für die vollständige Wiederholung werden alle 18 Dateien getrennt als Argumente
übergeben. Sie dürfen für die Intervallmessung nicht zu einer scheinbar
durchgehenden Aufnahme zusammengefügt werden.

Prüfung des ergänzten Offline-Werkzeugs vor Vorbereitung des Solltemperatur-Tests:
149 Tests bestanden, Ruff-Lint/Formatprüfung und `git diff --check` erfolgreich.
Das bestehende Release 0.6.0 bleibt unverändert. Version 0.7.0 enthält zusätzlich
die oben verlinkte, separat freizugebende Testfunktion.
