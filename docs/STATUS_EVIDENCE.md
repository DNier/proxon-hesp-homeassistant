# Freigabestand der Schaltzustände

Stand: 3. Oktober 2026. Erneute Offline-Inventarisierung von 41 unterschiedlichen
Aufnahmefenstern der Referenzanlage: 183.780 prüfsummengültige Frames, keine
unaufgelösten Bytes. Identische Startzeit/Chunk-Folgen sind dedupliziert;
überlappende Fenster bleiben enthalten. Die Anzahl ist kein Maß unabhängiger
Schaltvorgänge. Frühere zeitgleiche Fotovergleiche wurden erneut gegen die
Rohdaten geprüft. Community-Daten ergänzen den Vergleich, ersetzen aber keine
BDE-Gegenprobe eines Schaltzustands.

Bitnummern zählen ab 0 im Little-Endian-Wort. Die vollständige Telegrammidentität
und Payloadlänge bleiben Teil jeder Zuordnung.

| Anzeige/Kandidat | Beleg und Grenze | Entscheidung |
| --- | --- | --- |
| MV-Heizen/Kühlen: `224000/006C/4`, Bit 9 | BDE-Vergleiche beider Zustände und gefilmte fallende Flanke stimmen überein. Bleibt nach Verdichterstopp noch gesetzt. | Bestehende optionale Anzeige beibehalten; keine Aussage „aktive Kühlung“. |
| MV-Abtau: gleiche Antwort, Bit 7 | Fotozustände passen; der relevante Übergang war durch Seitenwechsel verdeckt. Kein bestätigter vollständiger Abtauablauf. | Kandidat, keine neue Entität. |
| PTC-Wohnen: `01F8` Bit 11 / `03B6` / `118007/0191` | Korrelation bei Sollwertänderungen, aber ein BDE-Foto zeigt PTC ein bei jeweils null in diesen Feldern. | Diese allgemeine Zuordnung ist widerlegt. |
| MV-Vorwärme | Kein unabhängiger positiver BDE-Beleg. | Unbekannt. |
| Aktives Heizen/Kühlen: `224000/0208/4` | Bit 8 tritt bei Heizen und Kühlen auf; Bits 9/10 fallen teilweise vor Verdichterstopp. Bit 28 fehlt bei bestätigter Kühlung. | Keine belastbare Betriebszustandsanzeige aus diesen Einzelbits. |
| Eco-Luftstufe Zeitplan/fest | Auto in Eco Sommer/Winter folgt einem nutzerdefinierten Wochenzeitplan. Gleiche numerische Stufe kann Zeitplan- und feste Auswahl darstellen. In Komfort/Ofen bestimmt die Steuerung die Stufe ohne diese Auswahl. | Auswahl und Zeitplan nicht aus Rohstellwert oder Stufe ableiten. |

Für eine spätere Freigabe sind positive und negative BDE-Referenzen einschließlich
Übergang, unverdeckter Anzeige und zeitgleicher vollständiger Rohaufnahme nötig.
Bekannte Gegenbeispiele müssen weiterhin bestanden werden. Eine passende
Temperatur oder ein gesetztes Anforderungsbit allein belegt keinen laufenden
Heiz- oder Kühlprozess. Fehlende oder veraltete Daten bleiben unbekannt.

Die neuen Vergleichsdaten rechtfertigen daher keine zusätzliche benannte
Schaltzustandsentität. Die vorhandenen experimentellen Bits bleiben ausdrücklich
als Rohbits bezeichnet. Es wurden für diese Prüfung keine Anlagenbefehle gesendet.

Siehe [Bedienfolgen](CONTROL_EVIDENCE.md), [Community-Auswertung](COMMUNITY_EXPORT_ANALYSIS.md)
und [FWT-Kompatibilitätsgrenzen](COMPATIBILITY.md).

Bedienhinweis ergänzt am 4. Oktober 2026 auf Grundlage der Beobachtung an der
Referenzanlage. Der oben genannte Offline-Korpus wurde dafür nicht erweitert.
[Bedienverhalten und passende Versuchsbedingungen](REFERENCE_TESTS.md).
