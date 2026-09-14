# Entwurf: Aktive HESP-Leseabfragen parallel zum laufenden BDE

Veröffentlicht am 14.09.2026:
https://github.com/markusmauch/proxon-hesp/issues/1#issuecomment-5659731209

Hallo Markus,

wir entwickeln eine passive Home-Assistant-Integration auf Grundlage deiner
Dokumentation. Das BDE und das PTC-Modul bleiben in Betrieb. Ueber einen
Waveshare-TCP/RS485-Adapter lesen wir den bestehenden Verkehr mit.

Bevor wir gezielt Temperatur-Einzelwerte und Metadaten abfragen, fehlen uns
noch diese konkreten Details:

1. Wie koordinierst du eigene QUERY-Telegramme mit den zyklischen Anfragen
   des PTC-Masters? Gibt es einen vorgesehenen Zugriff fuer weitere Master,
   oder ersetzt deine Loesung einen vorhandenen Teilnehmer? In deinem
   FHEM-Beitrag schreibst du, dass du das BDE nicht mehr verwendest; laeuft
   das PTC-Modul dabei weiterhin als Master?
2. Kannst du ein vollstaendiges Anfrage-/Antwortpaar fuer einen
   Temperatur-Einzelwert, beispielsweise 0x0194, bereitstellen?
3. Wie lauten die Anfragen fuer 0x0033/0034/0038/0039, einschliesslich
   Selektor, Anzahl, eventueller Pagination und Antwortlaenge?
4. Was bedeutet das 16-Bit-Argument einer QUERY genau? Bei uns:
   0x00ED Argument 1 -> 4 Antwortbytes;
   0x00C9 Argument 2 -> 8 Antwortbytes;
   0x03B7 Argument 11 -> 22 Antwortbytes;
   0x0330 Argument 0 -> 4 Antwortbytes.
   Es scheint typisierte Elemente statt einer festen Wortanzahl zu meinen.
5. Gibt es ein vollstaendigeres Pruefsummenmodell fuer die 8-Byte-
   Drehzahlpayloads oder den 22-Byte-Temperaturblock? Die veroeffentlichte
   Tabelle ist auf kurze Nachrichten begrenzt.

Vielen Dank! Mit diesen Angaben koennten wir Einzelabfragen umsetzen,
ohne aus TCP-Empfangspausen faelschlich eine freie RS485-Leitung abzuleiten.

## Quellen und Einordnung

- https://forum.fhem.de/index.php?topic=96437.0
  Beitrag von prxnhntr vom 13.07.2026: BDE nicht mehr verwendet.
  Das beweist weder die Abwesenheit noch die Anwesenheit eines PTC-Masters.
- https://markusmauch.github.io/proxon-hesp/protokoll/
  Beschreibt PTC-Master und Halbduplex, aber kein Mehrmaster-Verfahren.
- https://markusmauch.github.io/proxon-hesp/dp-referenz/
  Beschreibt aktive Zugriffe, aber keine vollstaendige Arbitration.

Ein fehlender Nachweis bedeutet nicht, dass Parallelbetrieb unmoeglich ist.
Die bisherige Recherche reicht nur nicht fuer eine verlaessliche Freigabe.
