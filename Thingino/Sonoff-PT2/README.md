# thingino-ha

Home Assistant MQTT auto-discovery for Thingino cameras (prudynt-t firmware).
One script run per camera, then the camera appears in Home Assistant as a device
with all controls (image, day/night, lights, PTZ, audio, motion, streams).

Based on [AsDinFlames/thingino-mqtt-ha-discovery](https://github.com/AsDinFlames/thingino-mqtt-ha-discovery).

## Files

| File | Purpose |
|------|---------|
| `install.ps1` | Windows installer. Uploads and configures everything over SSH. |
| `thingino-ha-discovery.sh` | Runs on the camera: installs `/usr/sbin/thingino-cmd` and publishes the MQTT discovery payloads. Re-runs at every boot. |

## Requirements

- Thingino firmware with the **prudynt** streamer (`prudyntctl` present). Tested with `stable+0598a56` (2026-03).
- MQTT broker (e.g. Mosquitto add-on) and the MQTT integration in Home Assistant.
- Windows with the built-in OpenSSH client. `ssh-copy-id` (e.g. from Git for Windows) is optional.

## Flashing Thingino on a Sonoff CAM PAN/TILT 2

From [wltechblog/thingino-installers](https://github.com/wltechblog/thingino-installers)
(installer for this model: [sonoff-pt2](https://github.com/wltechblog/thingino-installers/tree/main/sonoff-pt2),
video: https://www.youtube.com/watch?v=82s4WcsuUYc):

1. Write the SD card image from the installer repo to an SD card and insert it into the camera.
2. Power the camera with a "dumb" USB-C cable (power only, no data/handshake).
3. After a few minutes the camera flashes itself. A WiFi network `THING-xxx` appears:
   connect to it and configure WiFi in the captive portal
   ([Wi-Fi guide](https://github.com/themactep/thingino-firmware/wiki/Configuration:-Wi%E2%80%90Fi-Access#captive-portal)).
4. The SD card then contains `autoupdate-full.done` (flash finished) and a `backup` folder
   with the **factory firmware of this specific camera**. Save that folder per camera, it
   contains device-specific keys and is the only way back to stock.
5. Revert to stock: put the backup `.bin` on an empty SD card as `autoupdate-full.bin` and boot.
6. The installer images are refreshed weekly; do a full firmware upgrade via the WebUI right after installing.
7. Unbricking a dead PT2 requires a CH341A flash programmer (Sonoff disabled the easier ways); see the Thingino wiki.

Note on privacy mode: the factory firmware parks the lens, Thingino's privacy mode blacks
out the image instead. Combine it with a PTZ preset (camera turned away, mic off) if needed.

### Live stream in Home Assistant (optional)

In the Thingino WebUI set a password under *Settings -> RTSP/ONVIF Access*, then add the
camera in Home Assistant with the ONVIF integration. This is independent of the MQTT setup.

## Setting up a new camera

1. Flash Thingino (see above), connect the camera to the network, set the root password in the WebUI.
2. Put `install.ps1` and `thingino-ha-discovery.sh` in one folder and run in PowerShell:

   ```powershell
   .\install.ps1
   ```

   It asks for the camera IP and the broker settings (defaults are at the top of the
   script). Non-interactive: `.\install.ps1 -CameraIp 192.168.0.71 -NonInteractive`.

3. The installer
   - copies your SSH key to the camera (if `ssh-copy-id` is available), so later steps need no password,
   - uploads the discovery script,
   - configures the MQTT subscriber (`<hostname>/cmd`, action `eval $MQTT_PAYLOAD`),
   - configures motion events -> MQTT (`<hostname>/motion`) and enables motion detection,
   - disables the logo OSD, restarts prudynt and the MQTT subscriber,
   - installs `/etc/init.d/S99ha-discovery` (re-publishes discovery at boot, waits for the broker),
   - runs the discovery and checks that the retained config arrived at the broker.

4. In Home Assistant: Settings -> Devices & services -> MQTT -> the camera appears
   with the hostname as device name. Entity ids are `<hostname>_<control>`.

## Manual setup (what install.ps1 does, step by step)

Replace `CAM` with the camera IP and `BROKER`, `USER`, `PASS` with your MQTT settings.
Steps 1 and 2 run on the PC, everything else in an SSH session on the camera
(`ssh root@CAM`). The order matters.

1. **SSH key (optional, saves password prompts):**
   `ssh-copy-id root@CAM` or paste your public key in the WebUI under *Configuration -> SSH*.

2. **Upload the discovery script** (PowerShell; `tr` strips the CR that PowerShell appends):

   ```powershell
   Get-Content .\thingino-ha-discovery.sh -Raw | ssh root@CAM "tr -d '\r' > /usr/sbin/thingino-ha-discovery.sh && chmod +x /usr/sbin/thingino-ha-discovery.sh"
   ```

3. **MQTT subscriber** (commands from HA). Either in the WebUI *Tools -> MQTT subscriptions*:
   broker, port, user, password, one subscription with topic `%hostname/cmd` and
   action `eval $MQTT_PAYLOAD` — or on the camera:

   ```sh
   TOKEN=$(cat /etc/thingino-api.key)
   curl -sf -X POST "http://localhost/x/json-config-mqtt-sub.cgi?token=$TOKEN" -H "Content-Type: application/json" \
     -d '{"enabled":true,"host":"BROKER","port":1883,"username":"USER","password":"PASS","use_ssl":false,"subscriptions":[{"topic":"%hostname/cmd","qos":0,"action":"eval $MQTT_PAYLOAD","enabled":true}]}'
   ```

4. **Logo OSD off** (optional). Do this *before* step 6, because `save_config` overwrites
   `/etc/prudynt.json` with prudynt's in-memory config:

   ```sh
   printf '{"stream0":{"osd":{"logo":{"enabled":false}}},"stream1":{"osd":{"logo":{"enabled":false}}},"action":{"save_config":null}}' | prudyntctl json -
   ```

5. **Motion events -> MQTT.** WebUI *Tools -> Send to services -> MQTT*: broker, port, user,
   password, client id = hostname, topic `<hostname>/motion`, message `{"timestamp": "%s"}`,
   enabled — or on the camera:

   ```sh
   H=$(hostname)
   curl -sf -X POST "http://localhost/x/json-config-send2.cgi?token=$TOKEN" -H "Content-Type: application/json" \
     -d '{"config":{"mqtt":{"enabled":true,"host":"BROKER","port":1883,"username":"USER","password":"PASS","use_ssl":false,"client_id":"'"$H"'","topic":"'"$H"'/motion","message":"{\"timestamp\": \"%s\"}","send_photo":false,"topic_photo":""}}}'
   ```

6. **Enable motion detection** in the config file and restart prudynt. Do **not** enable it
   live on a fresh camera: with a 0x0 detection frame prudynt crashes. The frame must
   match the main stream size (1920x1080 on the Sonoff PT2):

   ```sh
   for kv in "enabled true" "send2mqtt true" "frame_width 1920" "frame_height 1080" "roi_count 1" "roi_0_x 0" "roi_0_y 0" "roi_1_x 1919" "roi_1_y 1079"; do
     jct /etc/prudynt.json set "motion.${kv% *}" "${kv#* }"
   done
   /etc/init.d/S31prudynt restart
   ```

7. **Restart the MQTT subscriber** so it picks up the new settings. `stop` alone leaves the
   old `mosquitto_sub` alive, which would execute every command twice:

   ```sh
   /etc/init.d/S91mqttsub stop; killall mqtt-sub-dispatcher mosquitto_sub 2>/dev/null; sleep 1
   /etc/init.d/S91mqttsub start
   pidof mosquitto_sub   # must print exactly one PID
   ```

8. **Autostart at boot:**

   ```sh
   cat > /etc/init.d/S99ha-discovery <<'EOF'
   #!/bin/sh
   case "$1" in
       start) /usr/sbin/thingino-ha-discovery.sh > /tmp/ha-discovery.log 2>&1 & ;;
   esac
   EOF
   chmod +x /etc/init.d/S99ha-discovery
   ```

9. **Run the discovery once now:** `/usr/sbin/thingino-ha-discovery.sh`
   It installs `/usr/sbin/thingino-cmd`, publishes all entities, removes stale ones
   and starts the state-sync loop.

10. **Verify at the broker** (from the camera or any machine with mosquitto clients):

    ```sh
    mosquitto_sub -h BROKER -u USER -P PASS -t "homeassistant/switch/$(hostname)_privacy/config" -C 1 -W 5
    ```

    A JSON payload means Home Assistant will show the device.

## How commands work

Home Assistant publishes a shell command line to `<hostname>/cmd`, e.g.
`/usr/sbin/thingino-cmd brightness 130`. The camera's `mqtt-sub-dispatcher`
executes it as root. The wrapper applies the change live (prudynt JSON API),
persists it, and publishes the new value retained to `<hostname>/state/<control>`
so Home Assistant shows the correct state after restarts.

Changes made outside Home Assistant (WebUI, camera button, day/night automatic)
are picked up by a state-sync loop that the discovery script starts in the
background: every 20 s it reads the live values from prudynt and the GPIOs and
publishes only what changed. Not covered (no readable state): privacy, status LED, sound.

At every run the discovery script also deletes retained discovery entries of this
camera at the broker that it did not publish itself (leftovers of older script
versions or of the firmware's own `thingino-ha` package), so no ghost entities remain.

**Security note:** anyone who can publish to the broker can run commands as root
on the camera. Keep the broker on the LAN with a password.

## Entities

- Switches: privacy, IR cut, IR/white light (only if the camera has that GPIO), status LED,
  color mode, flips, mic settings, motion detection, stream audio/video, recording (only with an SD card mount)
- Selects: day/night mode (day/night/auto), anti-flicker, white balance, mic codec, sample rates, stream mode, sound
- Numbers: image tuning, ISP tuning (WDR, tone, noise reduction), audio levels, motion sensitivity/cooldown, stream bitrate/fps/gop
- Buttons: reboot, PTZ steps, presets, stop sound
- Binary sensor: Motion (from `<hostname>/motion`, auto-off after 30 s)
- Switch "Motion Alarm": a flag stored in the broker for your own automations (no camera function)

The command topic must end in `/cmd`; the part before it becomes the entity prefix
(default: the hostname, e.g. `ing-sonoff-pt2-26a4/cmd`).

### Example: play a sound on motion (Motion Alarm switch + Play Sound select)

```yaml
alias: Camera motion alarm sound
triggers:
  - trigger: state
    entity_id: binary_sensor.ing_sonoff_pt2_26a4_motion
    to: "on"
conditions:
  - condition: state
    entity_id: switch.ing_sonoff_pt2_26a4_motion_alarm
    state: "on"
actions:
  - action: select.select_option
    target:
      entity_id: select.ing_sonoff_pt2_26a4_play_sound
    data:
      option: motiondetectionactivated.opus
mode: single
max_exceeded: silent
```

Replace `ing_sonoff_pt2_26a4` with your camera's hostname (dashes become underscores).
Note that a select only fires when the option changes, so the same sound cannot be
played twice in a row without selecting another one in between.

## Troubleshooting

- Boot log of the discovery on the camera: `/tmp/ha-discovery.log`
- Re-run manually: `ssh root@<cam> /usr/sbin/thingino-ha-discovery.sh`
- Test a command without HA: `ssh root@<cam> /usr/sbin/thingino-cmd brightness 128`
- Check the subscriber: `ssh root@<cam> "ps | grep mosquitto_sub"` (exactly one process)
- Check the state-sync loop: `ssh root@<cam> "kill -0 \$(cat /run/ha-state.pid) && echo running"`

## Known limitations

- No availability: entities stay "available" while the camera is off.
- Playing a sound gives no feedback when it has finished (prudynt queues the file and returns immediately).
- Privacy, status LED and sound have no readable state on the camera; they only reflect what was set via Home Assistant.

Reported by the original author for prudynt (not re-verified here):

- Toggling the Mic switch more than twice can crash prudynt; recover with the Reboot button.
- Force Stereo causes a short audio glitch (audio thread restart); best left off.
- `motion.playonspeaker` is not implemented in the firmware.
- `dpc_strength` and ISP day/night mode are not supported by prudynt on this hardware.

## Field notes (Sonoff PT2)

- Reset camera WiFi: press and hold the reset button, plug in power, wait 5 seconds, release, then wait; the camera does nothing for about a minute.
- In access-point/captive-portal mode the camera is at 172.16.0.1.
- After the WiFi setup wait for the reboot (the camera moves its lens).
- A reset deletes all settings.
