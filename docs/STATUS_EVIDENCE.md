# Freigabestand der Schaltzustände

Die Tabelle fasst die mit der BDE-Anzeige abgeglichenen Zuordnungen und
Kandidaten zusammen. Die geprüfte Basis umfasst 41 Aufnahmefenster mit 183.780
prüfsummengültigen Frames und vollständiger Abdeckung der empfangenen Bytes.
Identische Fenster sind dedupliziert. Überlappende Fenster können denselben
Schaltvorgang enthalten. Separate BDE-Vergleiche belegen unter anderem den
unverdeckten Ein→Aus-Wechsel von MV-Abtau.

Bitnummern zählen ab 0 im Little-Endian-Wort. Die vollständige Telegrammidentität
und Payloadlänge bleiben Teil jeder Zuordnung.

| Anzeige/Kandidat | Beleg und Grenze | Entscheidung |
| --- | --- | --- |
| MV-Heizen/Kühlen: `224000/006C/4`, Bit 9 | BDE-Vergleiche beider Zustände und gefilmte fallende Flanke stimmen überein. Bleibt nach Verdichterstopp noch gesetzt; bei natürlichem Heizbetrieb auch als Aus beobachtet. | Bestehende optionale Anzeige beibehalten; keine Aussage „aktive Kühlung“. |
| MV-Abtau: gleiche Antwort, Bit 7 | Positive und negative BDE-Anzeigen sowie ein unverdeckter gefilmter Ein→Aus-Wechsel passen. | Optionale BDE-Ventilanzeige ab 0.13.1; kein Nachweis aktiven Abtauens. |
| PTC-Wohnen: `118000/01F8/4` Bit 11 / `118000/03B6/4` Bit 1 / `118007/0191/2` Bit 1 | Einschalten und Ausschalten passen in Eco Winter; ältere Komfort-Belege passen ebenfalls. PTC Ein bei allen drei Kandidaten null wurde beim Kühl-Auslauf zusätzlich per Video reproduziert. Beim späteren Kandidatenanstieg werden externe Raumaktoren erreichbar, bleiben jedoch ausgeschaltet und melden dann 0 W; davor ist ihre Leistung unbekannt. Die drei Felder können dieselbe Information spiegeln. | Eine allgemeine direkte Kopie der BDE-Anzeige ist widerlegt. Anforderung/Freigabe bleibt eine Hypothese; keine Zuordnung zur tatsächlichen Raumheizleistung. |
| MV-Vorwärme | Kein unabhängiger positiver BDE-Beleg. | Unbekannt. |
| Aktives Heizen/Kühlen: `224000/0208/4` | Bit 8 tritt bei Heizen und Kühlen auf; Bits 9/10 fallen teilweise vor Verdichterstopp. Bit 28 fehlt bei bestätigter Kühlung. | Keine belastbare Betriebszustandsanzeige aus diesen Einzelbits. |
| Eco-Luftstufe Zeitplan/fest | Auto in Eco Sommer/Winter folgt einem nutzerdefinierten Wochenzeitplan. Gleiche numerische Stufe kann Zeitplan- und feste Auswahl darstellen. In Komfort/Ofen bestimmt die Steuerung die Stufe ohne diese Auswahl. | Auswahl und Zeitplan nicht aus Rohstellwert oder Stufe ableiten. |

Der Upstream-Autor hat seine frühere Aussage **„0191=1 bedeutet Wärmeelemente
freigegeben“** [ausdrücklich zurückgenommen](https://github.com/markusmauch/proxon-hesp/pull/2#issuecomment-7189097549).
Seine Vergleichsfolge änderte gleichzeitig die Betriebsart; PTC-Wohnen wurde
nicht abgelesen. Sie belegt weder einen gespeicherten Freigabewert noch eine
ausschließliche Betriebsartenkodierung. Die oben genannten Kandidaten bleiben
ungeklärt. `0191` im LT-Katalog an Adresse 2 bezeichnet zudem eine andere
Identität als das Zwei-Byte-Wort an Adresse 30.
[Adress- und Nutzlängengrenze (Englisch)](ADDRESS_EVIDENCE.md)

Der später veröffentlichte
[Juli-Originalmitschnitt](https://gist.github.com/markusmauch/3f1a431a55cc71830be21ca2fd0ba9e0/ba888e35a475906bf6cf9070eed2edf697b66f83)
bestätigt diese Grenze anhand prüfsummengültiger Telegramme: Trotz berichteter
Freigabe bleibt `118007/0191/2` in Eco Winter null, wird im Ofen eins und fällt
noch vor dem Aus-SET wieder auf null. `03B6` Bit 0 zeigt dieselbe Wertfolge;
`01F8`, `022C` und die PTC-Bit-1-Kandidaten bleiben null. Es fehlt weiterhin
eine unabhängige PTC-Wohnen-Anzeige. Die Folge belegt weder eine tatsächliche
Heizleistung noch eine reine Betriebsartenkodierung. Ohne Zeitstempel liefert
der Mitschnitt nur die Frame-Reihenfolge.
[Umfang des Originalbelegs (Englisch)](CONTROL_EVIDENCE.md#original-p-2h-l-bde-mode-sequence)

## Ergänzende Belege aus natürlichem Winterbetrieb

Passive Winteraufnahmen zeigen `03B6` und `0191` Bit 0 vor der ersten positiven
Verdichterdrehzahl. Die PTC-Bit-1-Kandidaten bleiben im beobachteten Startfenster
null. Für ihren späteren Anstieg mit `01F8` Bit 11 fehlt eine zeitgleiche
PTC-Anzeige.

Ein BDE-Vergleich zeigt Heizbetrieb mit positiver Verdichterdrehzahl. Auf der
anschließend abgelesenen Schaltzustandsseite steht MV-Heizen/Kühlen auf Aus.
Die zeitlich getrennten Anzeigeseiten begrenzen die Aussage auf ihre jeweiligen
Beobachtungszeitpunkte. Bit 25 bleibt semantisch ungeklärt.

Eine weitere Originalfolge vom 27. November zeigt die obere LED grün und
**Heizbetrieb** auf der Hauptseite. Wenige Sekunden später zeigt die
Schaltseite Bypass, PTC-Wohnen, MV-Abtau, MV-Vorwärme und MV-Heizen/Kühlen
jeweils **Aus**, weiterhin mit grüner LED. HA-Screenshots vor und nach den
Gerätefotos führen die LED als **Nicht verfügbar**. Die unverfügbare LED-Anzeige
in HA belegt somit weder einen dunklen physischen Indikator noch ein leeres
Betriebsfeld. Die zeitlich getrennten Seiten liefern keinen gleichzeitigen
Widerspruch. Der nachfolgende Recorderabgleich bestätigt den vollständigen
Status-/Ventilkontext `12930092/27000000` bei den Fotozeiten; LED,
Betriebsanzeige und Regler-Luftstufe waren in HA unverfügbar. Ursprüngliche
Mode-/RPM-Empfangszeiten fehlen, sodass keine rückwirkende
15-Sekunden-Qualifikation behauptet wird. Eine getrennte Episode des Vortags
stützt denselben genauen Kontext mit LED Ein, Heizbetrieb und Luftstufe 2.
Die Zuordnung erweitert keine Ventilbit- oder PTC-Bedeutung.
[LED-Abdeckung und Aussagegrenzen (Englisch)](BDE_DISPLAY_EVIDENCE.md#observed-availability-gaps-november-2026)

In einer weiteren Phase mit positiver Drehzahl überdauert Bit 28 das
MV-Abtau-Ein-Fenster. Auch die begleitenden Temperatur- und Lüfteränderungen
reichen ohne zeitgleiche BDE-Referenz nur für eine Gegenprobe gegen die direkte
Gleichsetzung beider Zustände.

Die [Luftstufen-Freigabeliste](DATA_POINTS.md#optional-diagnostics) hält die
einzelnen vollständigen Wörter und ihre Belege fest. Die Zuordnung basiert
je nach Quelle auf vollständigen Rohintervallen oder auf Recorderwerten mit
validiertem Empfangszeitpunkt. Die abgelesene Geräteminute wird über empfangene
Kalenderwerte eingegrenzt. Für spätere Fotos gelten die beobachteten Zustände
ausschließlich zur sichtbaren Zeit. Deren Übertragung auf frühere
Verdichterflanken bleibt unbelegt.

Bei der Rückkehr zum ursprünglichen Sollwert fallen die drei PTC-Kandidaten
vor dem Verlust der HA-Erreichbarkeit externer Raumaktoren. Die Beobachtung
trennt den Kandidatenwechsel vom Ende der HA-Verfügbarkeit. Ob die elektrische
Freigabe früher endete, lässt sich ohne unabhängige Spannungs- oder Leistungsmessung
nicht ablesen.

Die Zuordnung weiterer Schaltzustände erfordert unabhängige positive und
negative BDE-Referenzen mit Rohkontext der vollständigen Identitäten.
[Passiv zu BDE-Belegen beitragen](REFERENCE_TESTS.md)

## Begrenzte BDE-Betriebsanzeige

Die bestehende optionale Diagnoseentität zeigt **Heizbetrieb** bei Eco Winter,
vollständigem `0208=0x82001312`, `0x8200131A` oder ab 0.16.9 `0x82009312`,
`006C=0x27` und positiver
Verdichterdrehzahl. Die einzelnen Zuordnungen beruhen auf
zeitlich eingegrenzten BDE-Belegen.

Für `0x82009312` zeigt eine unabhängige BDE-Referenz Eco Winter, Luftstufe 2 und
Heizbetrieb. Empfangene Kalendertelegramme grenzen die sichtbare Minute ein.
Status, Schaltwort und Modus sind darin stabil, die Drehzahl ist positiv. Die
15-Sekunden-Qualifikation kann erst nach Beginn der möglichen Fotozeit erfüllt
sein. [Zeitabgleich und Bedingungen (Englisch)](BDE_DISPLAY_EVIDENCE.md#additional-level-2-heating-context-0169).

Ab 0.16.5 ergänzt dieselbe Entität **Betriebsfeld leer** ausschließlich bei
Eco Winter, vollständigem `0208=0x8000100A`, `006C=0x25` und gültiger
Verdichterdrehzahl null. Zwei unabhängige Originalepisoden zeigen das leere
Betriebsfeld über vollständig passende Geräte-Minutenklammern. Ein weiterer
kompatibler Grenzfall zählt wegen einer kurzen Qualifikationslücke nicht als
dritte vollständig zeitgesicherte Referenz. Eine frühere Nachlaufphase erfordert eine eigene
zeitgleiche Referenz.

Für Eco Winter müssen alle vier Quellen höchstens sieben Sekunden alt sein;
die Komfort-Kühlanzeige behält ihre sechs Sekunden. Die erste Bestätigung
braucht mindestens 15 Sekunden kohärenten echten Empfang. Ein bereits
qualifizierter Heiztext darf zwischen den für das gewählte Profil zugelassenen
Heizkombinationen wechseln, solange alle Quellen frisch bleiben. Andere Kontexte
bleiben nicht verfügbar. „Betriebsfeld leer“ bezeichnet ausschließlich die
sichtbare BDE-Beschriftung, keine allgemeine Anlagenbetriebsart und keine
Aussage „Heizung aus“ oder „keine Wärmeabgabe“.

Ab 0.16.21 sind die getrennt belegten P2-Heizkombinationen
`0x8200931A/0x27` und `0x92009312/0xA7` mit positiver Drehzahl zusätzlich
zugelassen. Andere Bit-28-Kontexte bleiben ohne eigenen Beleg ausgeschlossen.
Ab 0.16.23 ist zusätzlich `0x92009312/0x27` mit positiver Drehzahl für das
ausgewählte P2-Referenzgerät zugelassen. Zwei getrennte BDE-Episoden stützen
Heizbetrieb, obere LED Ein und angezeigte Luftstufe 2 in genau diesem Kontext.
Heiztext und Luftstufe benötigen alle vier empfangenen Quellen innerhalb von
sieben Sekunden, die LED innerhalb von acht Sekunden. Der Heiztext benötigt
zunächst 15 Sekunden gültigen Empfang; ein bereits qualifizierter Heiztext
darf bei frischen Quellen zwischen den zugelassenen A7- und 27-Ventilworten
wechseln. Die weiteren LED-Kontexte `12930080/27000000`,
`12930082/67000000` und `12930082/47000000` ergänzen ausschließlich die
LED-Anzeige, keinen Heiztext, keine neue Luftstufe und keinen PTC-Zustand.
Die unabhängig zeitgeprüften PTC-Ein/000-Gegenfälle gelten weiterhin;
der Heiztext ergänzt keinen PTC- oder Abtauzustand. Entitäts-ID und
Aktivierungseinstellung bleiben erhalten.
[Genauer Beleg- und Testumfang (Englisch)](BDE_DISPLAY_EVIDENCE.md).
