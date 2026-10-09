# Freigabestand der Schaltzustände

Stand: 9. Oktober 2026. Basis ist die Offline-Inventarisierung vom 3. Oktober
mit 41 unterschiedlichen Aufnahmefenstern der Referenzanlage:
183.780 prüfsummengültige Frames, keine
unaufgelösten Bytes. Identische Startzeit/Chunk-Folgen sind dedupliziert;
überlappende Fenster bleiben enthalten. Die Anzahl ist kein Maß unabhängiger
Schaltvorgänge. Frühere zeitgleiche Fotovergleiche wurden erneut gegen die
Rohdaten geprüft. Community-Daten ergänzen den Vergleich, ersetzen aber keine
BDE-Gegenprobe eines Schaltzustands.

Ergänzend wurden ein gefilmter Heizungsstart und ein Sollwertwechsel bei
unverändertem Eco Winter gegen die vollständigen Rohaufnahmen geprüft. Die
oben genannten Korpuszahlen beziehen sich auf die Basisauswertung. MV-Abtau
hat jetzt einen unverdeckten fallenden Anzeigewechsel; die neue optionale
Entität ist ab Version 0.13.1 verfügbar.

Ein zusätzlicher gefilmter Sollwertwechsel bei unverändertem Komfort während
einer bestätigten Kühlphase reproduziert den PTC-Gegenfall: Das BDE zeigt
PTC-Wohnen Ein, während alle drei Kandidaten wiederholt null melden. Erst im
späteren Anlauf steigen die Kandidaten; danach ist PTC-Wohnen erneut als Ein
sichtbar. Die Anzeige ist zwischen diesen Belegen zeitweise verdeckt.
Die Basiskorpuszahlen oben enthalten diesen zusätzlichen Vergleich nicht.

Bitnummern zählen ab 0 im Little-Endian-Wort. Die vollständige Telegrammidentität
und Payloadlänge bleiben Teil jeder Zuordnung.

| Anzeige/Kandidat | Beleg und Grenze | Entscheidung |
| --- | --- | --- |
| MV-Heizen/Kühlen: `224000/006C/4`, Bit 9 | BDE-Vergleiche beider Zustände und gefilmte fallende Flanke stimmen überein. Bleibt nach Verdichterstopp noch gesetzt; bei natürlichem Heizbetrieb auch als Aus beobachtet. | Bestehende optionale Anzeige beibehalten; keine Aussage „aktive Kühlung“. |
| MV-Abtau: gleiche Antwort, Bit 7 | Positive und negative BDE-Anzeigen sowie ein unverdeckter gefilmter Ein→Aus-Wechsel passen. | Optionale BDE-Ventilanzeige ab 0.13.1; kein Nachweis aktiven Abtauens. |
| PTC-Wohnen: `118000/01F8/4` Bit 11 / `118000/03B6/4` Bit 1 / `118007/0191/2` Bit 1 | Einschalten und Ausschalten passen in Eco Winter; ältere Komfort-Belege passen ebenfalls. PTC Ein bei allen drei Kandidaten null wurde beim Kühl-Auslauf zusätzlich per Video reproduziert. Beim späteren Kandidatenanstieg werden externe Raumaktoren erreichbar, bleiben jedoch ausgeschaltet und melden dann 0 W; davor ist ihre Leistung unbekannt. Die drei Felder können dieselbe Information spiegeln. | Eine allgemeine direkte Kopie der BDE-Anzeige ist widerlegt. Anforderung/Freigabe bleibt eine Hypothese; keine Zuordnung zur tatsächlichen Raumheizleistung. |
| MV-Vorwärme | Kein unabhängiger positiver BDE-Beleg. | Unbekannt. |
| Aktives Heizen/Kühlen: `224000/0208/4` | Bit 8 tritt bei Heizen und Kühlen auf; Bits 9/10 fallen teilweise vor Verdichterstopp. Bit 28 fehlt bei bestätigter Kühlung. | Keine belastbare Betriebszustandsanzeige aus diesen Einzelbits. |
| Eco-Luftstufe Zeitplan/fest | Auto in Eco Sommer/Winter folgt einem nutzerdefinierten Wochenzeitplan. Gleiche numerische Stufe kann Zeitplan- und feste Auswahl darstellen. In Komfort/Ofen bestimmt die Steuerung die Stufe ohne diese Auswahl. | Auswahl und Zeitplan nicht aus Rohstellwert oder Stufe ableiten. |

## Ergänzende Belege aus natürlichem Winterbetrieb

Eine zusätzlich geprüfte passive Startaufnahme reproduziert die vorbereitende
Statusfolge: `03B6` und `0191` Bit 0 steigen vor der ersten positiven
Verdichterdrehzahl. Das ist kein neuer PTC-Wohnen-Nachweis; die Bit-1-Kandidaten
bleiben im Startfenster null. In einer späteren Phase wechseln sie zusammen
mit `01F8` Bit 11, ohne zeitgleiche BDE-PTC-Referenz. Der zusätzliche Beleg ist
in den Basiskorpuszahlen oben nicht enthalten.

Ein kurzer Referenzclip zeigt auf getrennten BDE-Seiten Heizbetrieb, grüne LED,
warme Zuluft und positive Verdichterdrehzahl; die Schaltzustandsseite zeigt
alle fünf Zustände Aus. Diese Seiten wurden kurz nacheinander, nicht gleichzeitig
abgelesen. Der Vergleich ergänzt die Gegenbelege zu MV-Heizen/Kühlen als
allgemeinem Heizsignal. PTC-Wohnen Aus im späteren Clip bestätigt nicht
rückwirkend die Start- oder Bit-28-Phasen. Bit 25 bleibt semantisch ungeklärt.

Eine gesonderte Phase bei durchgehend positiver Drehzahl zeigt ein längeres
Bit-28-Fenster als das darin enthaltene MV-Abtau-Ein-Fenster. Temperaturverlauf
und veränderte Lüfteransteuerung passen zu Abtauen, bestätigen aber ohne
zeitgleiche BDE-Referenz keine neue Anzeige aktiven Abtauens. Bit 28 und
MV-Abtau dürfen nicht gleichgesetzt werden.

Der stabile vollständige Status `8200131A` ist separat mit BDE-Luftstufe 3
abgeglichen und ab 0.15.1 für diese Anzeige freigegeben. Alle übrigen
ungeprüften vollständigen Wörter bleiben unverfügbar. Negative Temperaturen
werden anhand des Messblocks und einer ausdrücklichen negativen BDE-Anzeige
geprüft; [Codierung und Grenzen](TEMPERATURE_EVIDENCE.md) (Englisch).

Für eine spätere Freigabe sind positive und negative BDE-Referenzen einschließlich
Übergang, unverdeckter Anzeige und zeitgleicher vollständiger Rohaufnahme nötig.
Bekannte Gegenbeispiele müssen weiterhin bestanden werden. Eine passende
Temperatur oder ein gesetztes Anforderungsbit allein belegt keinen laufenden
Heiz- oder Kühlprozess. Fehlende oder veraltete Daten bleiben unbekannt.

Die Erreichbarkeit externer Raumaktoren ist eine zusätzliche Referenz der
betreffenden Installation, keine HESP-Freigabebestätigung. Bei der späteren
Rückstellung fallen die drei Kandidaten bereits mit dem Sollwert, während HA
die Aktoren noch mehrere Minuten als erreichbar meldet. Einschaltverzögerung,
Nachlauf und mögliche Erreichbarkeits-Timeouts bleiben getrennt zu prüfen;
deren elektrische Schaltzeiten sind nicht gemessen. Eine allgemeine
Freigabeentität wird daraus nicht abgeleitet.

Die zusätzliche MV-Abtau-Entität beschreibt ausschließlich den angezeigten
Magnetventilzustand auf der Referenzanlage. Unbekannte vollständige Statuswörter
und veraltete Daten ergeben nicht verfügbar. PTC-Wohnen, MV-Vorwärme und aktive
Heiz-/Kühl-/Abtauzustände erhalten keine neue Zuordnung. Die vorhandenen
experimentellen Bits bleiben ausdrücklich als Rohbits bezeichnet. Die
Integration sendete für diese Prüfungen keine Anlagenbefehle.

Siehe [Bedienfolgen](CONTROL_EVIDENCE.md), [Community-Auswertung](COMMUNITY_EXPORT_ANALYSIS.md)
und [FWT-Kompatibilitätsgrenzen](COMPATIBILITY.md).

Bedienhinweis ergänzt am 4. Oktober 2026 auf Grundlage der Beobachtung an der
Referenzanlage. Der oben genannte Offline-Korpus wurde dafür nicht erweitert.
[Bedienverhalten und passende Versuchsbedingungen](REFERENCE_TESTS.md).
