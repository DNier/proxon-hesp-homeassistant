# Metadatenlisten: belegte Telegramme und offene Bedeutung

Original recorded evidence: 27 September 2026. Offline page preparation: 9 November 2026.

## Herkunft und Prüfung

Grundlage ist der öffentlich bereitgestellte [SQL-Export von Mannheim68199](https://github.com/user-attachments/files/32697336/Proxon.sql)
aus [Diskussion 1](https://github.com/DNier/proxon-hesp-homeassistant/discussions/1#discussioncomment-18622902).
Der vollständige Export wird nicht ins Repository übernommen. Die Testdatei
`tests/fixtures/metadata_replies.json` enthält ausschließlich die drei ausgewählten
Protokollantworten ohne Zeitstempel, Datenbanknamen oder Anlagendaten außerhalb der Listen.
Die Prüfsummen stammen unverändert aus der Aufzeichnung, nicht aus dem Testcode.

Die Datensätze 5930 und 26458 enthalten identische Antworten auf `0033`;
26746 enthält `0034`, 26352 enthält `0038`. Sie stammen vom 18./19. September 2026
laut Export; die Zeitzone der als Text gespeicherten Zeiten ist nicht unabhängig bestätigt.
Die getrennten Felder `HEX` und `HEX2` werden für diese Datensätze zusammengesetzt.
Bei 26458 und 26352 folgt nach dem 138-Byte-Telegramm noch eine 12-Byte-Abfrage.
Diese gehört nicht zur Metadatenliste und wird nicht in die Fixture übernommen.

Alle vier Antworten haben nach genau 138 Bytes eine passende Prüfsumme nach
unserer bestehenden Byte-Rekurrenz. Davon sind acht Bytes Header, 128 Bytes
Nutzdaten und zwei Bytes Prüfsumme. Die Nutzdaten ergeben jeweils 64 Little-Endian-
16-Bit-Werte. Die drei Listen wurden zu unterschiedlichen Zeiten aufgezeichnet;
ihre positionsweise Zuordnung ist eine Arbeitshypothese auf Basis derselben Anlage.

## Eng begrenzte Erkennung

Die ursprünglich belegte Form umfasst Identität `224000`, reservierte Bytes `0000`,
Datenpunkt `0033`, `0034` oder `0038` und Längenfeld `00`. Sie beschreibt diese
138-Byte-Form. Daraus folgt keine allgemeine Regel, jedes Längenfeld `00` als
128 Bytes zu interpretieren. Insbesondere besitzen Bestätigungen weiterhin leere
Nutzdaten. Ob `00` hier einen Überlauf der Nibble-Länge oder eine spezielle
Kodierung bedeutet, ist nicht abschließend geklärt.

Die gemeinsame Prüfsummenfunktion unterstützt nun bis zu 136 Bytes ohne die
zwei Prüfsummenbytes. Der Live-Decoder behält seine bisherigen Datenpunkt- und
Längenfreigaben. Es entstehen keine neuen Entitäten und keine Busabfragen.

## Was die Listen belegen

Die nachfolgende Tabelle stellt die drei Spalten unverändert positionsweise dar.
Die Bezeichnungen Datenpunkt, Typcode und Maskencode entsprechen der bisherigen
Interpretation; insbesondere werden aus einer Maske keine Schreibrechte abgeleitet.
Auch 64 gültige Einträge beweisen keinen vollständigen Gerätekatalog. Weitere
Seiten, Gerätekonfigurationen oder Firmwarevarianten sind nicht ausgeschlossen.
Eine fehlende zyklische Einzelantwort macht einen Listeneintrag nicht ungültig.

| Position | Datenpunkt | Typcode | Maskencode |
| --- | --- | --- | --- |
| 1 | `0x0066` | `0x000A` | `0x0055` |
| 2 | `0x006C` | `0x000A` | `0x0055` |
| 3 | `0x0258` | `0x01F6` | `0x00C0` |
| 4 | `0x0067` | `0x000A` | `0x0055` |
| 5 | `0x025A` | `0x01F6` | `0x00C0` |
| 6 | `0x025C` | `0x01F6` | `0x00C0` |
| 7 | `0x025D` | `0x01F8` | `0x00FF` |
| 8 | `0x006A` | `0x03E9` | `0x00C0` |
| 9 | `0x006B` | `0x03E9` | `0x00C0` |
| 10 | `0x0262` | `0x01F6` | `0x00C0` |
| 11 | `0x0263` | `0x01F6` | `0x00C0` |
| 12 | `0x0267` | `0x01F6` | `0x0055` |
| 13 | `0x0266` | `0x01F6` | `0x00C0` |
| 14 | `0x0268` | `0x01F8` | `0x0055` |
| 15 | `0x0269` | `0x01F8` | `0x0055` |
| 16 | `0x0259` | `0x01F6` | `0x00C0` |
| 17 | `0x025B` | `0x01F6` | `0x00C0` |
| 18 | `0x022D` | `0x0204` | `0x0055` |
| 19 | `0x022E` | `0x0204` | `0x0055` |
| 20 | `0x0230` | `0x0204` | `0x0055` |
| 21 | `0x0231` | `0x0204` | `0x0055` |
| 22 | `0x0232` | `0x0204` | `0x0055` |
| 23 | `0x0226` | `0x0204` | `0x00FF` |
| 24 | `0x0229` | `0x0204` | `0x00FF` |
| 25 | `0x0227` | `0x0204` | `0x00FF` |
| 26 | `0x022A` | `0x0204` | `0x00FF` |
| 27 | `0x0233` | `0x0204` | `0x00D5` |
| 28 | `0x0234` | `0x0204` | `0x00D5` |
| 29 | `0x0235` | `0x0204` | `0x00D5` |
| 30 | `0x0236` | `0x0204` | `0x00D5` |
| 31 | `0x0237` | `0x0204` | `0x00D5` |
| 32 | `0x0238` | `0x0204` | `0x00D5` |
| 33 | `0x0239` | `0x0204` | `0x00D5` |
| 34 | `0x023A` | `0x0204` | `0x00D5` |
| 35 | `0x023B` | `0x0204` | `0x00D5` |
| 36 | `0x023C` | `0x0204` | `0x00D5` |
| 37 | `0x023D` | `0x0204` | `0x00D5` |
| 38 | `0x0228` | `0x0204` | `0x00FF` |
| 39 | `0x022B` | `0x0204` | `0x00FF` |
| 40 | `0x023E` | `0x0204` | `0x00D5` |
| 41 | `0x023F` | `0x0204` | `0x0055` |
| 42 | `0x0240` | `0x0204` | `0x00C0` |
| 43 | `0x0241` | `0x0204` | `0x00C0` |
| 44 | `0x0242` | `0x0204` | `0x0055` |
| 45 | `0x022C` | `0x0204` | `0x0055` |
| 46 | `0x0243` | `0x0032` | `0x00F5` |
| 47 | `0x00FA` | `0x0203` | `0x0055` |
| 48 | `0x0103` | `0x0203` | `0x0055` |
| 49 | `0x0112` | `0x0203` | `0x0055` |
| 50 | `0x0114` | `0x0203` | `0x0055` |
| 51 | `0x0113` | `0x0203` | `0x00C0` |
| 52 | `0x00FB` | `0x0203` | `0x0055` |
| 53 | `0x00FC` | `0x0203` | `0x0055` |
| 54 | `0x00FD` | `0x0203` | `0x00C0` |
| 55 | `0x00FE` | `0x0203` | `0x00C0` |
| 56 | `0x0102` | `0x0203` | `0x0055` |
| 57 | `0x0190` | `0x0203` | `0x0055` |
| 58 | `0x0191` | `0x0203` | `0x0055` |
| 59 | `0x0192` | `0x0203` | `0x0055` |
| 60 | `0x0194` | `0x0203` | `0x0055` |
| 61 | `0x0193` | `0x0203` | `0x0055` |
| 62 | `0x0195` | `0x0203` | `0x0055` |
| 63 | `0x0107` | `0x0203` | `0x00C0` |
| 64 | `0x010D` | `0x0203` | `0x0055` |


## Offline preparation for follow-up pages and units (9 November 2026)

Martin's [FWT 2-R report in discussion #6](https://github.com/DNier/proxon-hesp-homeassistant/discussions/6)
proposes that the upper 16 bits of a metadata register ID select an **element
offset**, with 64 uint16 entries in each reply. His adapter additionally reads
`0039` as an array of unit codes. This is useful new candidate evidence; the
complete original metadata export and its timed QUERY/RESPONSE recording have
not yet been supplied to this project. The original public fixture above remains
the recorded evidence for zero-offset `0033`, `0034` and `0038` only.

The existing offline inventory is prepared for these narrowly bounded forms:

- Header `224000`, metadata DP `0033`, `0034`, `0038` or `0039`, length byte `00`,
  exactly 128 payload bytes, and a valid original checksum. Upper ID bits are
  retained as a candidate offset, including for `0039` at offset zero.
- Header `108000` to the same metadata points, two payload bytes exactly `0100`
  (uint16 count **1**). This follows Martin's reported request form; **64 entries
  in a reply do not establish a request count of 64**. Other counts are unsupported
  by the page auditor. Other frame families still require zero reserved bytes.

This does not generalize the length-byte wrap rule to every identity, accept
empty confirmations as 128-byte replies, or change the production decoder.
Offset-zero group keys and all five fields of existing frame observations remain
unchanged. A nonzero offset uses the complete ID, for example
`224000/0x00400033/128`; the group additionally reports `register_id` and
`selector_offset`. The address matcher pairs **the full register ID**, so replies
to different pages cannot be merged by the lower DP alone.

The page auditor uses the same inventory, checksums and conservative exchange
matcher. It merges identical overlap entries at their original absolute indices,
rejects conflicting overlaps and ambiguous/orphaned exchanges, and keeps failed
queries visible. Missing column/page ranges are explicit. `catalog_length` stays
`null`: a 64-entry page, a highest observed offset, or a timeout cannot prove a
complete device catalog. An optional `0039` column contains raw `unit_code`
values only; type, mask and unit meanings and write permissions are not approved.

All new offset/`0039` regression examples are **synthetic**, including the
0/64/86 overlapping-last-page example. They verify offline handling, not actual
FWT/P2 compatibility, list length, access rights or units. No bus query, sender,
new entity, automatic discovery or firmware change is introduced. The existing
temperature candidates and production `03B7` mapping are unchanged.

See [input formats and usage](OFFLINE_ANALYSIS.md#metadata-replies-and-follow-up-pages).

## Grenzen des Exports

Der Export enthält 90.055 gefilterte Datensätze mit Text-Zeitstempeln vom
16. bis 27. September 2026. Er ist kein lückenloser Mitschnitt.
Der mitgelieferte [Node-RED-Code](https://github.com/user-attachments/files/32697463/Proxon.txt)
vergleicht primär `value[0]`; Änderungen weiterer Elemente einer Sammelantwort
können deshalb fehlen. Zudem wird der Vergleichswert bereits vor dem zusätzlichen
Zeitfilter aktualisiert. Eine verworfene Änderung muss nicht später nachgetragen werden.
Der Code filtert `00c9` und `0226` auf eine letzte Sekundenziffer von `0`, also
Sekunden 00/10/20/30/40/50, nicht ausschließlich auf den Minutenanfang. Der Filter
für `0330` ist in dieser Codefassung auskommentiert. Historische Filter können
abweichen, wie der Autor ausdrücklich beschreibt.

`Wert1` ersetzt Werte kleiner oder gleich -1 durch -1 und ist daher keine
verlässliche Quelle für negative Messwerte. Die Spalte `HEX` ist auf 200 Zeichen
begrenzt und kann ein 138-Byte-Telegramm nicht allein aufnehmen. In den hier
verwendeten älteren Datensätzen ist die Fortsetzung jedoch in `HEX2` vorhanden.
Eine zukünftige Aufzeichnung sollte vollständige Originalnachrichten vor dem
Zerlegen und Filtern erhalten. Der Export belegt weder präzise Buspausen noch
zuverlässig, welcher Teilnehmer einen Sollwert geschrieben hat.

## Reproduktion und nächste Prüfungen

```sh
uv run python -m tools.audit_metadata tests/fixtures/metadata_replies.json --output /tmp/metadata-audit.json
uv run pytest -q tests/test_metadata_recordings.py
```

Die Tests prüfen Originalprüfsummen, jede einzelne Bitveränderung, alle Aufteilungen
auf zwei Empfangsblöcke, folgende Abfragen und leere Bestätigungen sowie das
Zurückweisen abgeschnittener oder abweichender Frames. Die Auswertung bleibt offline.

Vor einer semantischen Freigabe sind unabhängige Gegenproben für Typcodes und
Masken nötig. Für Schreibtests bleibt ein vollständiger, ungefilterter Ablauf
mit Bedienreferenz erforderlich. Die vorhandenen Metadaten beweisen keine
zuverlässige Steuerung und werden nicht zur automatischen Geräteerkennung benutzt.
