# Gegenprüfung eines Community-Exports

Auswertung vom 27. September 2026. Grundlage sind der öffentliche
[SQL-Export](https://github.com/user-attachments/files/32697336/Proxon.sql) und der
[Node-RED-Code](https://github.com/user-attachments/files/32697463/Proxon.txt) von
Mannheim68199 aus [Diskussion 1](https://github.com/DNier/proxon-hesp-homeassistant/discussions/1#discussioncomment-18622902).
Die Befunde gelten für diesen Export und bestätigen keine allgemeine Kompatibilität
weiterer Hardwareversionen.

## Vorgehen und Grenzen

Die 90.055 SQL-Datensätze wurden ausschließlich als Text gelesen; SQL und
Node-RED-Code wurden nicht ausgeführt. Die Text-Zeitstempel reichen vom
16. September 2026, 17:46:37 bis zum 27. September 2026, 11:13:49. Die Zeitzone
ist nicht unabhängig bestätigt. Zeitangaben besitzen nur Sekundenauflösung.

Innerhalb jedes Datensatzes wurden hexadezimale Inhalte von `HEX` und `HEX2`
zusammengesetzt. Nichthexadezimale Kennzeichnungen wie `Response` wurden nicht
als Bytes behandelt. Zwischen verschiedenen Datensätzen wurden keine Bytes
verbunden: Der Export ist ein gefiltertes Änderungsprotokoll, kein Busmitschnitt.
Jeder Datensatz wurde mit einer neuen Instanz des vorhandenen Decoders geprüft.
Die vorhandene Offline-Inventarisierung prüft separat Struktur und Prüfsummen.
Die Metadaten-Ausnahme ist in [METADATA_EVIDENCE.md](METADATA_EVIDENCE.md) beschrieben.

Ergebnisse dieser Prüfung:

- 116.677 strukturell und prüfsummenseitig passende gespeicherte Frame-Vorkommen.
  Darin stecken Duplikate, weil Antworten sowohl an Anfragen angehängt als auch
  separat gespeichert sein können. Das ist keine Zahl unabhängiger Busnachrichten.
- 24 Datensätze enthalten nicht zuordenbare Bytes; 28 enthalten keinen vollständig
  validierten Frame. Diese Mengen sind nicht identisch: Auch leere oder rein
  textuelle Inhalte kommen vor. Unbekannte Bytes sind nicht automatisch ein neuer DP.
- Der Produktionsdecoder akzeptiert 89.715 gespeicherte Frame-Vorkommen seiner
  bestehenden Freigabeliste. Innerhalb seiner erkannten Kandidaten treten keine
  Prüfsummen- oder vollständigen Wertverwerfungen auf. Das bestätigt weder den
  gesamten Export noch die Bedeutung unbekannter Werte.

`Wert1`, `Werte` und `Type` waren keine Grundlage für die Dekodierung. Die
Node-RED-Filterung vergleicht vor allem den ersten Wert eines Arrays. Änderungen
anderer Elemente können fehlen; negative Werte werden in `Wert1` teilweise durch
einen Ersatzwert überschrieben. Filtereinstellungen wechselten laut Autor.
Aus fehlenden Datensätzen folgen weder unveränderte Zustände noch Buspausen.

## Metadaten sind keine automatische Datentyp- oder Rechtefreigabe

Von den 64 Einträgen der Metadatenliste erscheinen acht DP-Nummern in den
strukturell gültigen Frame-Gruppen: `006C`, `0226`, `0227`, `0229`, `022A`,
`022C`, `0191` und `0194`. Bei den letzten beiden unterscheiden sich die
Identitäten von den durch die Integration freigegebenen Identitäten. Eine gleiche
DP-Nummer allein beweist deshalb keine gleiche Quelle oder Semantik.

Ein besonders wichtiger Gegenbeleg gegen eine pauschale Typzuordnung:

| Datenpunkt | Metadaten-Typ | Maske | Beobachtete Nutzdaten |
| --- | --- | --- | --- |
| `0227` | `0204` | `00FF` | Vier Bytes; bekannte Float-Solltemperatur |
| `022C` | `0204` | `0055` | Zwei Bytes; Werte `0100` und `0000`, Bedeutung offen |

Somit kann `0204` nicht ungeprüft als immer vier Byte langes Float-Feld behandelt
werden. Der Unterschied könnte unter anderem mit Maske, Funktion oder Darstellung
zusammenhängen; dafür liegt noch keine bestätigte Regel vor. Insbesondere ist
`022C` trotz der Werte 0/1 noch kein freigegebener Schalter.

`0229` enthält vier Byte, als Float 21; `022A` enthält als Float 21 oder 18.
Das ist mit Temperatur-Sollwerten vereinbar, belegt aber weder Betriebsart,
Raumzuordnung noch Schreibberechtigung. Es werden keine neuen Entitäten angelegt.

## Lüfterwerte sind anlagenspezifisch

Am 24. September liegen folgende Änderungen in benachbarten gespeicherten
Datensätzen vor. Zeiten bezeichnen Datenbankeinträge, keine elektrische Buszeit:

| Anforderung `00E1` | Zeitpunkt Anforderung | Stellwerte `00D7` | Zeitpunkt Stellwerte |
| --- | --- | --- | --- |
| Stufe 4 | 00:01:31 | 10000 / 10000 | 00:01:32 |
| Stufe 3 | 06:11:32 | 7000 / 7000 | 06:11:32 |
| Stufe 2 | 07:31:33 | 5000 / 5000 | 07:31:34 |

Andere bereits untersuchte Aufnahmen zeigten häufig 5200/5200 bei Stufe 3 und
4000/4000 bei Stufe 2. Eine globale feste Rückrechnung vom Rohstellwert auf die
Luftstufe wäre damit nicht belastbar.

Zusätzlich enthalten die konstanten Viererblöcke `00D2` und `00D3` als Float
die Folgen 31/50/70/100 bzw. 25/50/70/100. Im Export kommen die Stellwertpaare
3100/2500, 5000/5000, 7000/7000 und 10000/10000 vor. Das legt konfigurierte
Lüfterkennlinien nahe. Einheit, Zuordnung und Sonderbetriebsfälle benötigen
jedoch eine Anzeige- oder Dokumentationsreferenz; es wird daraus noch kein
Prozent-Sensor oder allgemeiner Stufendecoder abgeleitet. Auch 10000/7000 kommt vor.

Die anschließende [Gegenprüfung der Lüfterkennlinien](FAN_CURVE_EVIDENCE.md)
vergleicht diese Listen mit der Referenzanlage und stellt eine reproduzierbare
Offline-Prüfung für numerische Kandidaten bereit.

## Statusbits und Temperaturen

Die 46 gespeicherten gültigen Status-Vorkommen enthalten ausschließlich die vier
Wörter `8000101A`, `80001012`, `80001522` und `80001022`. Sie sind bereits in der
bestehenden Freigabeliste für die Regler-Luftstufe enthalten. Bit 8 ist in zwei
gespeicherten Vorkommen gesetzt; Bit 9 und Bit 28 sind in keinem gesetzt.
Duplikate und fehlende Zwischenzustände erlauben daraus keine Ereigniszählung.

Der Verdichter erreicht in gespeicherten Antworten bis etwa 4852 rpm. Der als
Heizstunden interpretierte Einzelzähler steigt von 18 auf 20, der Kühlzähler bleibt
bei 658. Mangels zeitgleicher BDE-Referenz und vollständigem Verlauf beweist dies
keine neue Statusbit-Zuordnung und widerlegt auch keine kurzzeitigen Übergänge.
Der Export liefert insbesondere keine Abtau-Gegenprobe für Bit 28.

Alle 5280 gespeicherten, validierten Temperaturblock-Vorkommen enthalten in den
ersten zehn Kanälen Rohwerte innerhalb der bisherigen positiven Empfangsgrenzen.
Der elfte Wert ist durchgehend null. Damit liefert dieser Export weder eine
bestätigte Negativtemperaturkodierung noch eine Bedeutung für den elften Kanal.

## Sammelantwort `02DF`: Gleichheit im untersuchten Export

Sieben vollständige Antworten auf `02DF` besitzen 112 Byte Nutzdaten, interpretierbar
als 28 Little-Endian-32-Bit-Zahlen. Die ersten acht Positionen stimmen in allen
sieben Beispielen mit den nächstgelegenen gespeicherten Einzelantworten überein:

| Position (ab 1) | Einzel-DP | Bisherige Interpretation |
| --- | --- | --- |
| 1–4 | `02D0`–`02D3` | Betriebsstunden Luftstufen 1–4 |
| 5 | `02D4` | Heizbetrieb Wärmepumpe |
| 6 | `02D5` | Kühlbetrieb Wärmepumpe |
| 7 | `02D7` | Steuerung |
| 8 | `02D9` | Vorheizung |

55 der 56 Einzelvergleiche liegen höchstens fünf Sekunden entfernt. Bei einem
unverändert null gespeicherten `02D9` beträgt der Abstand 970 Sekunden; dieser
Vergleich ist kein zeitgleicher Nachweis.

Die verbleibenden 20 Zahlen stimmen in allen sieben Beispielen vollständig mit
dem Inhalt von `02D6` überein, dort jedoch als 20 **16-Bit**-Werte übertragen.
Die zugeordneten `02D6`-Einträge liegen jeweils null oder eine Sekunde entfernt.
So entspricht die Folge 21, 1 in `02D6` den beiden getrennten Zahlen 21, 1 in
`02DF`; sie darf nicht als einzelne 32-Bit-Zahl 65557 interpretiert werden.
Die fachliche Bedeutung dieser 20 Positionen bleibt offen.

Diese Gleichheit gilt ausschließlich für diesen Export. Gegenprüfungen mit den
lokalen P-Serie-Aufnahmen und einem separaten FWT2L-Diagnoseexport widersprechen
einer allgemeinen Alias-Regel: Dort enthalten `02DF` und die Einzelantworten
unterschiedliche Zählerstände. Auch die letzten 20 Positionen stimmen dort nicht
mit `02D6` überein. Die Gegenbeispiele und Grenzen stehen in
[Data points: unmapped reply blocks](DATA_POINTS.md#unmapped-reply-blocks).

Dies stützt die numerische Form der Sammelantwort, liefert aber keine zusätzlich
bestätigte Messgröße oder gemeinsame Zählerbasis. Der Produktionsdecoder
übernimmt die Sammelantwort nicht als zweite Aktualisierungsquelle für die
vorhandenen Zähler.

## Umsetzung und nächste Belege

Die vorhandenen Entitäten und ihre Bedeutungen bleiben unverändert. Ausgewählte
Originaltelegramme ohne Datenbank- und Zeitmetadaten sichern als Regressionstest
ab, dass die bekannten Werte dekodiert und unbekannte Formen nicht automatisch
freigegeben werden:

```sh
uv run pytest -q tests/test_community_recordings.py tests/test_metadata_recordings.py
```

Für die nächsten fachlichen Freigaben sind gezielte Belege sinnvoll:

1. Unabhängige Belege für Einheit und Richtungszuordnung von `00D2`/`00D3`, etwa
   Herstellerunterlagen oder zugängliche Einstellungen einer anderen Anlage.
   Am Referenz-BDE gibt es laut Bediener keine solche Einstellungsseite. Der
   ersatzweise durchgeführte [Betriebsabgleich für Stufen 1–4 und Intensivlüftung](FAN_CURVE_EVIDENCE.md)
   ist abgeschlossen; eine weitere Menüsuche ist dort nicht erforderlich.
2. Bedienreferenz für `0229`, `022A` und `022C`, ohne aus den Masken Schreibrechte
   abzuleiten oder unbekannte Schreibbefehle zu versuchen.
3. Vollständiger kurzer Mitschnitt einer normalen BDE-Sollwertänderung für die
   Abfolge von Schreiben, Bestätigen und späterem Wert. Der vorhandene Export
   unterscheidet den Sender eigener und regulärer SET-Nachrichten nicht zuverlässig.

Eine neue Aufnahme an der Referenzanlage ist für diese abgeschlossene
Offline-Auswertung nicht erforderlich.
