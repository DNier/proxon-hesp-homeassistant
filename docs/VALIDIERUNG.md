# Validierung der ersten Entwicklungsfassung

Stand: 13. September 2026, Version 0.1.0.

## Automatisierte Prüfung

- Python 3.14.7, Home Assistant 2026.9.2.
- 21 Tests erfolgreich: Decoder, Prüfsummen, TCP-Empfang ohne Schreibzugriffe,
  Einrichtung und Reconfiguration, Sensoren, Registry, Verfügbarkeit und Entladen.
- Ruff-Lint, Formatprüfung und `git diff --check` erfolgreich.
- Entwicklungsabhängigkeiten sind in `uv.lock` fixiert.

## Wiedergabe des vorhandenen Anlagenmitschnitts

Der zuvor aufgezeichnete Mitschnitt mit 8430 Bytes wurde offline in künstlichen
37-Byte-Blöcken verarbeitet. Ergebnis: je sechs gültige Werte für Raumtemperatur,
Solltemperatur, Betriebsprogramm und Luftstufe, insgesamt 24 Werte.
Keine der vier unterstützten Kandidatenarten wurde wegen Prüfsumme oder Wertebereich
verworfen. Andere Telegramme werden übersprungen; das bestätigt ausdrücklich
nicht deren Prüfsummen oder eine vollständige Protokollabdeckung.

Die Rohaufnahme bleibt außerhalb des Repositorys. Vier reduzierte Telegramme
liegen als reproduzierbare Test-Fixtures bei.

## Noch offen

- Installation und längerer Betrieb auf der echten Home-Assistant-Instanz.
- Weitere Anlagenvarianten, Programme und Datenpunkte.
- Allgemeines Framing und vollständiger Prüfsummenalgorithmus.
- Steuerung einschließlich Buszugriff, Bestätigung und Zusammenspiel mit dem BDE.
- HACS-Installation auf der echten Home-Assistant-Instanz.

Bei dieser Implementierung wurden weder Live-HA noch das Gateway verändert.
Es wurden keine Steuertelegramme gesendet und keine Änderungen gepusht.

## Veröffentlichungsstand

Das Repository ist inzwischen öffentlich. Der eigene Code ist unter MIT lizenziert;
übernommenes Referenzmaterial bleibt gemäß NOTICE.md unter CC BY 4.0.
