# Kühlung: Sollwertversuch am 14.09.2026

Quelle: vom Betreiber bereitgestellter Diagnoseexport mit Integration 0.4.0,
Start 10:02:28 Ortszeit, sowie seine Beschreibung der BDE-Bedienung und
Technikerauskunft. Der private Rohmitschnitt bleibt außerhalb des Repositorys.

## Beobachtung

- Aufnahme manuell beendet; letzter Chunk bei 65,778 Sekunden. Die angegebenen
  120 Sekunden sind das konfigurierte Limit, nicht die tatsächliche Dauer.
- BDE-Sollwert auf DP 0x0227 zunächst 21 °C, ab 7,669 Sekunden 18 °C;
  anschließend bis zum Ende wiederholt 18 °C. Damit ist die Übertragung des
  geänderten Panel-Sollwerts belegt, keine erfolgreiche eigene HA-Steuerung.
- BDE-Raumtemperatur DP 0x0226 konstant 22,50034 °C: Differenz zum neuen
  Sollwert etwa 4,5 K.
- Betriebsart Eco Sommer und Luftstufe 1 bleiben unverändert.
- 0x0160 konstant Payload 01; 0x0208 konstant 0a100080. Hier ist kein
  Zustandswechsel dieser Datenpunkte zu beobachten. Daraus folgt keine
  vollständige Dekodierung der Schaltzustände oder Sperrbedingungen.
- Zulufttemperatur konstant 21,1 °C. Der Betreiber berichtet, dass die
  Kühlung nicht anlief. Der Mitschnitt enthält etwa 58 Sekunden nach der
  ersten beobachteten Sollwertänderung; spätere Reaktionen bleiben offen.
- 1176 vollständig gefundene Telegrammkandidaten bestehen die Prüfsumme.
  Diagnose ohne Verbindungsabbrüche, Prüfsummen- oder Wertefehler;
  application_bytes_sent bleibt null.

## Technikerauskunft und Grenzen

Laut Betreiber nennt der Techniker mehrere Voraussetzungen für den Kühlstart;
zu ihnen gehört eine Solltemperatur 3 °C unter der Isttemperatur. Die gemessene
Differenz zwischen übertragenem BDE-Ist- und Sollwert ist hier größer.
Die vollständige Freigabelogik, der dafür verwendete Ist-Fühler, Hysterese und
mögliche Verzögerungen sind damit nicht nachgewiesen. Es wird weder ein Defekt
noch eine fehlende konkrete Startbedingung aus dieser Aufnahme abgeleitet.

Für die Integration bleiben Sollwert, Kühlfreigabe und tatsächlicher Kühlbetrieb
unterschiedliche Größen. Aus Soll < Ist darf kein binärer Sensor „Kühlung aktiv“
abgeleitet werden. Die nächste belastbare Vergleichsaufnahme zeigt den normalen
Übergang am BDE samt Schaltzuständen; alternativ helfen dokumentierte vollständige
Startbedingungen. Kein wiederholtes Heizen/Kühlen-Umschalten für diesen Nachweis.

Anlagenkontext: [Referenzanlage mit nachgerüsteter Kühlung](ANLAGENPROFIL.md).

## Folgeaufnahme: Wechsel zu Komfort, 10:07:23 Ortszeit

Export mit Kennzeichnung (7), 32948 Bytes, reguläres 120-Sekunden-Limit,
letzter Chunk bei 119,971 Sekunden. Alle 2167 vollständig gefundenen
Telegrammkandidaten bestehen die Prüfsummenprüfung. Diagnose weiterhin ohne
Verbindungsabbrüche oder Wertefehler, keine von HA gesendeten Busbytes.

| Zeit ab Aufnahmebeginn | Beobachtung auf dem Bus |
|---|---|
| 0,451 s | Betriebsart 0x020A = 1, Eco Sommer |
| 10,541 s | Betriebsart 0x020A = 3, Komfort |
| 10,764 s | 0x006C: 25000000 → 65000000 |
| 10,880 s | 0x0208: 0a100080 → 1a100080 |
| 11,051 s | Luftstufe 0x00E1: 1 → 3 |
| 15,655 s | Panel-Datenpunkt 0x022C: 0000 → 0100, Bedeutung offen |
| 15,763 s | 0x006C: 65000000 → e7020000 |
| 15,864 s | 0x0208: 1a100080 → 22140080 |
| 17,964 s | 0x0120: 0000 → 1e00, Bedeutung offen |
| 20,826 / 26,075 s | 0x006C: c7020000 / a7020000 |
| 77,154 / 103,307 s | 0x0519: 0f00 → 1400 → 1b00, Bedeutung offen |
| 110,132 s | 0x006C: a7020000 → 27020000 |
| 110,242 s | 0x0208: 22140080 → 22150080 |

Solltemperatur durchgehend 18 °C, übertragene Raumtemperatur 22,50034 °C.
0x0160 bleibt 01. Die Zuluftdrehzahl steigt von etwa 933 auf zuletzt 2562 rpm,
die Abluftdrehzahl von etwa 893 auf zuletzt 2585 rpm. Die Datenpunkte 0x022C,
0x0120 und 0x0519 erhalten trotz zeitlicher Korrelation keine geratenen Namen.
Die Herkunft des zusätzlichen Panel-Zustandswechsels (automatisch oder weitere
Bedienung) ist durch den Mitschnitt allein nicht belegt.

### BDE-Fotos und zeitlicher Bezug

Die EXIF-Aufnahmezeiten liegen mit UTC+02:00 innerhalb des Mitschnitts; eine
sekundengenaue Synchronisierung zwischen Kamera und HA wurde nicht geprüft.

- Foto IMG_1610, 10:08:17 (ungefähr +54 s): Zuluft 2538 rpm, Abluft 2487 rpm,
  **Kompressor 0 rpm**, T1 20,9 °C, T2 22,5 °C.
- Foto IMG_1611, 10:08:30 (ungefähr +67 s): T7 23,0 °C, T8 19,6 °C,
  T10 21,0 °C, T12 21,6 °C, T13 19,8 °C; diese Temperaturwerte stimmen
  mit den Werten im entsprechenden Aufnahmeabschnitt überein.
- Foto IMG_1612, 10:08:51 (ungefähr +88 s): Bypass Ein, PTC-Wohnen Aus,
  MV-Abtau Ein, MV-Vorwärme Aus, MV-Heizen/Kühlen Ein.

Gegen Aufnahmeende (etwa +100 bis +116 s) fällt T1 von 20,8 auf 19,0 °C,
T10 von 21,0 auf 19,3 °C; T4 steigt bis 22,5 °C. Diese spätere thermische
Reaktion ist mit Kühlung vereinbar, beweist jedoch allein keinen Kompressorstart.
Das Foto mit 0 rpm stammt aus einem früheren Abschnitt und widerlegt deshalb
keinen möglichen späteren Start. Die Bezeichnung MV-Abtau Ein allein wird
nicht mit einem laufenden Abtauprozess gleichgesetzt.

### Konsequenz für die Integration

Der Betriebsartwert 3 = Komfort ist jetzt zusätzlich an einer ausdrücklich
benannten Bedienhandlung auf dieser Anlage geprüft. Das liefert keine
vollständige Definition aller Komfort-Freigabebedingungen.
Mehrere Bits in 0x006C/0x0208 ändern sich zusammen mit mehreren Schaltzuständen.
Mit diesem einzigen Wechsel können MV-Abtau und MV-Heizen/Kühlen noch nicht
eindeutig einzelnen Bits zugeordnet werden. Deshalb noch keine neuen binären
Sensoren mit diesen Namen und kein abgeleiteter Zustand „Kühlung aktiv“.

## Folgeaufnahme: laufende Kühlung, 10:15:20 Ortszeit

Export (8), 11302 Bytes, manuell beendet nach 41,760 Sekunden. Alle 741
vollständig gefundenen Telegrammkandidaten bestehen die Prüfsummenprüfung.
Sollwert weiterhin 18 °C, Betriebsart Komfort, Luftstufe 3.

Foto IMG_1613 um 10:15:27 (EXIF UTC+02:00) zeigt Zuluft 2559 rpm,
Abluft 2563 rpm, Kompressor 5430 rpm, T1 10,0 °C und T2 22,5 °C.
Im Mitschnitt liegen T1 bei 10,0 bis 9,8 °C, Frischluft bei 18,7 bis
18,6 °C und die übertragene Raumtemperatur bei 22,50034 °C. Zusammen
mit dem laufenden Kompressor belegt dies die inzwischen aktive Kühlung
in diesem Versuch. Die vollständigen Startbedingungen bleiben unbekannt.

### Kompressordrehzahl auf 0x051C

Die vier Payload-Bytes ergeben als Float32 Little Endian:

| Zeit ab Aufnahmebeginn | Payload | Wert |
|---|---|---|
| 4,727 / 10,026 s | 56b5a945 | 5430,667 |
| 15,358 / 20,735 s | 56f7a945 | 5438,917 |
| 25,958 s | 5749a945 | 5417,167 |
| 31,254 / 36,553 s | 5725a945 | 5412,667 |

Das Foto liegt zwischen den beiden ersten Busbeobachtungen und zeigt
5430 rpm, passend zum übertragenen Wert mit weniger als 1 rpm Abweichung.
Die vorige Aufnahme (7) lieferte auf diesem Datenpunkt durchgehend null;
das damalige Foto zeigte ebenfalls Kompressor 0 rpm. Damit ist 0x051C
als Kompressordrehzahl an der Referenzanlage stark durch den BDE-Abgleich
belegt. Die genaue Rundungsregel des BDE und der gesamte zulässige
Drehzahlbereich sind noch nicht bestimmt. Ein künftiger Drehzahlsensor
darf aus einem positiven Wert allein keinen Kühlmodus ableiten, weil
ein Kompressor auch zum Heizen laufen kann. Noch keine Codeänderung.

### Schaltzustände bleiben getrennt von Betriebszuständen

Foto IMG_1614 um 10:15:49 zeigt Bypass Ein, PTC-Wohnen Aus, MV-Abtau
Aus, MV-Vorwärme Aus und MV-Heizen/Kühlen Ein. Gegenüber IMG_1612
hat sich auf dieser BDE-Seite allein MV-Abtau von Ein zu Aus geändert.
0x006C bleibt in der neuen Aufnahme auf 27020000, 0x0208 auf 22150080
und 0x0160 auf 01. Gegenüber dem Abschnitt von IMG_1612 änderte sich
in 0x006C Bit 7 (a7020000 → 27020000) und in 0x0208 Bit 8
(22140080 → 22150080), jeweils als Little-Endian-Ganzzahl betrachtet.
Der Kompressor ist inzwischen ebenfalls angelaufen. Deshalb ist die
Zuordnung eines einzelnen Bits zum Magnetventil weiterhin eine Hypothese.
Die Anzeige MV-Abtau Aus widerspricht dem laufenden Kompressor nicht;
Ventilansteuerung und tatsächlicher Betriebsmodus sind getrennte Größen.

Die unbekannten Werte 0x0120 (5900/5a00) und 0x0519 (5000/5100)
werden trotz Korrelation mit dem Kompressorbetrieb nicht umbenannt.

## Folgeaufnahme: Sollwert 18 → 26 °C, 10:20:27 Ortszeit

Export (9), 32814 Bytes, letzter Chunk bei 119,925 Sekunden. Alle 2156
vollständig gefundenen Telegrammkandidaten bestehen die Prüfsummenprüfung.
Komfort, Luftstufe 3 und Raumtemperatur 22,50034 °C bleiben unverändert.

| Zeit ab Aufnahmebeginn | Beobachtung |
|---|---|
| 10,680 s | Panel 0x0227: 18 → 26 °C |
| 11,358 s | 0x0208: 22150080 → 22110080 |
| 13,576 s | 0x0120: 5a00 → 1e00 |
| 14,786 s | 0x0519: 5100 → 1b00 |
| 4,540 bis 98,681 s | 0x051C: rund 5326 → 3534 rpm, stufenweise sinkend |
| 67,023 s | 0x051C: 4271,935 rpm |
| 102,660 s | 0x0120: 1e00 → 0000 |
| 103,980 s | 0x051C: 00000000 = 0 rpm |
| 105,541 s | 0x006C: 27020000 → 25020000 |
| 105,651 s | 0x0208: 22110080 → 1a100080 |

Der Bus meldet etwa 93 Sekunden nach der ersten Sollwertänderung null
Kompressordrehzahl. Dies beschreibt den beobachteten Ablauf, keine allgemeine
Abschaltverzögerung. Die Zulufttemperatur steigt im Mitschnitt von 9,7 auf
12,5 °C; die Lüfter gehen von rund 2561/2548 auf 1864/1860 rpm zurück.
T13 steigt von 76,9 auf 82,6 °C. Aus diesem einzelnen Temperaturverlauf
wird keine Aussage über zulässige Grenzwerte oder einen Defekt abgeleitet.

### Fotos und Bestätigung

- IMG_1615, 10:21:31: Bypass Ein, PTC-Wohnen Ein, MV-Abtau Aus,
  MV-Vorwärme Aus, MV-Heizen/Kühlen Ein.
- IMG_1616, 10:21:42: Kompressor 4271 rpm, Zuluft 2525 rpm,
  Abluft 2564 rpm, T1 10,4 °C, T2 22,5 °C. Der Buswert 4271,935 rpm
  liegt im zeitlich passenden Abschnitt. Das bestätigt 0x051C an einem
  weiteren von null verschiedenen Betriebspunkt.
- IMG_1617, 10:21:50: T7 22,8 °C, T8 20,0 °C, T10 7,9 °C,
  T12 22,8 °C, T13 81,4 °C.
- IMG_1618, 10:22:29: Kompressor 0 rpm, Zuluft 1863 rpm,
  Abluft 1860 rpm, T1 12,5 °C, T2 22,5 °C.
- IMG_1619, 10:22:35: T10 11,7 °C, T13 82,8 °C; IMG_1620,
  10:22:43: gleiche Schaltzustände wie IMG_1615.

Die letzten drei Fotos entstanden nach Aufnahmeende (ca. 10:22:27,692).
Sie werden deshalb nicht als exakt gleichzeitige Busmessung ausgegeben.
Auch innerhalb der Aufnahme ist die sekundengenaue Uhrensynchronisierung
von Kamera und HA nicht geprüft.

PTC-Wohnen ist nun erstmals auf den Vergleichsfotos Ein. Das ist eine
BDE-Schaltanzeige, kein Nachweis der elektrischen Leistungsaufnahme.
Das Löschen von Bit 10 in 0x0208 fällt unmittelbar nach der Sollwertänderung
auf; ob es PTC-Wohnen, eine Kühlanforderung oder etwas anderes abbildet,
bleibt offen. Bit 1 in 0x006C ändert sich erst nahe der Kompressorabschaltung
und kann daher nicht pauschal mit PTC-Wohnen gleichgesetzt werden.
Ein anschließender Wärmepumpen-Heizbetrieb ist hier noch nicht belegt.

### Korrektur der Sollwertauswertung

Der bisherige Empfangsfilter erlaubte nur 15–25 °C und verwarf deshalb
21 gültige Telegramme mit 26 °C. Die obere Grenze wurde auf die jetzt
belegten 26 °C erweitert, ohne daraus den gesamten Einstellbereich der
Anlage abzuleiten. Der Replay liest nun alle 23 Sollwerttelegramme
(18 → 26 °C), bei null abgelehnten Werten. Ein Regressionstest verwendet
das aufgezeichnete 26-°C-Telegramm samt seiner tatsächlichen Prüfsumme.
Die Änderung ist lokal vorbereitet; damit ist noch kein HACS-Update erfolgt.

## Folgeaufnahme: 30 °C und grüne BDE-LED, 10:28:56 Ortszeit

Der Betreiber bestätigt den BDE-Einstellbereich 18–30 °C und berichtet nach
Erhöhung auf 30 °C eine grüne LED. Nach seiner Erklärung ist diese bei Heizen
und Kühlen die sichtbare Betriebsanzeige; eine Schaltanzeige „Ein“ allein
genügt nicht. Diese Bedienbeobachtung ist keine bereits dekodierte LED-Bitmaske.

Export (10) wurde während laufender Aufnahme heruntergeladen (`recording`)
und enthält nur 24,052 Sekunden bzw. 6438 Bytes, nicht das konfigurierte
120-Sekunden-Limit. Alle 428 vollständig gefundenen Telegrammkandidaten
bestehen die Prüfsummenprüfung. Die Solltemperatur ist bereits ab dem ersten
enthaltenen Panel-Telegramm 30 °C; der Wechsel und der Zeitpunkt des
LED-Einschaltens sind nicht im Export lokalisiert.

- Komfort, Luftstufe 3, Raumtemperatur 22,50034 °C.
- T1-Zuluft steigt von 22,2 auf 25,8 °C, T10 von 20,4 auf 23,1 °C.
- T4-Fortluft sinkt von 20,0 auf 16,7 °C, T6 von 18,6 auf 15,1 °C.
- T3-Frischluft bleibt 18,9 °C; T13 sinkt von 78,1 auf 77,2 °C.
- 0x0160 ist jetzt 00 statt zuvor 01: erster beobachteter Gegenwert zum
  bisherigen Bypass-Ein. Eine gleichzeitige neue BDE-Schaltseite fehlt noch.
- 0x006C = 27000000, 0x0208 = 1a130080, 0x0120 = 1e00,
  0x0519 = 1b00. Diese Werte ändern sich innerhalb der kurzen Aufnahme nicht.

LED-Beobachtung und Temperaturverlauf sind mit Heizbetrieb vereinbar. Sie
werden nicht als Beweis für eine bestimmte einzelne Heizkomponente verwendet.
**0x051C bleibt in allen fünf Antworten null.** Die zuvor gute Übereinstimmung
mit der BDE-Kompressordrehzahl im Kühlbetrieb reicht deshalb noch nicht aus,
um den Datenpunkt als allgemeine Kompressordrehzahl in allen Betriebsarten
freizugeben. Ein zeitgleicher BDE-Wert für n-Kompressor im Heizbetrieb fehlt.
Mögliche Verzögerung, unterschiedliche Datenquellen oder eine andere
Heizkomponente bleiben offen; keine dieser Erklärungen ist schon bestätigt.

Der Empfangsfilter wurde bis 30 °C erweitert. Die bisherige untere
Plausibilitätsgrenze 15 °C bleibt für andere Varianten erhalten; der
beobachtete lokale Bedienbereich ist separat 18–30 °C dokumentiert.
Dieser reine Lesefilter ist kein Stellbereich einer schreibenden HA-Entität.
Replay bestätigt fünf Sollwerttelegramme mit 30 °C und null Wertefehler.
Regressionstests enthalten die tatsächlichen 26- und 30-°C-Telegramme;
17 gezielte Decoder-Tests bestehen. Änderung weiterhin lokal, nicht veröffentlicht.

### Nachgereichte BDE-Fotos: Heizbetrieb um 10:30 Uhr

- IMG_1621, EXIF 10:30:19 UTC+02:00: grüne LED, Bypass Aus,
  PTC-Wohnen Ein, MV-Abtau Aus, MV-Vorwärme Aus, MV-Heizen/Kühlen Aus.
- IMG_1622, 10:30:27: Kompressor 2510 rpm, Zuluft 1774 rpm,
  Abluft 1734 rpm, T1-Zuluft 31,7 °C, T2-Wohnen 22,5 °C.
- IMG_1623, 10:30:32: T7 22,9 °C, T8 19,7 °C, T10 27,5 °C,
  T12 24,7 °C, T13 72,5 °C.

Kompressordrehzahl, warme Zuluft und grüne LED belegen jetzt Heizbetrieb
an der Referenzanlage. MV-Heizen/Kühlen Aus ist dabei die beobachtete
Ventilanzeige und bedeutet nicht „Heizung aus“. Sie darf nicht als einfacher
Ein/Aus-Sensor des gesamten Heiz-/Kühlbetriebs verwendet werden.

Export (10) endet bereits um 10:29:20,215 Ortszeit. Das Drehzahlfoto liegt
rund 67 Sekunden später. Deshalb widersprechen dessen 2510 rpm dem zuvor
aufgezeichneten Nullwert auf 0x051C nicht unmittelbar. Die mögliche Zuordnung
als allgemeine Kompressordrehzahl ist weder widerlegt noch im Heizbetrieb
bestätigt. Dafür fehlt eine zeitlich überlappende Aufnahme mit BDE-Referenz.
Auch Bypass Aus passt zum vorherigen 0x0160 = 00, ist aber kein gleichzeitiger
Abgleich; das spätere Foto wird nicht rückwirkend als synchroner Messwert benutzt.

## Folgeaufnahme: Drehzahl im Heizbetrieb bestätigt, 10:33:23 Ortszeit

Export (11) beginnt um 10:33:23,752 und endet um 10:35:23,739 Ortszeit
(119,987 Sekunden, 32598 Bytes). Alle 2150 vollständig gefundenen
Telegrammkandidaten bestehen die Prüfsumme. Der lokal korrigierte Decoder
liest 23 Sollwerttelegramme mit 30 °C ohne Wertefehler; Komfort und Luftstufe 3.

### Zeitlich überlappende BDE-Drehzahlreferenzen

| Fotos / EXIF-Ortszeit | BDE n-Kompressor | Zeitlich passender 0x051C-Float32-LE-Wert |
|---|---|---|
| IMG_1624 10:33:40, IMG_1625 10:33:45 | 4851 rpm | 4851,6758 rpm, ab +11,384 s |
| IMG_1626 10:33:47, IMG_1627 10:33:50 | 4845 rpm | 4845,6758 rpm, ab +21,894 s |
| IMG_1630 10:34:46, IMG_1631 10:34:47 | 3429 rpm | 3429,6975 rpm, ab +79,750 s |

Alle diese Fotos liegen innerhalb der Aufnahme. Mehrere übereinstimmende
Betriebspunkte bestätigen 0x051C jetzt auch im Heizbetrieb an der Referenzanlage.
Der zuvor fehlende Heiznachweis ist damit erbracht. Die Sub-rpm-Abweichung ist
mit der ganzzahligen BDE-Anzeige vereinbar; keine sekundengenaue Synchronisierung
oder universelle Gerätekompatibilität wird daraus abgeleitet. Die Busdrehzahl
sinkt über die Aufnahme von rund 4847 auf 2562 rpm, die Zuluft steigt von
45,8 auf zuletzt 48,0 °C. Ein positiver Drehzahlwert unterscheidet weiterhin
nicht zwischen Heizen und Kühlen. Die semantische HA-Entität ist noch nicht ergänzt.

### Bypass und nach Aufnahmeende gehörtes Knacken

0x0160 meldet in allen 22 Antworten 00. Auch IMG_1629 um 10:34:04 zeigt
bereits Bypass Aus, PTC-Wohnen Ein, MV-Abtau Aus, MV-Vorwärme Aus und
MV-Heizen/Kühlen Aus. Damit ist 0x0160 = 00 jetzt innerhalb desselben
Aufnahmezeitraums mit der BDE-Anzeige Bypass Aus abgeglichen; zuvor war
01 mit Bypass Ein beobachtet worden. Das beschreibt den gemeldeten Status,
nicht den Nachweis eines mechanischen Positionssensors.

Der Betreiber berichtet ein Knacken nach Ende der 120 Sekunden. Eine
Geräuschaufnahme bzw. ein Busmitschnitt dieses Ereignisses fehlt. Weil der
Bypass vorher bereits Aus war, wird das Geräusch keiner Bypassabschaltung
oder anderen Komponente zugeordnet. Die neu bereitgestellten Fotos liegen
laut EXIF sämtlich vor Aufnahmeende. 0x006C bleibt 27000000 und 0x0208
1a130080; darin ist in dieser Aufnahme kein Schaltwechsel enthalten.

### Neue Temperaturgrenze: mögliche negative Werte

Die ersten zwei 0x03B7-Telegramme enthalten für T4/T6 die Wortwerte
65533/65528 bzw. 65534/65535. Als vorzeichenbehaftete Zehntelgrade wären
das -0,3/-0,8 bzw. -0,2/-0,1 °C, gefolgt von nichtnegativen Werten.
Der Verlauf ist ein neuer Hinweis auf signed int16, aber eine passende
BDE-Aufnahme der negativen T4/T6-Werte fehlt noch. Keine automatische
Umdeutung von 65535, das in anderen Kontexten auch ein Fehlerwert sein kann.
Der bisherige Decoder lässt deshalb diese vier Teilwerte aus, während die
übrigen Temperaturkanäle weiter aktualisiert werden (T4/T6 je 21 statt 23
Messwerte). Sein framebezogener Zähler value_rejected bleibt dabei null;
das bedeutet nicht, dass jeder einzelne Temperatur-Slot akzeptiert wurde.

## Folgeaufnahme: Sollwert zurück auf 21 °C, 10:39:37 Ortszeit

Export (12), 33108 Bytes, Beginn 10:39:37,742 und letzter Chunk
10:41:37,731 Ortszeit (119,989 Sekunden). Alle 2179 vollständig gefundenen
Telegrammkandidaten bestehen die Prüfsumme. Der lokale Decoder liefert
23 Sollwertmessungen, ohne Werte- oder Prüfsummenfehler.

- Bei +14,028 s wird auf Panel-DP 0x0227 erstmals 21 statt 30 °C übertragen.
  Komfort, Luftstufe 3 und Raumtemperatur 22,50034 °C bleiben unverändert.
- Kompressordrehzahl 0x051C zunächst 2611,46 rpm, später rund 2020 rpm;
  letzter Wert bei +116,559 s ist 2026,47 rpm. Kein Nullwert enthalten.
- Bei +53,663 s sind es 2018,219 rpm. IMG_1634 um 10:40:31 liegt
  im zeitlich passenden Abschnitt und zeigt 2018 rpm, T1 47,3 °C,
  T2 22,5 °C und eine grüne LED.
- T1 sinkt während der gesamten Aufnahme von 47,4 auf 44,8 °C, T10 von
  46,7 auf 43,1 °C. T13 steigt von 78,7 auf 79,8 °C. Der Heizbetrieb
  endet nicht unmittelbar mit der Sollwertabsenkung; die Aufnahme umfasst
  knapp 106 Sekunden nach dem ersten übertragenen 21-°C-Wert.
- Ob Mindestlaufzeit, Hysterese, interne Regelgrößen oder ein anderer
  Mechanismus den weiteren Betrieb erklärt, ist nicht belegt. Es wird
  weder eine feste Nachlaufdauer noch ein Defekt daraus abgeleitet.

### PTC-Anzeige und Grenzen der Statuswort-Hypothesen

IMG_1632 um 10:36:03 liegt vor dieser Aufnahme und zeigt PTC-Wohnen Ein.
IMG_1633 um 10:40:21 liegt innerhalb der Aufnahme und zeigt sämtliche
fünf Schaltanzeigen Aus, weiterhin mit grüner LED. Somit kann eine vollständig
auf Aus stehende BDE-Schaltseite mit laufendem Kompressor zusammenfallen.
Der genaue Zeitpunkt des PTC-Wechsels ist durch die Fotos nicht erfasst.

0x006C bleibt hier durchgehend 27000000 und 0x0208 durchgehend 1a130080,
also identisch mit den Heizaufnahmen (10)/(11), zu denen PTC-Wohnen Ein
fotografiert wurde. Eine direkte zustandslose Bitzuordnung dieser beiden
Wörter zu PTC-Wohnen ist damit durch die vorhandenen Daten nicht gestützt.
0x0160 bleibt 00 und passt weiterhin zu Bypass Aus.
0x0168 ist bereits ab der ersten enthaltenen Antwort 00 statt zuvor 02;
der Wechsel liegt zwischen den Mitschnitten und seine Bedeutung bleibt offen.
0x0120 geht bei +16,817 s auf 1e00, 0x0519 bei +17,918 s auf 1b00.
Diese Korrelation allein benennt weder einen PTC-Ausgang noch eine Freigabe.

Für die Integration bleiben Solltemperatur, Kompressordrehzahl, BDE-Schaltanzeige
und aktiver Heiz-/Kühlbetrieb getrennte Größen. Aus Ist > Soll oder allen
Schaltanzeigen Aus darf kein automatischer Kompressor-Aus-Zustand entstehen.
