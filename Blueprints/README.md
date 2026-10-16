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

## BILBUT_AZ_Tuer (Arbeitszimmer-Tür), `automationen/bilbut_az_tuer.yaml`

| Taste | einfach | doppelt | lang |
|---|---|---|---|
| oben (1) | Deckenspots an (vorherige Szene `scene.arbeitszimmer_vorher`, sonst alle drei an) | – | PC-Steckdose an (`switch.az_ins_schreibtisch_ba_2`) |
| unten (2) | Deckenspots aus (merkt den Zustand als Szene) | – | PC-Steckdose aus (`switch.az_ins_schreibtisch_ba_2`) |

## BILBUT_SZ_Tuer (Schlafzimmer-Tür), `automationen/bilbut_sz_tuer.yaml`

Eigene Automation (kein Blueprint), damit Loslassen das Dimmen beendet: `mode: restart`, die Dimm-Schleife läuft,
solange `event_type` der Taste `long_press` ist; `long_release` startet die Automation neu und beendet sie.

| Taste | einfach | doppelt | lang (halten) |
|---|---|---|---|
| oben (1) | Bettlicht an (immer 1 %, 1 s Übergang) / aus (`light.sz_tra_bett`) | Rauschen lauter (+20, max. 100) | heller, 10 % alle 0,4 s bis 100 % |
| unten (2) | Rauschen an/aus (`switch.ing_sonoff_pt2_a574_noise`) | Rauschen leiser (−20, min. 20) | dunkler, 10 % alle 0,4 s bis 1 % (bleibt an) |

Lautstärke: `number.ing_sonoff_pt2_a574_noise_volume`; wirkt sofort, wenn das Rauschen läuft, sonst beim nächsten Start.

## meine_heizung/externer_temperaturfuehler.yaml

Raumthermometer → SONOFF TRVZB (externer Fühler) mit Fallback auf den eingebauten Fühler. Details in [../Heizung/README.md](../Heizung/README.md).
