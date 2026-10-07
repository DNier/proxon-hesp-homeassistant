# Entitäten am Hauptgerät

Diese Einteilung verwendet seit **0.12.0b4** die vorgesehenen HA-Entitätskategorien.
Die folgende Tabelle beschreibt den Stand **0.15.0**.
Zusätzliche Geräte allein zur Sortierung von Messwerten werden nicht angelegt.

| Einordnung | Entitäten | Bei Neueinrichtung |
|---|---|---|
| Normale Sensoren und Zustände | Betriebsart, angeforderte Luftstufe, Raum-/Solltemperatur, Zu-/Ab-/Fort-/Frischlufttemperatur, Verdichter läuft, Bypass und Intensivlüftung | Aktiviert |
| Diagnose | Filterrestlaufzeit, Betriebsstunden, Aufnahmestatus und Aufnahmeaktionen | Aktiviert |
| Optionale Diagnose | Sechs interne Temperaturen, drei Drehzahlen, getrenntes Gerätedatum und Geräteuhrzeit, kombinierte lokale Gerätezeit, Regler-Luftstufe, aktuelle Lüfteransteuerung in Prozent, konfigurierte Lüfterstufen und Leistungsgrenzen, Kühlschwelle, ungeklärte Hex-Datenpunkte, Verbindung und letzter gültiger Empfang | Deaktiviert |
| Konfiguration | Manueller Gerätezeitabgleich | Deaktiviert |

Die Kategorie Diagnose beschreibt den Verwendungszweck, nicht die Genauigkeit.
Ein deaktivierter Drehzahlsensor unterbindet weder den Datenempfang noch den
Sensor **Verdichter läuft**. Optionale Werte lassen sich einzeln in den
Entitätseinstellungen aktivieren.

## Bestehende Installationen

Ab 0.14.0 ergänzen elf zunächst deaktivierte Diagnosesensoren die Kühlschwelle,
konfigurierte maximale Heiz-/Kühlleistung und je vier Zu-/Abluftstufen. Diese
Einstellungen sind keine gemessene Leistung oder aktuelle Luftstufe. Ohne
frischen Empfang werden sie unverfügbar. Quellen und Grenzen stehen im
[technischen Evidenzbericht (Englisch)](SERVICE_SETTINGS_EVIDENCE.md).

Ab 0.15.0 entfallen sieben bestätigte Rohduplikate. Die alten Registrierungen
werden automatisch entfernt; aktivierte Rohsensoren aktivieren bisher nur
standardmäßig deaktivierte Ersatzsensoren. Eigene Verweise müssen auf die
[Ersatzsensoren](DATA_POINTS.md#readable-telemetry-and-entity-migration-0150)
umgestellt werden. Die neuen Lüfter-Prozentwerte erhalten eigene IDs.

Alle übrigen Entitäts-IDs, eindeutigen Identitäten, eigenen Namen sowie
Aktivierungsentscheidungen bleiben beim Update erhalten. Die geänderte Kategorie ordnet bestehende Werte der
Diagnose zu. Neue Aktivierungsstandards deaktivieren keine bisher aktiven Entitäten.
Die deutschen Drehzahlnamen lauten einheitlich Zuluftdrehzahl, Abluftdrehzahl und
Verdichterdrehzahl. Eigene Namen haben weiterhin Vorrang.

Nicht benötigte Detailwerte können manuell deaktiviert werden, sofern sie nicht
in Dashboards, Verlauf oder Automationen gebraucht werden. Die Integration nimmt
keine pauschale Deaktivierung oder Umbenennung bestehender Entitäts-IDs vor.
Die Standard-Geräteseite bestimmt ihr Layout selbst; frei gestaltete fachliche
Abschnitte gehören in ein eigenes Dashboard.

Ab 0.12.0b5 ergänzen drei standardmäßig deaktivierte [experimentelle Statusbits](EXPERIMENTAL.md) die Diagnose.

**MV-Heizen/Kühlen** ist eine optionale Diagnoseanzeige des BDE-Magnetventils.
Ab Version 0.13.1 ergänzt **MV-Abtau** dieselbe
Einordnung. Beide Entitäten gehören zum Hauptgerät und sind zunächst deaktiviert.
Sie lassen sich in dessen Entitätseinstellungen aktivieren. Ihre Zustände
bezeichnen weder aktive Kühlung noch einen tatsächlichen Abtauvorgang;
ungeprüfte Statuswörter ergeben „Nicht verfügbar“.

Für gezielte Beobachtungen ergänzen vier optionale Hex-Diagnosesensoren die
vollständigen Payloads `118000/01F8`, `118000/03B6`, `118007/0191` und
`224000/0208`. Sie bleiben zunächst deaktiviert und weisen den Bits keine
PTC- oder Heizbedeutung zu. Zusammen mit `224000/006C` führen sie den Zeitpunkt
des letzten gültigen Empfangs als Attribut. Auch identische Telegramme erneuern
diesen Zeitpunkt; für Benachrichtigungen zählt deshalb der Wechsel des
Hex-Zustands und nicht jede Attributaktualisierung.
