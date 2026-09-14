# Intensivlüftung: getrennte Einstellung der Dauer

Stand: 14.09.2026. Geltungsbereich: [lokale Referenzanlage](ANLAGENPROFIL.md).
Die Abschnitte halten die Untersuchung chronologisch fest. Aktuelles Ergebnis:
Das automatische Ende nach ungefähr 30 Minuten ist mit (17)/(18) bestätigt;
Dauer-/Restzeit-Datenpunkt und externer Schreibweg bleiben offen. 0x00E1 ist
eine Panel-Anforderung und kann von der BDE-Hauptanzeige abweichen; siehe letzter
Abschnitt zu Export (18).
Quellen: privater Diagnoseexport (13), Integration 0.4.0, und Video IMG_1636.MOV.
Die Originaldateien bleiben außerhalb des Repositorys.

## Bedienung am BDE

Der Betreiber berichtet: In Eco Sommer sind Luftstufen 1–4 und Automatik
wählbar. In Komfort bietet das BDE stattdessen Intensivlüftung ein/aus an;
die Dauer lässt sich in einem separaten Menü einstellen. Das Video bestätigt
die beiden getrennten Menüs in Komfort. Eco Sommer und dessen Automatik
werden durch diesen Versuch nicht zusätzlich geprüft.

Im Video ist folgende Auswahlfolge erkennbar: 120 → 110 → 100 → 30 → 35 →
120 Minuten. Die Auswahl wird jeweils mit Rückkehr ins Hauptmenü abgeschlossen;
110, 100, 30 und 35 Minuten sind auch beim erneuten Öffnen sichtbar.
Die sichtbaren Listeneinträge liegen in Schritten von fünf Minuten. Daraus
folgt noch kein vollständig geprüfter Einstellbereich.

| Videozeit, ungefähr | Beobachtung |
|---|---|
| 15 s | Ausgangsauswahl 120 Minuten |
| 21–22 s | 110 Minuten bestätigt, Rückkehr ins Hauptmenü |
| 33–34 s | 100 Minuten bestätigt |
| 46–47 s | 30 Minuten bestätigt |
| 60–61 s | 35 Minuten bestätigt |
| 73–74 s | 120 Minuten ausgewählt, Rückkehr ins Hauptmenü |
| 88 s | Hauptanzeige Komfort, Luftstufe 3 |
| 91–94 s | Menü Intensivlüftung ein/aus; keine Aktivierung im Bus beobachtet |

## Zeitliche Abdeckung und Prüfung

- Mitschnittstart 10:54:19,658 Ortszeit; letzter Chunk bei 114,056 Sekunden,
  entsprechend 10:56:13,714. Der Export meldet noch `recording`; 120 Sekunden
  sind die konfigurierte Obergrenze, nicht die exportierte Länge.
- Video: 94,352 Sekunden; Erstellungszeit laut Videometadaten 10:54:26 +02:00.
  Unter Annahme übereinstimmender Geräteuhren liegt das gesamte Video innerhalb
  des Mitschnitts. Die Zuordnung ist keine separat vermessene Uhrensynchronisation.
- 32.340 Bytes in 2.192 Chunks. Der vorhandene Prüfer findet 2.131 Kandidaten
  der vier üblichen Header; alle bestehen die Prüfsumme.
- Eine zusätzliche sequenzielle Offline-Prüfung ohne Beschränkung auf diese
  vier Header findet 2.223 gültige Frames und deckt alle 32.340 Bytes lückenlos ab.
  Verwendet werden das vorhandene Prüfsummenmodell, die Header-Längenangabe
  (gerade Halbbyteanzahl, maximal 112 Payloadbytes) und reservierte Nullbytes.
  Weitere Header sind `118007`, `108007`, `e34100`, `e24100`, jeweils 23 Frames.
  Vollständige Frame-Abdeckung bedeutet keine vollständige semantische Dekodierung.
- Gruppierung nach den ersten drei Headerbytes und Datenpunkt: Veränderungen
  finden sich nur bei 0x0226, 0x00C9, 0x03B7, 0x0330 und 0x032E. Kein weiterer
  Payload wechselt passend zu den ausgewählten Minutenwerten.
- Produktionsdecoder offline: 771 akzeptierte Werte, keine Prüfsummen- oder
  Wertefehler. Komfort, Solltemperatur 21 °C und Luftstufe 3 bleiben konstant;
  Kompressordrehzahl 0x051C bleibt null. Es erfolgte kein Zugriff auf die Anlage.

## Schlussfolgerung und nächster Versuch

Dieser Mitschnitt belegt keinen Datenpunkt für die eingestellte Dauer. Insbesondere
ist das Ausbleiben eines Dauerwerts nicht allein durch die begrenzte Liste der
Produktionssensoren erklärt: Auch die übrigen gültigen Frames wurden verglichen.

Mögliche Erklärungen sind eine lokale Speicherung/Zeitsteuerung im BDE oder eine
Übertragung erst bei Aktivierung. Beide bleiben Hypothesen; ebenso ist daraus
keine generelle Nichtlesbarkeit über HESP abzuleiten. Keine Dauer-Entität und
keine Schreibfunktion auf dieser Grundlage anlegen.

Als Nächstes Intensivlüftung in Komfort bei unveränderter Dauer aktivieren und
wieder beenden: etwa 20 Sekunden Ausgangszustand, Aktivierung, etwa 40 Sekunden
laufen lassen, manuell deaktivieren und den Rest des Mitschnitts abwarten.
Start und Ende am BDE zeitlich dokumentieren. So lassen sich Stufe 4, ein mögliches
Aktivierungssignal und eine eventuell erst dann gesendete Dauer auseinanderhalten.
Ein automatisches Ende ist damit noch nicht geprüft.

## Aktivierung und manuelles Ende: Mitschnitt (14)

Quellen: Diagnoseexport (14), Videos IMG_1637.MOV und IMG_1638.MOV.
Aufnahme 10:58:38,655–11:00:38,652 Ortszeit; Status `duration_limit`, tatsächlich
119,997 Sekunden und 33.130 Bytes. Alle 2.178 Kandidaten der üblichen vier
Header bestehen die Prüfsumme. Die erweiterte sequenzielle Prüfung erfasst
2.274 gültige Frames und sämtliche Bytes, einschließlich 24 Frames pro
zusätzlichem Header `118007`, `108007`, `e34100`, `e24100`.
Offline-Wiedergabe im Produktionsdecoder: 789 akzeptierte Werte, keine
Prüfsummen- oder Wertefehler. Die Luftstufe 3 → 4 → 3 wird bereits dekodiert;
0x01F8 wird noch nicht als Entität ausgegeben.

### BDE- und Busabgleich

Video 1637 dauert 20,540 Sekunden, Erstellungszeit 10:58:43 +02:00.
Bei etwa 13 Sekunden wird Intensivlüftung ein bestätigt. Ab 17 Sekunden zeigt
die Hauptanzeige **Komfort, Luftstufe 4, 120min**.

Video 1638 dauert 41,563 Sekunden, Erstellungszeit 10:59:06 +02:00. Es zeigt
zunächst den laufenden Vorgang. Bei etwa 24 Sekunden wird die separate Dauer
auf **30 Minuten** gestellt. Die Hauptanzeige zeigt danach, bei 27–29 Sekunden,
weiter **Luftstufe 4, 120min**. Bei etwa 34 Sekunden wird Intensivlüftung aus
bestätigt; bei 38–39 Sekunden ist die Minutenanzeige verschwunden, zunächst
steht noch Luftstufe 4. Bei 40–41 Sekunden wird Luftstufe 3 angezeigt.
Die Videometadaten dienen zur ungefähren Zuordnung, nicht als Nachweis einer
exakten Synchronisation mit HA oder der nachlaufenden BDE-Uhr.

| Zeit seit Mitschnittstart | Telegramm | Beobachteter Wechsel |
|---|---|---|
| 17,934 s | Panel 0x00E1 | `0300` → `0400`: Luftstufe 3 → 4 |
| 21,551 s | Controller 0x0208 | `1a100080` → `22100080` |
| 21,631 s | Panel 0x01F8 | `00000000` → `40000000` |
| 22,051 s | Controller 0x00D7 | Zwei float32 LE: jeweils 5200 → 10000; Skalierung/Einheit hier nicht belegt |
| ca. 51 s | BDE-Dauerwahl 120 → 30 Minuten | Kein zusätzlicher passender Payloadwechsel |
| 61,931 s | Panel 0x00E1 | `0400` → `0300`: Luftstufe 4 → 3 |
| 62,827 s | Panel 0x01F8 | `40000000` → `00000000` |
| 63,264 s | Controller 0x00D7 | Beide Werte zurück auf 5200 |
| 67,804 s | Controller 0x0208 | `22100080` → `1a100080` |

Die Zeiten sind erste empfangene Änderungen, keine gemessenen internen
Schaltverzögerungen. Periodische Telegramme können den Zustandswechsel später
wiedergeben als der unmittelbare Luftstufenbefehl.

Die tatsächlichen Lüfterdrehzahlen in 0x00C9 steigen von ungefähr 1750 rpm auf
2500–2600 rpm und fallen nach dem Beenden wieder in Richtung 1750 rpm.
Video 1638 zeigt bei 12–15 Sekunden Zuluft 2481 rpm und Abluft 2462 rpm;
der Mitschnitt liefert bei 37,530 Sekunden 2481,596 / 2462,775 rpm.
Bei 16 Videosekunden zeigt das BDE 2544 / 2538 rpm, passend zu
2544,203 / 2538,833 rpm bei 42,829 Mitschnittsekunden.
Komfort, Solltemperatur 21 °C und Kompressordrehzahl null bleiben erhalten.

### Bedeutung und Grenzen

- **0x01F8, Maske 0x00000040 (Bit 6 bei u32 LE)** ist ein starker Kandidat
  für die BDE-Intensivlüftungsanforderung. Einschalten und Ausschalten sind
  gemeinsam mit dem Video belegt. Ein einzelner Ein-/Aus-Versuch beweist noch
  keine Exklusivität gegenüber manueller Stufe 4 oder anderen Betriebsarten.
- 0x01F8 ist kein einfaches Gesamt-Boolean: In den bisherigen Heizaufnahmen
  (10), (11) und teilweise (12) kommt auch `00080000` vor, entsprechend
  Maske 0x00000800. Die Bedeutung dieses anderen Bits ist hier nicht bestimmt.
  In den Aufnahmen (1)–(13) wurde Bit 6 nicht gesetzt beobachtet.
- 0x0208 ist kein spezifischer Intensivlüftungsschalter: Der Wertwechsel
  `1a100080` → `22100080` kann eine allgemeinere Lüftungsanforderung abbilden.
  Das Feld bleibt ohne neue semantische Entität.
- Für eine Dauerübertragung gibt es auch beim Start dieses Vorgangs keinen
  getrennten Nachweis. Der Wechsel von 120 auf 30 Minuten ändert die sichtbare
  Restzeitanzeige des laufenden Vorgangs nicht unmittelbar. Das ist mit einer
  bei Aktivierung übernommenen Dauer vereinbar, beweist aber weder den Ort
  der Zeitsteuerung noch das tatsächliche spätere Abschaltverhalten.
- Nächster gezielter Gegenversuch: Mit den neu eingestellten 30 Minuten erneut
  einschalten, Hauptanzeige mit Dauer dokumentieren und wieder manuell beenden.
  Bleibt 0x01F8 bei `40000000`, obwohl das BDE nun 30 statt 120 Minuten anzeigt,
  stärkt das die Zuordnung als Aktivierungsbit unabhängig von der Dauer.
  Anschließend separat manuelle Stufe 4 in Eco Sommer prüfen, um eine allgemeine
  Stufe-4-Kennung von der Intensivlüftungsanforderung zu unterscheiden.

## Wiederholung mit 30 Minuten: Mitschnitt (15)

Quellen: Diagnoseexport (15) und Video IMG_1639.MOV. Aufnahme
11:13:58,313–11:15:58,236 Ortszeit, Status `duration_limit`, tatsächlich
119,923 Sekunden und 32.958 Bytes. Alle 2.168 Kandidaten der vier üblichen
Header bestehen die Prüfsumme. Die erweiterte Prüfung erfasst lückenlos
2.260 gültige Frames und sämtliche Bytes. Offline im Produktionsdecoder:
785 akzeptierte Werte, keine Prüfsummen- oder Wertefehler.

Das Video dauert 47,878 Sekunden; Erstellungszeit laut Metadaten
11:14:09 +02:00. Bei ungefähr 9 Sekunden wird Intensivlüftung ein bestätigt.
Ab 14 Sekunden zeigt die Hauptanzeige **Komfort, Luftstufe 4, 30min**;
bei ungefähr 41 Sekunden wird Intensivlüftung aus bestätigt. Die Rückkehr
zu Luftstufe 3 ist im Bus erfasst, die Hauptanzeige danach nicht mehr im Video.

| Zeit seit Mitschnittstart | Telegramm | Beobachteter Wechsel |
|---|---|---|
| 20,313 s | Panel 0x00E1 | `0300` → `0400` |
| 22,561 s | Controller 0x0208 | `1a100080` → `22100080` |
| 22,641 s | Panel 0x01F8 | `00000000` → `40000000` |
| 23,057 s | Controller 0x00D7 | Beide float32-Werte 5200 → 10000 |
| 52,741 s | Panel 0x00E1 | `0400` → `0300` |
| 54,058 s | Panel 0x01F8 | `40000000` → `00000000` |
| 54,466 s | Controller 0x00D7 | Beide Werte zurück auf 5200 |
| 58,862 s | Controller 0x0208 | `22100080` → `1a100080` |

Die Lüfterdrehzahlen steigen erneut von ungefähr 1750 auf 2500–2600 rpm
(kurzzeitig Abluft 2638 rpm) und fallen nach dem Beenden zurück.
Komfort, Solltemperatur 21 °C und Kompressordrehzahl null bleiben konstant.

Der Vergleich mit (14) zeigt bei 0x01F8 **dieselben Payloads und dieselbe
Ein-/Aus-Folge trotz unterschiedlicher sichtbarer Startdauer (120/30 Minuten)**.
Auch 0x00E1, 0x0208 und 0x00D7 zeigen dieselben Wertefolgen. Die sonstigen
Unterschiede der Payload-Wertemengen zwischen beiden Aufnahmen betreffen
0x0226, 0x00C9, 0x02D2, 0x02DF, 0x032E, 0x0330 und 0x03B7. Daraus wird
keine Zuordnung eines dieser Felder zur Dauer abgeleitet.

Damit ist Bit 6 von 0x01F8 in **zwei Komfort-Ein-/Aus-Versuchen mit
unterschiedlichen Dauern** als Begleitsignal der Intensivlüftungsaktivierung
belegt. Es enthält in diesen Versuchen weder die Minutenanzahl noch eine
mitlaufende Restzeit. Eine separate Dauerübertragung ist weiterhin nicht
identifiziert. Ein vollständig im BDE ausgeführter Timer bleibt eine Hypothese.

Zusammen mit (14) ist jetzt auch beobachtet: Die Änderung auf 30 Minuten ließ
die Anzeige des damals laufenden Vorgangs bei 120 Minuten; der nächste Start
verwendet 30 Minuten. Automatisches Abschalten nach der eingestellten Zeit ist
weiterhin nicht getestet.

**Verbleibender Gegenversuch:** Eco Sommer, zunächst manuell Stufe 3, dann
Stufe 4, anschließend zurück auf 3. Moduswechsel und Stufenwechsel zeitlich
trennen. So lässt sich prüfen, ob Bit 6 auch eine allgemeine Stufe-4-Kennung
sein könnte. Erst danach die Exklusivität als Intensivlüftungsstatus bewerten.
Die Wiederholung allein führt zu keiner neuen Steuerfunktion oder Dauer-Entität.

## Gegenvergleich: manuelle Stufen und Automatik in Eco Sommer (16)

Quellen: Diagnoseexport (16) und Video IMG_1640.MOV. Aufnahmebeginn
11:24:42,492 Ortszeit, letzter Chunk nach 115,458 Sekunden um 11:26:37,950.
Der Export meldet noch `recording`; die eingestellten 120 Sekunden sind nicht
vollständig enthalten. 32.054 Bytes, 2.105 Kandidaten der üblichen vier Header,
alle prüfsummengültig. Die erweiterte Prüfung erfasst lückenlos 2.193 gültige
Frames und sämtliche Bytes. Produktionsdecoder offline: 763 akzeptierte Werte,
keine Prüfsummen- oder Wertefehler.

Das Video dauert 82,435 Sekunden, Erstellungszeit 11:24:48 +02:00.
Es beginnt in Komfort und zeigt dann den Wechsel zu Eco Sommer einschließlich
einer Abfrage zur Kühlfreigabe. In diesem Versuch wird keine Bitzuordnung zu
dieser Freigabe vorgenommen. Danach sind die manuellen Stufen 4, 3, 2, 1 und
erneut 4 zu sehen. Bei etwa 68–71 Sekunden wird `Luftstufe auto` ausgewählt;
die Hauptanzeige zeigt danach Eco Sommer / Luftstufe 1. Beim erneuten Öffnen
des Luftstufenmenüs um 76 Sekunden ist weiterhin `Luftstufe auto` markiert.
Am Ende wird das Menü Zeitprogramm Sommer für Mittwoch geöffnet; eine Änderung
des Zeitprogramms ist nicht Teil dieses Versuchs. Die angezeigte Mittwochseite
belegt nicht das aktuell am Montag wirksame Zeitprogramm.

### Telegramme und unabhängiger Vergleich

| Zeit seit Mitschnittstart | Panel 0x00E1 | Kontext |
|---|---|---|
| 4,276 s | 3 | Ausgangszustand Komfort |
| 19,542 s | 4 | Wechsel zu Eco Sommer; 0x020A gleichzeitig 3 → 1 |
| 33,023 s | 3 | Manuell Stufe 3 |
| 44,246 s | 2 | Manuell Stufe 2 |
| 53,976 s | 1 | Manuell Stufe 1 |
| 62,924 s | 4 | Erneut manuell Stufe 4, Betriebsart jetzt unverändert |
| 75,320 s | 1 | Nach Auswahl von Automatik; wirksame Stufe 1 |

**0x01F8 bleibt während der gesamten Aufnahme `00000000`.** Insbesondere
bleibt Bit 6 auch bei der zweiten manuellen Stufe-4-Aktivierung aus. Diese
zweite Aktivierung ist vom Betriebsartwechsel getrennt und damit der
aussagekräftigere Gegenvergleich zu (14) und (15).

| Lokal beobachteter Zustand | Bit 6 in 0x01F8 | Panel-Luftstufe |
|---|---|---|
| Komfort, Intensivlüftung aus | 0 | 3 |
| Komfort, Intensivlüftung mit 120 Minuten | 1 | 4 |
| Komfort, Intensivlüftung mit 30 Minuten | 1 | 4 |
| Eco Sommer, manuell Stufe 4 | 0 | 4 |
| Eco Sommer, Automatik, wirksame Stufe 1 | 0 | 1 |

Damit ist **0x01F8 / Maske 0x00000040 als BDE-Intensivlüftungsanforderung
für die lokale Referenzanlage hinreichend belegt**, einschließlich zweier
Dauern, Ein-/Aus-Wechseln und Abgrenzung zur manuellen Stufe 4. Das trägt einen
künftigen lesenden Status, nicht automatisch einen eigenen Schreibbefehl oder
eine Zusage für alle Gerätevarianten. Das Feld muss als Bitmaske behandelt
werden; das bereits beobachtete andere Bit 0x00000800 bleibt davon unabhängig.

0x0208 folgt ebenfalls den Luftstufen. In dieser Aufnahme ergibt sich nach den
jeweiligen Aktualisierungen folgende Zuordnung:

| Wirksame Stufe | Payload 0x0208 | Beide float32-Werte in 0x00D7 |
|---|---|---|
| 1 | `0a100080` | 2500 |
| 2 | `12100080` | 4000 |
| 3 | `1a100080` | 5200 |
| 4 | `22100080` | 10000 |

0x0208 unterscheidet hier nicht zwischen manueller Stufe 4 und Intensivlüftung.
Die Zuordnung gilt für den übrigen unveränderten Zustand dieser Aufnahme und
ist keine vollständige Dekodierung des Statusworts. Für 0x00D7 bleibt die
Skalierung/Einheit offen; diese Werte sind insbesondere nicht die gemessenen
Lüfterdrehzahlen aus 0x00C9. Wegen der kurzen Haltezeiten werden keine stationären
Drehzahlen je Stufe aus diesem Versuch abgeleitet.

### Automatik und verbleibende Grenzen

Bei Automatik wird in 0x00E1 keine zusätzliche Auswahlkennung wie 0 oder 5
beobachtet, sondern die danach wirksame Stufe 1. Es darf deshalb weder
`fan_level == 1` als Automatik interpretiert noch aus 0x00E1 allein die manuelle
Auswahl rekonstruiert werden. Auch 0x01F8 ändert sich bei der Automatikwahl nicht.
Es gibt in diesem Mitschnitt keinen zusätzlich identifizierten Auto-Status.

Die Dauer-/Restzeitübertragung und das automatische Ende der Intensivlüftung
sind weiterhin offen. Weitere Wiederholungen der bisherigen Ein-/Aus-Tests
sind für die lokale Bit-6-Zuordnung zunächst nicht nötig. Ein separater Test
des Sommerzeitprogramms würde die bislang offene Automatikfunktion untersuchen.

## Implementierung in 0.5.0

Version 0.5.0 enthält die standardmäßig aktivierte Plattform
`binary_sensor` mit dem übersetzten Namen **Intensivlüftung aktiv** und dem
stabilen Schlüssel `intensive_ventilation`. Sie gehört zum bestehenden Gerät.
Der Decoder akzeptiert ausschließlich den beobachteten Panel-Header `118000`,
DP 0x01F8, vier Payloadbytes und eine gültige Prüfsumme. Ausgewertet wird nur
Maske 0x40; insbesondere löst das andere beobachtete Bit 0x0800 kein Ein aus.
Die Anzeige bildet die BDE-Anforderung ab, keine unabhängige Lüfterrückmeldung.

Fehlende oder mindestens 30 Sekunden alte Statuswerte sowie ein Verbindungsabbruch
führen zu `unavailable`, auch wenn die Luftstufe noch frisch ist. Ein gültiger
Nullwert ergibt dagegen `off`. Es gibt keine zusätzliche Verbindung oder
Steuertelegramme. Dauer, Restzeit und Automatik bleiben ohne abgeleitete Entität.

Erste Prüfung des lokalen Arbeitsstands am 14.09.2026: **88 Tests
erfolgreich**, Ruff-Lint und Formatprüfung erfolgreich. Die neuen Tests decken
reale Ein-/Aus-/anderes-Bit-Telegramme, sämtliche Aufteilungen dieser Frames,
synthetische Bitkombinationen, falsche Quelle/Länge/Prüfsumme sowie HA-Registry,
Zustandswechsel, fehlende/veraltete Daten, Wiederkehr, Verbindungsabbruch und
Entladen ab.

Zusätzlich wurden die privaten Aufnahmen (10)–(16) offline mit Chunkgrößen
1, 37, 127 und der vollständigen Aufnahmelänge wiedergegeben. In (14)/(15)
jeweils 23 Statuswerte und die Folge Aus → Ein → Aus; in (10) fünf, (11)–(13)
jeweils 23 und (16) 22 Statuswerte, durchgehend Aus. Alle Größen liefern dieselben
Ergebnisse ohne Prüfsummenfehler. Die Rohaufnahmen bleiben außerhalb des Repositorys.
Version 0.5.0 wurde am 14.09.2026 veröffentlicht. Anschließend bestätigte der
Betreiber den BDE-Abgleich der drei neuen Werte (Kompressordrehzahl,
Bypass-Schaltzustand und Intensivlüftung). Das ist eine Betreiberbestätigung,
kein zusätzlicher automatisierter Langzeittest.

## Erneute vollständige Dauerprüfung nach 0.5.0

Die Exporte (13)–(16) wurden mit dem neuen Offline-Werkzeug
[inventory_capture.py](../tools/inventory_capture.py) erneut geprüft. Anders
als das gezielte SET/ACK-Audit beschränkt es sich weder auf ausgewählte
Datenpunkte noch auf eine Liste bekannter Header. Es prüft reservierte Bytes,
die beobachtete gerade Halbbyte-Längenkodierung und die Prüfsumme. Gruppiert wird
nach allen drei Identitätsbytes, Datenpunkt und Payloadlänge; jeder erste Wert
und jede nachfolgende Payloadänderung erhält den Zeitstempel des abschließenden
TCP-Chunks. Ein strukturell gültiger Kandidat ist noch keine semantische Zuordnung.

| Export | Anlass | Bytes vollständig erfasst | Gültige Frames | Gruppen |
|---|---|---:|---:|---:|
| (13) | Dauerwahl 120 → 110 → 100 → 30 → 35 → 120 | 32.340 | 2.223 | 98 |
| (14) | Start mit 120 min; Dauerwahl auf 30; manuelles Ende | 33.130 | 2.274 | 98 |
| (15) | Neuer Start mit 30 min; manuelles Ende | 32.958 | 2.260 | 98 |
| (16) | Eco Sommer, manuelle Stufen und Automatik | 32.054 | 2.193 | 98 |

Insgesamt **130.482 Bytes, 8.950 Frames, keine unaufgelösten Bytes**. Alle vier
Exporte enthalten dieselben 98 Gruppenschlüssel und acht Headeridentitäten.
Auch die Payloads der Abfragen, der anderen Nodes und des 112-Byte-Blocks sind
in diesem Vergleich enthalten. Die Byteabdeckung bezieht sich auf die Exporte,
nicht auf eine nachgewiesen verlustfreie Erfassung des gesamten physischen Busses.

Ergebnis der Änderungssuche:

- Während der separaten Dauerwahl (13) ändern sich nur Panel 0x0226 sowie
  Controller 0x00C9, 0x032E, 0x0330 und 0x03B7. Das sind dieselben Gruppen
  wie in der ersten Auswertung. Es gibt keinen zusätzlich entdeckten Payload,
  der die bestätigte Minutenfolge abbildet.
- Beim Vergleich der Starts mit 120 und 30 Minuten (14)/(15) bleiben die
  Wertemengen sämtlicher Gruppen bis auf sieben identisch: Panel 0x0226 sowie
  Controller 0x00C9, 0x02D2, 0x02DF, 0x032E, 0x0330 und 0x03B7.
  0x02D2 wechselt zwischen den Aufnahmen von 38.495 auf 38.496;
  im 112-Byte-Block 0x02DF ändert sich ausschließlich der u32-LE-Slot an
  Byteoffset 8 von 124 auf 125. Diese Abweichungen liefern keinen Nachweis
  für eine Dauer von 120 beziehungsweise 30 Minuten.
- Das gezielte SET/ACK-Audit bestätigt für (14) und (15) jeweils **25 Luftstufen-
  SETs und 23 Bitfeld-SETs**, alle mit zeitlich zugeordnetem ACK. In beiden Fällen
  lautet die Luftstufenfolge 3 → 4 → 3 und die Bitfeldfolge 0 → 0x40 → 0.
  Diese Telegramme belegen die Aktivierung und das manuelle Ende, keinen
  eigenständigen Minuten-Schreibbefehl.

Die Videoauswahl in IMG_1636 wurde erneut anhand von Einzelbildern geprüft
(unter anderem 20, 30, 44, 55, 59 und 72 Sekunden). IMG_1638 zeigt bei
27 Sekunden weiterhin **120min**, IMG_1639 bei 15 Sekunden **30min**.
Damit bestätigt die erneute Prüfung das bisherige Ergebnis, erschließt aber
keinen zusätzlichen Datenpunkt. Insbesondere wurde kein vollständiger Countdown
beobachtet: **Eine echte Restzeit und das automatische Ende sind weiter offen.**

Eine lokale Zeitverwaltung im BDE passt zu diesen Beobachtungen. Sie ist keine
bewiesene Implementierungseigenschaft. Unbekannte Kodierungen, andere
Übertragungszeitpunkte und andere Schnittstellen sind damit nicht ausgeschlossen.
Die Integration erhält deshalb keinen geschätzten Restzeitsensor und kein
Bedienelement für eine nicht identifizierte Dauer.

### Reproduzieren

```sh
uv run python -m tools.inventory_capture diagnose-13.json diagnose-14.json diagnose-15.json diagnose-16.json --output /tmp/dauer-inventar.json
uv run python -m tools.audit_panel_writes diagnose-14.json diagnose-15.json --output /tmp/dauer-set-ack.json
uv run pytest -q tests/test_inventory_capture.py tests/test_audit_panel_writes.py
```

Die Berichte enthalten rohe Payloads und bleiben privat. Dateipfade,
Eintrags-IDs und Videometadaten werden nicht in diese Dokumentation übernommen.
Die Werkzeuge öffnen keine Verbindung zur Anlage.

### Nächster Versuch: einmal automatisch auslaufen lassen

Ziel ist der Vergleich des **automatischen** Endes mit den bereits erfassten
manuellen Enden. Ein erneuter kurzer Ein-/Aus-Versuch bringt hierfür wenig.
Die vorhandene 120-Sekunden-Aufnahme bleibt unverändert; zwei getrennte Fenster
erfassen Start und erwartetes Ende ohne durchgehendes 30-Minuten-Video.

1. In Komfort eine Dauer von **30 Minuten** wählen (auf dieser Anlage bereits
   beobachtet), Intensivlüftung zunächst aus. Ursprüngliche Dauer notieren.
   Solltemperatur und sonstige Programme während des Versuchs unverändert lassen.
2. Erste HA-Aufnahme starten, etwa 15–20 Sekunden warten, Intensivlüftung am BDE
   aktivieren. Zeitpunkt der Bestätigung mit einer Stoppuhr festhalten und die
   Hauptanzeige mit 30min kurz filmen. Nicht manuell ausschalten.
3. Nach Ende der 120-Sekunden-Aufnahme die Diagnose herunterladen und als
   **Startaufnahme** sichern. Unbedingt vor der zweiten Aufnahme: Ein erneuter
   Aufnahmestart löscht den bisherigen internen Mitschnitt.
4. Nach **29 Minuten seit Aktivierung** die zweite HA-Aufnahme starten. Sie
   erfasst ungefähr Minute 29–31. Das BDE während dieses Fensters filmen,
   einschließlich Minutenanzeige und der selbsttätigen Rückkehr zur normalen
   Lüftung. Falls der Zustand früher wechselt, den tatsächlichen Zeitpunkt
   festhalten; daraus keinen im Mitschnitt enthaltenen Übergang behaupten.
5. Zweiten Export als **Endaufnahme** sichern. Falls bis zum Aufnahmeende kein
   automatisches Ende erfolgt, Zustand und abgelaufene Zeit melden. Ein weiterer
   Aufnahmestart darf erst nach Sicherung des vorherigen Exports erfolgen.
6. Nach abgeschlossenem Versuch die ursprüngliche Dauer wieder einstellen.

Abgleich: Fällt 0x01F8/0x40 beim automatischen Ende zurück? Welche Luftstufen-
SETs und ACKs begleiten dies? Ändert sich vorher ein bislang konstanter Payload
mit der BDE-Minutenanzeige? Folgt die reale Lüfterdrehzahl? Ein erfolgreicher
Versuch bestätigt zunächst das beobachtete Zeitverhalten; er beweist allein
weder den Speicherort des Timers noch einen extern nutzbaren Schreibweg.

## Start des Versuchs zum automatischen Ende: Export (17)

Quelle: privater Diagnoseexport (17), vom Betreiber als Einschaltaufnahme
bereitgestellt. Kein zusätzliches Video und kein direkt lesbarer Dauerwert
in diesem Export; 30 Minuten sind die vereinbarte Versuchseinstellung,
keine aus dem Mitschnitt rekonstruierte Dauer.

Aufnahme am 14.09.2026 von **12:52:31,707 bis 12:54:31,696 MESZ**, Status
`duration_limit`. Das vollständige Inventar erfasst alle **32.712 Bytes in
2.241 prüfsummengültigen Frames**, ohne unaufgelöste Bytes. Der Produktionsdecoder
liefert 822 akzeptierte Werte ohne Prüfsummen- oder Wertefehler.

| Zeit seit Aufnahmebeginn | MESZ, ungefähr | Beobachtung |
|---|---|---|
| 1,207–1,708 s | 12:52:33 | Ausgangszustand Eco Sommer, Panel-Luftstufe 1, Intensivbit 0 |
| 11,409 s | 12:52:43 | Panel 0x020A: Eco Sommer → Komfort |
| 11,898 s | 12:52:44 | Panel 0x00E1: Stufe 1 → 3 |
| 16,695 s | 12:52:48 | Panel 0x00E1: Stufe 3 → 4 |
| 16,903 s | 12:52:49 | Panel 0x01F8: 0 → 0x40, Intensivlüftung aktiviert |
| bis 117,489 s | 12:54:29 | Letztes erfasstes Bitfeld weiterhin 0x40 |

Alle 24 Luftstufen-SETs und 23 Bitfeld-SETs haben ein zeitlich zugeordnetes
ACK; keine mehrdeutige oder offene Zuordnung. Der Sollwert bleibt bei 21 °C.

Die Lüfter laufen schon zu Beginn mit etwa 2.570/2.612 rpm, der Kompressor
mit etwa 2.024 rpm. Controller 0x0208 bleibt `22150080`, beide Werte in 0x00D7
bleiben 10000. Deshalb ist diese Aufnahme kein isolierter Nachweis eines durch
Intensivlüftung ausgelösten Drehzahlanstiegs. Der Panel-Einschaltvorgang ist
trotz des vorherigen Moduswechsels direkt erfasst.

Für die vereinbarten 30 Minuten ergibt sich aus dem ersten Stufe-4-Telegramm
ein **erwartetes**, noch nicht beobachtetes Ende um **13:22:48 MESZ**.
Das zweite 120-Sekunden-Fenster sollte ungefähr **13:21:45–13:23:45 MESZ**
abdecken. Die Zeiten beruhen auf der HA-Aufnahmeuhr; die Geräteuhr läuft
abweichend und wird nicht als Zeitreferenz verwendet. Der exakte interne
Timerstart und seine Rundung bleiben bis zur Endaufnahme offen.

## Automatisches Ende bei weiterlaufender Kühlung: Export (18)

Quellen: privater Diagnoseexport (18), Video IMG_1655.MOV und Betreiberangabe,
dass Stufe 4 wegen der Kühlung bestehen blieb. Der zuvor bereitgestellte
Zwischenstand zeigte 9min Restanzeige, Komfort, Luftstufe 4, Raumtemperatur
24,5 °C und Kühlbetrieb; Sollwert laut Betreiber 21 °C.

Die Endaufnahme beginnt am 14.09.2026 um **13:21:56,335 MESZ** und enthält
114,817 Sekunden bis **13:23:51,152 MESZ**. Exportstatus noch `recording`,
also nicht als vollständig abgelaufene 120-Sekunden-Aufnahme bezeichnen.
Alle **31.120 Bytes in 2.128 Frames** sind strukturell und per Prüfsumme
erfasst. Produktionsdecoder: 784 akzeptierte Werte, keine Prüfsummen- oder
Wertefehler. Die Wiedergabe beider Exporte (17)/(18) mit Chunkgrößen 1, 37,
127 und gesamter Länge liefert identische Ergebnisse.

Das 78,280 Sekunden lange Video hat als Erstellungszeit **13:22:05 MESZ**.
Bei 42 Videosekunden steht noch „Luftstufe 4 1min“, bei 43 Sekunden bereits
„Luftstufe 4“ ohne Minutenanzeige. Gleichzeitig springt die BDE-Uhr von 13:21
auf 13:22. **Komfort, Kühlbetrieb und Luftstufe 4 bleiben sichtbar**, auch
bei 60 und 77 Sekunden. Vor dem Verschwinden der Restanzeige ist kein
manuelles Ausschalten erkennbar. Die Videometadaten liefern nur eine ungefähre
Synchronisation mit den HA-Zeitstempeln.

| Ereignis im Bus | Seit Aufnahmebeginn | MESZ |
|---|---:|---|
| 0x01F8: Intensivbit 0x40 → 0 | 53,244 s | 13:22:49,579 |
| 0x00E1: angeforderte Panel-Stufe 4 → 3 | 53,353 s | 13:22:49,688 |

Zwischen dem ersten Intensiv-Ein in (17) und dem ersten Intensiv-Aus in (18)
liegen **1.800,970 Sekunden**, also ungefähr **30 Minuten und eine Sekunde**.
Das sind Empfangszeitpunkte periodischer Telegramme, keine auf eine Sekunde
vermessen genaue interne Timerlaufzeit. Zusammen mit Video, Zwischenstand und
Versuchsablauf ist das automatische Ende des 30-Minuten-Versuchs damit belegt.
Der Zwischenzeitraum wurde nicht durchgehend als Rohdaten aufgezeichnet.

Alle 21 Bitfeld-SETs und 22 Luftstufen-SETs erhalten zeitlich zugeordnete ACKs,
ohne Mehrdeutigkeiten oder offene Zuordnungen. Solltemperatur 21 °C und Komfort
bleiben konstant. Ein zusätzlicher Dauer-/Restzeit-Payload wurde nicht identifiziert.

### Anforderung, BDE-Anzeige und tatsächlicher Betrieb unterscheiden

**0x00E1 geht auf 3 zurück, obwohl die BDE-Hauptanzeige bei 4 bleibt.** Damit
ist die bisher teilweise verwendete Bezeichnung „effektive Luftstufe“ widerlegt.
Der Datenpunkt zeigt die Panel-Anforderung auf HESP, nicht zuverlässig die
am BDE angezeigte, durch die Anlagenregelung wirksame Luftstufe. Der vorhandene
HA-Sensor `fan_level` dekodiert folglich korrekt 3; seine neutrale Beschriftung
„Luftstufe“ ist für Nutzer aber erklärungsbedürftig. Eine eindeutigere Benennung
als angeforderte Luftstufe ist bei der nächsten Produktänderung vorzusehen.

Der Controllerstatus 0x0208 bleibt während der gesamten Aufnahme `22150080`.
Die Ist-Drehzahlen sind zu Beginn etwa 2572/2608 rpm, am Ende etwa 2577/2588 rpm.
Es gibt zwischenzeitliche Schwankungen; sie werden nicht als dauerhafter
Stufenwechsel interpretiert. Beide Werte in 0x00D7 sind beim automatischen Ende
10000. Die bis dahin dokumentierte Stufenzuordnung in 0x0208 bleibt ein Kandidat
für die wirksame Anforderung, keine vollständige oder allgemein freigegebene
Dekodierung dieses Statusworts.

Andere Vorgänge liegen zeitlich davor: Bypassstatus 0x0160 wechselt bei 28,503 s
von 1 auf 0; der zweite Wert in 0x00D7 liegt vorübergehend bei 7000, ab 48,382 s
wieder bei 10000. Diese Änderungen sind nicht mit dem erst bei 53,244 s
erfassten Intensiv-Aus gleichzusetzen.

### Ergebnis für die Integration

- `intensive_ventilation` erkennt auch das automatische Ende unabhängig von
  fortbestehendem Kühlbetrieb und hoher Lüfterdrehzahl richtig.
- 0x00E1, Intensivbit und Ist-Drehzahlen bleiben getrennte Größen. Ein
  Regressionstest mit aufgezeichneten Telegrammen hält diesen Fall fest.
- Eine aus Stufe 4 oder grüner LED abgeleitete Intensivanzeige wäre falsch.
- Der 30-Minuten-Versuch ist abgeschlossen; keine weitere Wiederholung dieses
  Ablaufs erforderlich. Für Dauer/Restzeit als eigene Entität fehlt weiterhin
  ein belegter lesbarer Datenpunkt. Ein lokaler BDE-Timer bleibt eine plausible
  Erklärung, keine durch diesen Ablauf bewiesene Hardwarearchitektur.
