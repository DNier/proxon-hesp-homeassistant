# Gezielte BDE-Vergleiche

Bei einer Belegaufnahme liest du die BDE-Anzeige während des normalen Betriebs
ab und vergleichst sie mit den empfangenen HESP-Daten. Die technische Einordnung
und die bekannten Gegenbeispiele stehen unter [Schaltzustände](STATUS_EVIDENCE.md).

1. Eine vorhandene Aufnahme nutzen oder die passive Aufnahme in Home Assistant
   starten. Benötigte frühere Mitschnitte zuerst sichern.
2. Betriebsart, sichtbare Anzeige und den ungefähren Beobachtungszeitpunkt
   festhalten. Bei laufender Aufnahme eignet sich die Aktion
   **Diagnosebeobachtung markieren** für die Zuordnung.
3. Den Vergleich auf den Zeitraum begrenzen, in dem der angegebene Zustand
   tatsächlich sichtbar war. Mehrere Aufnahmen desselben Ereignisses zählen als
   ein Beleg.
4. Originale und genaue Zeitachsen privat aufbewahren. Für eine öffentliche
   Meldung genügen Hardwareprofil, beobachtete Anzeige und ein bereinigter
   Ausschnitt. [Diagnose und Aufnahmen](DIAGNOSTICS.md)

## Bedienverhalten der Referenzanlage

Am BDE der Referenzanlage wurden folgende Auswahlmöglichkeiten beobachtet.

| Betriebsart | Luftstufenwahl am BDE | Intensivlüftung |
| --- | --- | --- |
| Eco Sommer | Feste Stufe 1–4 oder Auto wählbar | Nicht verfügbar; Stufe 4 wird manuell gewählt |
| Eco Winter | Feste Stufe 1–4 oder Auto wählbar | Nicht verfügbar; Stufe 4 wird manuell gewählt |
| Komfort | Steuerung bestimmt die Stufe; keine manuelle Auswahl und keine Eco-Auto-Auswahl | Stufe 4 für eine voreingestellte Dauer |
| Ofenbetrieb | Steuerung bestimmt die Stufe; keine manuelle Auswahl und keine Eco-Auto-Auswahl | Stufe 4 für eine voreingestellte Dauer |
| Aus | Bedienverhalten noch nicht separat abgeglichen | Noch nicht separat abgeglichen |

Diese fünf Betriebsarten sind am BDE der Referenzanlage vorhanden. **Intensivlüftung
ist zeitlich begrenzte Lüftung auf Stufe 4 in Komfort oder Ofenbetrieb.** Eine
manuell gewählte Stufe 4 in Eco ist keine Intensivlüftung. Die numerische Stufe
allein unterscheidet diese Fälle nicht; der vorhandene Intensivstatus bleibt eine
separate Anzeige.

**Auto in Eco** bedeutet Betrieb nach einem vom Nutzer eingestellten
Wochenzeitplan mit Wochentag, Uhrzeit und Luftstufe. Es bezeichnet keine belegte
bedarfsgeführte Vollautomatik. Die Stufenwahl durch die Steuerung in Komfort/Ofen
ist davon zu unterscheiden; ihre Regelkriterien werden hier nicht festgelegt.
Diese Beobachtung wird nicht pauschal auf andere Firmware- oder Gerätevarianten
übertragen. Die Übertragung des Zeitplans beziehungsweise der Auswahl auf dem
beobachteten Bus ist weiterhin nicht zugeordnet.

## Referenzen für PTC-Wohnen

Auf der BDE-Seite **Schaltzustände** den sichtbaren Zustand **PTC-Wohnen** ablesen.
Für zusammengehörige Aufnahmen die Anzeige einheitlich als
`BDE PTC-Wohnen` und den Zustand als `ein` oder `aus` markieren.

Die Markierung beschreibt den angezeigten Zustand. Für die elektrische Leistung
sind frische Messwerte der betreffenden Heizelemente erforderlich. Ein
erreichbarer Aktor oder ein eingeschalteter Schalter allein belegt keinen
Stromfluss. Fehlende oder veraltete Leistungsmessungen bleiben unbekannt.

## Gezielter Kühlvergleich für den PTC-Gegenfall

Normal beobachtete Kühl- und Nachlaufphasen eignen sich zur Gegenprobe.
Für den Vergleich werden die BDE-Anzeige, Betriebsart, Soll-/Istwert,
Verdichterdrehzahl sowie die vollständigen Telegramme `224000/006C/4` und
`224000/0208/4` zusammen mit den PTC-Kandidaten betrachtet. Eine zwischenzeitlich
verdeckte Anzeige bleibt für diesen Zeitraum unbekannt.

<a name="ergebnis-und-anschließende-prüfung"></a>

### Beleggrenzen

Ein- und Ausschaltbelege in Eco Winter und Komfort passen teilweise zu
`118000/01F8/4` Bit 11, `118000/03B6/4` Bit 1 und `118007/0191/2` Bit 1.
Zeitlich zugeordnete Gegenbelege zeigen PTC-Wohnen **Ein**, während alle drei
Kandidaten null melden. Damit scheidet eine allgemeine direkte Kopie der
Anzeige aus. Welche Felder eine Anforderung melden, bleibt offen. Die genauere
Abgrenzung steht unter [Schaltzustände](STATUS_EVIDENCE.md).

## Optionaler Vergleich in Eco: Zeitplan oder feste Luftstufe

In Eco Sommer und Eco Winter lässt sich die gewählte **Auto**- oder
**Feststufen**-Auswahl unabhängig von der gemeldeten Stufennummer ablesen.
Für den Vergleich eignen sich Zustandsabschnitte mit gleicher numerischer Stufe
und unveränderter Betriebsart. Unterschiede in Temperatur, Drehzahl oder
Empfangszeit können andere Ursachen haben.

Für eine laufende passive Aufnahme eignet sich die Beschriftung
`BDE Luftstufenauswahl` mit `auto` oder etwa `manual_3`. Markierte Zustände
gelten für den beobachteten Zeitraum; die Auswertung behandelt eine Markierung
als Meldung am Ablesezeitpunkt. Die untersuchte Auswahl muss am BDE sichtbar
sein: Eine numerische Luftstufe oder Intensivlüftung allein genügt als Referenz
nicht. [Manuelle Markierungen auswerten](OFFLINE_ANALYSIS.md#aligning-recorded-user-observations)

## Weitere Anzeigegruppen

| Anzeigegruppe | Fehlender unterscheidender Beleg | Unabhängige Referenz |
| --- | --- | --- |
| PTC-Wohnen | Freigabe, Raumforderung und tatsächliche elektrische Leistung getrennt | BDE-Zustand, externe Schalter und Leistungsmessung; nicht erreichbare Sensoren bleiben unbekannt |
| MV-Abtau | BDE-Anzeige jetzt zugeordnet; tatsächlicher Abtauvorgang und andere Hardware bleiben separat offen | Positive/negative Anzeige und gefilmter Ein→Aus-Wechsel; keine Gleichsetzung mit aktivem Abtauen |
| MV-Vorwärme | Positiver Ein-Zustand und Aus-Gegenprobe | BDE-Anzeige und Rohaufnahme |
| Aktives Heizen/Kühlen | Anforderung, Ventil und Verdichterlauf einschließlich Nachlauf getrennt | BDE-Anzeigen, Drehzahl und passende Phasen; Temperatur allein genügt nicht |
| Fehlermeldung | Natürlich auftretender Fehler mit sichtbarem Text | BDE-Fehleranzeige und unveränderte Rohaufnahme; keine Störung absichtlich auslösen |
| Systeminformationen / Zeitprogramme | Übertragung oder lokale BDE-Daten unterscheiden | Sichtbare Einzelanzeige und gezielte Vergleichsaufnahme; bisher keine bestätigte neue Zuordnung |

Ein einzelner Treffer ist eine Beobachtung. Für eine belastbare Zuordnung
zählen bestätigte Gegenproben, vollständige Telegrammidentitäten und die
getrennte Prüfung weiterer Hardwareprofile.
