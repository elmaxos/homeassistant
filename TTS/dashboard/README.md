# Dashboard „Ansage“

Dashboard in der Seitenleiste (`/dashboard-ansage`): Text eingeben, Ziele wählen (Wohnzimmer 3684,
SONOFF PT2 4 / 4420, Handy), Stimme und Sound wählen, Optionen setzen, „Ansage abspielen“ drücken.
Der Knopf ruft `script.ansage_senden`, das die Eingaben an `script.tts_cam_sound_text` weitergibt.

## Bestandteile

| Datei | Inhalt |
|---|---|
| `dashboard_ansage.json` | Dashboard-Konfiguration (Abschnitte-Ansicht, nur Standard-Karten) |
| `ansage_senden.yaml` | Skript für `scripts.yaml` (Label -> Stimmen-ID / Sound-Key, Ziele aus den Schaltern) |
| `ansage_stoppen.yaml` | Stopp-Knopf: bricht laufende und wartende Läufe von `ansage_senden` und `tts_cam_sound_text` ab (auch von Automationen gestartete), drückt „Stop Sound“ auf beiden Kameras, schaltet deren Weißlicht aus und sendet `command_stop_tts` ans Handy |

Helfer (in HA unter *Einstellungen -> Geräte & Dienste -> Helfer* angelegt):

| Entity | Typ | Werte |
|---|---|---|
| `input_text.ansage_text` | Text | max. 255 Zeichen (HA-Grenze) |
| `input_select.ansage_stimme` | Auswahl | Thorsten LOW/MEDIUM/HIGH, Thorsten emotional MEDIUM, Eva LOW, Karlsson LOW, Kerstin LOW, Ramona LOW, Pavoque LOW, mls MEDIUM, US Lessac MEDIUM |
| `input_select.ansage_sound` | Auswahl | Gong (Cam), Kein Sound, Klingel, Alarm, Hinweis, Music Trap, 21st Century Fox, 12 Uhr |
| `input_boolean.ansage_wohnzimmer` / `_kamera4420` / `_handy` | Schalter | Ziele |
| `input_boolean.ansage_zweimal` / `_licht` / `_warten` | Schalter | Optionen |

## Neu aufbauen

1. Helfer mit genau diesen Namen anlegen („Ansage Text“, „Ansage Stimme“ usw.), die Entity-IDs ergeben sich daraus.
   Die Optionstexte der Auswahlen müssen exakt den Schlüsseln in `ansage_senden.yaml` entsprechen.
2. `ansage_senden.yaml` an `scripts.yaml` anhängen, Skripte neu laden.
3. Neues Dashboard „Ansage“ anlegen, *Bearbeiten -> drei Punkte -> Rohkonfiguration*, Inhalt von
   `dashboard_ansage.json` einfügen (JSON wird als YAML akzeptiert).

Neue Stimme oder neuer Sound: Option im Helfer ergänzen und die Zuordnung in `ansage_senden.yaml` nachziehen.
