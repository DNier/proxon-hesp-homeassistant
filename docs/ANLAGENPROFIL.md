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
| Kühlung | Am **03.09.2026 nachgerüstet und konfiguriert**, Funktionsprüfung laut Servicebericht i.O. | S, durch W bestätigt; kein Nachweis für eigene HA-Steuerbefehle |
| Material der Kühlnachrüstung | Spule für 4-Wegeventil, Artikel **P0015/91**, ein Stück | S |
| Raumthermostate | Laut Wartungsbericht nicht mehr die Originalgeräte; beim Termin nicht geprüft | W; Hersteller, Typ und Einbindung der Ersatzgeräte nicht dokumentiert |
| Trinkwassergerät | T300 vorhanden; genaue Variante widersprüchlich angegeben | W: **T 300 1,5**; S: **T 300 2.x** |
| Software T300 | Update auf **V3.8** beim Wartungstermin dokumentiert | W; nicht die Firmware der HESP-Hauptplatine oder des BDE |
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
