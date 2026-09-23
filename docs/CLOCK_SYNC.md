# Gerätezeit abgleichen

Nach einem Stromausfall kehren manche geprüften Steuerungen zu einem anfänglichen
Kalenderdatum zurück. Das kann die Auswahl des Zeitprogramms beeinflussen.
Die optionale Schaltfläche **Gerätezeit abgleichen** korrigiert den Kalender
anhand der in Home Assistant eingestellten Zeitzone.

Sie ändert weder direkt die Betriebsart noch sendet sie einen Luftstufenbefehl.
Die korrigierte Uhrzeit kann jedoch dazu führen, dass das bestehende Zeitprogramm
eine andere Luftstufe auswählt.

## Verwendung

1. Datum, Uhrzeit und Zeitzone von Home Assistant prüfen.
2. Auf der PROXON-Geräteseite **Gerätezeit abgleichen** in den Entitätseinstellungen
   aktivieren. Die Schaltfläche ist zunächst deaktiviert und benötigt frische Kalenderdaten.
3. Einmal drücken und Datum/Uhrzeit am BDE kontrollieren.

Die Aktion sendet genau ein Kalendertelegramm über die bestehende Verbindung
und wartet bis zu 20 Sekunden auf eine passende Kalenderantwort der Steuerung.
Ein ACK allein reicht nicht. Das Attribut `status` wird bei passender Antwort
`confirmed`; ohne erforderliche Korrektur lautet es `already_current`.
Wegen eines möglichen Minutenwechsels wird auch die folgende Kalenderminute
als Bestätigung akzeptiert. Das belegt keine dauerhafte Speicherung.

Ein fehlgeschlagener oder unterbrochener Versuch wird `unconfirmed`, gegebenenfalls
mit einem Aktionsfehler. Vor einem erneuten Versuch am BDE prüfen: Eine fehlende
Antwort beweist nicht, dass der Befehl wirkungslos war. Es gibt keine automatische
Wiederholung oder Warteschlange. Nach einem Sendeversuch gilt eine Sperrzeit von
30 Sekunden. Ein Verbindungsabbruch beendet die Bestätigungsprüfung; beim
Wiederverbinden wird nichts erneut gesendet.

## Umfang und Grenzen

Korrigiert werden Jahr, Monat, Tag, Wochentag, Stunde und Minute, nicht die Sekunden.
Das ist kein sekundengenauer Zeitabgleich. HESP enthält hier keine Zeitzone;
die Aktion verwendet die lokale HA-Zeitzone einschließlich aktueller Sommerzeit.
Bestehende numerische Kalenderwerte und Entitätsidentitäten bleiben erhalten.

Die Funktion wurde an einer LT-ZIM V1.6 / PTC 4× V1.2 / BDE Comfort über den
ursprünglichen PTC-zur-Steuerung-Abgriff am Display bestätigt. Andere Revisionen
und die Beibehaltung nach Stromausfall sind nicht bestätigt. Es gibt weder
Startautomatik noch periodisches Schreiben oder einen Dienst für beliebige Telegramme.

Empfang, Verbindungstest, Aufnahmen und Wiederverbindung bleiben passiv.
Keinen zweiten TCP-Mitschnitt gegen ein Gateway mit nur einem Client öffnen,
während die Integration verbunden ist. Empfangsmitschnitte enthalten ausschließlich
RX-Daten; gesendete Bytes und das letzte Ziel des Zeitabgleichs werden separat erfasst.
