# Vorbereitung gezielter Leseabfragen

Status: Offline-Vorbereitung, keine Kommunikation mit der Anlage.

## Ergebnis

READ_QUERY_PLAN.json enthaelt zehn QUERY-Kandidaten fuer die dokumentierten
Temperatur-Einzelwerte und fuenf noch offene Metadatenabfragen. Das Werkzeug
hat keinen Socketzugriff, keine Host-/Portoption und keine Sendefunktion.
Die laufende Integration bleibt passiv.

Der Header ist fest auf QUERY 10 80 00 und Subselektor 00 00 begrenzt.
Die Payload 01 00 ist fuer Temperatur-Einzelwerte ein Kandidat fuer ein
angefordertes typisiertes Element. Die fruehere Annahme "02 00 = zwei
16-Bit-Worte" war falsch und wurde korrigiert. Aufgezeichnete Beispiele:
00ED: Argument 1, Antwort 4 Byte; 00C9: Argument 2, Antwort 8 Byte;
03B7: Argument 11, Antwort 22 Byte. 0330 verwendet sogar Argument 0.
Deshalb ist das Argument keine universelle Byte- oder Wortanzahl.
Die Semantik fuer noch nicht beobachtete Temperatur-Queries ist unbestaetigt.
Unbekannte Pruefsummenbeitraege fuehren zu keiner Frame-Erzeugung.

Bei Metadaten werden Laenge und Pagination nicht geraten: 0033 (DP-Liste),
0034 (Typen), 0038 (Zugriffsrechte), 0039 (Einheiten) sowie 0001 (Name)
brauchen zuerst eine belegte Abfragestruktur. Die parallelen Listen duerfen
nur bei geklaerter Reihenfolge und gleicher Elementzahl verbunden werden.
Eine Zugriffsmaske ist keine Zustimmung zu automatischen Schreibzugriffen.

## Vor einem Live-Test

1. Request-Semantik an aufgezeichneten Queries oder Referenzcode bestaetigen.
2. Antwort-Framing fuer die erwarteten Laengen pruefen. Laengenangaben fuer
   lange Arrays sind in der Referenz nicht durchgehend eindeutig beschrieben.
3. Empfang und einzelne Abfrage ueber dieselbe bestehende Verbindung planen;
   keine parallele Verbindung zum Gateway neben Home Assistant.
4. Bus-Zugriff mit dem zyklischen Master koordinieren. Eine ruhige TCP-Luecke
   beweist keine freie RS485-Leitung; kein unkoordiniertes periodisches Polling.
5. Erst einen einzelnen bekannten Lesewert testen, mit begrenztem Timeout,
   ohne Wiederholungsschleife. Sende- und Empfangsbytes getrennt protokollieren.
6. Antworten nach Node, DP, Laenge und Pruefsumme zuordnen; keine Antwort,
   fehlerhafte Pruefsumme oder unklarer Datentyp erzeugt keinen Sensorwert.

## Reproduktion

Im Projektverzeichnis:

    uv run python -m tools.prepare_read_queries --output docs/READ_QUERY_PLAN.json

Referenz: https://markusmauch.github.io/proxon-hesp/protokoll/
und https://markusmauch.github.io/proxon-hesp/dp-referenz/

## Referenzcode und Verbindung

Das oeffentliche Referenzrepository enthaelt Dokumentation, aber keinen
Bus-Client oder Scheduler als Implementierungsvorlage (main geprueft).
Unser open_receiver gibt nur den Reader weiter und schliesst den Writer beim
Verlassen. Ein Live-Test verlangt eine explizite Erweiterung des gemeinsamen
Transportbesitzers samt Antwortzuordnung und Sendezaehler; eine zweite
Verbindung ist keine Loesung fuer die Bus-Koordination.

RECORDED_QUERIES.json enthaelt die aufgezeichneten Anfragekandidaten mit
Pruefsummenstatus. Es ist keine Sendeliste. Nur Status match belegt einen
Treffer des vorhandenen Pruefsummenmodells, nicht die Sicherheit einer
Wiederholung auf dem laufenden Bus. Der Status von generierten Einzelabfragen
bleibt candidate_not_validated_on_device.

## Implementierter Austauschbaustein

hesp/read_probe.py enthaelt einen isolierten Austauschbaustein: feste
Allowlist ausschliesslich fuer die beobachtete Filterabfrage 00ED/0100,
eine Anfrage gleichzeitig, drei Sekunden Timeout inklusive Senden,
keine Wiederholungen, begrenzter Empfangspuffer, exakte Antwortidentitaet
und Pruefsummenpruefung, Aufraeumen bei Abbruch und Fehlern.
bytes_submitted zaehlt an den Sender uebergebene Bytes, nicht nachweislich
auf der Leitung zugestellte Bytes. last_status protokolliert den Ausgang.

Der Baustein ist bewusst noch nicht mit dem Produktivtransport verbunden.
coordinated=True ist eine Verpflichtung des spaeteren Aufrufers, kein
implementierter Bus-Arbiter. Eine passende Antwort kann auch durch eine
Master-Anfrage entstanden sein: HESP liefert hier keine Transaktions-ID.
response_observed bedeutet daher nur beobachtete passende Antwort, keine
bewiesene Kausalitaet der eigenen Anfrage. Genau deshalb wird keine
Sendefunktion im HA-UI angeboten, solange die Koordination offen ist.

## Entscheidung nach Quellenpruefung vom 14.09.2026

Der urspruengliche FHEM-Thread dokumentiert kein Verfahren fuer parallele
Master. Markus nennt dort eine fertige Loesung ohne verwendetes BDE;
welche Rolle das PTC-Modul darin weiter spielt, bleibt offen. Deshalb ist
die Annahme "Referenzzugriff funktioniert unveraendert neben unserem BDE"
nicht belegt. Eine neue Sende-UI oder ein geratenes TCP-Ruhefenster wuerde
diese Frage nicht loesen. Keine Live-Freigabe auf dieser Grundlage.
Die genauen Rueckfragen stehen in UPSTREAM_LESEZUGRIFF_FRAGEN.md.
