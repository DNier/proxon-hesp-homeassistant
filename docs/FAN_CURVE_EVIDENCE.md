# Lüfterkennlinien und Rohstellwerte

Aktualisierung 6. Oktober 2026: Die öffentliche Service-App-Abbildung bestätigt
die asymmetrischen Zu-/Abluft-Listen des Community-Beispiels. Ab Version 0.14.0
stehen die acht konfigurierten Stufen als optionale Diagnosesensoren bereit.
Keine Schreibbefehle; Quellen und Aussagegrenzen im
[technischen Evidenzbericht (Englisch)](SERVICE_SETTINGS_EVIDENCE.md).
Die folgende Offline-Auswertung stammt vom 27. September 2026.

## Ergebnis

Die Antworten `224000/00D2/16` und `224000/00D3/16` enthalten jeweils vier
Little-Endian-Float-Werte. Zwei Anlagen liefern unterschiedliche Listen:

| Aufnahmequelle | `00D2` | `00D3` |
| --- | --- | --- |
| Lokale Referenzaufnahmen | 25 / 40 / 52 / 100 | 25 / 40 / 52 / 100 |
| Öffentlicher Community-Export | 31 / 50 / 70 / 100 | 25 / 50 / 70 / 100 |

Bei der Referenzanlage wurden die Listen in fünf bereits inventarisierten
Aufnahmen wiedergefunden. Das sind keine fünf unabhängigen Anlagen. Im neuesten
Originalmitschnitt wurden die vollständigen Frames erneut mit der bestehenden
Prüfsumme geprüft; die beobachtete Stellwertantwort 5200/5200 passt zu Position 3.

Im [öffentlichen Export](https://github.com/user-attachments/files/32697336/Proxon.sql)
kommen sechs verschiedene gültige Stellwertpaare auf `00D7` vor:

| Stellwertpaar | Passende Position in beiden Listen bei Faktor 100 |
| --- | --- |
| 3100 / 2500 | 1 |
| 5000 / 5000 | 2 |
| 7000 / 7000 | 3 |
| 10000 / 10000 | 4 |
| 10000 / 7000 | Keine: erster Kanal passt zu 4, zweiter zu 3 |
| 0 / 0 | Keine Position in diesen Listen |

Die Zuordnung `00D2` zum ersten und `00D3` zum zweiten Stellwert wird insbesondere
durch das asymmetrische Paar 3100/2500 gestützt. Die später veröffentlichte
Service-App-Abbildung stützt die Richtung für dieses Community-Beispiel zusätzlich.
Ein synchronisierter BDE-Änderungsversuch steht weiterhin aus. Das Offline-Werkzeug
weist numerische Kandidaten aus, keine automatisch bewiesene Eigenschaft beliebiger Geräte.

Die [öffentliche HESP-Referenz](https://github.com/markusmauch/proxon-hesp/blob/main/docs/dp-referenz.md)
beschreibt `00D2`/`00D3` als Lüfterstufen-Prozentkennlinien für eine P 2H-L.
Dies ist ein zusätzlicher Hinweis zur Zahlenbeobachtung, keine Herstellerfreigabe
oder Bestätigung jeder Hardwareversion. Die dortige Bezeichnung von `00D7` als
Ziel-Drehzahl wird nicht übernommen: Zahlenvergleich und vorhandene Referenzen
belegen bei uns weiterhin keine gemessene Drehzahl oder physische Spannung für
diesen Datenpunkt.

## Was daraus nicht folgt

Ein numerischer Treffer ist keine bestätigte aktuelle Luftstufe. Es können
Sonderzustände, gleiche Werte mehrerer Tabellenpositionen, geänderte Einstellungen
oder nicht zeitgleich aufgezeichnete Antworten vorliegen. Der Export filtert
Änderungen und enthält Duplikate; siehe [Community-Auswertung](COMMUNITY_EXPORT_ANALYSIS.md).
Eine fehlende gemeinsame Position wird nicht auf die nächstgelegene Stufe gerundet.
Auch 0/0 wird nicht automatisch als Stufe 0 interpretiert.

Die vom BDE angeforderte Stufe und die aus geprüften vollständigen Statuswörtern
gelesene Reglerstufe bleiben die bestehenden, getrennten Entitäten. Eine globale
Zuordnung wie »5200 entspricht immer Stufe 3« ist ungeeignet. Die Tabellen sind
zudem keine gemessenen Volumenströme.

## Reproduzierbare Offline-Prüfung

```sh
uv run python -m tools.audit_fan_curves tests/fixtures/fan_curve_replies.json --output /tmp/fan-curves.json
uv run pytest -q tests/test_audit_fan_curves.py
```

Das JSON enthält vollständige Antworten in `00d2` und `00d3` sowie eine Liste
vollständiger `00D7`-Antworten unter `observations`. Alle Frames müssen einzeln
Identität, Länge und Prüfsumme erfüllen. Das Werkzeug nutzt die vorhandene
Inventarisierung; es implementiert keinen zweiten Frameparser.

Ausgegeben werden Kandidatenpositionen je Kanal und deren Schnittmenge. Doppelte
Tabellenwerte ergeben gegebenenfalls mehrere Kandidaten. NaN, unendliche Werte
und Werte außerhalb des untersuchten Bereichs werden zurückgewiesen. Die kleine
numerische Toleranz gleicht nur Float32-Darstellung aus, nicht Regelabweichungen.
Das Werkzeug behauptet weder Gleichzeitigkeit noch Aktualität der Eingabeframes.

Die öffentliche Fixture enthält die ursprünglichen vollständigen Antworten auf
`00D2`/`00D3` und die sechs unterschiedlichen `00D7`-Antworten aus dem Community-
Export, ohne Zeitstempel oder Datenbankmetadaten. Lokale Diagnoseoriginale bleiben
außerhalb des öffentlichen Repositorys.

## Abgeschlossener Betriebsabgleich: Stufen 1–4 und Intensivlüftung

Am Referenz-BDE sind laut Bediener keine einsehbaren Kennlinieneinstellungen
vorhanden; angezeigt werden unter anderem Luftstufe, Drehzahlen und Temperaturen.
Der vorgeschlagene Abgleich einer Einstellungsseite ist deshalb keine ausstehende
Nutzeraufgabe. Stattdessen wurden die Stufen am BDE manuell gewählt und jeweils
anschließend die aktuellen HA-Werte ausschließlich lesend abgefragt.

Am 27. September 2026 ergab sich folgender Vergleich. Alle Uhrzeiten beziehen
sich auf Europe/Berlin; die BDE-Referenzen sind Bedienerangaben, kein
sekundengenau synchronisiertes Video. Beide HA-Stufen bezeichnen Anforderung
und Steuerungsrückmeldung, die Stellwertpaare Zuluft/Abluft laut Integration.

| HA-Abfrage | BDE-Auswahl laut Bediener | Beide HA-Stufen | Rohstellwerte | Intensivsignal | Drehzahlen Zu-/Abluft (U/min, gerundet) |
| --- | --- | --- | --- | --- | --- |
| 14:29:03 | Intensivlüftung | 4 / 4 | 10000 / 10000 | An | 2361 / 2465 |
| 14:30:22 | Stufe 1 | 1 / 1 | 2500 / 2500 | Aus | 1064 / 1015 |
| 14:33:42 | Stufe 2 | 2 / 2 | 4000 / 4000 | Aus | 1360 / 1342 |
| 14:34:33 | Stufe 3 | 3 / 3 | 5200 / 5200 | Aus | 1716 / 1726 |
| 14:36:07 | Stufe 4 gemeldet, zunächst abweichend | 3 / 3 | 5200 / 5200 | Aus | 1770 / 1772 |
| 14:38:00 | Stufe 4 ausdrücklich am BDE bestätigt | 4 / 4 | 10000 / 10000 | Aus | 2577 / 2637 |
| 14:39:16 | Rückkehr zu Auto | 1 / 1 | 2500 / 2500 | Aus | 1173 / 1172 |

Die HA-Meldungen waren bei diesen Abfragen laut `last_reported` gerundet
0,0–0,3 Sekunden alt; dies sind HA-Meldezeiten, keine elektrischen
Telegrammzeitstempel. Der Verdichter meldete jeweils 0 U/min. Die Drehzahlen
sind Momentaufnahmen, keine nachgewiesen eingeschwungenen Sollwerte. Die
vollständigen Einzelabfragen bleiben als private Belege außerhalb des Repositorys.

**Abgeschlossen:** Für die vier manuell bestätigten Stufen dieser Anlage passen
2500/4000/5200/10000 jeweils zu beiden Kennlinien 25/40/52/100 bei Faktor 100.
Die Tabellen selbst stammen aus vorherigen prüfsummengeprüften Mitschnitten,
nicht aus diesen HA-Abfragen. Der ursprüngliche Einzelabgleich für Stufe 3
um 14:09:36 hatte bereits 5200/5200 bei beiden HA-Stufen 3 ergeben.

Reguläre Stufe 4 und Intensivlüftung lieferten dieselben Rohstellwerte, aber
unterschiedliche Zustände des separaten Intensivsignals. Aus dem Stellwert allein
lässt sich Intensivlüftung deshalb nicht erkennen. Auch Auto ist hier nur durch
die Bedienerangabe bekannt: Die abgefragten Werte unterscheiden Auto bei Stufe 1
nicht von manuell gewählter Stufe 1. Die ursprüngliche Auswahl wurde wiederhergestellt.

Die Abweichung um 14:36 wurde auch bei einer zweiten frischen Abfrage um 14:36:24
beobachtet. Erst nach der erneuten BDE-Bestätigung stimmte der Vergleich überein.
Die Ursache ist ungeklärt; daraus wird weder ein Decoderfehler noch eine bestimmte
Übernahmeverzögerung abgeleitet. Die abweichende Probe bleibt im Ergebnis erhalten.

## Getrennt davon offene fachliche Freigaben

HA liest dieselben HESP-Daten wie die Integration und liefert keine zweite
unabhängige Messung der Stellwerte oder Drehzahlen. Die unabhängige Referenz für
die Auswahl ist die Bedienerbeobachtung am BDE. Der Stufenvergleich bestätigt
keine Einheit wie Prozent oder Volt. Weil beide Tabellen an der Referenzanlage
identisch sind, bestätigt er auch keine Richtungszuordnung von `00D2` gegenüber
`00D3`. Die Zuordnung darf nicht als feste Wertetabelle auf andere Anlagen
übertragen werden.

## Aktualisierter Community-Vergleich (3. Oktober 2026)

Reimunds ergänzende Aufzeichnungen zeigen Stufen 4, 3 und 2 jeweils zusammen
mit Rohstellwerten 10000/10000, 7000/7000 und 5000/5000. Die zugehörigen
Lüfterdrehzahlen sind eine andere Messgröße. Die sekundengenauen Datenbankzeiten
beweisen weder eine Telegrammreihenfolge noch einen vollständigen Sendetakt.
Eine zugängliche Kennlinienseite am BDE wurde nicht gefunden; eine weitere Suche
in diesem Menü ist deshalb keine Voraussetzung für die Auswertung.

Der FWT-2-L-Mitschnitt ergänzt einen asymmetrischen Vergleich: Die Tabellen
25/50/70/100 und 25/47/67/100 passen bei Stufe 3 zu 7000/6700. Minimale
Originaltelegramme sind in `tests/fixtures/fwt_frames.json` abgesichert.
Damit wird die numerische Kennlinienhypothese über mehrere Anlagen gestützt,
aber keine allgemeine physische Einheit oder Auto-Erkennung bestätigt.

Die bestehende Luftstufenanzeige bleibt die maßgebliche Anzeige. Aus Rohstellwerten
wird keine zusätzliche allgemeine Stufe berechnet. Insbesondere bleiben
Sonderzustände, Intensivlüftung und Auto/manuell getrennte Fragestellungen.

Quellen: [Community-Vergleich und Antwort](https://github.com/DNier/proxon-hesp-homeassistant/discussions/1#discussioncomment-18727498),
[FWT-Kompatibilität und Grenzen](COMPATIBILITY.md).

## Bedienhinweis vom 4. Oktober 2026

Laut aktueller Beobachtung an der Referenzanlage ist manuelle Stufenwahl nur in
Eco Sommer/Winter möglich. Auto folgt dort dem Nutzerzeitplan; Komfort/Ofen
bestimmen die Stufe durch die Steuerung. Intensivlüftung bedeutet zeitlich
begrenzte Stufe 4 in Komfort/Ofen. In Eco gibt es diese Option nicht; dort wird
Stufe 4 manuell gewählt.

Die historischen Messwerte oben bleiben unverändert. Die damalige Betriebsart
wurde nicht festgehalten; aus der Reihenfolge der Beobachtungen wird weder eine
gemeinsame Betriebsart noch ein damaliger Betriebsartwechsel rekonstruiert. Der
Vergleich gleicher Stellwerte bei unterschiedlichem Intensivstatus bleibt gültig.
Für künftige Vergleiche gelten die [betriebsspezifischen Bedingungen](REFERENCE_TESTS.md).
