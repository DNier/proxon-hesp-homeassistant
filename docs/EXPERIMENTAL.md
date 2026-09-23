# Experimentelle Statusbits mit dem BDE vergleichen

Ab **0.12.0b5** stehen drei optionale Diagnoseentitäten bereit:

- **Experimentell: Status 0x0208 Bit 8**
- **Experimentell: Status 0x0208 Bit 9**
- **Experimentell: Status 0x0208 Bit 28**

Die Entitäten sind zunächst deaktiviert. Auf der PROXON-Geräteseite die gewünschte
Entität öffnen und in den Einstellungen aktivieren. HA lädt die Integration
gegebenenfalls neu; benötigte Mitschnitte zuvor herunterladen.

„Ein“ heißt nur, dass das Bit gesetzt ist. „Aus“ heißt nur, dass es nicht gesetzt
ist. Keine der Anzeigen ist bereits als Heizanforderung, Verdichter-, PTC- oder
Ventilzustand bestätigt. Auch ein gültiges Telegramm mit vollständig null oder
FFFFFFFF wird ausschließlich als Bitmuster angezeigt, nicht als gültiger Anlagenzustand.

## Belege sammeln

Bei einem ohnehin auftretenden Übergang Uhrzeit, Bitzustand und den genauen
BDE-Schaltzustand notieren. Zusätzlich sind Betriebsart und Verdichterdrehzahl
hilfreich. Widersprüche und Übergänge sind aussagekräftiger als wiederholte
Beobachtungen desselben Zustands. Fotos sind optional; Störungen oder Abtauvorgänge
nicht absichtlich erzwingen. Ein laufender passiver Mitschnitt erleichtert später
den zeitlichen Vergleich.

Die Attribute enthalten Datenpunkt `0x0208`, Telegrammkennung `224000`, Bitnummer,
Rohbytes (`payload_hex`), vollständiges Statuswort (`status_word_hex`) und letzte
gültige Aktualisierung (`last_valid_update`, UTC). Die Nummerierung beginnt bei
Bit 0 des Little-Endian-32-Bit-Werts. Beispiel: Rohbytes `1a130090` entsprechen
Statuswort `9000131A`. Die Aktualisierung bezeichnet den Empfang, nicht den
physikalischen Schaltzeitpunkt; `interpretation: unconfirmed` bleibt ausdrücklich gesetzt.

Nur Telegramme mit passender Kennung, Länge, reservierten Bytes und Prüfsumme
aktualisieren die Werte. Nach 30 Sekunden ohne gültiges Telegramm oder sofort
bei Verbindungsabbruch sind die Entitäten nicht verfügbar. HA kann dabei Attribute
ausblenden. Fehlende Daten werden nicht als „aus“ ausgegeben.

Unbekannte vollständige Statuswörter werden für diese reine Bitansicht empfangen,
aber nicht zusätzlich als Regler-Luftstufen interpretiert. Die bisherige Liste
bestätigter Luftstufen bleibt unverändert. Dadurch zählen strukturell gültige
Statuswörter jetzt als akzeptierte Telegramme, auch ohne Luftstufenzuordnung.
Die Sensoren senden keine Befehle und eignen sich nicht als bestätigte Grundlage
für automatische Anlagensteuerung. Weitere Ventil-/PTC-Kandidaten bleiben offen.
