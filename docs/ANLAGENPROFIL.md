# Referenzanlage und Grenzen der Übertragbarkeit

Stand: 14.09.2026. Dieses Profil beschreibt die konkrete Anlage, an der die
Integration entwickelt und mit BDE-Anzeigen sowie Busmitschnitten geprüft wird.
Es ist keine automatische Geräteerkennung und keine Zusage für alle P-Anlagen.
Der interne Profilname bleibt `lt_zim_16_observed`.

## Quellen und Belegstatus

- **W:** Wartungsbericht von Zimmermann vom 03.09.2026, Seite 1,
  Gerätezeile und Bemerkungen.
- **S:** Servicebericht von Zimmermann vom 03.09.2026, Seite 1,
  Gerätefelder, durchgeführte Tätigkeiten und Materialliste.
- **F:** Vom Betreiber bereitgestellte Platinenfotos und BDE-Aufnahmen im
  September 2026; insbesondere BDE-Systeminformation und Messwertseiten.
- **M:** Passive HESP-Mitschnitte vom 13./14.09.2026, zuletzt mit Integration 0.4.0.
- **U:** [Markus Mauchs Anlagenbeschreibung](https://markusmauch.github.io/proxon-hesp/anlage/)
  und [Projektübersicht](https://markusmauch.github.io/proxon-hesp/),
  abgerufen am 14.09.2026. Diese Quelle beschreibt seine eigene Referenzanlage.

Die privaten Originalberichte bleiben außerhalb des Repositorys. Hier stehen
nur die technischen Angaben, ohne Personen, Anschrift, Kontaktdaten,
Auftragsnummer oder Unterschriften. Die Berichte sind Belege für den dort
beschriebenen Zustand, nicht für ausgelesene Buskennungen.

## Technisches Profil der Entwicklungsanlage

| Merkmal | Festgestellter Stand | Quelle / Einschränkung |
|---|---|---|
| Hersteller | Zimmermann Lüftungs- und Wärmesysteme | W, S |
| Zentrales Lüftungsgerät | **P 2 H-L laut Wartungsbericht** | W; abweichendes Feld in S, siehe unten |
| Weitere Gerätebezeichnung | LZG: **P 1.0 (Hermes)** | S; nicht ungeprüft mit P 2 H-L gleichsetzen |
| Software des P-Geräts | **V3.6**, beim Wartungstermin bereits vorhanden | W; kein Update des P-Geräts im Bericht dokumentiert |
| Hauptplatine | Hermes electronic, **LT-ZIM V1.6**, Aufdruck 01.2014 | F; Platinenaufdruck ist kein belegtes Baujahr der Gesamtanlage |
| Zusatzplatine | **PTC-Modul 4× V1.2** | F |
| Zentrales Bediengerät | **BDE Comfort**, Anzeige **V03.6.07A0** | F; diese Versionsanzeige dem BDE zuordnen, nicht automatisch jedem Busknoten |
| BDE-Solltemperaturbereich | **18–30 °C** laut Betreiber am 14.09.2026 | Bedienbeobachtung; 18, 26 und 30 °C im Bus bestätigt. Nicht als universelle Grenze aller Varianten behandeln |
| Kühlung | Am **03.09.2026 nachgerüstet und konfiguriert**, Funktionsprüfung laut Servicebericht i.O. | S, durch W bestätigt; kein Nachweis für eigene HA-Steuerbefehle |
| Material der Kühlnachrüstung | Spule für 4-Wegeventil, Artikel **P0015/91**, ein Stück | S |
| Raumthermostate | Laut Wartungsbericht nicht mehr die Originalgeräte; beim Termin nicht geprüft | W; Hersteller, Typ und Einbindung der Ersatzgeräte nicht dokumentiert |
| Trinkwassergerät | T300 vorhanden; genaue Variante widersprüchlich angegeben | W: **T 300 1,5**; S: **T 300 2.x** |
| Software T300 | Update auf **V3.8** beim Wartungstermin dokumentiert; Display zeigt **0038** | W und Foto IMG_1646; Anzeige passt zur Berichtsangabe, nicht zur Firmware der HESP-Hauptplatine oder des BDE gehörig |
| HA-Anbindung | Passiver Empfang über Waveshare RS485/TCP-Gateway | M; bestehende BDE-/PTC-Kommunikation bleibt bestehen |

### Noch offene Identifikationsfragen

Die beiden Berichte nennen unterschiedliche Geräte-/Variantenbezeichnungen:
P 2 H-L gegenüber P 1.0 (Hermes), T 300 1,5 gegenüber T 300 2.x. Ob dies
Formularkategorien, unterschiedliche Generationsangaben oder ein Eintragungsfehler
sind, geht aus den Berichten nicht hervor. Deshalb lautet die Arbeitsbezeichnung
**„PROXON P 2 H-L laut Wartungsbericht, Hermes LT-ZIM V1.6“**. Ein Typenschild
oder eine Herstellerbestätigung könnte die Abweichungen auflösen. Die
Seriennummernfelder im Servicebericht sind leer; eine Seriennummer wird nicht
angenommen oder aus Platinenaufklebern abgeleitet.

### Ergänzende T300-Fotos vom Betreiber, 14.09.2026

**Priorität:** T300-Anbindung auf Wunsch des Betreibers vorerst zurückgestellt.
Die folgenden Angaben dienen als spätere Referenz; Hauptarbeit bleibt die
HESP-Integration des Lüftungs-/Heizgeräts. Quellen: IMG_1645 bis IMG_1651;
Originalfotos bleiben außerhalb des Repositorys.

| Foto | Direkt ablesbare Anzeige / Beobachtung |
|---|---|
| IMG_1645 | Hauptanzeige 46 °C, Geräteuhr 11:53; daraus allein keine Unterscheidung von Ist- und Sollwert ableiten |
| IMG_1646 | Systeminfo: S2 Komp. 027474; S3 Extra 000000; S4 E-Heiz 000082; S5 Vent. 027470; S6 Abtau 000238; Software 0038 |
| IMG_1647 | Systeminfo: „Wärme“ 194 kWh; „E.Arb.“ 48 kWh |
| IMG_1648 | Temperaturanzeige: T5 V.Verda 21,4; T6 Verdamp 19,7; T20 Untbeh 44,7; T21 Mitbeh 46,9; T13 Komp. 97,7; T11 Sauggas 25,3 |
| IMG_1649–IMG_1651 | Platinen- und Anschlussansichten; unter anderem Aufdrucke X13, X16 und X17 sichtbar |

Die S2–S6-Werte werden ohne zusätzliche Einheiten dokumentiert, da diese auf
dem Foto fehlen. Für die beiden Energieanzeigen sind Mess-/Berechnungsverfahren,
Bezugszeitraum und Rücksetzverhalten unbekannt; daraus wird kein COP oder
Jahresverbrauch abgeleitet. Eine Übertragung dieser Anzeigen über den vorhandenen
HESP-Anschluss wurde nicht nachgewiesen.

Die Fotos enthalten kein eindeutig lesbares Typenschild bzw. keine eindeutige
Platinenrevision und lösen die Variantenabweichung in den Berichten noch nicht
auf. Der Aufdruck X17 allein bestätigt weder die elektrische Pinbelegung noch
die Übertragbarkeit einer Anschlussanleitung aus einem anderen T300-Projekt.
Modbus-Adresse, Parität und Schreibfreigabe sind auf diesen Menüfotos nicht sichtbar.

## Was diese Ausstattung für die Integration bedeutet

- **Kühlung ist eine konkrete Nachrüstung.** Die hier ausgewerteten Mitschnitte
  entstanden nach dem Umbau. Daraus folgt keine Kühlfähigkeit aller P 2H-L und
  keine Freigabe einer Kühlsteuerung ohne validierte Schreibkommunikation.
- **T300 getrennt behandeln.** Ihre Wartung und Firmware V3.8 gehören nicht zur
  Validierung der aktuellen HESP-Integration. U beschreibt einen eigenständigen
  T300-Regler außerhalb des HESP-Busses; lokal ist keine T300-Telemetrie über
  diesen Anschluss nachgewiesen. Keine Warmwasserentitäten daraus ableiten.
- **BDE und Raumthermostate unterscheiden.** BDE Comfort ist per Foto belegt;
  die nicht originalen Raumthermostate sind eine zusätzliche lokale Besonderheit.
  Raumzonen und PTC-Heizelemente dürfen nicht pauschal als identische Regler gelten.
- **Anschlussbezeichnungen sind platinenbezogen.** Lokal wurde BDE an PTC-X1 und
  die Verbindung von PTC-X2 zur Hauptplatine X5 dokumentiert. U verwendet X2/X7.
  Das ist keine universelle Pinbelegung und keine Anschlussanleitung für andere
  Revisionen. Nummern oder Aderfarben allein identifizieren keinen Anschluss.

## Vergleich mit Markus Mauchs Anlage

| Aspekt | Lokale Referenzanlage | Markus Mauchs Dokumentation | Aussage |
|---|---|---|---|
| Modellname | P 2 H-L laut W, abweichendes Feld in S | P 2H-L | Modellbezeichnungen stimmen bis auf Schreibweise überein; W/S-Abweichung bleibt offen |
| Architektur | Hauptplatine, PTC-Modul 4×, BDE Comfort | Hauptplatine, PTC-Modul 4×, BDE Comfort | Gleiche beschriebene Grundarchitektur |
| Exakte Platinenrevision / Firmware | LT-ZIM V1.6, PTC V1.2; BDE-Version wie oben | In den verglichenen Übersichtsseiten keine entsprechenden Revisions-/Versionsangaben | Identische Revision und Firmware nicht belegt |
| Kühlung | Nachrüstung mit Vierwegeventilspule dokumentiert | Kühlung als optionale Funktion beschrieben | Gleiche Option möglich, identischer Ausbau nicht belegt |
| Buszugang | Lokal abweichende Steckverbinderbezeichnungen; Waveshare-TCP | X7, USB-RS485-Adapter | Gleiche Busfamilie, kein Beleg für identischen Anschluss oder Adapter |
| Dateninterpretation | An lokalen Mitschnitten und BDE-Anzeigen geprüft | Grundlage für Protokoll und Datenpunktreferenz | Gemeinsamkeiten durch lokale Tests bestätigen, keine pauschale Gleichsetzung |
| Erdwärmetauscher | In W/S nicht dokumentiert | Laut U nicht vorhanden | Lokale Ausstattung bleibt offen; fehlende Erwähnung beweist keine Abwesenheit |

**Fazit für Kompatibilität:** Es spricht viel für denselben Modelltyp und
verwandte Steuerungstechnik. „Identische Anlage“ wäre stärker als die vorliegenden
Belege. Die Integration benennt deshalb ihr geprüftes Profil nach der lokal
beobachteten Hardware, statt beliebige P-Anlagen als vollständig kompatibel
anzunehmen. Das generische HA-Gerätemodell bleibt unverändert, damit diese
lokalen Berichtsdaten nicht allen Installationen als automatisch erkannte
Eigenschaften zugewiesen werden.

## Umfang der bisherigen lokalen Prüfung

Integration 0.4.0: vier BDE-Werte, Filterrestlaufzeit, acht Betriebsstundenzähler,
Geräteuhrzeit und zwölf neue Messwertsensoren. Die zehn positiven Temperaturkanäle
und zwei Ist-Drehzahlen wurden mit BDE-Aufnahmen abgeglichen. Zuletzt lieferte
jeder neue Messwert im zweiminütigen Mitschnitt 24 Aktualisierungen, ungefähr
alle 4,9 Sekunden, ohne Prüfsummenfehler. Das ist ein lokaler Funktionsnachweis,
kein Langzeittest aller Programme, Fehlerzustände oder Hardwarevarianten.

Negative Temperaturkodierungen, eigene Steuerung, Zeitprogramme und die
vollständige Semantik der Schaltzustände bleiben separat zu validieren.
Siehe [Datenpunktabdeckung](DATENPUNKTE.md) und
[Prüfsummenalgorithmus](CHECKSUM_ALGORITHM.md).

Bei Vergleichen mit einer weiteren Anlage sollten Modell vom Typenschild,
Platinenrevisionen, BDE-Version, Kühl-/PTC-/EWT-Ausstattung und die konkret
geprüften Datenpunkte genannt werden. Firmwareangaben des P-Geräts, des BDE und
der T300 dabei getrennt halten. Private Kennungen sind dafür nicht erforderlich.
