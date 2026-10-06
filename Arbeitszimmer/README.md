# Arbeitszimmer

## `automationen/bilresa_schreibtische.yaml` – Bilresa Fernbedienungen (Matter), 3 Lampen, 2 Klicker

Zwei BILRESA-Zweitastenfernbedienungen steuern die drei KAJPLATS-Schreibtischlampen
(`light.kajplats_gu10_ws_575lm`, `_2`, `_3`). Kurz drücken schaltet, wiederholtes Drücken innerhalb von 2 s wechselt die
Farbtemperatur (2700/4000/6500 K), Halten dimmt die zuletzt aktive Lampe: Taste 1 heller, Taste 2 dunkler.

Dimmen: 20 % alle 0,6 s mit 0,6 s Übergang (voller Bereich in etwa 3 s, 5 Stufen). Früher: 5 % alle 0,3 s (6 s), dann kurz 10 % alle 0,3 s.
Kürzere Abstände als 0,3 s nicht empfohlen: die Matter-Lampen stauen sonst Befehle und dimmen nach dem Loslassen weiter.
`mode: restart` beendet die Dimm-Schleife beim Loslassen (long_release startet die Automation neu).
