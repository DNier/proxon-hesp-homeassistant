# Gerätezeit abgleichen

Zimmermann bestätigt für die angefragte P-Serie-Generation, dass Datum und Uhrzeit
nach vollständiger Spannungsunterbrechung zurückgesetzt werden. Sie sollen danach
kontrolliert und gegebenenfalls neu eingestellt werden. Das passt zu den
Beobachtungen an der Referenzanlage; eine falsche Uhrzeit kann die Auswahl des
Zeitprogramms beeinflussen. [Herstellerangaben und Geltungsbereich](MANUFACTURER_INFORMATION.md).
Die optionale Schaltfläche **Gerätezeit abgleichen** korrigiert den Kalender
anhand der in Home Assistant eingestellten Zeitzone.

Sie ändert weder direkt die Betriebsart noch sendet sie einen Luftstufenbefehl.
Die korrigierte Uhrzeit kann jedoch dazu führen, dass das bestehende Zeitprogramm
eine andere Luftstufe auswählt.

## Datum und Uhrzeit anzeigen

Auf der Geräteseite lassen sich die Diagnoseentitäten **Gerätedatum** und
**Geräteuhrzeit** getrennt aktivieren. Das Datum verwendet die bestätigte
Kalenderantwort `032E` und den HA-Gerätetyp Datum. Die Uhrzeit aus `0330`
zeigt `HH:MM:SS` als lokale Gerätezeit ohne Zeitzonenumrechnung. Ihre bisherige
Entitätsidentität bleibt erhalten; der Zusatz „experimentell“ entfällt.

Die kombinierte Entität **Gerätedatum und -uhrzeit (lokal)** bleibt für bestehende
Dashboards und Automationen unverändert. Wer nur die getrennte Anzeige benötigt,
kann sie deaktivieren. Neue Datumssensoren sind zunächst deaktiviert.
Fehlende, veraltete Daten und Verbindungsabbrüche ergeben „Nicht verfügbar“.
Die Anzeige bestätigt die Gerätewerte, nicht die Richtigkeit der eingestellten Uhr.

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
Eine nur kurz passende Antwort genügt nicht, wenn danach auf derselben
Verbindung ein abweichender oder ungültiger Kalender empfangen wird, bevor
die Bestätigungsprüfung abgeschlossen ist.

Ein fehlgeschlagener oder unterbrochener Versuch wird `unconfirmed`, gegebenenfalls
mit einem Aktionsfehler. Vor einem erneuten Versuch am BDE prüfen: Eine fehlende
Antwort beweist nicht, dass der Befehl wirkungslos war. Es gibt keine automatische
Wiederholung oder Warteschlange. Nach einem Sendeversuch gilt eine Sperrzeit von
30 Sekunden. Ein Verbindungsabbruch beendet die Bestätigungsprüfung; beim
Wiederverbinden wird nichts erneut gesendet.

## Sommer-/Winterzeit automatisch abgleichen

Am PROXON-Hauptgerät steht unter **Konfiguration** der Schalter
**Sommer-/Winterzeit automatisch abgleichen**. Er ist standardmäßig aus und
speichert die Einstellung pro Anlage. Beim Einschalten vergleicht die Integration
einmalig die frisch empfangene Gerätezeit mit der lokalen HA-Zeit auf die Minute
genau. Bei einer Abweichung korrigiert sie die Uhr sofort. Fehlen gültige, frische
Kalenderdaten, bleibt der Schalter eingeschaltet und der Erstabgleich entfällt.
Ein HA-Neustart oder eine Wiederverbindung löst keinen Erstabgleich aus.

Bei eingeschaltetem Schalter prüft die Integration um 04:15 Uhr in der
HA-Zeitzone. Ein einzelner Abgleich kommt infrage, wenn sich seit diesem
Zeitpunkt am Vortag die Sommerzeit und der UTC-Offset geändert haben und die
frische Gerätezeit um den erwarteten Betrag in der richtigen Richtung abweicht.
Die Toleranz beträgt zwei Minuten. Den Bestätigungsstatus zeigt die Integration
in der Diagnose sowie an der optionalen Schaltfläche **Gerätezeit abgleichen**.

Bei einer Unterbrechung zum Prüfzeitpunkt oder einem unbestätigten Abgleich
wartet die Integration auf die nächste Zeitumstellung. Für eine schon länger
abweichende Uhr kannst du den zuvor beschriebenen manuellen Abgleich nutzen.

### Vorhandenen Blueprint verwenden

Der [Home-Assistant-Blueprint](../blueprints/automation/proxon_hesp/dst_clock_sync.yaml)
steht weiterhin zur Verfügung. Er benötigt die aktivierten Entitäten
**Gerätedatum und -uhrzeit (lokal)** und **Gerätezeit abgleichen** am selben
PROXON-Hauptgerät. Importiere die YAML-Datei unter **Einstellungen →
Automatisierungen & Szenen → Blueprints** und wähle beide Entitäten beim
Erstellen der Automation aus. Verwende je Anlage einen der beiden Wege.

## Umfang und Grenzen

Korrigiert werden Jahr, Monat, Tag, Wochentag, Stunde und Minute, nicht die Sekunden.
Das ist kein sekundengenauer Zeitabgleich. HESP enthält hier keine Zeitzone;
die Aktion verwendet die lokale HA-Zeitzone einschließlich aktueller Sommerzeit.
Ab 0.15.0 entfallen die numerische Rohkalender-Entität und das rohe Uhrzeit-Duplikat.
Gerätedatum und Geräteuhrzeit bleiben als getrennte verständliche Sensoren
verfügbar; der optionale kombinierte lokale Zeitwert bleibt ebenfalls erhalten.
Interne Kalenderdaten und die Identität der Abgleichaktion ändern sich nicht.
[Ersatzsensoren und Aktivierung beim Update](DATA_POINTS.md#readable-telemetry-and-entity-migration-0150).

Die Funktion wurde an einer LT-ZIM V1.6 / PTC 4× V1.2 / BDE Comfort über den
ursprünglichen PTC-zur-Steuerung-Abgriff am Display bestätigt. Andere Revisionen
sind nicht bestätigt. Die Korrektur verhindert keinen erneuten Zeitverlust nach
einer vollständigen Spannungsunterbrechung.

Empfang, Verbindungstest, Aufnahmen und Wiederverbindung bleiben passiv.
Keinen zweiten TCP-Mitschnitt gegen ein Gateway mit nur einem Client öffnen,
während die Integration verbunden ist. Empfangsmitschnitte enthalten ausschließlich
RX-Daten; gesendete Bytes und das letzte Ziel des Zeitabgleichs werden separat erfasst.

In der Diagnose bezeichnet `clock_bytes_attempted` die für einen
Kalendersendeversuch übergebenen Bytes, auch bei unklarem Ausgang der Übergabe.
`clock_bytes_confirmed` zählt nur die Bytes von Vorgängen mit passendem,
gültigem Kalenderrücklauf. Die Zähler gelten für die aktuelle Integrationslaufzeit;
sie sind keine dauerhafte Historie und keine Messung physischer Buszustellung.
