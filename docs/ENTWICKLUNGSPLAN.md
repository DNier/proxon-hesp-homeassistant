# Entwicklungsplan: PROXON HESP für Home Assistant

Stand: 13. September 2026. Zielplan; die erste lesende Entwicklungsfassung ist implementiert.
Historischer Ausgangsstand; das am 14.09.2026 anhand der Serviceberichte ergänzte
[Anlagenprofil](ANLAGENPROFIL.md) beschreibt Hardware, Firmware und Variantenabgrenzung.
Aktuelle Datenpunktabdeckung: siehe DATENPUNKTE.md.

## 1. Ziel und Umfang

Eine lokal arbeitende, über die HA-Oberfläche eingerichtete Custom-Integration
für unterstützte PROXON-P-Anlagen. Verbindung über einen transparenten
RS485/TCP-Gateway; MQTT, Cloud und ein zusätzlicher Dauerprozess sind nicht nötig.
Die Anlage regelt weiterhin selbst; HA wird kein Ersatz für ihre Regelung.

„Vollumfänglich“ bedeutet: alle nachweislich verfügbaren und sinnvoll nutzbaren
Funktionen der jeweils unterstützten Anlage. Es bedeutet nicht, jeden unbekannten
Datenpunkt oder jeden Fachmannparameter als bedienbare Entität anzubieten.
FWT/Modbus ist ein anderer Protokollpfad. Eine separate Trinkwasser-Wärmepumpe
ist nicht automatisch Bestandteil dieses HESP-Busses. Kühlung, PTC-Raumzonen,
Bypass, EWT und Zeitprogramme benötigen jeweils einen eigenen Nachweis.

**Zielarchitektur:** Proxon → transparenter TCP-Gateway → asynchrone
HESP-Bibliothek → HA-Gerät und Entitäten. Ein Verbindungsinhaber pro Anlage.

## 2. Ausgangslage und Evidenz

- Funktionierender passiver Mitschnitt: 30 s, 8.430 Bytes, 576 strukturell
  zerlegte Telegramme. Dies ist noch kein Dauer- oder vollständiger Protokolltest.
- 516 Telegramme passen zum eingeschränkten Prüfsummenmodell der Referenz;
  48 liegen außerhalb seines geprüften Umfangs; 12 passen nicht dazu
  (0x0160 und 0x0208). Ursache offen, nicht pauschal als Leitungsfehler einstufen.
- Am BDE abgeglichen: Luftstufe 3 (0x00e1), Eco Sommer / Wert 1 (0x020a),
  Solltemperatur 21 °C (0x0227). Raumtemperatur 22,61–22,68 °C (0x0226)
  ist mit der gerundeten BDE-Anzeige 23 °C vereinbar; kein zeitgleicher Präzisionstest.
- Lüfterdrehzahlen erscheinen plausibel; Kanalreihenfolge ist noch zu bestätigen.
  Filterrestzeit 114 Tage ist bisher eine Zuordnung aus der Referenz.
- Keine eigenen Schreibbefehle getestet. Beobachtete SET-Telegramme stammen
  aus der bestehenden Kommunikation und belegen keine eigene Schreibfähigkeit.
- Nutzeranlage: Hauptplatine LT-ZIM V1.6, PTC-Modul 4× V1.2, BDE an PTC-X1,
  Verbindung PTC-X2 zur Hauptplatine X5. Diese beobachtete Variante getrennt
  von der X7-Bezeichnung der Referenz dokumentieren. Keine universelle
  Anschlussanleitung allein aus Aderfarben oder Steckernummern ableiten.

## 3. Geräte- und Identitätsmodell

### Hauptgerät

Ein HA-Gerät „PROXON“ repräsentiert die zentrale Lüftungsheizung. Hersteller,
exakter Gerätetyp, Hardware- und Firmwareversion werden nur übernommen, wenn
gelesen oder belegt. Der lokale Wartungsbericht nennt inzwischen P 2 H-L;
die abweichende Bezeichnung im Servicebericht bleibt im Anlagenprofil dokumentiert.
Diese lokale Angabe nicht als automatisch erkanntes Modell anderer Anlagen ausgeben.
HA hat keinen generischen Gerätetyp-Schalter „Wärmepumpe“: Gerätedaten beschreiben
die Hardware; die Domains climate, fan und sensor bestimmen die Funktionen.

Zunächst keine Geräte je interner Platine und kein eigenständiges Gateway-Gerät,
solange wir dessen Identität/Diagnose nicht wirklich verwalten. Spätere, unabhängig
adressierbare Raumregler erhalten eigene Geräte und Raumzuordnung. Physische
Verbindung und logische Unterteilung gemäß der dann unterstützten HA-Version
modellieren; via_device nicht als beliebige Gruppierung verwenden.

### Dauerhafte Identität

- Bevorzugt eine nachweislich eindeutige Anlagen-/Controllerkennung; deren
  Verfügbarkeit und Stabilität zuerst untersuchen.
- Fallback: bei Einrichtung erzeugte und persistierte Anlagen-UUID.
  Keine IP-Adresse und keine Gateway-MAC als Identität der Wärmepumpe.
- Entitäts-Unique-ID aus Anlagenidentität und dauerhaftem semantischem Schlüssel;
  interne DP-Zuordnung bleibt im Profil. Keine lokalisierten Namen in Unique-IDs.
- IP-/Port-Wechsel, Umbenennung, Reload und Update erhalten Entitäten und Historie.
  Bei UUID-Fallback Grenzen der Wiedererkennung nach Löschen ausdrücklich nennen.
- Doppelte Einrichtung desselben Endpunkts verhindern; Anlagenidentität zusätzlich
  prüfen, falls verfügbar. Mehrere Anlagen müssen voneinander getrennt bleiben.

## 4. Entitätsmodell

Alle Namen unten sind Vorschläge für Anzeigenamen, keine fest verdrahteten entity_ids.
Einheiten, Übersetzungen (Deutsch/Englisch), has_entity_name und stabile Schlüssel
gehören in zentral definierte EntityDescriptions.

| Funktion | HA-Abbildung | Voraussetzung / Semantik |
|---|---|---|
| Zentrale Temperaturregelung | climate „Raumklima“ | Erst mit freigegebener Steuerung; Ist-/Solltemperatur, passende Betriebsarten und Presets |
| Lüftung | fan „Lüftung“ | Ein gemeinsamer Stufensteller; nicht zwei unabhängig steuerbare Lüfter erfinden |
| Raumtemperatur | sensor, temperature, °C, measurement | Eigener Sensor für Verlauf; zusätzlich climate.current_temperature |
| Zuluft, Abluft, Frischluft, Fortluft, weitere Temperaturen | sensor, temperature, °C, measurement | Jede Kanalzuordnung separat am BDE überprüfen |
| Solltemperatur, Betriebsart, Luftstufe | Zunächst lesende Sensoren | Bei Einführung von climate/fan vorhandene IDs beibehalten; redundante Sensoren ggf. standardmäßig deaktivieren |
| Zu-/Abluftdrehzahl | sensor, rpm, measurement | Kanalreihenfolge, Einheit und gültige Werte bestätigen |
| Filter-Restlaufzeit | sensor in Tagen | Abgleich und tägliches Dekrement; keine total_increasing-Semantik |
| Filterwechsel erforderlich | binary_sensor, problem | Nur belegtes Signal oder eindeutig bestätigte Schwelle |
| Verdichter läuft, Abtauung, PTC aktiv | binary_sensor | Nur aus bestätigten Rückmeldungen, nicht aus Sollwerten ableiten |
| Bypass | Zunächst Statussensor / binary_sensor | Offen/geschlossen oder Prozentstellung erst nach Semantikprüfung; kein cover ohne Positions-/Steuernachweis |
| Störung | binary_sensor problem + Fehlertext/-code | Bestätigte Fehlerzuordnung, kein „alles okay“ bei fehlenden Daten |
| Betriebsstunden | sensor, duration | Einheit, Reset und Zählverhalten bestimmen, dann state_class entscheiden |
| Buszustand, letzter gültiger Empfang, Prüffehlerzähler | Diagnoseentitäten | entity_category diagnostic; detaillierte Zähler standardmäßig deaktiviert |
| Leistungs-/Energiewerte | sensor power/energy nur bei echter Datenquelle | Keine geschätzten Verbrauchswerte als Messung veröffentlichen |

### Climate-Semantik als eigene Entscheidung

Eco Sommer, Eco Winter, Komfort und Ofen sind herstellerspezifische Programme.
Sie werden als Presets abgebildet, sofern deren Zusammenspiel mit HA-HVAC-Modi
eindeutig ist. Vor Implementierung eine Hin- und Rückabbildung aller Zustände
definieren: Proxon-Zustand → HA-Modus/Preset und HA-Aktion → exakter Proxon-Befehl.

- FAN_ONLY für Eco Sommer nur, wenn tatsächlich kein Heiz-/Kühlbetrieb möglich ist.
- HEAT für Heizprogramme nur nach bestätigtem Verhalten; COOL nur bei belegter
  Kühlfunktion. AUTO bedeutet nicht einfach „die Wärmepumpe regelt automatisch“.
- OFF darf nicht als vollständiges Ausschalten erscheinen, wenn tatsächlich nur
  eine Heizfunktion aus ist und Lüftung weiterläuft. Das reale Verhalten prüfen.
- Ofenbetrieb hat ggf. besondere Lüftungsanforderungen: nicht als beliebigen
  Modus behandeln und keine nicht belegten Sicherheitsfunktionen versprechen.
- Falls Presets keine ehrliche vollständige Abbildung erlauben: eigener select
  „Anlagenprogramm“ als Alternative. Keine zwei unabhängigen Schreibpfade für
  dieselbe Einstellung; alle Änderungen laufen über eine gemeinsame Zustandslogik.
- hvac_action nur aus tatsächlicher Rückmeldung. „Soll > Ist“ beweist weder
  Verdichterlauf noch aktives Heizen.
- Zulässiger Temperaturbereich und Sollwertschritt kommen aus einem verifizierten
  Profil. Die Rundung der Isttemperaturanzeige sagt nichts über Sollwertschritte aus.

### Fan-Semantik

Anzahl tatsächlich unterstützter Stufen prüfen. Bei vier Stufen kann HA 25/50/75/100 %
als diskrete Auswahl abbilden; das sind Stufenpositionen, keine gemessenen
Luftmengen oder Drehzahlprozente. Ausschalten und Zusammenspiel mit climate
explizit testen. Kein zusätzlicher unabhängig arbeitender fan_mode im climate
nötig, wenn fan die Lüftung bereits vollständig bedient.

## 5. Protokollbibliothek und Profile

HA-unabhängige Python-Bibliothek, asynchron, mit klarer API für Verbindung,
Statusereignisse, Datenpunkte und später geprüfte Kommandos. Zunächst gemeinsam
entwickelbar; vor Distribution als versioniertes Python-Paket bereitstellen,
damit HA es über requirements installieren kann. Kein sys.path-Trick und keine
Abhängigkeit von einem manuell gestarteten Skript.

- TCP ist ein Bytestrom: Fragmentierung, zusammengefasste Frames, Start mitten
  im Frame, Resynchronisierung, begrenzte Puffer und malformed input behandeln.
- Längenfeld anhand realer Kurz-/Langframes und ungerader Längen verifizieren;
  nicht jede Längenklasse ungeprüft durch dieselbe Formel dekodieren.
- Frame-Typ, Richtung, Node/Subadresse, DP und Nutzdaten trennen. Gleiche DP-ID
  an einem anderen Node ist nicht automatisch derselbe Sensor.
- Prüfsumme rekonstruieren/validieren. Referenzmodell hat unbekannte Bitbeiträge:
  für neue Werte nicht einfach Null einsetzen und daraus Schreibframes bauen.
- Zu jedem Wert Zeitstempel, Herkunft (Panel-SET oder Antwort), Qualität und
  Frische halten. NaN, Infinity, Sentinelwerte, unbekannte Enums und fehlerhafte
  Frames dürfen keinen plausibel aussehenden Zustand erzeugen.
- Datenpunktkatalog: Typ, Einheit, Skalierung, Zugriff, Grenzen, Node, Profil,
  Belege und Aktualisierungsrate. Stufen „unbekannt“, „Referenz“, „lokal abgeglichen“,
  „über Zustandswechsel bestätigt“, „steuerbar bestätigt“ getrennt führen.
- Unknown-Profil nur passiv. Neue Merkmale nicht anhand eines einzelnen
  zufälligen Werts automatisch freischalten. Passive Erkennung bevorzugen;
  aktive Selbstauskunft erst im separat geprüften Lesebetrieb.

## 6. HA-Einrichtung und Lebenszyklus

Config Flow: Host, Port, verständliches Anlagenprofil und Anzeigename. Prüfung
unterscheidet „TCP erreichbar“ von „gültige HESP-Daten erkannt“. Passiv beginnen;
keine Schreibprobe bei Einrichtung. Gateway muss transparent arbeiten, HESP ist
kein Modbus. Baudrate 19200/8N1 ist die beobachtete HESP-Konfiguration und bleibt
im Gateway eingestellt; die Integration konfiguriert ihn nicht stillschweigend um.

Ein gemeinsamer Client und Zustandsverteiler versorgen alle Entitäten. Push-Updates
über HA-kompatible Callbacks/Coordinator; keine Netzwerkzugriffe in Properties.
Manifest zunächst local_push, sofern ausschließlich empfangen wird; bei späterem
Polling Datenmodell und Deklaration erneut bewerten.

Reconfigure/Options für Endpunkt und geprüfte Funktionen. Fehlertexte für Timeout,
unpassendes Protokoll, unbekanntes Profil und belegten Gateway. Exponentielle
Wiederverbindung mit Begrenzung; EOF, Neustart und Netzunterbrechung behandeln.
Unload schließt Socket, Tasks, Timer und Listener vollständig. Keine parallelen
Mitschnittprogramme als Voraussetzung; Diagnosen aus derselben Verbindung gewinnen.

Verfügbarkeit pro Datenpunkt nach beobachteter Aktualisierungsrate, zusätzlich
Verbindungszustand. TCP offen bedeutet nicht frische Daten. Fehlende Werte sind
unknown/unavailable und nicht 0. Wiederhergestellte Werte bleiben veraltet, bis
aktuelle Busdaten vorliegen. Normale Änderungen nicht als Logspam ausgeben.

## 7. Steuerung: größtes offenes Arbeitspaket

Die [Offline-Auswertung der BDE-Schreibtelegramme](SCHREIBBEFEHLE_BEOBACHTUNGEN.md)
belegt inzwischen 1.300 SETs mit zeitlich passenden ACKs für vier ausgewählte
Datenpunkte in den Exporten (1)–(16). Das Werkzeug trennt Wiederholungen,
Wertänderungen und mehrdeutige Zuordnungen; eigener Buszugriff und dauerhafte
Übernahme eines externen Sollwerts sind damit noch nicht nachgewiesen.

Die Referenz berichtet, dass das BDE bzw. PTC seine Einstellungen etwa alle fünf
Sekunden wiederholt. Schnelleres Dauerschreiben ist keine freigabefähige Lösung.
Eine parallele RS485-Verbindung über TCP garantiert außerdem keine Kollisionsfreiheit:
lokale Stille am Socket ist wegen Pufferung/Latenz kein sicher freies Bus-Zeitfenster.

### Untersuchung vor eigener Bussteuerung

1. Passive Aufzeichnungen von gezielten normalen BDE-Änderungen aufnehmen.
   Jeweils eine Einstellung ändern; Zeitpunkt, vorher/nachher und Reaktion notieren.
2. Bestimmen, wer den Sollzustand besitzt, was wiederholt wird und ob externe
   Änderungen tatsächlich gespeichert oder lediglich kurz ausgeführt werden.
3. Prüfen, ob ein kooperativer Schreibweg existiert, z. B. eine bestätigte
   Bedienpanel-Funktion oder ein natives temporäres Override. Keine Existenz annehmen.
4. Buszugriffsverfahren prüfen: zusätzlicher Teilnehmer zulässig? Adressierung,
   Antwortkorrelation, Echo, Kollisionen und Timeout-Verhalten bestimmen.
5. Erst mit prüfbarer vollständiger Prüfsumme und geeignetem Zugriffsverfahren
   kontrollierte Einzeltests freigeben. Gefährliche/geschützte Parameter ausschließen.

**Entscheidungstor:** Gibt es auf dieser Hardware keinen zuverlässigen kooperativen
Schreibweg, bleibt die direkte Integration read-only. Eine Bridge, die gezielt
Kommunikation vermittelt, wäre ein eigenes Hardware-/Firmwareprojekt mit eigener
Ausfallprüfung; kein stilles Software-Upgrade des vorhandenen parallelen Adapters.
Vollständige Steuerbarkeit darf daher heute noch nicht zugesagt werden.

### Anforderungen an freigegebene Befehle

- Zentrale serielle Befehlswarteschlange, Wertevalidierung, Begrenzung der Rate,
  Zusammenfassen überholter Sollwerte. Keine parallelen Schreiber pro Entity.
- Nur erlaubte Nutzereinstellungen: zunächst Solltemperatur, Luftstufe und
  bestätigte Programme. Keine beliebigen Register-/Hex-Schreibaktionen.
- Korrelation über Node, DP, Typ und Zeitfenster; Echo nicht als Antwort zählen.
- Zustand erst nach Bestätigung/Rückmeldung übernehmen. ACK allein kann bloße
  Annahme bedeuten: Fortbestand über mehrere BDE-Zyklen und Wirkung prüfen.
- Fehler/Timeout verständlich als fehlgeschlagene Aktion melden. Keine
  unbeschränkten Retries, kein falsches „erfolgreich“ durch optimistische Anzeige.
- BDE-Bedienung hat im vorgesehenen Standardbetrieb Vorrang. Ein ausdrücklich
  wählbares Override wäre zeitlich begrenzt und müsste separat nachgewiesen werden.
- Bei HA-Ausfall, Reconnect oder Neustart keine alten Kommandos wieder abspielen.
  Nach Verbindungsaufbau zuerst Zustand neu empfangen. Normale Anlagenregelung
  muss ohne HA weiterlaufen.
- Verdichterzyklen, Frostschutz, Temperaturgrenzen und Schutzfunktionen bleiben
  in der Proxon; keine direkte Relais-/Verdichterregelung durch diese Integration.

## 8. Arbeitspakete und Abnahme

| Phase | Ergebnis | Abnahmekriterium |
|---|---|---|
| P0: Grundlagen | Exakten Gerätetyp/Firmware aufnehmen, Funktionsmatrix, Profil und Quellen festhalten | Bekannt, vermutet und offen sind getrennt; aktueller Aufbau nachvollziehbar |
| P1: Offline-Decoder | Bibliothek, kuratierte Mitschnitt-Fixtures, Framing und Prüfsummen | Gleiche Ergebnisse unabhängig von TCP-Schnittgrenzen; offene CRC-Fälle erklärt oder konsequent ausgefiltert |
| P2: Read-only-Integration | Config Flow, Hauptgerät, vier abgeglichene Sensoren, Diagnose | Einrichtung/Reload/Reconfigure funktionieren, passiver Modus sendet nachweislich keine Anwendungsbytes |
| P3: Telemetrie | Temperaturkanäle, Drehzahlen, Filter, Status, Zähler | Jeder veröffentlichte Kanal hat Beleg, Einheit, Datentyp und Frische-Regel |
| P4: Steuerungsuntersuchung | BDE-Ablaufmodell und Entscheidung für/gegen direkten Schreibweg | Kein bloßes Überstimmen durch Dauersenden; belastbarer Buszugriff und Zustandsbesitz geklärt |
| P5: Bedienelemente | climate/fan und ggf. ergänzende Elemente | Jede Aktion bestätigt, bleibt wirksam, verträgt BDE-Änderungen und fällt kontrolliert aus |
| P6: Beta | Dokumentation, Diagnoseexport, Installation auf zweiter Anlage | Mindestens 72 h lesender Betrieb; Ausfälle/Updates geprüft; Varianten nicht fälschlich erkannt |
| P7: Release | HACS-Paket, versionierte Library, Release Notes und Kompatibilitätsmatrix | Reproduzierbare Installation in sauberem HA; kein lokales Checkout erforderlich |

P4 kann anhand der Mitschnitte früh beginnen. P5 hängt zwingend von P4 ab;
ein fertiges Dashboard ist kein Nachweis für funktionierende Steuerung.

## 9. Teststrategie

- Decoder: Fragmentierung an jeder Byteposition, mehrere Frames je Block,
  falsche Längen/Checksummen, abgeschnittene Frames, unbekannte Nodes, Rauschen,
  Typ-/Skalierungstests und Speicherbegrenzung. Golden Fixtures unabhängig prüfen.
- Gefälschter TCP-Gateway: EOF, Stille bei offener Verbindung, Reconnect,
  doppelte/verspätete Telegramme und wechselnde Zustände reproduzierbar simulieren.
- HA-Tests: Config Flow, Duplikate, Profilwechsel, Entity-IDs, unterstützte
  Features, Übersetzungen, Migration, Unload, Nichtverfügbarkeit und Servicefehler.
- Befehle: Grenzwerte, kollidierende Nutzeraktionen, Panel-Override,
  Ack ohne Wirkung, fehlendes Ack, keine Wiederholung alter Aufträge nach Neustart.
- Reale Anlage: kontrollierte normale BDE-Änderungen abgleichen; keine
  automatisierten Hardware-Schreibtests in CI. Kühlung/Heizen nicht allein für
  Softwaretests ohne gesondert abgestimmten Ablauf auslösen.
- CI: Lint, Typprüfung, Bibliotheks- und Integrationstests, HA/HACS-Validierung;
  deklarierte Mindestversion und aktuelle unterstützte HA-Version testen.

## 10. Veröffentlichung und Pflege

Vor Freigabe: Code-Lizenz wählen, Attribution/Lizenz für übernommene Dokumentation
und Testdaten sauber halten. Öffentliches Repository und Paketveröffentlichung
separat beauftragen; dieser Plan erzeugt keine öffentlichen Issues/PRs.

HACS-konforme Struktur custom_components/proxon_hesp, manifest, config_flow,
translations, tests und hacs.json. Installation, Updates, Deinstallation,
Gateway-Voraussetzungen und bekannte Modellgrenzen dokumentieren. Versionsnummern
und Config-Entry-Migrationen von Anfang an führen. HA-Core-Aufnahme ist ein
späteres separates Ziel, keine Voraussetzung für HACS.

Gerätebilder/Anschlussfotos nur mit klarer Revision, Orientierung und Rechteklärung.
IP-Adressen, MACs, Seriennummern und personenbezogene Daten aus Diagnoseexporten
entfernen. Keine unbeschränkten Rohmitschnitte im Recorder oder in Standardlogs.
Rohdatenexport ausdrücklich anfordern und zeitlich/größenmäßig begrenzen.

Support: anonymisierte Diagnose, Versions-/Profilangaben, Issue-Vorlagen und
Release Notes. Neue Profile benötigen reproduzierbare Evidenz; Unterstützung
einer P-Serie ist kein Nachweis für alle PROXON-Modelle.

## 11. Unmittelbarer nächster Entwicklungsschritt

P0/P1 beginnen: Gerätetyp und Firmware ergänzen, vorhandenen Mitschnitt als
Testgrundlage aufbereiten, die beiden abweichenden Prüfsummenfälle untersuchen
und einen wiederverwendbaren Offline-Decoder bauen. Danach P2 mit vier Sensoren
auf einer Testinstallation. Keine Steuerung und keine Änderungen an der laufenden
HA-Konfiguration sind Bestandteil dieses Planungsdokuments.

## 12. Primäre Grundlage: markusmauch/proxon-hesp

Repository-Inhalt einschließlich README, MAINTAINING und Fachseiten am 13.09.2026
geprüft: Das öffentliche Projekt enthält Dokumentation, MkDocs-Konfiguration und
Website-Deployment, keine installierbare HA-Integration oder Python-Bibliothek.
Laut MAINTAINING findet die Laborarbeit in einem separaten privaten Repository
statt. Dessen Implementierungsumfang und Wiederverwendbarkeit sind unbekannt.

Vor eigener Implementierung beim Autor nach vorhandener Bibliothek, Parser,
Testmitschnitten und Interesse an Zusammenarbeit fragen. Keine automatische
Übernahme privater oder unveröffentlichter Implementierungen voraussetzen.

Bereits erarbeitet und als Referenz zu übernehmen: vier Steuer-/Raumdatenpunkte,
zehn Temperaturkanäle, Ist-/Zieldrehzahlen, Bypass, Filterlaufzeit, Fehlertext,
Betriebsstunden, Rohwerte, Kennlinien und Teile des Parameterblocks. Hinzu kommen
Frameformat, Nachrichtentypen, eingeschränktes Prüfsummenmodell und Selbstauskunft.
Diese Ergebnisse nicht neu erfinden; jeweils gezielt auf der Nutzeranlage bestätigen.

Selbstauskunft konkret prüfen: Node-Name 0x0001, DP-Verzeichnis 0x0033,
Typcodes 0x0034, Zugriffsmasken 0x0038 und Einheiten 0x0039. Sie kann Profile
unterstützen, beweist aber weder ein exaktes Anlagenmodell noch die vollständige
Semantik oder Sicherheit eines Schreibbefehls. Aktive Abfragen benötigen dieselbe
Buszugriffsprüfung wie andere selbst gesendete Telegramme.

Zusätzliche Randbedingungen: Zeitprogramme/Nachtabsenkung liegen laut Referenz
im BDE; ein Ersatz müsste diese explizit übernehmen. Eine Anbindung erhält das
BDE zunächst. Der 9600-Baud-Weg ist laut bisherigen Untersuchungen kein etablierter
alternativer Steuerweg. Das dokumentierte wiederholte Schreiben auf HESP hat eine
nachgewiesene Wirkung an der Referenzanlage; produktreife Konfliktbehandlung und
das Verhalten unserer Variante sind weiterhin zu untersuchen.

Zwei Unstimmigkeiten als konkrete Klärungspunkte festhalten: Die Protokolltabelle
nennt 0xe0 als 224 Nutzbytes, obwohl die Nibble-Definition 112 ergeben würde.
Außerdem bezeichnet offene-punkte.md das tägliche Filterdekrement als bestätigt,
während dp-referenz.md dies noch als offen führt. Im Implementierungsplan nicht
stillschweigend eine Seite als endgültig übernehmen.

Quellen: https://github.com/markusmauch/proxon-hesp und dessen MAINTAINING.md.

## 13. Ergänzender Vergleich mit charma/proxon-homeassistant

README und vollständige modbus.yml geprüft (13.09.2026). Das Projekt ist eine
Konfigurationsanleitung für die native HA-Modbus-Integration, getestet mit FWT2
(2017); kein eigener Python-HESP-Client und keine Custom-Integration.

Enthalten: 13 Sensoren (Betriebsart, CO2, Wohnzimmerfeuchte, Außen- und
Wohnzimmertemperatur, sechs weitere Raumtemperaturen, zwei Filterzeitzähler)
und ein Kühlungsschalter mit Rückleseprüfung. Abruf überwiegend alle 30 Sekunden,
Modbus TCP Port 502, Slave 41. Keine climate-/fan-Entitäten und keine
Solltemperatur-/Luftstufensteuerung in dieser Datei.

Für unseren Funktionskatalog zusätzlich prüfen: CO2 und Luftfeuchtigkeit, einzelne
Raumsensoren und getrennte Filterzeitzähler. Nur anbieten, wenn entsprechende
Hardware und HESP-Datenpunkte nachgewiesen sind. Modbus-Registeradressen,
Skalierungen und Betriebsartcodes nicht auf HESP übertragen. In der Vorlage
ist der als CO2 bezeichnete Sensor mit carbon_monoxide klassifiziert; dies wäre
für einen bestätigten CO2-Sensor zu carbon_dioxide zu korrigieren.

Übernehmbar sind Funktionsideen und das Prinzip der Rückmeldung nach Schreiben.
Transport, Parser, Profile, Geräteidentität und Steuerungskoordination müssen
für unseren HESP-Pfad eigenständig umgesetzt werden. Von der nativen
Modbus-Integration bereitgestellte Basisfunktionen sind nicht mit eigenem
Implementierungsumfang dieses Repositorys zu verwechseln.

Quelle: https://github.com/charma/proxon-homeassistant/blob/main/modbus.yml

## Quellen

- [Markus Mauch: Architektur](https://markusmauch.github.io/proxon-hesp/anlage/)
- [Markus Mauch: HESP-Protokoll](https://markusmauch.github.io/proxon-hesp/protokoll/)
- [Markus Mauch: Datenpunkte](https://markusmauch.github.io/proxon-hesp/dp-referenz/)
- [HA: Geräte](https://developers.home-assistant.io/docs/device_registry_index/)
- [HA: Climate](https://developers.home-assistant.io/docs/core/entity/climate/)
- [HA: Fan](https://developers.home-assistant.io/docs/core/entity/fan/)
- [HA: Config Flow](https://developers.home-assistant.io/docs/core/integration/config_flow/)
- [HA: Integration Quality Scale](https://developers.home-assistant.io/docs/core/integration-quality-scale/)
- [HACS: Integration veröffentlichen](https://www.hacs.xyz/docs/publish/integration/)

Architekturentscheidungen in diesem Dokument sind Projektvorschläge; sie sind
keine Behauptung, dass das Protokoll alle genannten Funktionen bereits ermöglicht.
