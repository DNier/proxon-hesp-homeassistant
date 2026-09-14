# BDE-Sollwert: Untersuchung nach dem ersten Schreibtest

Stand: 14.09.2026, Integration 0.7.1. Diese Nachuntersuchung ist ausschließlich
lesend/offline. Sie wertet den bereits vom Nutzer ausgeführten Versuch aus;
es wurde kein weiterer Befehl an die Anlage gesendet.

## Ergebnis

Der einmalige HESP-Schreibversuch hat **keine dauerhafte Übernahme im BDE**
nachgewiesen. Das BDE zeigte beim erneuten Aufwecken weiterhin 22 °C.
Ein späterer Rücktransfer von der Hauptplatine zum BDE ist damit für diesen
Versuch nicht beobachtet worden. Ob die Hauptplatine den Testwert kurzzeitig
angewendet hat, bleibt offen.

Für einen gemeinsamen Sollwert ist der Zugang zum BDE selbst der bevorzugte
Untersuchungsweg. Ein historischer Erfahrungsbericht nennt konkret eine
USB-Inbetriebnahmesoftware. Deren Protokoll, Verfügbarkeit und Eignung für
laufende Sollwertänderungen sind noch nicht belegt. Eine Inline-Bridge kann
alternativ Vorgaben ersetzen, löst aber allein keine BDE-Anzeigesynchronisierung.

## Messbelege aus Export (21)

Quelle: privater Diagnoseexport (21), separate `target_temperature_test.receive_capture`.
Beginn 13:49:40.345 UTC / 15:49:40.345 MESZ; Laufzeit 120 Sekunden.
35.098 Empfangsbytes, 2.400 strukturell und per Prüfsumme gültige Frames,
keine ungeparsten Bytes. Die TCP-Verbindung meldet null Wiederverbindungen.

| Zeitpunkt relativ zum Sendeversuch | Beobachtung |
| --- | --- |
| 0 ms | Einmal 14 Bytes für DP `0x0227`, 22,5 °C, an den Transport übergeben |
| +36 ms | Reguläre Abfrage von DP `0x0206` empfangen |
| +38 ms | Zusätzliches leeres ACK für `0x0227` empfangen |
| +1.327 ms | Reguläres SET für `0x0227` mit **22 °C** empfangen |
| +1.344 ms | Dazu passendes leeres ACK empfangen |

Sendeversuch bei Capture-Zeit 16.095 ms: `11800027020000080000b4416cdc`.
Alle 24 empfangenen SETs für `0x0227` enthalten 22 °C; dem stehen 25 leere
ACKs gegenüber. Ein Rücklesen von 22,5 °C oder ein Echo unseres SETs fehlt.
Das zusätzliche ACK passt zeitlich zum Versuch, enthält aber weder den
übernommenen Wert noch eine Transaktionsnummer. `transport_flushed_unverified`
ist deshalb weiterhin die zutreffende technische Ergebnisbeschreibung.

Für `0x0206` gibt es 25 Abfragen, aber nur 24 Antworten. Zur Abfrage direkt
nach unserem Versuch fehlt im Mitschnitt eine passende Antwort. Das ist eine
Auffälligkeit, kein bewiesener elektrischer Buskonflikt. Auch vollständig gültige
empfangene Frames beweisen nicht, dass keine Telegramme verloren gingen.
Zeitangaben stammen aus TCP-Chunks, nicht aus einer elektrischen Busmessung.

Der Nutzer hat die Sollwertanzeige nach Displayruhe erneut aufgerufen und
22 °C bestätigt. Die normale Hauptanzeige eignet sich nicht zur durchgehenden
Sollwertkontrolle. Diese Beobachtung ergänzt den Mitschnitt; sie ist kein
automatisches Sensor-Readback.

## Welche Zugänge sind belegt?

### USB am BDE: konkrete Spur, noch keine nutzbare Schnittstelle

Christian Tan beschreibt am 30.01.2014 für eine PROXON P1 mit BDE Comfort,
dass Windows das per USB angeschlossene BDE erkannte. Ein Techniker habe es
mit einem Programm namens **„Proxon Inbetriebnahme“** konfiguriert. Bertel2014
berichtet im selben Thema über eine funktionierende originale Modbus-Busbridge.
Das sind historische Nutzerbeobachtungen, keine Kompatibilitätsbestätigung für
unsere Firmware. USB-Sollwertänderung und BDE-Rückmeldung werden nicht vorgeführt.
Ein öffentlich nutzbares Softwarepaket oder USB-Protokoll wurde nicht gefunden.

Quelle: [Erfahrungsberichte zum BDE Comfort](https://www.haustechnikdialog.de/Forum/p/2086671?print=1).

Die SD-Sicherung enthält Messprotokolle und Feldmetadaten, keine gefundene
Inbetriebnahmesoftware oder Firmware. `TRaumsoll` hat dort Gruppe 10 / ID 124,
während auf der aufgezeichneten HESP-Seite `0x0227` verwendet wird. Die ID 124
ist daher ein späterer Suchbegriff für Servicekommunikation, **kein freigegebener
Schreibbefehl**. `AccessModes=85` ist ohne Definition nicht interpretierbar.
Details: [SD-Abgleich](SD_KARTEN_ABGLEICH.md).

### BDE/PTC-Bus: separates, bislang nicht aufgezeichnetes Segment

Markus Mauchs Referenz beschreibt BDE–PTC mit 9600 Baud und PTC–Hauptplatine
mit 19200 Baud. Die Rolle des STM32 bei der Vermittlung und die vollständige
Panel-Kommunikation sind nicht abschließend geklärt. Seine Vermutung einer
analogen Ursache für ignorierte Fremdframes ist keine nachgewiesene Ursache
an unserer Anlage. Aus unseren 19200-Baud-Aufzeichnungen lässt sich kein
vollständiges 9600-Baud-Protokoll rekonstruieren.

Quelle: [Referenz, offene Punkte](https://github.com/markusmauch/proxon-hesp/blob/0c5151342299084db0f57836f5bbd140822e7e33/docs/offene-punkte.md).

Der Autor bestätigt im FHEM-Forum, dass er das BDE entfernt hat. Seine Lösung
belegt somit keine parallele Bedienung mit synchronisiertem BDE. Der Grund für
die Entfernung ist damit nicht abschließend erklärt.

Quelle: [FHEM, Beitrag vom 13.07.2026](https://forum.fhem.de/index.php?topic=96437.0).

### Ältere Hermes-Steuerung: kein übertragbarer Befehlssatz

Das WR3223-openHAB-Projekt bietet einen eigenen seriellen Zugriff und verwendet
Befehlsnamen wie `SP`, `MD` und `SW` für PC-Steuerung. Es stellt kein BDE-Comfort-
USB-Protokoll bereit. Herstellerverwandtschaft reicht nicht zur Übertragung auf
unsere HESP-Telegramme oder XML-IDs.

Quelle: [WR3223-Befehlsdefinitionen](https://github.com/frami/org.openhab.binding.wr3223/blob/master/src/main/java/org/openhab/binding/wr3223/internal/client/WR3223Commands.java).

## Nächster Versuch mit klarer Aussagekraft

1. **USB identifizieren**, sobald ein passendes Datenkabel vorhanden ist:
   am Rechner zunächst nur Hersteller-/Produkt-ID, Produktname, Geräteklasse
   und angebotene Schnittstellen erfassen. Keine geratenen seriellen Befehle,
   keine Update- oder Einregulierungsfunktion starten. Das Ergebnis entscheidet,
   ob beispielsweise eine serielle Schnittstelle oder ein herstellerspezifisches
   USB-Protokoll untersucht werden muss. Geräteerkennung allein ist noch kein
   Beleg für lesenden oder schreibenden Parameterzugriff.
2. **Servicezugang klären:** passendes Programm und Protokollbeschreibung für
   exakt diese BDE-Version suchen bzw. beim Hersteller erfragen. Konkrete Frage:
   Kann die USB-Serviceverbindung den laufenden Raumsollwert ändern, sodass
   Anzeige und nachfolgende BDE-Vorgaben denselben Wert enthalten? Historische
   Softwareexistenz garantiert weder heutigen Bezug noch diese Funktion.
3. **Falls USB keinen Zugang eröffnet:** BDE/PTC-Verkehr passiv aufzeichnen,
   idealerweise zeitgleich mit der bisherigen HESP-Seite. Dafür zuerst
   Platinenrevision, Pinorientierung und elektrische Schnittstelle belegen.
   Ein gezielter manueller Sollwertwechsel und seine Rückstellung liefern dann
   mehr Information als ein weiterer Fremd-SET auf dem bisherigen Segment.
4. **Erfolgskriterium für spätere Steuerung:** externe Änderung wird beim
   Aufwecken im BDE angezeigt, erscheint in den folgenden regelmäßigen Vorgaben,
   und eine anschließende manuelle Änderung bleibt wirksam. Zusätzlich sind
   Zeitprogramme und Verbindungsverlust zu prüfen. Ein ACK allein genügt nicht.

Bis dahin begründen die Daten weder periodisches Gegenschreiben noch einen
automatischen Wiederholungsversuch. Eine Bridge mit zeitlich begrenztem Override
wäre eine separate Betriebsart mit ausdrücklich getrenntem BDE- und wirksamem
Sollwert. Sie darf nicht als gelöste Synchronisierung bezeichnet werden.

## Nachprüfbarkeit

`tools.inventory_capture.inventory()` wurde erneut direkt auf die separate
Empfangsaufnahme aus Export (21) angewandt. Die oben genannte Zeitfolge wurde
aus vollständig prüfsummengeprüften Frames und dem gespeicherten TX-Marker
rekonstruiert. Rohdaten und Detailinventar bleiben im ignorierten `tmp/`.
Diese Untersuchung ändert ausschließlich Dokumentation, weder Sender noch
Produktionsdecoder oder Live-Konfiguration.
