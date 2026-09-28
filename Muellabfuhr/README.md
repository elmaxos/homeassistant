# Müllabfuhr-Ansage (Neu-Ulm, Bezirk 7)

## Aufbau

- Kalender: Integration **Remote Calendar**, Entity `calendar.mullabfuhr`, Quelle ist die ICS-Datei des
  Abfallkalenders der Stadt Neu-Ulm (Bezirk 7).
- Automation `automationen/muellabfuhr_ansage.yaml`: fragt um 18:00 und 20:00 (Vorabend) sowie 08:00, 09:00
  und 09:30 (Abholtag) die Termine ab und lässt die Tonnen über `script.tts_ansage_an_alle_gerate` ansagen
  (Handy + Kamera). Ohne Termin am jeweiligen Tag passiert nichts.

## Wichtig: der Download-Link der Stadt läuft ab

Die Links auf https://nu.neu-ulm.de/index.php?id=1082 (Abfallkalender) sind signierte Download-Links
(`/securedl/sdl-<JWT>/...`), gültig nur etwa 13 Stunden. Trägt man so einen Link direkt in Remote Calendar
ein, ist der Kalender nach einem halben Tag „nicht verfügbar“ und die Ansage bleibt stumm, ohne Fehler im Log.
Genau das war vom 03.09. bis 29.09.2026 der Fall.

Lösung: die ICS-Datei einmal herunterladen und lokal in HA hosten.

## Einrichten / reproduzieren

1. Auf https://nu.neu-ulm.de/index.php?id=1082 den Link „Bezirk 7“ (ICS) herunterladen
   (Datei liegt auch hier unter `kalender/`).
2. Datei nach `/config/www/muell/Abfallkalender_NU_<Jahr>_Bezirk-7.ics` kopieren.
   Sie ist dann unter `http://192.168.0.48:8123/local/muell/Abfallkalender_NU_<Jahr>_Bezirk-7.ics` erreichbar
   (`www` wird ohne Anmeldung ausgeliefert, das ist für den Kalender unkritisch).
3. Integration *Remote Calendar* hinzufügen: Name `Müllabfuhr`, URL = die lokale Adresse aus Schritt 2.
   Entity muss `calendar.mullabfuhr` heißen (steht so in der Automation).
4. Automation aus `automationen/` an `automations.yaml` anhängen, *YAML -> Automationen neu laden*.
5. Test: *Entwicklerwerkzeuge -> Aktionen -> calendar.get_events* mit `calendar.mullabfuhr` und 14 Tagen Zeitraum.

## Jährlich

Die Datei gilt nur für ein Kalenderjahr (letzter Termin 31.12.). Im Dezember die neue Datei herunterladen,
nach `/config/www/muell/` legen und die URL im Remote-Calendar-Eintrag anpassen (*Neu konfigurieren*),
oder die neue Datei unter dem alten Dateinamen ablegen.
