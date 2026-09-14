# Beobachtete BDE-Schreibtelegramme und ACKs

Stand: 14.09.2026. Geltungsbereich: [lokale Referenzanlage](ANLAGENPROFIL.md).
Offline ausgewertet wurden die privaten, nummerierten Diagnoseexporte (1)–(16).
Die zusätzlich anders benannte Datei `2.json` gehört nicht zu dieser Stichprobe.
Originaldateien bleiben außerhalb des Repositorys.

## Ergebnis

Für vier ausgewählte Datenpunkte wurden **1.300 SET-Telegramme** des beobachteten
BDE-Headers `11 80 00` gefunden. Auf jedes folgt innerhalb des gewählten
Zuordnungsfensters von 1.000 ms ein leeres ACK mit Header `23 40 00` und
demselben Datenpunkt. Keine mehrdeutige Zuordnung, kein verwaistes ACK und
kein offenes SET am Mitschnittende in dieser Stichprobe.

| Datenpunkt | Beobachteter Inhalt | SETs / zugeordnete ACKs | Unveränderte Wiederholungen | Größte Zeitdifferenz im Capture |
|---|---|---:|---:|---:|
| `0x00E1` | angeforderte Panel-Luftstufe | 331 / 331 | 304 | 80 ms |
| `0x01F8` | BDE-Bitfeld, darin Intensivlüftung `0x40` | 322 / 322 | 301 | 116 ms |
| `0x020A` | Betriebsart | 322 / 322 | 304 | 132 ms |
| `0x0227` | Solltemperatur, Float32 Little Endian | 325 / 325 | 307 | 142 ms |

Wiederholungen und Änderungen werden **innerhalb** eines Mitschnitts verglichen.
Sein erster Wert ist eine Ausgangsbeobachtung und zählt nicht als Änderung.
Die Auswertung deckt alle 458.394 exportierten Bytes mit prüfsummengültigen
Frames der acht bereits beobachteten Header ab; keine unaufgelösten Bytes.
Das bestätigt die Auswertbarkeit der exportierten Daten, nicht eine lückenlose
Erfassung aller vorherigen oder späteren Vorgänge auf dem physischen Bus.

## Was die Bedienversuche zusätzlich zeigen

- Solltemperatur: Export (9) enthält 18 → 26 °C bei 10,680 s, Export (12)
  30 → 21 °C bei 14,028 s. Auch die geänderten Werte erhalten ACKs.
- Intensivlüftung (14): Luftstufe 4 erscheint bei 17,934 s, das Bit `0x40`
  erst bei 21,631 s. Beim Abschalten folgen Luftstufe 3 bei 61,931 s und
  Bit 0 bei 62,827 s.
- Wiederholung (15): Luftstufe 4 bei 20,313 s, Intensiv-Bit bei 22,641 s;
  Luftstufe 3 bei 52,741 s, Bit 0 bei 54,058 s.
- Manuelle Stufe 4 in Eco Sommer (16) setzt das Intensiv-Bit nicht.
  `0x00E1 = 4` allein beschreibt deshalb keine vollständige Intensivfunktion.
- `0x01F8` enthält auch den anderen beobachteten Wert `0x00000800`.
  Ein pauschales Schreiben von `0x40` oder `0` könnte andere Bits überschreiben.
  Ihre Semantik und Zuständigkeit sind nicht ausreichend geklärt.

Die Auswahl der Intensivdauer führte weiterhin zu keinem identifizierten
Minuten-Schreibwert; siehe [Intensivlüftungsversuche](INTENSIVLUEFTUNG_BEOBACHTUNGEN.md).
Eine erneute Prüfung der Exporte (13)–(16) ohne Header- oder Datenpunkt-Auswahlliste
bestätigt diesen Stand: sämtliche 130.482 Bytes wurden strukturell erfasst,
aber keine zusätzliche Dauerübertragung zugeordnet. Der nächste gezielte
Versuch erfasst das automatische Ende statt eines weiteren manuellen Ein/Aus.

## Bedeutung und Grenzen eines ACKs

Beispiel für 21 °C, unverändert aus einem Mitschnitt:

```text
SET  11800027020000080000a84152d0
ACK  234000270200000039a1
```

Das ACK enthält weder den übernommenen Wert noch einen Statuscode oder eine
Transaktionsnummer. Die Zuordnung beruht ausschließlich auf Header,
Datenpunkt, Reihenfolge und Zeitfenster. Sie beweist weder dauerhafte Speicherung
noch den späteren Anlagenzustand. Auch ein fremder Teilnehmer könnte eine
gleichartige Antwort ausgelöst haben.

Zeitstempel gehören zum TCP-Chunk, der ein Frame vervollständigt. Mehrere Frames
im selben Chunk können eine Differenz von 0 ms ergeben; das ist keine gemessene
Antwortzeit auf dem RS485-Bus. Das Fenster von 1.000 ms ist eine Auswertungsregel,
kein ermittelter Geräte-Timeout. Die beobachteten 142 ms sind ebenfalls kein
garantiertes Antwortlimit.

## Wiederholbare Offline-Prüfung

```sh
uv run python -m tools.audit_panel_writes diagnose-01.json diagnose-02.json --output /tmp/panel-write-audit.json
```

Das [Werkzeug](../tools/audit_panel_writes.py) prüft Header, Länge und Prüfsumme,
rekonstruiert Frames über Chunkgrenzen, protokolliert Änderungen und zählt
Wiederholungen. Es erfasst nur die vier oben genannten SET-Datenpunkte.
Weitere Frames werden für die Byteabdeckung gezählt, nicht semantisch bewertet.
Der Bericht enthält Quellenindizes statt privater Dateipfade oder Eintrags-IDs.

Bei mehreren ausstehenden SETs desselben Datenpunkts bleibt eine ACK-Zuordnung
mehrdeutig. Ein Mitschnittende vor Ablauf des Fensters wird als noch offen
ausgewiesen; ein fehlendes ACK wird daraus nicht abgeleitet. Unbekannte,
beschädigte oder abgeschnittene Bytes erscheinen als `unparsed_bytes`.

## Konsequenz für Schreibunterstützung

Die passiven Bedienversuche liefern reproduzierbare SET/ACK-Belege. Die nächste
offene Voraussetzung ist **koordinierter Buszugriff mit weiter angeschlossenem
BDE/PTC**: zulässige Teilnehmeradresse, Zuständigkeit für den Sollwert und Verhalten
gegenüber den regelmäßig wiederholten BDE-SETs. Ein nachgebildetes BDE-Telegramm
löst diese Fragen nicht. Siehe [Entwicklungsplan](ENTWICKLUNGSPLAN.md) und
[offene Upstream-Fragen](UPSTREAM_LESEZUGRIFF_FRAGEN.md).

Das Audit besitzt keinen Netzwerkzugriff und keinen Sender. Die Integration
bleibt passiv; es wurden keine Schreibtelegramme an die Anlage gesendet.

## Präzisierung durch das automatische Ende in Export (18)

Bei weiterhin angezeigtem Kühlbetrieb und BDE-Luftstufe 4 schreibt die Panel-Seite
nach Ablauf der Intensivlüftung 0x01F8 = 0 und anschließend 0x00E1 = 3.
Controllerstatus und hohe Ist-Drehzahlen bleiben davon unabhängig.
Die ursprüngliche Bezeichnung „effektive Luftstufe“ war deshalb zu weitgehend:
0x00E1 bildet die **angeforderte Panel-Luftstufe** ab. Im Offline-Audit lautet
der Berichtsname jetzt `panel_requested_fan_level`; der HA-Schlüssel `fan_level`
und seine Werte werden dadurch nicht verändert. Die Tabelle oben behält ihren
historischen Stichprobenumfang (1)–(16).

In Export (18) sind alle 22 Luftstufen-SETs und 21 Bitfeld-SETs mit zeitlich
zugeordneten ACKs erfasst, einschließlich der Änderungen beim automatischen Ende.
Details und Zeitvergleich mit Export (17):
[automatisches Ende unter Kühlung](INTENSIVLUEFTUNG_BEOBACHTUNGEN.md#automatisches-ende-bei-weiterlaufender-kühlung-export-18).
