# Gezielte BDE-Vergleiche

Ziel ist eine belegte lesende Zuordnung. Jede Aufnahme untersucht eine konkrete
Anzeige mit unabhängig abgelesenem Zustand. Der derzeitige
[Freigabestand](STATUS_EVIDENCE.md) einschließlich Gegenbeispielen bleibt Grundlage.
Die Softwareentwicklung selbst erfordert keine Bedienhandlung an der Anlage.

## Bedienverhalten der Referenzanlage

Bedienerbeobachtung vom **4. Oktober 2026** an der Referenzanlage:

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

Für den nächsten Schaltzustandsvergleich die aktuelle Betriebsart beibehalten.
Auf der BDE-Seite **Schaltzustände** den Zustand **PTC-Wohnen** ablesen. In der
laufenden manuellen Aufnahme folgende Angaben markieren:

- **Beobachtete Anzeige:** immer `BDE PTC-Wohnen`.
- **Beobachteter Zustand:** `ein` oder `aus`, genau wie gerade am BDE angezeigt.

Die entscheidenden Anzeigen und Übergänge parallel filmen. Die Markierung
bezeichnet ausschließlich diese Anzeige, nicht pauschal alle Raumheizelemente.
Für elektrische Leistung werden zusätzlich vorhandene, frische Schalter- und
Leistungsmessungen der tatsächlich zugehörigen Heizelemente ausgewertet.
Erreichbarkeit allein bestätigt keine zentrale Freigabe; ein eingeschalteter
Schalter allein bestätigt keinen Stromfluss. Fehlende oder veraltete
Leistungsmessungen bleiben unbekannt.

Ein- und Ausschaltbelege in Eco Winter passen zu `118000/01F8/4` Bit 11,
`118000/03B6/4` Bit 1 und `118007/0191/2` Bit 1. Ältere Komfort-Belege stimmen
ebenfalls überein. Ein Komfort-Foto während des Kühl-Auslaufs zeigt jedoch
PTC-Wohnen Ein bei allen drei Kandidaten null; ein gefilmter Vergleich bei
unverändertem Komfort reproduziert diesen Gegenfall. Die Felder werden deshalb noch
nicht als PTC-Wohnen-Entität angeboten. Eine allgemeine direkte Kopie der
BDE-Anzeige oder eine Ausnahme nur nach Betriebsart ist nicht belegt.

## Gezielter Kühlvergleich für den PTC-Gegenfall

Der am 4. Oktober 2026 durchgeführte Vergleich untersucht den Gegenfall bei **unveränderter Betriebsart**:
PTC-Wohnen vor und nach einem höheren Sollwert während einer bestehenden
Kühlphase. Die Einstellung der Betriebsart gehört zur Vorbereitung der
Kühlsituation, nicht zum entscheidenden Sollwertvergleich. Der Versuch benötigt
die Aufnahme- und Markierungsfunktionen aus 0.13.0; die neue MV-Abtau-Entität
ist dafür keine Voraussetzung.

Vor Ort BDE-Verbindung, unveränderte Verkabelung, normale Bedienbarkeit und
fehlende Warnanzeigen bestätigen. Vor einem Kühlstart muss ein vorheriger
Heiz-/Abtauvorgang samt Nachlauf beendet sein. Frische Drehzahlmeldungen,
BDE-Betriebsanzeige und Schaltzustände gemeinsam prüfen; Drehzahl null allein
beweist keine ruhige Ausgangslage. Bei Störung oder Telemetrieverlust keine
weitere Bedienänderung durchführen.

1. Benötigte manuelle und automatische Aufnahmen sichern. Manuelle Dauer
   **600 Sekunden** und aktivierte Ereignisaufnahme prüfen; ein neuer manueller
   Start ersetzt die bisherige Aufnahme. Die Ereignisaufnahme hält bis zu
   180 Sekunden Vor- und Nachlauf in höchstens vier Fenstern.
2. Eine geeignete Kühlsituation am BDE vorbereiten. An der Referenzanlage wird
   dafür Komfort mit Soll 18 °C verwendet; der spätere Vergleich erhöht einmalig
   auf 26 °C. Diese Werte sind keine allgemeine Freigabe für andere Anlagen.
   Komfort regelt die Lüfter selbst. Kühlsituation mit BDE-Anzeige, Soll/Ist,
   Ventilzuständen und Drehzahl bestätigen; Soll unter Ist allein genügt nicht.
3. Sobald die Kühlphase bestätigt ist, Ausgangszustand und geplanten einmaligen
   Sollwechsel vorab abstimmen. Ein frisches manuelles Aufnahmefenster starten
   und prüfen, dass der Status aufzeichnend ist, Bytes zunehmen und gültige
   Telegramme empfangen werden. **Erst danach das kurze Video starten lassen.**
4. PTC-Wohnen, die Magnetventile, Bypass und LED kurz filmen. Den vorab
   vereinbarten Sollwechsel durchführen, direkt zur Schaltzuständeseite
   zurückkehren und den neuen Zustand zeigen. Betriebsart, Lüftereinstellungen,
   Freigaben und Zeitplan bleiben dabei gleich.
5. Die Einstellung während des Nachlaufs halten. Die Rohaufnahme läuft weiter;
   zusätzliche kurze BDE-Referenzen werden nur für noch offene Phasen benötigt.
   Vor einer Folgeaufnahme zuerst das beendete Fenster sichern. Eine spätere
   Rückstellung separat abstimmen, ohne schnelle Heiz-/Kühlwechsel.

Verglichen werden die drei vollständigen Kandidatenidentitäten, Soll-/Istwert,
Betriebsart, Verdichterdrehzahl sowie `224000/006C/4` und `224000/0208/4`.
Ausgangsreferenz, Menüverdeckung und beobachtete Folgezustände getrennt markieren.
Eine Referenzpause bedeutet unbekannt und ist kein dritter Gerätezustand.
Kamera- und Empfangszeiten getrennt erhalten; eine Meldung im Bus ist keine
sekundengenaue elektrische Schaltzeit.

Entscheidend ist, ob PTC Ein bei Kandidaten null erneut auftritt und wie die
Felder im folgenden Übergang reagieren. Auch dann ist „Anforderung“ oder
„Freigabe“ zunächst nur eine Hypothese. Eine passende Temperatur, LED oder
elektrische Raumleistung ersetzt die beobachtete BDE-Schaltzustandsreferenz nicht.

### Ergebnis und anschließende Prüfung

Der Gegenfall wurde reproduziert: PTC-Wohnen ist im Video Ein, während alle
drei Kandidaten wiederholt null melden. Erst beim späteren Anlauf steigen
sie; im anschließend sichtbaren Schaltzustand steht PTC-Wohnen weiterhin Ein.
Die Menüverdeckung lässt keinen exakten PTC-Flankenzeitpunkt zu.

Externe Raumaktoren werden kurz nach dem Kandidatenanstieg erreichbar. Ihre
Schalter bleiben aus, ihre dann verfügbaren Leistungsmessungen melden 0 W.
Vor der Erreichbarkeit ist die Leistung unbekannt. Bei der Rückstellung auf
den ursprünglichen Sollwert fallen die Kandidaten deutlich vor den späteren
HA-Nichtverfügbarkeitsmeldungen der Aktoren. Somit müssen eine mögliche
Anforderung, eine tatsächliche zentrale Stromfreigabe und deren Nachlauf
getrennt untersucht werden; HA-Erreichbarkeit allein misst keine Netzspannung.

Die vorhandenen Ein- und Ausschaltaufnahmen desselben Tages wurden zusätzlich
mit der HA-Historie der externen Aktoren verglichen. Auch beim früheren
Sollwechsel in Eco Winter fallen die Kandidaten deutlich vor den späteren
Nichtverfügbarkeitsmeldungen. Die nächste semantische Prüfung benötigt daher
eine unabhängige Unterscheidung von Anforderung und tatsächlicher zentraler
Freigabe. Eine Wiederholung desselben Kühlvideos ist dafür nicht erforderlich.
Die obige Bedienfolge dokumentiert den durchgeführten Versuch und ist keine
Aufforderung zu weiteren Anlagenänderungen.

## Optionaler Vergleich in Eco: Zeitplan oder feste Luftstufe

Dieser Vergleich ist ausschließlich für **Eco Sommer oder Eco Winter** mit
zugänglicher Auto-Auswahl vorgesehen. In **Komfort und Ofenbetrieb ist er nicht
durchführbar**. Ein Wechsel aus Komfort allein für diesen Nebenvergleich gehört
nicht zum aktuellen PTC-Versuch. Erst bei einer separat vereinbarten passenden
Eco-Ausgangslage durchführen.

Aus einer gemeldeten Stufe 3 allein folgt keine Auto-Auswahl. Vor Beginn
Betriebsart, Auswahl **Auto (Zeitplan)** oder feste Stufe und die momentan
vorgegebene Stufe am BDE ablesen. Der Vergleich muss innerhalb eines unveränderten
Zeitplanabschnitts liegen; einen geplanten Stufenwechsel vermeiden. Der Zeitplan
bleibt unverändert. Vorhandene funktionierende Verkabelung und BDE-Verbindung
verwenden.

Benötigt: Integration ab **0.13.0**, Zugang zur PROXON-Geräteseite und zu
**Entwicklerwerkzeuge → Aktionen** in HA, BDE und ein Video der Luftstufenauswahl.
Das Video sollte die entscheidenden Auswahlen zeigen; ein Wechsel in andere
Menüs ist für diesen Versuch nicht nötig. HA-Meldungen ersetzen die unabhängige
BDE-Referenz nicht.

1. Unter **Einstellungen → Geräte & Dienste → PROXON HESP → Konfigurieren**
   die manuelle Aufnahmedauer auf **600 Sekunden** stellen. Gemeint ist der
   Integrationseintrag, nicht der Dialog Systemoptionen.
2. In HA **Aufnahme starten** drücken, Video starten und kontrollieren, dass
   **Aufnahmestatus** aufzeichnend meldet. Vorhandene benötigte Aufnahmen vorher
   herunterladen, da erneutes Starten die vorige manuelle Aufnahme ersetzt.
3. In **Entwicklerwerkzeuge → Aktionen** die Aktion **Diagnosebeobachtung markieren**
   auswählen, den PROXON-Eintrag angeben und für **Beobachtete Anzeige** immer
   `BDE Luftstufenauswahl` verwenden.
4. Bei **Auto** den beobachteten Zustand `auto` markieren und etwa **60 Sekunden**
   halten. Die aktuell tatsächlich angezeigte Stufe notieren.
5. Am BDE manuell **dieselbe numerische Stufe** wählen. Bei vorheriger Stufe 3
   also manuelle Stufe 3. Jetzt `manual_3` markieren und etwa 60 Sekunden halten.
6. Zurück auf Auto, `auto` markieren und etwa 60 Sekunden halten.
7. Den Wechsel auf dieselbe manuelle Stufe und zurück auf Auto einmal wiederholen;
   beide Auswahlen markieren und jeweils etwa 60 Sekunden halten.
8. **Mitschnitt stoppen**, Diagnosedaten herunterladen und das Originalvideo
   aufbewahren. Den anfangs notierten Auswahlzustand wiederherstellen, falls er
   von der letzten Auto-Auswahl abweicht; eine Wiederherstellung nach Aufnahmeende
   separat nennen.

Währenddessen Betriebsart, Solltemperatur und Zeitplan nicht zusätzlich ändern.
Ziel ist die Unterscheidung der Auswahl bei möglichst gleicher
numerischer Stufe. Wenn ein Zeitplanwechsel die Stufe ändert oder ein anderes
Anlagenereignis auftritt, Zeitpunkt und Anzeige festhalten. Diese Abschnitte
werden nicht als isolierter Auto/manuell-Beleg gewertet.

Die Markierung ist eine beobachtete Zustandsangabe ab dem Meldezeitpunkt, keine
präzise Schaltflanke. Deshalb berücksichtigt die Auswertung eine Wartezeit nach
jeder Markierung. Der BDE-Zustand muss während des jeweiligen Vergleichsabschnitts
weiter gelten; Änderungen sofort neu markieren. Identische Zustände benötigen
identische Texte. Für andere Stufen den Text entsprechend wählen, z. B. `manual_2`.

Die Aufnahme dauert ungefähr fünf Minuten zuzüglich Bedienzeit. Tatsächliche
Dauer und Abschlussgrund prüfen: Speichergrenzen können vor dem Zeitlimit
stoppen. Die automatische Ereignisaufnahme genügt für diesen Versuch nicht,
da eine geänderte Auto-Auswahl allein keinen Verdichterwechsel auslösen muss.

## Weitere Anzeigegruppen

| Anzeigegruppe | Fehlender unterscheidender Beleg | Unabhängige Referenz |
| --- | --- | --- |
| PTC-Wohnen | Freigabe, Raumforderung und tatsächliche elektrische Leistung getrennt | BDE-Zustand, externe Schalter und Leistungsmessung; nicht erreichbare Sensoren bleiben unbekannt |
| MV-Abtau | BDE-Anzeige jetzt zugeordnet; tatsächlicher Abtauvorgang und andere Hardware bleiben separat offen | Positive/negative Anzeige und gefilmter Ein→Aus-Wechsel; keine Gleichsetzung mit aktivem Abtauen |
| MV-Vorwärme | Positiver Ein-Zustand und Aus-Gegenprobe | BDE-Anzeige und Rohaufnahme |
| Aktives Heizen/Kühlen | Anforderung, Ventil und Verdichterlauf einschließlich Nachlauf getrennt | BDE-Anzeigen, Drehzahl und passende Phasen; Temperatur allein genügt nicht |
| Fehlermeldung | Natürlich auftretender Fehler mit sichtbarem Text | BDE-Fehleranzeige und unveränderte Rohaufnahme; keine Störung absichtlich auslösen |
| Systeminformationen / Zeitprogramme | Übertragung oder lokale BDE-Daten unterscheiden | Sichtbare Einzelanzeige und gezielte Vergleichsaufnahme; bisher keine bestätigte neue Zuordnung |

Weitere Versuche erhalten jeweils einen eigenen Ablauf mit Ausgangszustand,
einer veränderten Bedingung, Wiederholung und Rückkehr. Eine positive
Übereinstimmung in einer Aufnahme wird anschließend gegen frühere Gegenbeispiele
und andere Installationen geprüft. Numerische Kandidaten werden nicht automatisch
als Sensoren freigegeben.
