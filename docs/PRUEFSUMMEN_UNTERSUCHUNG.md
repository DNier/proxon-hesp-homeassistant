# Temperaturtelegramm: Prüfsummenuntersuchung

Stand 13.09.2026. Offline-Untersuchung, keine Buszugriffe und keine Freischaltung
zusätzlicher Sensoren.

## Material und Verfahren

Zwei getrennte Aufnahmen: ursprünglicher 30-Sekunden-Mitschnitt und der
120-Sekunden-Diagnoseexport beim Ablesen der BDE-Seiten. Kandidaten wurden über
Header `22 40 00 b7 03 00 00 2c` und 32 Byte Gesamtlänge extrahiert. 22 Byte
Payload passen zu elf 16-Bit-Slots. Die ersten zehn passen als Zehntelgradwerte
zum BDE; Slot elf ist in diesen Aufnahmen null und bleibt ungeklärt.

Untersucht wurde ein affines GF(2)-Modell mit 240 Nachrichtenbits und zusätzlichem
konstanten Term. Keine unbekannten Beiträge wurden willkürlich auf null gesetzt.
Ein Validierungsframe ist nur vorhersagbar, wenn sein Eingabevektor im vom
Trainingsmaterial bestimmten Unterraum liegt. Die Prüfsumme des Validierungsframes
wird erst zum Vergleich verwendet, nicht zum Erweitern des Trainingsmodells.

## Ergebnis

- Training: sechs Temperaturframes, vier unterschiedliche Nachrichten, Rang 4.
- Innerhalb dieses Trainingsmaterials wechseln lediglich sechs Eingabebits.
- Unabhängige Validierung: 23 Frames mit sieben unterschiedlichen Nachrichten.
- Alle 23 liegen außerhalb des bestimmten Unterraums: keine eindeutige Vorhersage.
  Das sind weder 23 korrekte noch 23 falsche Vorhersagen.
- Beide Aufnahmen kombiniert: elf unterschiedliche Frames, Rang 8, keine
  Widersprüche zum affinen Ansatz. Das beweist den Ansatz nicht allgemein.
- Nur zwei einzelne Bitbeiträge sind aus dem kombinierten Material bestimmbar:
  Bit 96 (little-endian vom Nachrichtenanfang): 0x7D68;
  Bit 176: 0x0C91. Andere Beiträge sind damit nicht bestimmt.

Eine Tabelle passend zu diesen elf Nachrichten wäre kein allgemein validierter
Prüfsummenalgorithmus. Deshalb bleibt der Produktionsdecoder unverändert.

## Reproduktion

`tools/analyze_temperature_checksum.py TRAINING VALIDATION` akzeptiert rohe
Binäraufnahmen oder HA-Diagnoseexporte. Rohaufnahmen bleiben außerhalb des Repos.
Die Auswertung nennt Anzahl, Rang, Konflikte und Vorhersagbarkeit. Sie ist ein
Forschungswerkzeug, kein allgemeiner Framing- oder Prüfsummenvalidator.

## Nächster Nachweis

Weitere Aufnahmen im normalen Anlagenbetrieb bei anderen Temperaturen würden
die Datenbasis erweitern, garantieren aber keine vollständige Identifikation.
Mindestens eine komplette Aufnahme bleibt jeweils unabhängig zur Validierung.
Alternativ kann ein vollständiger Algorithmus oder ein diverserer Datensatz aus
dem Referenzprojekt helfen. Keine absichtlichen Heizläufe und keine künstlichen
Bus-Schreibtelegramme sind für diese Offline-Arbeit vorgesehen.

## Dritte Aufnahme: 22:27:36 bis 22:29:36 Ortszeit

Der zweite Diagnoseexport (Dateiname mit `(1)`) enthält 32618 Bytes,
23 Temperaturkandidaten und sechs unterschiedliche Temperaturframes. Gegen das
ausschließlich aus den ersten beiden Aufnahmen trainierte Modell sind alle 23
nicht eindeutig vorhersagbar; null bestätigte Vorhersagen und null widerlegte
Vorhersagen. Alle drei Aufnahmen zusammen ergeben Rang 13 ohne affine
Widersprüche. Das erweitert das Material, löst die Prüfsumme aber nicht.

| Slot (ab 0) | BDE-Zuordnung als Kandidat | Bereich im Mitschnitt °C | Foto °C |
|---|---|---|---|
| 0 | T1 Zuluft | 19,5–19,6 | 19,6 |
| 1 | T7 Abluft | 23,4 | 23,4 |
| 2 | T4 Fortluft | 20,2 | 20,2 |
| 3 | T3 Frischluft | 16,2–16,4 | 16,4 |
| 4 | T5 VorVerdampfer | 19,5 | 19,5 |
| 5 | T6 Verdampfer | 21,4 | 21,4 |
| 6 | T8 NachVorwärme | 17,4 | 17,4 |
| 7 | T12 VorKondensator | 20,4 | 20,4 |
| 8 | T10 Kondensator | 19,6 | 19,6 |
| 9 | T13 Kompressor | 20,9–21,0 | 20,9 |

Slot 10 bleibt null. T2 Wohnen gehört nicht zu diesen zehn Slots.
Die Fotos sind keine exakt zeitgleichen Referenzen für jeden Frame.

### Uhrzeit: zusätzliche Beobachtung

Kandidatenscan: Antworten für 0x032E steigen während der Aufnahme von
35832106 auf 35832108; die beobachteten Wechsel liegen ungefähr bei 10 und
68 Sekunden. Das entspricht keinem Sekundenzähler. Bei 104675 ms und
117184 ms erscheinen Panel-Schreibkandidaten für 0x032E mit Payload
`2cc12202` beziehungsweise `acc52202`, unmittelbar gefolgt von
Antwortkandidaten Typ 0x23. Die Antworten davor liefern weiterhin `2cc12202`;
nach dem zweiten Schreiben endet die Aufnahme, ohne hier einen bestätigenden
neuen Leseantwortwert nachzuweisen. Ein Zeit-/Datumsbezug ist deshalb eine
Arbeitshypothese; Epoche, Einheit und erfolgreiche Übernahme bleiben offen.
Das Foto mit „Speichern“ allein beweist die Übernahme ebenfalls nicht.
Der Kandidatenscan ist kein vollständiger Framing-/Prüfsummennachweis.

Keine Änderung am Produktionsdecoder und keine neue Veröffentlichung.

## Vierte Aufnahme: 22:36:02 Ortszeit

Der Export mit `(2)` wurde nach 29,922 Sekunden manuell beendet (8198 Bytes).
Das Feld duration_seconds=120 bezeichnet das konfigurierte Limit.
Sechs Antwortkandidaten zu 0x032E enthalten unverändert `a385261b`
(uint32 LE 455509411), deutlich verschieden vom vorherigen Mitschnitt.
Kein Panel-Schreiben mit dem untersuchten 0x032E-Header enthalten.
Der vorhandene partielle Prüfsummenalgorithmus berechnet für den ersten
Antwortkandidaten 63839, empfangen wurde 13542: keine Prüfsummenfreigabe.
Der neue Wert ist deshalb kein validierter Uhrzeitwert. Die kurze Aufnahme
zeigt zudem keinen Zählschritt; Einheit und Kodierung bleiben ungeklärt.
Das BDE-Foto zeigt 22:35 und Sonntag, 13. September auf der Hauptseite,
also die korrigierte Anzeige, ohne daraus eine Buskodierung abzuleiten.

Der Raumtemperaturwert 0x0226 beträgt konstant 22,937850952148438 °C
und seine sechs gefundenen Telegramme bestehen die vorhandene Prüfung.
Das passt zur gerundeten BDE-Anzeige von 23,0 °C.
Sechs Temperaturblock-Kandidaten (vier unterschiedliche) liegen sämtlich
außerhalb des durch die ersten drei Aufnahmen bestimmten affinen Unterraums.
Keine eindeutig vorhersagbare Prüfsumme in dieser unabhängigen Aufnahme.
Produktionsdecoder unverändert.

## Fünfte Aufnahme: 22:39:15 bis 22:41:15 Ortszeit

Export `(3)`: 34938 Bytes, duration_limit, letzter Chunk bei 119938 ms.
25 Antwortkandidaten zu 0x032E: 455509414 → 455509415 → 455509416.
Erste Beobachtung der Wechsel bei 30545 und 89339 ms (58,794 Sekunden
auseinander, Abfrageintervall etwa 4,9 Sekunden). Kein gefundener
Panel-Schreibheader für diesen Datenpunkt. Die vorhandene partielle
Prüfsummenberechnung passt weiterhin bei keinem dieser 25 Kandidaten.

### Neuer Uhrzeitkandidat 0x0330

Alle 25 gefundenen 0x0330-Antworten bestehen die vorhandene Prüfsummenprüfung.
Payload als uint32 LE, Stunden = x & 31, Minuten = (x >> 5) & 63,
Sekunden = (x >> 11) & 63 liefert eine zeitlich konsistente Folge:
22:38:31 bei 476 ms, 22:38:56 bei 24943 ms, 22:39:01 bei 29843 ms,
22:40:00 bei 88639 ms, 22:40:30 bei 118036 ms.
Diese Folge läuft etwa 45 Sekunden hinter der lokalen Capture-Zeit.
Das ist eine belegte Kandidatenkodierung für diese Aufnahme, noch kein
allgemeiner Nachweis für Tageswechsel, Datum oder Zeitzone.
Die Minutenwechsel von 0x032E stimmen zeitlich mit diesem Uhrzeitkandidaten
überein; vollständige Kodierung von 0x032E bleibt offen.

25 Temperaturkandidaten, drei unterschiedliche Frames. Gegen die ersten vier
Aufnahmen als Training sind alle 25 nicht eindeutig vorhersagbar.
Keine Produktionsänderung.
