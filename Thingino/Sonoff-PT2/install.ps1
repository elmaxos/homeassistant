<#
.SYNOPSIS
  Sets up a freshly flashed Thingino camera for Home Assistant (MQTT auto-discovery).

.DESCRIPTION
  Run from Windows PowerShell:   .\install.ps1
  or non-interactively:          .\install.ps1 -CameraIp 192.168.0.71
  update an already set up camera to the scripts in this folder (no MQTT password needed,
  the broker settings are taken from the camera):
                                 .\install.ps1 -CameraIp 192.168.0.71 -Update -NonInteractive

  Steps performed:
    1. Copies your SSH public key to the camera (ssh-copy-id, optional)
    2. Uploads thingino-ha-discovery.sh to the camera
    3. Configures on the camera: MQTT subscriber (<hostname>/cmd), motion -> MQTT,
       autostart of the discovery at boot, and runs the discovery once
    4. Verifies that the discovery payloads arrived at the broker
  Also installs noise (Rauschen) and ptz-state, heartbeat 10 s, motion off by default.
  The same script is used for new cameras and for updates, so all cameras run the same state.

  After the camera setup, if the SSH alias -HaHost (default "homeassistant") works with a key, entities that HA
  created with a "_2" suffix (new unique_ids after updating from an old discovery) are renamed back
  (ha_fix_suffix.py, only if the old name is free).

  Requirements: Windows OpenSSH client (ssh.exe), thingino-ha-discovery.sh next to this file.
  The camera must run a Thingino firmware with the prudynt streamer (prudyntctl).
#>
param(
    [string]$CameraIp,
    [string]$CameraUser = "root",
    [string]$Broker     = "192.168.0.48",
    [string]$Port       = "1883",
    [string]$MqttUser   = "thingino",
    [string]$MqttPass   = "thingino",
    [switch]$SkipKeyCopy,
    [switch]$Update,
    [string]$HaHost     = "homeassistant",   # SSH-Alias des HA-Servers (SSH-Add-on) fuer die _2-Korrektur; "" = aus
    [switch]$NonInteractive
)

$ErrorActionPreference = "Continue"
$SSH = Join-Path $env:SystemRoot "System32\OpenSSH\ssh.exe"
if (-not (Test-Path $SSH)) { $SSH = "ssh" }

function Write-Step($msg) { Write-Host ""; Write-Host "==> $msg" -ForegroundColor Green }
function Fail($msg)       { Write-Host "ERROR: $msg" -ForegroundColor Red; exit 1 }

# Dateien als Base64 uebertragen: Windows PowerShell 5.1 setzt beim Pipen in ssh.exe sonst ein BOM davor
# (Shebang kaputt) und macht aus Umlauten "?". Auf der Kamera: nur Base64-Zeichen behalten, dekodieren, CR entfernen.
$OutputEncoding = New-Object System.Text.ASCIIEncoding
function Send-Text([string]$text, [string]$remoteCmd, [string]$dest = $Target) {
    $b64 = [Convert]::ToBase64String((New-Object System.Text.UTF8Encoding $false).GetBytes($text))
    $b64 | & $SSH @SshOpts $dest "tr -cd 'A-Za-z0-9+/=' | base64 -d | tr -d '\r' $remoteCmd"
}
function Read-Utf8([string]$file) { [System.IO.File]::ReadAllText($file, (New-Object System.Text.UTF8Encoding $false)) }

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Thingino -> Home Assistant camera setup"   -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$DISCOVERY_SCRIPT = Join-Path $SCRIPT_DIR "thingino-ha-discovery.sh"
if (-not (Test-Path $DISCOVERY_SCRIPT)) { Fail "thingino-ha-discovery.sh not found next to install.ps1" }

# ---------- Inputs ----------
if (-not $CameraIp) { $CameraIp = Read-Host "Camera IP" }
if (-not $CameraIp) { Fail "no camera IP given" }

if (-not $NonInteractive) {
    $in = Read-Host "Camera SSH user [$CameraUser]";   if ($in) { $CameraUser = $in }
}
if (-not $NonInteractive -and -not $Update) {
    $in = Read-Host "MQTT broker IP [$Broker]";        if ($in) { $Broker = $in }
    $in = Read-Host "MQTT port [$Port]";               if ($in) { $Port = $in }
    $in = Read-Host "MQTT username [$MqttUser]";       if ($in) { $MqttUser = $in }
    $in = Read-Host "MQTT password [$MqttPass]";       if ($in) { $MqttPass = $in }
}

foreach ($v in @($Broker, $MqttUser, $MqttPass)) {
    if ($v -match '["\\'']') { Fail "double quotes, backslashes and single quotes are not supported in broker/user/password" }
}

Write-Host ""
Write-Host "  Camera : ${CameraUser}@${CameraIp}"
if ($Update) { Write-Host "  Mode   : update (MQTT settings stay as configured on the camera)" }
else         { Write-Host "  Broker : ${Broker}:${Port} (user $MqttUser)" }
if (-not $NonInteractive) {
    $c = Read-Host "Apply? [y/N]"
    if ($c -notin @("y", "Y")) { Write-Host "Aborted."; exit 1 }
}

$Target  = "${CameraUser}@${CameraIp}"
$SshOpts = @("-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=10")

function Test-KeyLogin {
    $out = & $SSH @SshOpts -o BatchMode=yes $Target "echo KEY_OK" 2>$null
    return ($out -match "KEY_OK")
}

# ---------- Step 1: SSH key ----------
Write-Step "[1/4] SSH access"
if (Test-KeyLogin) {
    Write-Host "Key-based login works."
} elseif ($SkipKeyCopy) {
    Write-Host "No key login; you will be asked for the camera password on every step." -ForegroundColor Yellow
} else {
    $copyId = Get-Command ssh-copy-id -ErrorAction SilentlyContinue
    if ($copyId) {
        Write-Host "Copying your SSH public key to the camera (enter the camera's root password once)..."
        & ssh-copy-id -o StrictHostKeyChecking=accept-new $Target
        if (Test-KeyLogin) { Write-Host "Key-based login works now." }
        else { Write-Host "Key copy did not work; continuing with password prompts." -ForegroundColor Yellow }
    } else {
        Write-Host "ssh-copy-id not found; continuing with password prompts (or add your key in the Thingino WebUI)." -ForegroundColor Yellow
    }
}

# ---------- Step 2: upload discovery script ----------
Write-Step "[2/4] Uploading thingino-ha-discovery.sh"
Send-Text (Read-Utf8 $DISCOVERY_SCRIPT) "> /usr/sbin/thingino-ha-discovery.sh && chmod +x /usr/sbin/thingino-ha-discovery.sh && sh -n /usr/sbin/thingino-ha-discovery.sh && echo UPLOAD_OK"
if ($LASTEXITCODE -ne 0) { Fail "upload failed" }

# Zusatzskripte: Rauschen (noise/noise) und PTZ-Position/Preset (ptz-state)
foreach ($extra in @(@{ Src = (Join-Path $SCRIPT_DIR "noise\noise"); Dst = "/usr/sbin/noise" },
                     @{ Src = (Join-Path $SCRIPT_DIR "ptz-state");   Dst = "/usr/sbin/ptz-state" })) {
    if (Test-Path $extra.Src) {
        Send-Text (Read-Utf8 $extra.Src) "> $($extra.Dst) && chmod +x $($extra.Dst) && sh -n $($extra.Dst) && echo UPLOAD_OK"
        if ($LASTEXITCODE -ne 0) { Fail "upload of $($extra.Dst) failed" }
    } else {
        Write-Host "  ($($extra.Src) not found, skipped)" -ForegroundColor Yellow
    }
}

# ---------- Step 3: configure camera ----------
Write-Step "[3/4] Configuring the camera"

$SETUP = @'
#!/bin/sh
# Generated by install.ps1 - runs on the camera
TOKEN=$(cat /etc/thingino-api.key 2>/dev/null)
HOST=$(hostname)
fail() { echo "ERROR: $1" >&2; exit 1; }
api() {
	# $1 = cgi name, $2 = JSON body; prints response, fails on HTTP error
	curl -sf -X POST "http://localhost/x/$1?token=$TOKEN" -H "Content-Type: application/json" -d "$2"
}

command -v prudyntctl >/dev/null 2>&1 || fail "prudyntctl not found - this firmware does not use the prudynt streamer"
command -v mosquitto_pub >/dev/null 2>&1 || fail "mosquitto_pub not found on the camera"
[ -n "$TOKEN" ] || fail "/etc/thingino-api.key missing"
# laufendes Rauschen verstellt spk_vol live; save_config/Neustart unten wuerden das speichern bzw. abbrechen
if [ -x /usr/sbin/noise ] && /usr/sbin/noise status 2>/dev/null | grep -q '^an'; then
	fail "Rauschen laeuft gerade - erst in HA ausschalten, dann nochmal starten"
fi

echo "--- Disable logo OSD (persist prudynt's current config first) ---"
# save_config dumps prudynt's in-memory config to /etc/prudynt.json, so this
# must happen BEFORE the motion settings are written into that file below.
printf '{"stream0":{"osd":{"logo":{"enabled":false}}},"stream1":{"osd":{"logo":{"enabled":false}}},"action":{"save_config":null}}' | prudyntctl json - >/dev/null 2>&1
sleep 1

if [ "__UPDATE__" = 1 ]; then
	# Update: Broker-Zugang aus der Kamera-Konfiguration, MQTT-Einstellungen bleiben unveraendert
	BROKER=$(jct /etc/thingino.json get mqtt_sub.host 2>/dev/null | tr -d '"'); PORT=$(jct /etc/thingino.json get mqtt_sub.port 2>/dev/null | tr -d '"')
	MUSER=$(jct /etc/thingino.json get mqtt_sub.username 2>/dev/null | tr -d '"'); MPASS=$(jct /etc/thingino.json get mqtt_sub.password 2>/dev/null | tr -d '"')
	[ -n "$BROKER" ] || fail "update: no MQTT subscriber configured on this camera - run install.ps1 without -Update"
	PORT=${PORT:-1883}
	echo "--- Update: MQTT settings kept ($BROKER:$PORT) ---"
else
BROKER="__BROKER__"; PORT="__PORT__"; MUSER="__USER__"; MPASS="__PASS__"
echo "--- MQTT subscriber (commands from HA on $HOST/cmd) ---"
api json-config-mqtt-sub.cgi '{"enabled":true,"host":"__BROKER__","port":__PORT__,"username":"__USER__","password":"__PASS__","use_ssl":false,"subscriptions":[{"topic":"%hostname/cmd","qos":0,"action":"eval $MQTT_PAYLOAD","enabled":true}]}' >/dev/null \
	|| fail "json-config-mqtt-sub.cgi failed"
[ "$(jct /etc/thingino.json get mqtt_sub.host | tr -d '"')" = "__BROKER__" ] || fail "mqtt_sub config was not saved"

echo "--- Motion events -> MQTT ($HOST/motion) ---"
api json-config-send2.cgi '{"config":{"mqtt":{"enabled":true,"host":"__BROKER__","port":__PORT__,"username":"__USER__","password":"__PASS__","use_ssl":false,"client_id":"'"$HOST"'","topic":"'"$HOST"'/motion","message":"{\"timestamp\": \"%s\"}","send_photo":false,"topic_photo":""}}}' >/dev/null \
	|| fail "json-config-send2.cgi (mqtt) failed"
fi

# Motion detection is written to /etc/prudynt.json and applied by restarting
# prudynt. Enabling it live on a fresh camera crashes prudynt (detection frame
# 0x0), so the frame is set to the main stream size here. It stays OFF by default
# (costs ~20 % CPU on the T23N); switch "Motion Detection" in HA turns it on.
W=$(jct /etc/prudynt.json get stream0.width 2>/dev/null); H=$(jct /etc/prudynt.json get stream0.height 2>/dev/null)
W=${W:-1920}; H=${H:-1080}
for kv in "enabled false" "send2mqtt true" "frame_width $W" "frame_height $H" "roi_count 1" "roi_0_x 0" "roi_0_y 0" "roi_1_x $((W - 1))" "roi_1_y $((H - 1))"; do
	jct /etc/prudynt.json set "motion.${kv% *}" "${kv#* }" >/dev/null || fail "cannot write motion.${kv% *}"
done
echo "--- Restart prudynt to apply motion settings ---"
TZ=$(cat /etc/TZ 2>/dev/null) /etc/init.d/S31prudynt restart >/dev/null 2>&1   # mit Zeitzone, sonst blendet prudynt UTC ein
n=0
while [ ! -S /run/prudynt/prudynt.sock ] || ! pidof prudynt >/dev/null 2>&1; do
	n=$((n + 1)); [ $n -ge 30 ] && fail "prudynt did not come back after restart"
	sleep 1
done
sleep 3
pidof prudynt >/dev/null 2>&1 || fail "prudynt crashed after restart (see logread)"

echo "--- Heartbeat (web UI status) every 10 s instead of every second ---"
# The stock heartbeat forks ~12 helpers per run; at 1 s it costs ~35 % CPU on the T23N.
if grep -q '^UPDATE_INTERVAL=1$' /etc/init.d/S99heartbeat 2>/dev/null; then
	sed -i 's/^UPDATE_INTERVAL=1$/UPDATE_INTERVAL=10/' /etc/init.d/S99heartbeat
	/etc/init.d/S99heartbeat stop >/dev/null 2>&1; sleep 1; /etc/init.d/S99heartbeat start >/dev/null 2>&1
fi

echo "--- Restart MQTT subscriber ---"
# S91mqttsub stop only kills the dispatcher shell; its mosquitto_sub child would
# survive and execute every command a second time. Kill only the dispatcher's
# subscriber (the official ha-daemon runs its own mosquitto_sub, leave that alone).
/etc/init.d/S91mqttsub stop >/dev/null 2>&1
killall mqtt-sub-dispatcher 2>/dev/null
pkill -f "mosquitto_sub.* -t $HOST/cmd" 2>/dev/null
sleep 1
/etc/init.d/S91mqttsub start
sleep 2
[ "$(ps w | grep -c "[m]osquitto_sub.* -t $HOST/cmd")" = "1" ] || fail "MQTT command subscriber not running exactly once (broker unreachable?)"

echo "--- Autostart discovery at boot ---"
cat > /etc/init.d/S99ha-discovery <<'EOF'
#!/bin/sh
case "$1" in
	start) /usr/sbin/thingino-ha-discovery.sh > /tmp/ha-discovery.log 2>&1 & ;;
esac
EOF
chmod +x /etc/init.d/S99ha-discovery

if [ -x /usr/sbin/noise ]; then
	echo "--- Rauschen: Autostart meldet nach dem Booten 'aus' an HA ---"
	[ -f /etc/noise.conf ] || printf 'VOL=35\nCOLOR=braun\n' > /etc/noise.conf
	printf '#!/bin/sh\ncase "$1" in\n\tstart) (sleep 20; /usr/sbin/noise boot) >/dev/null 2>&1 & ;;\nesac\n' > /etc/init.d/S99noise
	chmod +x /etc/init.d/S99noise
	/usr/sbin/noise boot
	echo "Hinweis: Fuer aussetzerfreie Wiedergabe das Mikrofon ausschalten (HA-Schalter 'Mic'), wenn es nicht gebraucht wird."
fi
if [ -x /usr/sbin/ptz-state ] && command -v motors >/dev/null 2>&1; then
	echo "--- PTZ-Position/Preset: Autostart + sofort starten ---"
	printf '#!/bin/sh\ncase "$1" in\n\tstart) (sleep 25; /usr/sbin/ptz-state start) >/dev/null 2>&1 & ;;\nesac\n' > /etc/init.d/S99ptz-state
	chmod +x /etc/init.d/S99ptz-state
	/usr/sbin/ptz-state start
fi

echo "--- Running HA discovery ---"
/usr/sbin/thingino-ha-discovery.sh || fail "discovery failed"

echo "--- Verifying retained discovery config at the broker ---"
if mosquitto_sub -h "$BROKER" -p "$PORT" -u "$MUSER" -P "$MPASS" -t "homeassistant/switch/${HOST}_privacy/config" -C 1 -W 5 >/dev/null 2>&1; then
	echo "OK: discovery payloads are stored at the broker"
else
	fail "discovery payload not found at the broker"
fi
echo "SETUP_OK"
'@

$SETUP = $SETUP.Replace("__UPDATE__", $(if ($Update) { "1" } else { "0" }))
$SETUP = $SETUP.Replace("__BROKER__", $Broker).Replace("__PORT__", $Port).Replace("__USER__", $MqttUser).Replace("__PASS__", $MqttPass)
Send-Text $SETUP "> /tmp/thingino-setup.sh && sh /tmp/thingino-setup.sh"
if ($LASTEXITCODE -ne 0) { Fail "camera setup failed (see output above)" }

# ---------- Step 4: HA-Seite: Entitaeten mit _2 zuruecksetzen ----------
$FIX = Join-Path $SCRIPT_DIR "ha_fix_suffix.py"
if ($HaHost -and (Test-Path $FIX)) {
    $haOk = & $SSH -o BatchMode=yes -o ConnectTimeout=8 $HaHost "echo HA_OK" 2>$null
    if ($haOk -match "HA_OK") {
        Write-Step "Home Assistant: checking for entities with _2 suffix"
        $camHost = (& $SSH @SshOpts $Target "hostname" 2>$null | Select-Object -First 1).Trim()
        Start-Sleep -Seconds 5   # HA die neuen Discovery-Topics verarbeiten lassen
        Send-Text (Read-Utf8 $FIX) "| sudo tee /config/.ha_fix_suffix.py >/dev/null && T=`$(sudo cat /run/s6/container_environment/SUPERVISOR_TOKEN) && sudo docker exec -e T=`$T homeassistant python3 /config/.ha_fix_suffix.py $camHost apply" $HaHost
    } else {
        Write-Host "HA SSH alias '$HaHost' not reachable - skipped _2 check (run ha_fix_suffix.py in HA if entities end with _2)." -ForegroundColor Yellow
    }
}

# ---------- Step 5: summary ----------
Write-Step "[4/4] Done"
Write-Host "The camera should now appear in Home Assistant under Settings -> Devices (MQTT)." -ForegroundColor Cyan
Write-Host "Log of the boot-time discovery on the camera: /tmp/ha-discovery.log"
