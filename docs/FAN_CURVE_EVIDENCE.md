# Lüfterkennlinien und aktuelle Ansteuerung

Die öffentliche Service-App-Abbildung beschriftet die asymmetrischen Zu- und
Abluft-Kennlinien des Community-Beispiels. Die Integration stellt die acht
konfigurierten Stufen und die daraus abgeglichene Ansteuerung je Richtung als
optionale Diagnosesensoren bereit. [Service-Einstellungen und Belegumfang
(Englisch)](SERVICE_SETTINGS_EVIDENCE.md)

## Aktuelle Prozentanzeige ab 0.15.0

Jeder Kanal von `224000/00D7/8` wird getrennt mit der frisch empfangenen Kennlinie
derselben Richtung verglichen: erster Kanal mit Zuluft `00D2`, zweiter Kanal mit
Abluft `00D3`. Ein gültiger endlicher Rohwert von 0 bis 10000 wird durch 100
geteilt. Nur wenn das Ergebnis einer frischen gültigen Kennlinienstufe entspricht,
zeigt die Entität deren empfangenen Prozentwert. Die Vergleichstoleranz beträgt
absolut `0,0001`, relativ `0`; sie gleicht nur Float32-Darstellung aus.

Beispiel: 5200 und eine frisch empfangene Abluftstufe mit 52 % ergeben eine
Abluft-Ansteuerung von 52 %. Das Paar 10000/7000 kann unabhängig 100 % Zuluft
und 70 % Abluft ergeben, wenn die jeweilige Kennlinie diese Werte enthält.
Eine gemeinsame Stufennummer ist keine Voraussetzung. Die Regler-Luftstufe wird
für diese Anzeige nicht benötigt; unbekannte Statuswörter sperren einen sonst
gültigen Kennlinientreffer nicht.

Rohwert und passende Kennlinienstufe müssen jeweils innerhalb der normalen
30-Sekunden-Frist frisch sein. Fehlen frische gültige und passende Daten, oder
bricht die Verbindung ab, ist der betroffene Kanal
„Nicht verfügbar“. Null wird nur mit einer frischen, tatsächlich auf 0 %
konfigurierten Stufe angenommen. Doppelte Prozentwerte in der Kennlinie erfordern
keine Auswahl einer Stufennummer. Es gibt keine Rundung auf die nächstgelegene
Stufe und keinen Ersatz durch gespeicherte Kennlinien oder angenommene Nullwerte.
Ungültige Telegramme erneuern den letzten gültigen Messwert nicht.

Die Prozentanzeige bezeichnet die Ansteuerung gemäß passender empfangener
Kennlinienstufe. Sie misst keine Spannung, Luftmenge oder Drehzahl und bestimmt
keine Betriebsart, Intensivlüftung oder Auto-Auswahl. Die Werte früherer
Rohstellwert-Entitäten werden nicht nachträglich umgerechnet. Neue Prozent-IDs
und die nötige Anpassung eigener Dashboards oder Automationen sind unter
[Entitätswechsel](DATA_POINTS.md#readable-telemetry-and-entity-migration-0150) beschrieben.

## Ergebnis

Die Antworten `224000/00D2/16` und `224000/00D3/16` enthalten jeweils vier
Little-Endian-Float-Werte. Zwei Anlagen liefern unterschiedliche Listen:

| Aufnahmequelle | `00D2` | `00D3` |
| --- | --- | --- |
| Referenzanlage | 25 / 40 / 52 / 100 | 25 / 40 / 52 / 100 |
| Öffentlicher Community-Export | 31 / 50 / 70 / 100 | 25 / 50 / 70 / 100 |

Bei der Referenzanlage stimmen die Listen in fünf Aufnahmen derselben Anlage
überein. Geprüfte Beispieltelegramme enthalten das Stellwertpaar 5200/5200
und die Kennlinienwerte 52/52 für Stufe 3.

Der in der [Community-Auswertung](COMMUNITY_EXPORT_ANALYSIS.md) beschriebene
Export enthält sechs verschiedene gültige Stellwertpaare:

| Stellwertpaar | Passende Position in beiden Listen bei Faktor 100 |
| --- | --- |
| 3100 / 2500 | 1 |
| 5000 / 5000 | 2 |
| 7000 / 7000 | 3 |
| 10000 / 10000 | 4 |
| 10000 / 7000 | Keine: erster Kanal passt zu 4, zweiter zu 3 |
| 0 / 0 | Keine Position in diesen Listen |

Die Zuordnung `00D2` zum ersten und `00D3` zum zweiten Stellwert wird insbesondere
durch das asymmetrische Paar 3100/2500 und die Service-App-Abbildung gestützt.
Das Offline-Werkzeug weist numerische Kandidaten für die jeweils untersuchte
Kennlinie aus.

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

<a name="abgeschlossener-betriebsabgleich-stufen-14-und-intensivlüftung"></a>

## Betriebsabgleich der Luftstufen

Die Referenzanlage lieferte bei den am BDE bestätigten Stufen folgende Werte.
Die Kennlinien stammen aus prüfsummengeprüften Mitschnitten. Die Auswahl wurde
separat am BDE abgelesen.

| BDE-Stufe | Anforderung und Reglerstufe | Rohstellwerte Zuluft/Abluft |
| --- | --- | --- |
| 1 | 1 / 1 | 2500 / 2500 |
| 2 | 2 / 2 | 4000 / 4000 |
| 3 | 3 / 3 | 5200 / 5200 |
| 4 | 4 / 4 | 10000 / 10000 |

Stufe 4 und Intensivlüftung lieferten dieselben Rohstellwerte bei
unterschiedlichem Intensivsignal. Bei einer Stufenabweichung meldete Home
Assistant zunächst frische Werte für Stufe 3 und stimmte erst nach einer erneuten
BDE-Bestätigung mit Stufe 4 überein. Die Ursache bleibt offen. Auch gleiche
numerische Stufen bei Auto und fester Wahl identifizieren keinen Auswahlmodus.

## Grenzen des historischen Betriebsabgleichs

HA liest dieselben HESP-Daten wie die Integration und liefert keine zweite
unabhängige Messung der Stellwerte oder Drehzahlen. Die unabhängige Referenz für
die Auswahl ist die Bedienerbeobachtung am BDE. Der Stufenvergleich allein bestätigt
keine Einheit wie Prozent oder Volt. Weil beide Tabellen an der Referenzanlage
identisch sind, bestätigt er auch keine Richtungszuordnung von `00D2` gegenüber
`00D3`. Die Zuordnung darf nicht als feste Wertetabelle auf andere Anlagen
übertragen werden.

Die spätere Service-App-Abbildung ergänzt Prozentangaben und eine asymmetrische
Richtungsreferenz für die Kennlinien. Zusammen mit den hier erhaltenen
Zahlenvergleichen trägt sie die begrenzte Prozentanzeige ab 0.15.0. Eine
gemessene physische Spannung oder die freie Umrechnung beliebiger Zwischenwerte
ist damit weiterhin nicht bestätigt.

<a name="aktualisierter-community-vergleich-3-oktober-2026"></a>

## Community-Vergleiche

Reimunds ergänzende Aufzeichnungen zeigen Stufen 4, 3 und 2 jeweils zusammen
mit Rohstellwerten 10000/10000, 7000/7000 und 5000/5000. Die zugehörigen
Lüfterdrehzahlen sind eine andere Messgröße. Die sekundengenauen Datenbankzeiten
beweisen weder eine Telegrammreihenfolge noch einen vollständigen Sendetakt.

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

<a name="bedienhinweis-vom-4-oktober-2026"></a>

## Betriebsart und Luftstufenwahl

An der Referenzanlage bieten Eco Sommer und Eco Winter eine feste Stufe oder
Auto nach Wochenzeitplan. In Komfort und Ofenbetrieb regelt die Anlage die
Stufe und bietet eine zeitlich begrenzte Intensivlüftung auf Stufe 4. Der
Stufenvergleich oben dokumentiert die Betriebsart nicht. Für die unabhängige
Anzeigeprüfung siehe [BDE-Vergleiche](REFERENCE_TESTS.md).
