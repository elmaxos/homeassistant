# Handy (Android Companion App)

## `automationen/handy_max_gps_modus_nach_zone.yaml`

Schaltet den High-Accuracy-GPS-Modus der HA-App auf dem Handy `sm_g781b` per Benachrichtigungsbefehl:
zu Hause aus (Akku), unterwegs an. Prüft den Soll-Zustand bei jedem Zonenwechsel, bei jeder
Modusänderung (2 min verzögert), alle 10 Minuten und nach HA-Start, damit ein verpasster Übergang
nicht hängen bleibt.

Voraussetzungen: App auf dem Handy mit aktivierten Sensoren *High accuracy mode* und
*High accuracy update interval* (Einstellungen -> Companion App -> Sensoren -> Background Location).
Entities: `device_tracker.sm_g781b`, `binary_sensor.sm_g781b_high_accuracy_mode`, Dienst `notify.mobile_app_sm_g781b`.

Befehle der App (nur Android):
- `message: command_high_accuracy_mode`, `data.command: turn_on | turn_off | force_on | force_off`
- Intervall: `data.command: high_accuracy_set_update_interval`, `data.high_accuracy_update_interval: <s>` (min. 5)

Falls in der App eine Zonen- oder Bluetooth-Bedingung für den Modus gesetzt ist, `force_on`/`force_off` statt `turn_*` verwenden.

Einspielen: Block an `automations.yaml` anhängen, dann *YAML -> Automationen neu laden*.
