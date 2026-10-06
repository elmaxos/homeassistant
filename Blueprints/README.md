# Blueprints

## `meine_ikea/bilrease_dual_button.yaml` – IKEA Bilbut Zwei-Tasten-Schalter

Ablage in HA: `/config/blueprints/automation/meine_ikea/bilrease_dual_button.yaml`.
Pro Taste je eine Aktion für einfach, doppelt, lang gedrückt und losgelassen.

Benutzt von: `BILBUT_WZ_Tuer` (Wohnzimmer-Tür: Licht, Beamer/Monitor, Zeitansage, Tesla-Statusansage),
`BILBUT_AZ_Tuer` (Arbeitszimmer-Tür), `BILBUT_Tesla_Fernsteuerung_Automation`.

`mode: parallel` (max. 10): Ein Tastendruck blockiert die Fernbedienung nicht, während eine längere Aktion läuft
(z. B. Tesla-Statusansage oder das Einschalten von Monitor + Jellyfin mit 1 min Wartezeit). Bis 06.10.2026 stand hier
`mode: single`, dann wurden weitere Tastendrücke ignoriert, solange eine Aktion lief.

## BILBUT_WZ_Tuer (Wohnzimmer-Tür), `automationen/bilbut_wz_tuer.yaml`

| Taste | einfach | doppelt | lang |
|---|---|---|---|
| oben (1) | kleine Lampe (`switch.ins_kleine_lampe`) | Schwibbogen (`switch.wz_ins_schwibbogen`) | Beamer: Steckdose `switch.az_ins_monitor` aus → an, nach 65 s Jellyfin auf `media_player.fire_tv_4k`; an → Fire TV aus, nach 10 s Steckdose aus |
| unten (2) | Zeitansage (`script.tts_zeitansage`) | Tesla-Status (`script.tts_tesla_statusansage`) | Wetterbericht (`script.tts_wetterbericht`) |
