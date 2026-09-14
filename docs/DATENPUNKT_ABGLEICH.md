# Datenpunkt-Abgleich, 14.09.2026

Vier lokale Diagnoseexporte: Response-Kandidatensuche nach 22 40 00,
Subselektor 00 00 und gerader Laengenangabe (Nutzbytes = Laengenbyte / 2).
Keine allgemeine Framing-Garantie. Keine Live-Buszugriffe.

| DP | Kandidaten | Pruefsummenmodell |
|---|---:|---|
| 00C9 Ist-Drehzahlen | 77 | Laenge nicht unterstuetzt |
| 00D7 Soll-Drehzahlen | 76 | Laenge nicht unterstuetzt |
| 03B7 Temperaturen | 77 | Laenge nicht unterstuetzt |
| 0330 Uhrzeitkandidat | 76 | Alle passend |
| 032E | 76 | 45 passend, 31 abweichend |
| 0160 Bypass | 74 | Alle abweichend |

Keine Antwortkandidaten fuer Temperatur-Einzel-DPs 0194, 0231, 0230,
0190, 0191, 022e, 0192, 022d, 0193, 0195 oder Metadaten 0001, 0033,
0034, 0038, 0039 gefunden. Das beweist keine fehlende Geraeteunterstuetzung.

## Umsetzung

Experimentelle Geraeteuhrzeit als standardmaessig deaktivierter Diagnosesensor,
HH:MM:SS, ohne Datum, Zeitzone oder Statistikklasse. Nur aus geprueftem 0330,
mit Bereichspruefung der Zeitfelder. Rohentitaet und ihre ID bleiben erhalten.
Verfuegbarkeit folgt dem bestehenden Cache-Ablauf.

Drehzahlen bleiben gesperrt: Kanalzuordnung allein reicht wegen der fehlenden
Pruefsummenabdeckung nicht. Naechster Schritt ist die Vorbereitung gezielter
Leseabfragen fuer Metadaten und Einzelwerte. Kein aktives Polling implementiert.

Referenzen:
- https://markusmauch.github.io/proxon-hesp/dp-referenz/
- https://markusmauch.github.io/proxon-hesp/protokoll/

## Morgenaufnahme 14.09.2026

Export (4): Start 05:48:16 UTC / 07:48:16 Ortszeit, 34936 Bytes,
letzter Chunk 119958 ms, regulaeres Zeitlimit. Diagnose: verbunden,
kein letzter Fehler, null Reconnects, null gesendete Applikationsbytes.
Keine neuen Response-DPs gegenueber den vier bisherigen Exporten.

25 gepruefte Filterantworten liefern 113 Tage statt zuvor 114. Damit ist
nun auch ein Dekrement ueber Nacht beobachtet, nicht nur ein BDE-Abgleich.
LS3-Zaehler 38495 h und Steuerung 95296 h: jeweils +12 gegenueber
den ersten BDE-Fotos (38483 und 95284).

24 gepruefte Uhrzeitantworten: 07:47:36 bis 07:49:29. Der neue lokale
Decoder liefert dieselbe Folge; der Wechsel zu Morgenstunden ist damit
getestet, ein kontinuierlicher Mitternachtsuebergang nicht.
Raumtemperatur 22.31284 Grad, Soll 21, Eco Sommer, Luftstufe 3.
25 Temperaturbloecke mit identischem Payload; alle ausserhalb des
aus den vier bisherigen Diagnoseexporten bestimmten affinen Unterraums.
25 Ist- und 25 Soll-Drehzahlantworten weiter ohne unterstuetzte Pruefsumme.
032E: 25 Abweichungen; Bypass: 24 Abweichungen. Keine weitere Freigabe.
