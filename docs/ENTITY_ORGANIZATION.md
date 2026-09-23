# Entitäten am Hauptgerät

Diese Einteilung gilt ab **0.12.0b4**. Die Integration verwendet die vorgesehenen HA-Entitätskategorien.
Zusätzliche Geräte allein zur Sortierung von Messwerten werden nicht angelegt.

| Einordnung | Entitäten | Bei Neueinrichtung |
|---|---|---|
| Normale Sensoren und Zustände | Betriebsart, angeforderte Luftstufe, Raum-/Solltemperatur, Zu-/Ab-/Fort-/Frischlufttemperatur, Verdichter läuft, Bypass und Intensivlüftung | Aktiviert |
| Diagnose | Filterrestlaufzeit, Betriebsstunden, Aufnahmestatus und Aufnahmeaktionen | Aktiviert |
| Optionale Diagnose | Sechs interne Temperaturen, drei Drehzahlen, roher Kalender, lokale Gerätezeit, Regler-Luftstufe, rohe Stellwerte, Hex-Datenpunkte, Verbindung und letzter gültiger Empfang | Deaktiviert |
| Konfiguration | Manueller Gerätezeitabgleich | Deaktiviert |

Die Kategorie Diagnose beschreibt den Verwendungszweck, nicht die Genauigkeit.
Ein deaktivierter Drehzahlsensor unterbindet weder den Datenempfang noch den
Sensor **Verdichter läuft**. Optionale Werte lassen sich einzeln in den
Entitätseinstellungen aktivieren.

## Bestehende Installationen

Entitäts-IDs, eindeutige Identitäten, eigene Namen sowie Aktivierungsentscheidungen
bleiben beim Update erhalten. Die geänderte Kategorie ordnet bestehende Werte der
Diagnose zu. Neue Aktivierungsstandards deaktivieren keine bisher aktiven Entitäten.
Die deutschen Drehzahlnamen lauten einheitlich Zuluftdrehzahl, Abluftdrehzahl und
Verdichterdrehzahl. Eigene Namen haben weiterhin Vorrang.

Nicht benötigte Detailwerte können manuell deaktiviert werden, sofern sie nicht
in Dashboards, Verlauf oder Automationen gebraucht werden. Die Integration nimmt
keine pauschale Deaktivierung oder Umbenennung bestehender Entitäts-IDs vor.
Die Standard-Geräteseite bestimmt ihr Layout selbst; frei gestaltete fachliche
Abschnitte gehören in ein eigenes Dashboard.

Ab 0.12.0b5 ergänzen drei standardmäßig deaktivierte [experimentelle Statusbits](EXPERIMENTAL.md) die Diagnose.
