# Solltemperatur-Test: abgeschlossen und archiviert

Stand: 14.09.2026. Die experimentellen Aktionen waren in **0.7.0 und 0.7.1**
enthalten und sind ab **0.8.0 entfernt**. Diese Seite ist keine Anleitung für
einen weiteren Versuch. Die historische Implementierung und Anleitung bleiben
im [Tag v0.7.1](https://github.com/DNier/proxon-hesp-homeassistant/blob/v0.7.1/docs/SOLLTEMPERATUR_TEST.md)
nachvollziehbar.

## Ergebnis des durchgeführten Versuchs

Der Nutzer führte einen einmaligen Versuch von 22 auf 22,5 °C aus. Es folgte ein
leeres ACK; nach etwa 1,3 Sekunden wurde wieder die reguläre Vorgabe 22 °C
empfangen. Beim späteren Aufwecken zeigte das BDE weiterhin 22 °C. Eine dauerhafte
Übernahme wurde nicht belegt; eine kurzzeitige Wirkung in der Hauptplatine bleibt
unbekannt. Die Antwort `transport_flushed_unverified` war keine Bestätigung
der Sollwertübernahme.

Zeitfolge, Datenqualität und Quellen stehen im
[Untersuchungsbericht](BDE_ZUGRIFF_UNTERSUCHUNG.md).

## Bereinigung in 0.8.0

Entfernt wurden beide Testaktionen, Freigabecodes, eigener Testmitschnitt und
Sendezugriff auf die TCP-Verbindung. Sensoren, stabile Entitäts-IDs sowie die
normalen Aufzeichnungsbuttons bleiben erhalten. Installation, Betrieb und
Wiederverbindung sind rein lesend. Ein HACS-Update erfordert einen HA-Neustart;
eine vorhandene Integration muss nicht neu eingerichtet werden.

Weiterführende Steuerungsentwicklung erfordert einen nachgewiesenen Zugriff auf
den BDE-Sollwert oder ein ausdrücklich definiertes alternatives Betriebsmodell.
Regelmäßiges Gegenschreiben wird nicht als Synchronisierung eingesetzt.
