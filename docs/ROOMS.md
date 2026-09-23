# Heizräume mit vorhandenen Home-Assistant-Entitäten

Die optionale Raumverwaltung ergänzt herstellerunabhängige, **nur lesende**
Überwachung elektrischer Raumheizelemente. Pro konfiguriertem Raum entsteht ein
virtuelles Gerät der PROXON-Integration. Es kann einem vorhandenen HA-Bereich
zugeordnet werden. Ohne konfigurierte Räume bleibt die Integration unverändert.

## Einrichtung

1. Unter **Einstellungen → Geräte & Dienste → PROXON HESP** am
   Integrationseintrag **Heizraum hinzufügen** wählen.
2. **Raum und Heizelemente:** Namen, optionalen HA-Bereich und mindestens eine
   `switch`-Entität auswählen. Optional Leistungssensoren der Heizelemente
   zuordnen. Mehrere Schalter und Messungen pro Raum sind möglich.
3. **Optionale Verknüpfungen:** Bestehendes Thermostat, Temperatur und
   Luftfeuchtigkeit auswählen oder leer lassen. Diese Referenzen erzeugen keine
   doppelten Sensoren und keine neue Regelung.
4. **Messwert-Einstellungen:** Leistungsschwelle und maximales Messwertalter
   passend zur Installation wählen. Mit dem Abschluss wird der Raum gespeichert.

Jeder Raum erscheint als eigener Untereintrag unter der PROXON-Integration.
Dort kann er direkt konfiguriert oder über die native HA-Löschfunktion entfernt
werden. Nur die virtuellen Raumgeräte und deren Überwachungsentitäten werden
entfernt. Die verknüpften Fremdgeräte, Sensoren, Schalter, Thermostate und
HA-Bereiche bleiben erhalten.

Aufnahmeoptionen werden ausschließlich über **Konfigurieren** am übergeordneten
PROXON-Eintrag geändert. Die Raumdialoge verändern diese Einstellungen nicht.
Ein abgebrochener Raumdialog speichert nichts. Raumänderungen starten weder die
Gateway-Verbindung noch laufende Aufnahmen neu.

### Übernahme bestehender Räume

Ab **0.12.0b3** werden die in früheren Betaversionen konfigurierten Räume beim
Laden automatisch in HA-Untereinträge überführt. Die bisherigen Raum-IDs,
Geräte- und Entitätsidentitäten, Bereiche und Quellverknüpfungen bleiben erhalten;
die Räume müssen nicht neu angelegt werden. Auch die Aufnahmeoptionen bleiben
bestehen.

Dabei steigt die Version des gespeicherten Konfigurationsformats von 1 auf 2.
Frühere Integrationsversionen können dieses Format nicht laden. Vor einem
Downgrade ist eine Sicherung von vor der Migration wiederherzustellen; bloßes
Installieren einer älteren Beta ist kein unterstützter Rückweg.

## Entitäten und Bedeutung

| Entität | Bedeutung |
| --- | --- |
| Alle Heizschalter erreichbar | An, wenn alle konfigurierten Schalter einen bekannten Zustand `on` oder `off` haben. Aus bedeutet, dass mindestens einer nicht so verfügbar ist. |
| Mindestens ein Heizschalter eingeschaltet | An, sobald mindestens ein Schalter `on` meldet. Aus nur, wenn alle `off` melden; sonst unbekannt. |
| Elektrischer Heizbetrieb erkannt | An, wenn die Summe gültiger Leistungswerte die konfigurierte Schwelle überschreitet. Aus nur bei vollständigen gültigen Messungen unterhalb oder auf der Schwelle; sonst unbekannt. Ohne Leistungssensoren immer unbekannt. |
| Leistung der Heizelemente | Summe aller konfigurierten Leistungssensoren in W. Nur vorhanden, wenn Leistungssensoren verknüpft wurden. Bei mindestens einem fehlenden oder ungültigen Teilwert unbekannt. |

Eine ausreichend hohe **Teilmenge** gültiger Leistungswerte kann elektrischen
Heizbetrieb belegen, obwohl die Gesamtleistung unbekannt bleibt. Das ist kein
Widerspruch: die vorhandenen Messungen belegen Verbrauch, aber nicht dessen
vollständige Höhe.

Erreichbarkeit bestätigt **keine zentrale PROXON-Freigabe**. Eine nicht erreichbare
Entität kann stromlos sein oder ein Verbindungsproblem haben. Ebenso beweist ein
eingeschalteter Schalter allein keinen Stromfluss. Die Raumüberwachung bestimmt
weder den Heiz-/Kühlbetrieb noch den Abtauzustand des zentralen Verdichters.

## Auswahl der Messwerte

- Nur Leistungsmessungen zuordnen, die ausschließlich die betreffenden
  Heizelemente erfassen. Andere Verbraucher können falsche Heiznachweise erzeugen.
- Keine überlappenden Summen und Einzelmessungen kombinieren. Die Integration
  kann nicht erkennen, ob zwei unterschiedliche Sensoren denselben Strom messen.
- Derselbe Schalter oder Leistungssensor darf innerhalb eines Integrationseintrags
  nur einem Raum zugeordnet werden. Temperaturquellen dürfen geteilt werden.
- Die Schwelle gilt für die **Summe** des Raums und wird strikt überschritten.
  Standard: 10 W. Dieser Wert ist ein Ausgangspunkt, kein universell bestätigter
  Grenzwert. Oberhalb des gemessenen Standby-Verbrauchs einstellen.
- Maximales Alter: standardmäßig 300 Sekunden, einstellbar von 30 bis 86400.
  Bezug ist die letzte Meldung des Zustands an Home Assistant (`last_reported`),
  nicht nur die letzte Wertänderung. Auch eine wiederholte Meldung desselben Werts
  erneuert die Frische. Die Alterung wird spätestens beim nächsten 30-Sekunden-
  Prüflauf sichtbar. Quellen, die nur Wertänderungen melden, benötigen eine
  entsprechend gewählte Grenze oder eine regelmäßig meldende Messquelle.
- `unknown`, `unavailable`, wiederhergestellte Platzhalter, negative oder nicht
  endliche Zahlen sowie andere Einheiten werden nicht als gültige Leistung
  verwendet. Fehlende Werte werden niemals in 0 W umgewandelt.
- Die Frischekontrolle bewertet HA-Meldungen. Sie kann nicht erkennen, ob eine
  vorgeschaltete Integration intern alte Hardwaremessungen erneut meldet.

## Regelung und Geräteverwaltung

Bestehende Thermostate bleiben für Solltemperatur, Hysterese und Schalten
verantwortlich. Die Raumverwaltung ruft keine Dienste zum Schalten auf und
sendet keine HESP-Befehle. Hersteller, Raumanzahl, Namen und Entitäts-IDs sind
nicht fest vorgegeben. Shelly, SwitchBot oder andere Hersteller sind keine
Voraussetzung; entscheidend sind passende HA-Entitäten.

Raum-IDs bleiben beim Bearbeiten erhalten. Geräte- und Entitätsidentitäten
bleiben damit auch bei Umbenennung und Neustart stabil. Registrierte Quellentitäten
werden über ihre Registry-ID verfolgt, sodass eine Änderung ihrer Entitäts-ID
übernommen wird. Nach Löschen und Neuanlegen einer Quelle muss sie erneut
zugeordnet werden. Bei Quellen ohne Registry-Eintrag gilt die konfigurierte
Entitäts-ID; nach deren Umbenennung ist eine neue Auswahl notwendig.

Die Bereichsauswahl gilt nur für das virtuelle Raumgerät. Ein nachträglich in HA
am Gerät geänderter Bereich bleibt bei normalen Optionsänderungen und Neustarts
erhalten; eine ausdrücklich geänderte Bereichsauswahl im Raumdialog überschreibt
ihn. Fehlt dem Raumgerät ein Bereich, wird eine gespeicherte Bereichsauswahl
beim Laden wieder angewendet. Zum dauerhaften Entfernen die Bereichsauswahl auch
im Raumdialog löschen. Quellgeräte werden nie verschoben. Leere bzw. entfernte optionale Zuordnungen
werden beim Speichern gelöscht.

Nach einem HA-Neustart wird aus den verfügbaren Quellentitäten neu ausgewertet.
Alte Raumzustände werden nicht als bestätigter Heizbetrieb wiederhergestellt.
Die Raumverwaltung wird zusammen mit dem Integrationseintrag geladen; dessen
bestehender HESP-Verbindungsaufbau ist weiterhin Voraussetzung für den ersten
Setup-Erfolg. Ein späterer Gateway-Ausfall verhindert keine Aktualisierung aus
weiter verfügbaren Raumquellen.
