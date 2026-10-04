# Haustür / Ring Vordereingang

## `automationen/haustuer_wieder_oeffnen_nach_klingeln.yaml`

Wird innerhalb von 1 Minute nach dem Schließen der Wohnungstür am Vordereingang geklingelt, öffnet HA den
Vordereingang über Ring und schickt eine Benachrichtigung ans Handy.

| Rolle | Entity |
|---|---|
| Türkontakt Wohnungstür (Flur) | `binary_sensor.fl_par_wohnungstuer_contact` (`off` = zu) |
| Klingel | `event.vordereingang_klingeln_2` (event_type `ring`) |
| Türöffner | `button.vordereingang_tur_offnen_2` |
| Benachrichtigung | `notify.mobile_app_sm_g781b` |

Logik: Auslöser ist jedes neue Klingel-Ereignis. Bedingungen: Wohnungstür ist zu und wurde vor höchstens 60 Sekunden
geschlossen (`last_changed`). Wer in dieser Minute klingelt, kommt rein, egal wer es ist.

Hinweis: Die ältere Automation „Tür öffnen“ (öffnet bei jedem Klingeln) ist deaktiviert, weil ihr Gerät nicht mehr existiert.
