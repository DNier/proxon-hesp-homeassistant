# Gezielte BDE-Vergleiche

Ziel ist eine belegte lesende Zuordnung. Jede Aufnahme untersucht eine konkrete
Anzeige mit unabhängig abgelesenem Zustand. Der derzeitige
[Freigabestand](STATUS_EVIDENCE.md) einschließlich Gegenbeispielen bleibt Grundlage.
Die Softwareentwicklung selbst erfordert keine Bedienhandlung an der Anlage.

## Erster Vergleich: Luftstufenauswahl Auto/manuell

Die Betriebsart, beispielsweise **Komfort**, ist eine andere Einstellung als
**Luftstufe Auto/manuell**. Aus einer gemeldeten Stufe 3 allein folgt keine
Auto-Auswahl. Vor Beginn beide Auswahlen am BDE ablesen und den Ausgangszustand
festhalten. Vorhandene funktionierende Verkabelung und BDE-Verbindung verwenden.

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

Währenddessen Betriebsart, Solltemperatur und Intensivlüftung nicht zusätzlich
ändern. Ziel ist die Unterscheidung der Auswahl bei möglichst gleicher
numerischer Stufe. Wenn Auto selbst die Stufe ändert oder ein anderes
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
| MV-Abtau | Sichtbare Anzeige über einen vollständigen natürlich auftretenden Übergang | BDE-Schaltzustände und Rohaufnahme, ohne verdeckende Menüwechsel |
| MV-Vorwärme | Positiver Ein-Zustand und Aus-Gegenprobe | BDE-Anzeige und Rohaufnahme |
| Aktives Heizen/Kühlen | Anforderung, Ventil und Verdichterlauf einschließlich Nachlauf getrennt | BDE-Anzeigen, Drehzahl und passende Phasen; Temperatur allein genügt nicht |
| Fehlermeldung | Natürlich auftretender Fehler mit sichtbarem Text | BDE-Fehleranzeige und unveränderte Rohaufnahme; keine Störung absichtlich auslösen |
| Systeminformationen / Zeitprogramme | Übertragung oder lokale BDE-Daten unterscheiden | Sichtbare Einzelanzeige und gezielte Vergleichsaufnahme; bisher keine bestätigte neue Zuordnung |

Weitere Versuche erhalten jeweils einen eigenen Ablauf mit Ausgangszustand,
einer veränderten Bedingung, Wiederholung und Rückkehr. Eine positive
Übereinstimmung in einer Aufnahme wird anschließend gegen frühere Gegenbeispiele
und andere Installationen geprüft. Numerische Kandidaten werden nicht automatisch
als Sensoren freigegeben.
