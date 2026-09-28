#!/bin/sh
# Thingino -> Home Assistant MQTT Auto-Discovery (prudynt-t based firmware)
#
# Runs ON the camera. Reads the broker settings from /etc/thingino.json
# (section mqtt_sub, configured by install.ps1), installs the command wrapper
# /usr/sbin/thingino-cmd and publishes retained MQTT discovery payloads so the
# camera shows up in Home Assistant as one device with all controls.
#
# Home Assistant sends commands to <hostname>/cmd; the camera's
# mqtt-sub-dispatcher runs the payload with 'eval $MQTT_PAYLOAD' as root.
# All payloads published here therefore are plain shell command lines that
# call /usr/sbin/thingino-cmd <command> [args...].

CONFIG="/etc/thingino.json"
LOG="/tmp/ha-discovery.log"

# ============================================
# READ CONFIG
# ============================================
cget() { jct "$CONFIG" get "$1" 2>/dev/null | tr -d '"'; }

BROKER=$(cget mqtt_sub.host)
PORT=$(cget mqtt_sub.port)
MQUSER=$(cget mqtt_sub.username)
MQPASS=$(cget mqtt_sub.password)
HOST=$(hostname)
TOPIC=$(cget mqtt_sub.subscriptions.0.topic | sed "s/%hostname/$HOST/g")
[ -z "$TOPIC" ] && TOPIC="$HOST/cmd"
CAM=${TOPIC%/cmd}
PORT=${PORT:-1883}
TOKEN=$(cat /etc/thingino-api.key 2>/dev/null)

if [ -z "$BROKER" ]; then
	echo "ERROR: mqtt_sub.host is not configured in $CONFIG" >&2
	exit 1
fi

IP=$(ip route get 1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}' | head -1)
osrel() { grep "^$1=" /etc/os-release 2>/dev/null | cut -d= -f2- | tr -d '"'; }
FW=$(osrel BUILD_ID)
MODEL=$(osrel IMAGE_ID)
[ -z "$MODEL" ] && MODEL="Thingino"

DEVICE="{\"identifiers\":[\"thingino_$CAM\"],\"name\":\"$HOST\",\"model\":\"$MODEL\",\"manufacturer\":\"Thingino\",\"sw_version\":\"$FW\",\"configuration_url\":\"http://$IP\"}"

# ============================================
# MQTT HELPERS
# ============================================
MPUB="mosquitto_pub -h $BROKER -p $PORT"
[ -n "$MQUSER" ] && MPUB="$MPUB -u $MQUSER"
[ -n "$MQPASS" ] && MPUB="$MPUB -P $MQPASS"

MSUB="mosquitto_sub -h $BROKER -p $PORT"
[ -n "$MQUSER" ] && MSUB="$MSUB -u $MQUSER"
[ -n "$MQPASS" ] && MSUB="$MSUB -P $MQPASS"

PUBLISHED="/tmp/ha-discovery.published"
: > "$PUBLISHED"
pub() {
	$MPUB -r -t "$1" -m "$2"
	case "$1" in homeassistant/*/config) echo "$1" >> "$PUBLISHED" ;; esac
}
pub_state() { $MPUB -r -t "$CAM/state/$1" -m "$2"; }

# Remove retained discovery configs of this camera that this run did not publish
# (entities from older script versions would otherwise linger in HA forever).
cleanup_stale() {
	# own schema: homeassistant/<comp>/<host>_<uid>/config ; official thingino-ha
	# package schema: homeassistant/<comp>/thingino_<host>/<uid>/config
	if [ "$OFFICIAL" = "1" ]; then
		pat="^homeassistant/[a-z_]+/${CAM}_[^ /]*/config ."
	else
		pat="^homeassistant/[a-z_]+/(${CAM}_[^ /]*|thingino_${CAM}/[^ /]*)/config ."
	fi
	$MSUB -t "homeassistant/+/+/config" -t "homeassistant/+/+/+/config" -v -W 3 2>/dev/null |
	grep -E "$pat" | cut -d' ' -f1 | sort -u |
	while read -r t; do
		grep -qx "$t" "$PUBLISHED" && continue
		$MPUB -r -t "$t" -n
		echo "  [removed stale] $t"
	done
}

# ============================================
# STATE SYNC: report changes made outside HA (WebUI, button, day/night automatic)
# Runs in the background every 20 s and publishes only values that changed.
# ============================================
STATE_CACHE="/tmp/ha-state-cache"
onoff() { case "$1" in 1 | true | on | ON) echo ON ;; *) echo OFF ;; esac; }
sync_pub() {
	[ -n "$2" ] || return 0
	f="$STATE_CACHE/$1"
	[ -f "$f" ] && [ "$(cat "$f")" = "$2" ] && return 0
	mkdir -p "$STATE_CACHE"
	printf '%s' "$2" > "$f"
	pub_state "$1" "$2"
}
sync_state() {
	if [ "$OFFICIAL" = "0" ]; then
		has_gpio ircut && sync_pub ircut "$(onoff "$(ircut read 2>/dev/null)")"
		for l in ir850 ir940 white; do
			has_gpio "$l" && sync_pub "light_$l" "$(onoff "$(light "$l" read 2>/dev/null)")"
		done
	fi
	Q='{"image":{"brightness":null,"contrast":null,"saturation":null,"sharpness":null,"hue":null,"ae_compensation":null,"defog_strength":null,"drc_strength":null,"highlight_depress":null,"sinter_strength":null,"temper_strength":null,"backlight_compensation":null,"max_again":null,"max_dgain":null,"wb_rgain":null,"wb_bgain":null,"anti_flicker":null,"core_wb_mode":null,"hflip":null,"vflip":null,"running_mode":null},"audio":{"mic_enabled":null,"mic_agc_enabled":null,"mic_high_pass_filter":null,"force_stereo":null,"mic_vol":null,"mic_gain":null,"mic_bitrate":null,"spk_vol":null,"spk_gain":null,"mic_format":null,"mic_sample_rate":null,"spk_sample_rate":null,"mic_noise_suppression":null,"mic_alc_gain":null,"mic_agc_compression_gain_db":null,"mic_agc_target_level_dbfs":null},"motion":{"enabled":null,"sensitivity":null,"cooldown_time":null},"daynight":{"enabled":null},"stream0":{"audio_enabled":null,"video_enabled":null,"bitrate":null,"fps":null,"gop":null,"mode":null},"stream1":{"audio_enabled":null,"video_enabled":null,"bitrate":null,"fps":null,"gop":null,"mode":null}}'
	R=$(printf '%s' "$Q" | prudyntctl json - 2>/dev/null)
	[ -n "$R" ] || return 0
	sec() { printf '%s' "$R" | sed -n "s/.*\"$1\":{\([^}]*\)}.*/\1/p"; }
	val() { printf '%s' "$2" | grep -o "\"$1\":[^,}]*" | head -1 | cut -d: -f2- | tr -d '"'; }
	I=$(sec image); A=$(sec audio); M=$(sec motion); D=$(sec daynight)
	for k in brightness contrast saturation sharpness hue ae_compensation defog_strength drc_strength highlight_depress sinter_strength temper_strength backlight_compensation max_again max_dgain wb_rgain wb_bgain anti_flicker core_wb_mode; do
		sync_pub "$k" "$(val $k "$I")"
	done
	sync_pub hflip "$(onoff "$(val hflip "$I")")"
	sync_pub vflip "$(onoff "$(val vflip "$I")")"
	if [ "$OFFICIAL" = "0" ]; then
		rm_=$(val running_mode "$I"); [ -n "$rm_" ] && sync_pub color "$([ "$rm_" = "0" ] && echo ON || echo OFF)"
		sync_pub motion "$(onoff "$(val enabled "$M")")"
		if [ "$(val enabled "$D")" = "true" ]; then
			sync_pub daynight_mode auto
		else
			sync_pub daynight_mode "$(cat /run/prudynt/daynight_mode 2>/dev/null)"
		fi
	fi
	sync_pub mic "$(onoff "$(val mic_enabled "$A")")"
	sync_pub mic_agc "$(onoff "$(val mic_agc_enabled "$A")")"
	sync_pub mic_hpf "$(onoff "$(val mic_high_pass_filter "$A")")"
	sync_pub force_stereo "$(onoff "$(val force_stereo "$A")")"
	for k in mic_vol mic_gain mic_bitrate spk_vol spk_gain mic_format mic_sample_rate spk_sample_rate mic_noise_suppression mic_alc_gain mic_agc_compression_gain_db mic_agc_target_level_dbfs; do
		sync_pub "$k" "$(val $k "$A")"
	done
	sync_pub motion_sensitivity "$(val sensitivity "$M")"
	sync_pub motion_cooldown "$(val cooldown_time "$M")"
	for s in stream0 stream1; do
		S=$(sec "$s"); [ -n "$S" ] || continue
		sync_pub "${s}_audio" "$(onoff "$(val audio_enabled "$S")")"
		sync_pub "${s}_video" "$(onoff "$(val video_enabled "$S")")"
		for k in bitrate fps gop mode; do sync_pub "${s}_$k" "$(val $k "$S")"; done
	done
}
state_loop() {
	while :; do
		sleep 20
		sync_state
	done
}

# On boot the network / broker may not be ready yet: wait up to ~3 minutes.
wait_for_broker() {
	n=0
	while ! $MPUB -t "$CAM/status" -m "online" -r 2>/dev/null; do
		n=$((n + 1))
		if [ $n -ge 36 ]; then
			echo "ERROR: broker $BROKER:$PORT not reachable after 3 minutes" >&2
			exit 1
		fi
		sleep 5
	done
}

pget() { jct /etc/prudynt.json get "$1" 2>/dev/null | tr -d '"'; }

# Newer firmware ships its own HA integration (ha-daemon, WebUI "Home Assistant").
# When it is enabled we leave its entities (motion, ircut, day/night, privacy,
# color, lights, snapshot, preview, firmware) to it and only add what it lacks.
OFFICIAL=0
if [ "$(cget ha.enabled)" = "true" ] && [ -x /usr/sbin/ha-daemon ]; then
	OFFICIAL=1
	echo "Official thingino-ha integration is enabled: skipping the entities it provides"
fi

has_gpio() {
	jct "$CONFIG" get "gpio.$1" >/dev/null 2>&1
}

# Every entity gets: has_entity_name (entity_id = <hostname>_<name>), unique_id, device
COMMON="\"has_entity_name\":true,\"device\":$DEVICE"

pub_switch() {
	# uid name payload_on payload_off
	pub "homeassistant/switch/${CAM}_${1}/config" \
		"{\"name\":\"$2\",\"unique_id\":\"${CAM}_${1}\",\"command_topic\":\"$TOPIC\",\"payload_on\":\"$3\",\"payload_off\":\"$4\",\"optimistic\":true,$COMMON}"
	echo "  [switch] $2"
}

pub_switch_state() {
	# uid name payload_on payload_off initial(true/false)
	pub "homeassistant/switch/${CAM}_${1}/config" \
		"{\"name\":\"$2\",\"unique_id\":\"${CAM}_${1}\",\"command_topic\":\"$TOPIC\",\"payload_on\":\"$3\",\"payload_off\":\"$4\",\"state_topic\":\"$CAM/state/$1\",\"state_on\":\"ON\",\"state_off\":\"OFF\",\"optimistic\":true,$COMMON}"
	case "$5" in
		true | 1 | ON) pub_state "$1" "ON" ;;
		*) pub_state "$1" "OFF" ;;
	esac
	echo "  [switch] $2 (state: ${5:-unknown})"
}

pub_button() {
	# uid name payload
	pub "homeassistant/button/${CAM}_${1}/config" \
		"{\"name\":\"$2\",\"unique_id\":\"${CAM}_${1}\",\"command_topic\":\"$TOPIC\",\"payload_press\":\"$3\",$COMMON}"
	echo "  [button] $2"
}

pub_number() {
	# uid name command_template min max step unit initial
	extra=""
	[ -n "$7" ] && extra=",\"unit_of_measurement\":\"$7\""
	pub "homeassistant/number/${CAM}_${1}/config" \
		"{\"name\":\"$2\",\"unique_id\":\"${CAM}_${1}\",\"command_topic\":\"$TOPIC\",\"command_template\":\"$3\",\"state_topic\":\"$CAM/state/$1\",\"min\":$4,\"max\":$5,\"step\":$6$extra,\"optimistic\":true,$COMMON}"
	[ -n "$8" ] && pub_state "$1" "$8"
	echo "  [number] $2 ($4-$5, current: ${8:-?})"
}

pub_select() {
	# uid name command_template options_json initial
	pub "homeassistant/select/${CAM}_${1}/config" \
		"{\"name\":\"$2\",\"unique_id\":\"${CAM}_${1}\",\"command_topic\":\"$TOPIC\",\"command_template\":\"$3\",\"state_topic\":\"$CAM/state/$1\",\"options\":$4,\"optimistic\":true,$COMMON}"
	[ -n "$5" ] && pub_state "$1" "$5"
	echo "  [select] $2 (current: ${5:-?})"
}

# ============================================
# COMMAND WRAPPER (installed on the camera)
# ============================================
cat > /usr/sbin/thingino-cmd << 'WRAPPER'
#!/bin/sh
# Thingino command wrapper for Home Assistant (called via MQTT: eval $MQTT_PAYLOAD)
# Usage: thingino-cmd <command> [arg ...]
CONFIG="/etc/thingino.json"
TOKEN=$(cat /etc/thingino-api.key 2>/dev/null)
HOST=$(hostname)
CMD="$1"
VAL="$2"

cget() { jct "$CONFIG" get "$1" 2>/dev/null | tr -d '"'; }
pget() { jct /etc/prudynt.json get "$1" 2>/dev/null | tr -d '"'; }

# Publish a retained state value so Home Assistant stays in sync after restarts
st() {
	BROKER=$(cget mqtt_sub.host); PORT=$(cget mqtt_sub.port); U=$(cget mqtt_sub.username); P=$(cget mqtt_sub.password)
	[ -z "$BROKER" ] && return 0
	set -- -h "$BROKER" -p "${PORT:-1883}" -r -t "$HOST/state/$1" -m "$2"
	[ -n "$U" ] && set -- "$@" -u "$U"
	[ -n "$P" ] && set -- "$@" -P "$P"
	mosquitto_pub "$@" 2>/dev/null
}

# prudynt JSON API (live) + persist to /etc/prudynt.json
papi()  { printf '%s' "$1" | prudyntctl json - >/dev/null 2>&1; }
psave() { papi '{"action":{"save_config":null}}'; }

# CGI endpoints that need the API token
IMAGING="http://localhost/x/json-imaging.cgi?token=$TOKEN"
RECORD="http://localhost/x/tool-record.cgi?token=$TOKEN"

onoff() { case "$1" in on | ON | 1 | true) echo ON ;; *) echo OFF ;; esac; }

# Recording settings: tool-record.cgi expects the complete form each time,
# so read the current values from /etc/prudynt.json and override one field.
rec_post() {
	_key="$1"; _val="$2"
	mount=$(pget recorder.mount); device_path=$(pget recorder.device_path); filename=$(pget recorder.filename)
	channel=$(pget recorder.channel); duration=$(pget recorder.duration); limit=$(pget recorder.limit)
	min_free_mb=$(pget recorder.min_free_mb); check_interval=$(pget recorder.check_interval)
	autostart=$(pget recorder.autostart); cleanup_enabled=$(pget recorder.cleanup_enabled)
	eval "$_key=\"\$_val\""
	curl -s -X POST "$RECORD" -H "Content-Type: application/x-www-form-urlencoded" \
		--data-urlencode "form=video" \
		--data-urlencode "vr_mount=$mount" \
		--data-urlencode "vr_device_path=${device_path:-%hostname/records}" \
		--data-urlencode "vr_filename=${filename:-%Y/%m/%d/%H-%M-%S}" \
		--data-urlencode "vr_channel=${channel:-0}" \
		--data-urlencode "vr_duration=${duration:-60}" \
		--data-urlencode "vr_limit=${limit:-15}" \
		--data-urlencode "vr_min_free_mb=${min_free_mb:-500}" \
		--data-urlencode "vr_check_interval=${check_interval:-60}" \
		--data-urlencode "vr_autostart=${autostart:-false}" \
		--data-urlencode "vr_cleanup_enabled=${cleanup_enabled:-false}" >/dev/null
}

# Timelapse settings live in /etc/timelapse.json (same complete-form rule)
tl_post() {
	_key="$1"; _val="$2"
	tget() { jct /etc/timelapse.json get "timelapse.$1" 2>/dev/null | tr -d '"'; }
	enabled=$(tget enabled); mount=$(tget mount); filepath=$(tget filepath); filename=$(tget filename)
	interval=$(tget interval); keep_days=$(tget keep_days)
	[ -z "$mount" ] && mount=$(pget recorder.mount)
	eval "$_key=\"\$_val\""
	curl -s -X POST "$RECORD" -H "Content-Type: application/x-www-form-urlencoded" \
		--data-urlencode "form=timelapse" \
		--data-urlencode "tl_enabled=${enabled:-false}" \
		--data-urlencode "tl_mount=$mount" \
		--data-urlencode "tl_filepath=${filepath:-%hostname/timelapses}" \
		--data-urlencode "tl_filename=${filename:-%Y%m%d/%Y%m%dT%H%M%S.jpg}" \
		--data-urlencode "tl_interval=${interval:-1}" \
		--data-urlencode "tl_keep_days=${keep_days:-7}" \
		--data-urlencode "tl_preset_enabled=false" >/dev/null
}

case "$CMD" in
	# ---------- Image numbers / selects (live + persist) ----------
	brightness|contrast|saturation|sharpness|hue|ae_compensation|defog_strength|drc_strength|highlight_depress|sinter_strength|temper_strength|backlight_compensation|max_again|max_dgain|wb_rgain|wb_bgain|anti_flicker|core_wb_mode|running_mode)
		papi "{\"image\":{\"$CMD\":$VAL}}" && psave && st "$CMD" "$VAL"
		;;
	hflip_on)  papi '{"image":{"hflip":true}}'  && psave && st hflip ON ;;
	hflip_off) papi '{"image":{"hflip":false}}' && psave && st hflip OFF ;;
	vflip_on)  papi '{"image":{"vflip":true}}'  && psave && st vflip ON ;;
	vflip_off) papi '{"image":{"vflip":false}}' && psave && st vflip OFF ;;

	# ---------- Imaging CGI (ISP tuning) ----------
	wide_dynamic_range|tone|noise_reduction)
		curl -s -X POST "$IMAGING" -d "${CMD}=${VAL}" >/dev/null && st "$CMD" "$VAL"
		;;

	# ---------- Audio ----------
	mic_vol|mic_gain|mic_noise_suppression|mic_alc_gain|mic_agc_compression_gain_db|mic_agc_target_level_dbfs|mic_bitrate|spk_vol|spk_gain|mic_sample_rate|spk_sample_rate)
		papi "{\"audio\":{\"$CMD\":$VAL},\"action\":{\"restart_thread\":4}}" && psave && st "$CMD" "$VAL"
		;;
	mic_format)
		papi "{\"audio\":{\"mic_format\":\"$VAL\"},\"action\":{\"restart_thread\":4}}" && psave && st mic_format "$VAL"
		;;
	mic_on)      papi '{"audio":{"mic_enabled":true},"action":{"restart_thread":4}}'  && psave && st mic ON ;;
	mic_off)     papi '{"audio":{"mic_enabled":false},"action":{"restart_thread":4}}' && psave && st mic OFF ;;
	mic_agc_on)  papi '{"audio":{"mic_agc_enabled":true},"action":{"restart_thread":4}}'  && psave && st mic_agc ON ;;
	mic_agc_off) papi '{"audio":{"mic_agc_enabled":false},"action":{"restart_thread":4}}' && psave && st mic_agc OFF ;;
	mic_hpf_on)  papi '{"audio":{"mic_high_pass_filter":true},"action":{"restart_thread":4}}'  && psave && st mic_hpf ON ;;
	mic_hpf_off) papi '{"audio":{"mic_high_pass_filter":false},"action":{"restart_thread":4}}' && psave && st mic_hpf OFF ;;
	stereo_on)   papi '{"audio":{"force_stereo":true},"action":{"restart_thread":4}}'  && psave && st force_stereo ON ;;
	stereo_off)  papi '{"audio":{"force_stereo":false},"action":{"restart_thread":4}}' && psave && st force_stereo OFF ;;

	# ---------- Motion detection (live + persist) ----------
	motion_on)
		# prudynt crashes if motion starts with a 0x0 detection frame: fix the
		# frame in the config first and restart prudynt in that case.
		if [ "$(pget motion.frame_width)" = "0" ] || [ -z "$(pget motion.frame_width)" ]; then
			W=$(pget stream0.width); H=$(pget stream0.height)
			for kv in "enabled true" "frame_width ${W:-1920}" "frame_height ${H:-1080}" "roi_count 1" "roi_0_x 0" "roi_0_y 0" "roi_1_x $((${W:-1920} - 1))" "roi_1_y $((${H:-1080} - 1))"; do
				jct /etc/prudynt.json set motion.${kv% *} ${kv#* } >/dev/null
			done
			/etc/init.d/S31prudynt restart >/dev/null 2>&1
		else
			papi '{"motion":{"enabled":true}}'; jct /etc/prudynt.json set motion.enabled true >/dev/null
		fi
		st motion ON ;;
	motion_off)
		papi '{"motion":{"enabled":false}}'; jct /etc/prudynt.json set motion.enabled false >/dev/null; st motion OFF ;;
	motion_sensitivity)
		papi "{\"motion\":{\"sensitivity\":$VAL}}"; jct /etc/prudynt.json set motion.sensitivity "$VAL" >/dev/null; st motion_sensitivity "$VAL" ;;
	motion_cooldown)
		papi "{\"motion\":{\"cooldown_time\":$VAL}}"; jct /etc/prudynt.json set motion.cooldown_time "$VAL" >/dev/null; st motion_cooldown "$VAL" ;;

	# ---------- Recording ----------
	rec_ch0_on)  papi '{"mp4":{"start":{"channel":0}}}' ;;
	rec_ch0_off) papi '{"mp4":{"stop":{"channel":0}}}' ;;
	rec_ch1_on)  papi '{"mp4":{"start":{"channel":1}}}' ;;
	rec_ch1_off) papi '{"mp4":{"stop":{"channel":1}}}' ;;
	rec_autostart_on)  rec_post autostart true  && st recording_autostart ON ;;
	rec_autostart_off) rec_post autostart false && st recording_autostart OFF ;;
	rec_cleanup_on)    rec_post cleanup_enabled true  && st recording_cleanup ON ;;
	rec_cleanup_off)   rec_post cleanup_enabled false && st recording_cleanup OFF ;;
	clip_duration)     rec_post duration "$VAL"    && st clip_duration "$VAL" ;;
	storage_limit)     rec_post limit "$VAL"       && st storage_limit "$VAL" ;;
	min_free_space)    rec_post min_free_mb "$VAL" && st min_free_space "$VAL" ;;

	# ---------- Timelapse ----------
	tl_on)        tl_post enabled true   && st timelapse ON ;;
	tl_off)       tl_post enabled false  && st timelapse OFF ;;
	tl_interval)  tl_post interval "$VAL"  && st timelapse_interval "$VAL" ;;
	tl_retention) tl_post keep_days "$VAL" && st timelapse_retention "$VAL" ;;

	# ---------- Streams: stream_set <stream> <field> <value> ----------
	stream_set)
		papi "{\"$2\":{\"$3\":$4},\"action\":{\"restart_thread\":3}}" && psave && st "${2}_${3}" "$4"
		;;
	stream_set_str)
		papi "{\"$2\":{\"$3\":\"$4\"},\"action\":{\"restart_thread\":3}}" && psave && st "${2}_${3}" "$4"
		;;
	stream_audio_on)  papi "{\"$VAL\":{\"audio_enabled\":true},\"action\":{\"restart_thread\":3}}"  && psave && st "${VAL}_audio" ON ;;
	stream_audio_off) papi "{\"$VAL\":{\"audio_enabled\":false},\"action\":{\"restart_thread\":3}}" && psave && st "${VAL}_audio" OFF ;;
	stream_video_on)  papi "{\"$VAL\":{\"video_enabled\":true},\"action\":{\"restart_thread\":3}}"  && psave && st "${VAL}_video" ON ;;
	stream_video_off) papi "{\"$VAL\":{\"video_enabled\":false},\"action\":{\"restart_thread\":3}}" && psave && st "${VAL}_video" OFF ;;

	# ---------- Day/Night & color ----------
	daynight)
		case "$VAL" in
			auto) papi '{"daynight":{"enabled":true}}' ;;
			day | night) papi "{\"daynight\":{\"enabled\":false,\"force_mode\":\"$VAL\"}}" ;;
			*) echo "daynight: expected day|night|auto" >&2; exit 1 ;;
		esac
		st daynight_mode "$VAL"
		;;
	color_on)  papi '{"daynight":{"enabled":false},"image":{"running_mode":0}}' && st color ON ;;
	color_off) papi '{"daynight":{"enabled":false},"image":{"running_mode":1}}' && st color OFF ;;

	# ---------- Lights / IR cut / privacy (with state) ----------
	ircut)      ircut "$VAL" >/dev/null 2>&1; st ircut "$(onoff "$VAL")" ;;
	light)      light "$2" "$3" >/dev/null 2>&1; st "light_$2" "$(onoff "$3")" ;;
	privacy)    privacy "$VAL" >/dev/null 2>&1; st privacy "$(onoff "$VAL")" ;;
	status_led) pin=$(cget gpio.led_b.pin); [ -n "$pin" ] && gpio set "$pin" "$([ "$VAL" = on ] && echo 1 || echo 0)" >/dev/null 2>&1; st status_led "$(onoff "$VAL")" ;;

	# ---------- PTZ ----------
	ptz)        motors -d g -x "$2" -y "$3" >/dev/null 2>&1 ;;
	position_reset) motors -r >/dev/null 2>&1 ;;

	# ---------- Sound ----------
	play)      play "$VAL" >/dev/null 2>&1 ;;
	play_stop) play stop >/dev/null 2>&1 ;;

	# ---------- System ----------
	reboot)    reboot ;;
	*)
		echo "Unknown command: $CMD" >&2
		exit 1
		;;
esac
WRAPPER
chmod +x /usr/sbin/thingino-cmd
echo "Wrapper script installed at /usr/sbin/thingino-cmd"

# ============================================
# PUBLISH DISCOVERY
# ============================================
echo "Starting HA discovery for $HOST ($CAM) -> $BROKER:$PORT"
wait_for_broker
T="/usr/sbin/thingino-cmd"

if [ "$OFFICIAL" = "0" ]; then
	echo "--- Basic ---"
	pub_switch_state "privacy" "Privacy" "$T privacy on" "$T privacy off" "$([ -f /run/prudynt/privacy.active ] && echo true || echo false)"
	pub_button "reboot" "Reboot" "$T reboot"

	echo "--- Lights ---"
	has_gpio "ircut" && pub_switch_state "ircut" "IR Cut Filter" "$T ircut on" "$T ircut off" "$(ircut read 2>/dev/null)"
	has_gpio "ir850" && pub_switch_state "light_ir850" "IR Light 850nm" "$T light ir850 on" "$T light ir850 off" "$(light ir850 read 2>/dev/null)"
	has_gpio "ir940" && pub_switch_state "light_ir940" "IR Light 940nm" "$T light ir940 on" "$T light ir940 off" "$(light ir940 read 2>/dev/null)"
	has_gpio "white" && pub_switch_state "light_white" "White Light" "$T light white on" "$T light white off" "$(light white read 2>/dev/null)"

	echo "--- Color / Day-Night ---"
	pub_switch_state "color" "Color Mode" "$T color_on" "$T color_off" "$([ "$(pget image.running_mode)" = "0" ] && echo true || echo false)"
	if [ "$(pget daynight.enabled)" = "true" ]; then dn="auto"; else dn=$(pget daynight.force_mode); fi
	pub_select "daynight_mode" "Day/Night Mode" "$T daynight {{ value }}" "[\"day\",\"night\",\"auto\"]" "${dn:-auto}"
fi
has_gpio "led_b" && pub_switch "status_led" "Status LED" "$T status_led on" "$T status_led off"

echo "--- PTZ ---"
# motor config: /etc/motors.json (older firmware) or thingino.json "motors" (newer)
if [ -x /usr/bin/motors ] && { [ -f /etc/motors.json ] || jct "$CONFIG" get motors >/dev/null 2>&1; }; then
	pub_button "ptz_left"       "PTZ Left"       "$T ptz -50 0"
	pub_button "ptz_right"      "PTZ Right"      "$T ptz 50 0"
	pub_button "ptz_up"         "PTZ Up"         "$T ptz 0 -50"
	pub_button "ptz_down"       "PTZ Down"       "$T ptz 0 50"
	pub_button "ptz_left_fast"  "PTZ Left Fast"  "$T ptz -200 0"
	pub_button "ptz_right_fast" "PTZ Right Fast" "$T ptz 200 0"
	pub_button "ptz_up_fast"    "PTZ Up Fast"    "$T ptz 0 -200"
	pub_button "ptz_down_fast"  "PTZ Down Fast"  "$T ptz 0 200"
	pub_button "position_reset" "Position Reset" "$T position_reset"
	if [ -x /usr/sbin/ptz_presets ]; then
		for i in 0 1 2 3 4 5 6 7; do
			pub_button "preset_${i}_load"   "Preset $i Load"   "/usr/sbin/ptz_presets $i"
			pub_button "preset_${i}_save"   "Preset $i Save"   "/usr/sbin/ptz_presets -a $i Preset$i"
			pub_button "preset_${i}_delete" "Preset $i Delete" "/usr/sbin/ptz_presets -r $i"
		done
	fi
fi

echo "--- Image ---"
for field in brightness contrast saturation sharpness hue ae_compensation defog_strength drc_strength highlight_depress sinter_strength temper_strength; do
	val=$(pget "image.$field")
	[ -z "$val" ] && continue
	pub_number "$field" "$(echo "$field" | sed 's/_/ /g')" "$T $field {{ value | int }}" 0 255 1 "" "$val"
done
val=$(pget image.backlight_compensation); [ -n "$val" ] && pub_number "backlight_compensation" "backlight compensation" "$T backlight_compensation {{ value | int }}" 0 10 1 "" "$val"
val=$(pget image.max_again); [ -n "$val" ] && pub_number "max_again" "max analog gain" "$T max_again {{ value | int }}" 0 160 1 "" "$val"
val=$(pget image.max_dgain); [ -n "$val" ] && pub_number "max_dgain" "max digital gain" "$T max_dgain {{ value | int }}" 0 80 1 "" "$val"
val=$(pget image.wb_rgain); [ -n "$val" ] && pub_number "wb_rgain" "WB red gain" "$T wb_rgain {{ value | int }}" 0 1024 1 "" "$val"
val=$(pget image.wb_bgain); [ -n "$val" ] && pub_number "wb_bgain" "WB blue gain" "$T wb_bgain {{ value | int }}" 0 1024 1 "" "$val"
pub_switch_state "hflip" "Horizontal Flip" "$T hflip_on" "$T hflip_off" "$(pget image.hflip)"
pub_switch_state "vflip" "Vertical Flip" "$T vflip_on" "$T vflip_off" "$(pget image.vflip)"
pub_select "anti_flicker" "Anti-Flicker" "$T anti_flicker {{ value | int }}" "[\"0\",\"1\",\"2\"]" "$(pget image.anti_flicker)"
pub_select "core_wb_mode" "White Balance Mode" "$T core_wb_mode {{ value | int }}" "[\"0\",\"1\",\"2\"]" "$(pget image.core_wb_mode)"

echo "--- ISP tuning ---"
IMAGING_RESPONSE=$(curl -s "http://localhost/x/json-imaging.cgi?token=$TOKEN" 2>/dev/null | tr -d '\n ')
for field in wide_dynamic_range tone noise_reduction; do
	block=$(echo "$IMAGING_RESPONSE" | grep -o "\"$field\":{[^}]*}")
	echo "$block" | grep -q '"supported":true' || continue
	min=$(echo "$block" | grep -oE '"min":[0-9]+' | cut -d: -f2)
	max=$(echo "$block" | grep -oE '"max":[0-9]+' | cut -d: -f2)
	cur=$(echo "$block" | grep -oE '"value":[0-9]+' | cut -d: -f2)
	pub_number "$field" "$(echo "$field" | sed 's/_/ /g')" "$T $field {{ value | int }}" "${min:-0}" "${max:-255}" 1 "" "${cur:-128}"
done

echo "--- Audio ---"
# only keys that exist in this firmware's prudynt.json (the set differs between versions)
[ -n "$(pget audio.mic_enabled)" ]          && pub_switch_state "mic"          "Mic"          "$T mic_on"     "$T mic_off"     "$(pget audio.mic_enabled)"
[ -n "$(pget audio.mic_agc_enabled)" ]      && pub_switch_state "mic_agc"      "Mic AGC"      "$T mic_agc_on" "$T mic_agc_off" "$(pget audio.mic_agc_enabled)"
[ -n "$(pget audio.mic_high_pass_filter)" ] && pub_switch_state "mic_hpf"      "Mic HPF"      "$T mic_hpf_on" "$T mic_hpf_off" "$(pget audio.mic_high_pass_filter)"
[ -n "$(pget audio.force_stereo)" ]         && pub_switch_state "force_stereo" "Force Stereo" "$T stereo_on"  "$T stereo_off"  "$(pget audio.force_stereo)"
[ -n "$(pget audio.mic_vol)" ]     && pub_number "mic_vol"     "Mic Volume"     "$T mic_vol {{ value | int }}"     -30 120 1 ""     "$(pget audio.mic_vol)"
[ -n "$(pget audio.mic_gain)" ]    && pub_number "mic_gain"    "Mic Gain"       "$T mic_gain {{ value | int }}"      0  31 1 ""     "$(pget audio.mic_gain)"
[ -n "$(pget audio.mic_bitrate)" ] && pub_number "mic_bitrate" "Mic Bitrate"    "$T mic_bitrate {{ value | int }}"   8 256 8 "kbps" "$(pget audio.mic_bitrate)"
[ -n "$(pget audio.spk_vol)" ]     && pub_number "spk_vol"     "Speaker Volume" "$T spk_vol {{ value | int }}"     -30 120 1 ""     "$(pget audio.spk_vol)"
[ -n "$(pget audio.spk_gain)" ]    && pub_number "spk_gain"    "Speaker Gain"   "$T spk_gain {{ value | int }}"      0  31 1 ""     "$(pget audio.spk_gain)"
[ -n "$(pget audio.mic_noise_suppression)" ]       && pub_number "mic_noise_suppression"       "Mic Noise Suppression" "$T mic_noise_suppression {{ value | int }}"       0  3 1 "" "$(pget audio.mic_noise_suppression)"
[ -n "$(pget audio.mic_alc_gain)" ]                && pub_number "mic_alc_gain"                "Mic ALC Gain"          "$T mic_alc_gain {{ value | int }}"                0  7 1 "" "$(pget audio.mic_alc_gain)"
[ -n "$(pget audio.mic_agc_compression_gain_db)" ] && pub_number "mic_agc_compression_gain_db" "Mic AGC Compression"   "$T mic_agc_compression_gain_db {{ value | int }}" 0 90 1 "" "$(pget audio.mic_agc_compression_gain_db)"
[ -n "$(pget audio.mic_agc_target_level_dbfs)" ]   && pub_number "mic_agc_target_level_dbfs"   "Mic AGC Target Level"  "$T mic_agc_target_level_dbfs {{ value | int }}"   0 31 1 "" "$(pget audio.mic_agc_target_level_dbfs)"
[ -n "$(pget audio.mic_format)" ]      && pub_select "mic_format"      "Mic Codec"           "$T mic_format {{ value }}"            "[\"AAC\",\"G711A\",\"G711U\",\"G726\",\"OPUS\",\"PCM\"]" "$(pget audio.mic_format)"
[ -n "$(pget audio.mic_sample_rate)" ] && pub_select "mic_sample_rate" "Mic Sample Rate"     "$T mic_sample_rate {{ value | int }}" "[\"8000\",\"16000\",\"24000\",\"44100\",\"48000\"]"    "$(pget audio.mic_sample_rate)"
[ -n "$(pget audio.spk_sample_rate)" ] && pub_select "spk_sample_rate" "Speaker Sample Rate" "$T spk_sample_rate {{ value | int }}" "[\"8000\",\"16000\",\"24000\",\"44100\",\"48000\"]"    "$(pget audio.spk_sample_rate)"

echo "--- Motion ---"
if [ "$OFFICIAL" = "0" ]; then
	pub_switch_state "motion" "Motion Detection" "$T motion_on" "$T motion_off" "$(pget motion.enabled)"
	# send2mqtt publishes {"timestamp": ...} to <hostname>/motion on every event (non-retained)
	pub "homeassistant/binary_sensor/${CAM}_motion_detected/config" \
		"{\"name\":\"Motion\",\"unique_id\":\"${CAM}_motion_detected\",\"state_topic\":\"$CAM/motion\",\"value_template\":\"ON\",\"payload_on\":\"ON\",\"off_delay\":30,\"device_class\":\"motion\",$COMMON}"
	echo "  [binary_sensor] Motion"
fi
pub_number "motion_sensitivity" "Motion Sensitivity" "$T motion_sensitivity {{ value | int }}" 1  8 1 ""  "$(pget motion.sensitivity)"
pub_number "motion_cooldown"    "Motion Cooldown"    "$T motion_cooldown {{ value | int }}"    1 60 1 "s" "$(pget motion.cooldown_time)"
# "Motion Alarm": a plain flag stored in the broker for HA automations (no camera function).
# retain:true so the value survives HA restarts; seed OFF only if nothing is stored yet.
pub "homeassistant/switch/${CAM}_alarm/config" \
	"{\"name\":\"Motion Alarm\",\"unique_id\":\"${CAM}_alarm\",\"command_topic\":\"$CAM/alarm\",\"state_topic\":\"$CAM/alarm\",\"payload_on\":\"ON\",\"payload_off\":\"OFF\",\"retain\":true,\"icon\":\"mdi:bell-alert\",$COMMON}"
[ -z "$($MSUB -t "$CAM/alarm" -C 1 -W 2 2>/dev/null)" ] && pub "$CAM/alarm" "OFF"
echo "  [switch] Motion Alarm (HA-side flag)"

echo "--- Recording ---"
if [ -n "$(pget recorder.mount)" ]; then
	pub_switch "recording_ch0" "Recording Ch0" "$T rec_ch0_on" "$T rec_ch0_off"
	pub_switch "recording_ch1" "Recording Ch1" "$T rec_ch1_on" "$T rec_ch1_off"
	pub_switch_state "recording_autostart" "Recording Autostart" "$T rec_autostart_on" "$T rec_autostart_off" "$(pget recorder.autostart)"
	pub_switch_state "recording_cleanup"   "Recording Cleanup"   "$T rec_cleanup_on"   "$T rec_cleanup_off"   "$(pget recorder.cleanup_enabled)"
	pub_number "clip_duration"  "Clip Duration"  "$T clip_duration {{ value | int }}"  10 3600  10 "s"  "$(pget recorder.duration)"
	pub_number "storage_limit"  "Storage Limit"  "$T storage_limit {{ value | int }}"   1  128   1 "GB" "$(pget recorder.limit)"
	pub_number "min_free_space" "Min Free Space" "$T min_free_space {{ value | int }}" 100 2000 100 "MB" "$(pget recorder.min_free_mb)"
	tl_enabled=$(jct /etc/timelapse.json get timelapse.enabled 2>/dev/null)
	pub_switch_state "timelapse" "Timelapse" "$T tl_on" "$T tl_off" "${tl_enabled:-false}"
	pub_number "timelapse_interval"  "Timelapse Interval"  "$T tl_interval {{ value | int }}"  1 60 1 "min"  "$(jct /etc/timelapse.json get timelapse.interval 2>/dev/null || echo 1)"
	pub_number "timelapse_retention" "Timelapse Retention" "$T tl_retention {{ value | int }}" 1 30 1 "days" "$(jct /etc/timelapse.json get timelapse.keep_days 2>/dev/null || echo 7)"
else
	echo "  (no storage mount configured -> recording/timelapse entities skipped)"
fi

echo "--- Sounds ---"
pub_button "play_stop" "Stop Sound" "$T play_stop"
SOUNDS=$(ls /usr/share/sounds/*.opus 2>/dev/null | sed 's|.*/||')
if [ -n "$SOUNDS" ]; then
	OPTS=$(echo "$SOUNDS" | sed 's/.*/"&"/' | tr '\n' ',' | sed 's/,$//')
	pub_select "sound_select" "Play Sound" "$T play /usr/share/sounds/{{ value }}" "[$OPTS]" "$(echo "$SOUNDS" | head -1)"
fi

echo "--- Streams ---"
for stream in stream0 stream1; do
	[ "$(pget "${stream}.enabled")" = "true" ] || continue
	case "$stream" in stream0) SN="Main Stream" ;; *) SN="Sub Stream" ;; esac
	pub_switch_state "${stream}_audio" "$SN Audio" "$T stream_audio_on $stream" "$T stream_audio_off $stream" "$(pget "${stream}.audio_enabled")"
	pub_switch_state "${stream}_video" "$SN Video" "$T stream_video_on $stream" "$T stream_video_off $stream" "$(pget "${stream}.video_enabled")"
	val=$(pget "${stream}.bitrate"); [ -n "$val" ] && pub_number "${stream}_bitrate" "$SN Bitrate" "$T stream_set $stream bitrate {{ value | int }}" 256 8192 128 "kbps" "$val"
	val=$(pget "${stream}.fps");     [ -n "$val" ] && pub_number "${stream}_fps"     "$SN FPS"     "$T stream_set $stream fps {{ value | int }}"     0 30 1 "" "$val"
	val=$(pget "${stream}.gop");     [ -n "$val" ] && pub_number "${stream}_gop"     "$SN GOP"     "$T stream_set $stream gop {{ value | int }}"     1 120 1 "" "$val"
	val=$(pget "${stream}.mode");    [ -n "$val" ] && pub_select "${stream}_mode"    "$SN Mode"    "$T stream_set_str $stream mode {{ value }}" "[\"CBR\",\"VBR\",\"FIXQP\",\"SMART\"]" "$val"
done

echo "--- Cleanup ---"
cleanup_stale

# The MQTT command subscriber dies if the broker was down when it started
# (mosquitto_sub does not reconnect) - make sure it is running now.
if [ "$(jct "$CONFIG" get mqtt_sub.enabled 2>/dev/null)" = "true" ] && ! ps w | grep -q "[m]osquitto_sub.* -t $TOPIC"; then
	echo "MQTT subscriber not running - restarting it"
	killall mqtt-sub-dispatcher 2>/dev/null
	pkill -f "mosquitto_sub.* -t $TOPIC" 2>/dev/null
	/etc/init.d/S91mqttsub start
fi

# Start (or replace) the background state sync loop
if [ -f /run/ha-state.pid ] && kill -0 "$(cat /run/ha-state.pid)" 2>/dev/null; then
	kill "$(cat /run/ha-state.pid)" 2>/dev/null
fi
rm -rf "$STATE_CACHE"
( state_loop ) >/dev/null 2>&1 </dev/null &
echo $! > /run/ha-state.pid
echo "State sync loop started (pid $(cat /run/ha-state.pid), every 20 s)"

echo ""
echo "HA discovery complete: all entities published for $HOST"
