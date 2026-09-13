# Datenpunktabdeckung 0.2.0

Grundlage: Markus Mauchs Datenpunktreferenz (abgerufen am 13.09.2026) und
vorhandener 30-Sekunden-Mitschnitt der LT-ZIM-V1.6/PTC-4×-V1.2-Anlage.
https://markusmauch.github.io/proxon-hesp/dp-referenz/

## Veröffentlicht

| Datenpunkte | Darstellung | Evidenz |
|---|---|---|
| 00E1, 020A, 0226, 0227 | Vier bestehende BDE-Sensoren | Lokal abgeglichen bzw. Raumtemperatur mit gerundeter Anzeige vereinbar |
| 00ED | Filterrestlaufzeit, Tage | 114 im Mitschnitt, Bedeutung aus Referenz; lokaler BDE-Abgleich offen |
| 032E | Laufzeit seit Start, Sekunden | Bedeutung aus Referenz; Reset-Verhalten lokal offen; keine Statistikklasse |
| 02D0–02D5, 02D7, 02D9 | Acht deaktivierte Diagnosezähler, u32 | Werte prüfbar; keine Zuordnung zu Bauteilen und keine Stunden-Einheit behauptet |
| Weitere 18 kurze Controllerantworten | Deaktivierte Diagnosesensoren, Hex-Payload | Prüfsumme passend, Bedeutung bewusst offen |

Die 18 Rohdatenpunkte: 051E, 006C, 00EE, 0168, 0120, 01F5, 0110, 0105,
0115, 011C, 0116, 0206, 0519, 051C, 0330, 0123, 020F, 051D.
Hex-Werte erhalten Byte-Reihenfolge und führende Nullen. Sie sind keine Messwerte
mit bekannten Einheiten. Downloadbare Diagnosen enthalten weiterhin nur
Zähler und Schlüssel, keine Rohtelegramme oder Sensorwerte.

Controllerantworten werden nur mit Header 22 40 00 und den beobachteten
Längen akzeptiert. Panel-SETs behalten Header 11 80 00. Insbesondere wird eine
Antwort von Node 0x41 auf DP 0194 nicht als Zulufttemperatur interpretiert.
Es erfolgen weder Abfragen noch andere Schreibzugriffe.

## Noch nicht als Sensor ausgegeben

| Gruppe | Grund / nächster Nachweis |
|---|---|
| Zehn Temperaturkanäle 0190–0195, 022D, 022E, 0230, 0231 | Keine entsprechenden Temperaturantworten im vorhandenen Mitschnitt; eventuell während normaler BDE-Messwertanzeige passiv erfassbar |
| Ist-/Zieldrehzahlen 00C9/00D7 | Je zwei float32; Langtelegramm außerhalb des Prüfsummenmodells |
| Bypass 0160 | Prüfsummenmodell passt nicht zum aufgezeichneten Frame |
| Status 0208 | Prüfsummenmodell passt nicht; Bedeutung zudem ungeklärt |
| Zählerarray 02DF und 02D6 | Langtelegramme nicht prüfbar; widersprüchliche Array-/Einzelslotwerte nicht zusammenführen |
| Fehlertext 0130, Controllertext 03E8, Analogwerte 0064, Flags 0066 | Nicht im Mitschnitt als entsprechende Antworten vorhanden |
| Lüfterkennlinien 00D2/00D3 | Langtelegramme nicht prüfbar |
| Parameter und Selbstauskunft | Keine aktive Abfrage; keine vollständige Semantik belegt |

Es wird keine Prüfsumme umgangen oder aus einem einzigen Beispiel ergänzt.
Die vollständige Erschließung aller Daten braucht zusätzliche Protokollevidenz.

## Prüfung

34 Tests gegen Home Assistant 2026.9.2: bestehende Identitäten, zusätzliche
Registry-Einträge, Einheiten, standardmäßig deaktivierte Rohsensoren,
Controller-Identität, Fragmentierung, Prüfsummenfehler und Ausschluss unprüfbarer
Telegramme. Offline-Wiedergabe mit 37-Byte-Blöcken: 186 akzeptierte Werte für
32 Schlüssel. Kein zusätzlicher Live-TCP-Client wurde geöffnet.

## Abgleich am 13.09.2026 und Korrektur in 0.2.1

BDE-Fotos und HA-Anzeige stimmen für alle acht Zähler exakt überein:

| DP | BDE-Zuordnung | Stunden |
|---|---|---:|
| 02D0 | Luftstufe 1 | 42236 |
| 02D1 | Luftstufe 2 | 9607 |
| 02D2 | Luftstufe 3 | 38483 |
| 02D3 | Luftstufe 4 | 2414 |
| 02D4 | Wärmepumpe Heizen | 26708 |
| 02D5 | Wärmepumpe Kühlen | 5 |
| 02D7 | Steuerung | 95284 |
| 02D9 | Vorwärme | 1818 |

Dies ersetzt die vorläufige Rohwertzuordnung oben für diese Anlage.
Die IDs bleiben unverändert. Einheit h und Geräteklasse duration; noch keine
Statistikklasse, da Rücksetzverhalten nicht geprüft. Bei neuen Einrichtungen
aktiviert; bestehende Deaktivierungen bleiben erhalten.

032E mit 35831976 ist kein belegter Sekunden-seit-Neustart-Wert. Die Anlage
war laut Nutzer am selben Tag ausgeschaltet. Daher ab 0.2.1 neutraler Zähler
ohne Einheit und ohne Geräte-/Statistikklasse; Bedeutung bleibt offen.
Die 18 Hex-Sensoren bleiben ungeklärt und standardmäßig deaktiviert.
