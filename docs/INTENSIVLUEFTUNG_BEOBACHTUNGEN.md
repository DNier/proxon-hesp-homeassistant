# Intensivlüftung: getrennte Einstellung der Dauer

Stand: 14.09.2026. Geltungsbereich: [lokale Referenzanlage](ANLAGENPROFIL.md).
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
Diese Implementierung wurde noch nicht veröffentlicht oder auf Live-HA installiert.
