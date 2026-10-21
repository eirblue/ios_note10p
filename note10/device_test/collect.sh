#!/sbin/sh
# Note10 phase-1 recovery probe. Writes only its new directory below /tmp.
# No mounting, partition access, flashing, reboot, module loading or kexec.
set -u
PATH=/sbin:/system/bin:/system/xbin:/vendor/bin:$PATH
export PATH

die() { echo "NOTE10_PROBE_ERROR: $*" >&2; exit 1; }
[ "$(id -u)" = 0 ] || die "Root recovery shell required"
[ "$(uname -m)" = aarch64 ] || die "AArch64 recovery required"
TWRP=$(getprop ro.twrp.version)
[ -n "$TWRP" ] || die "TWRP required; stock recovery/Android refused"
DEVICE=$(getprop ro.product.device)
MODEL=$(getprop ro.product.model)
case "$DEVICE:$MODEL" in
    d2x:*|d2xks:*|*:SM-N976N) ;;
    *) die "Expected SM-N976N/d2x; got $DEVICE / $MODEL" ;;
esac

OUT=${1:-/tmp/note10-probe/session-$$}
case "$OUT" in /tmp/note10-probe/session-*) ;; *) die "Invalid RAM output path" ;; esac
LEAF=${OUT#/tmp/note10-probe/session-}
case "$LEAF" in ''|*[!a-zA-Z0-9_-]*) die "Invalid session name" ;; esac
[ ! -e "$OUT" ] || die "Session already exists; refusing stale output"
# /tmp must be memory-backed, not a symlink into persistent storage.
[ ! -L /tmp ] && [ ! -L /tmp/note10-probe ] || die "Unexpected output symlink"
awk '($2 == "/" || $2 == "/tmp") && length($2) > best {best=length($2); kind=$3}
     END {exit !(kind == "tmpfs" || kind == "ramfs" || kind == "rootfs")}' /proc/mounts \
    || die "Expected memory-backed /tmp"
umask 077
mkdir -p "$OUT" || die "Cannot create RAM output"
STATUS="$OUT/status.tsv"
printf 'item\texit_code\n' > "$STATUS"

capture() {
    KEY=$1; shift
    "$@" > "$OUT/$KEY" 2> "$OUT/$KEY.stderr"
    RC=$?
    printf '%s\t%s\n' "$KEY" "$RC" >> "$STATUS"
}
capture kernel.txt uname -a
capture iomem.txt cat /proc/iomem
capture meminfo.txt cat /proc/meminfo
capture mounts.txt cat /proc/mounts
capture config.gz cat /proc/config.gz
capture live.dtb cat /sys/firmware/fdt
capture dmesg.txt dmesg
# CPU serial and command-line identifier values are omitted from text captures.
capture cpuinfo.txt sed '/^[Ss]erial[[:space:]]*:/d' /proc/cpuinfo
capture cmdline.txt sed 's/androidboot.serialno=[^ ]*/androidboot.serialno=REDACTED/g' /proc/cmdline
capture process-status.txt cat /proc/self/status
{
    for PROP in ro.product.model ro.product.device ro.product.board ro.board.platform \
        ro.hardware ro.twrp.version ro.build.PDA ro.bootloader ro.boot.hw_rev ro.revision \
        ro.boot.flash.locked ro.boot.vbmeta.device_state ro.boot.verifiedbootstate; do
        printf '%s=%s\n' "$PROP" "$(getprop "$PROP")"
    done
} > "$OUT/properties.txt"

if [ ! -s "$OUT/live.dtb" ]; then
    if [ -d /sys/firmware/devicetree/base ]; then
        capture live-tree.tar tar -cf - -C /sys/firmware/devicetree/base .
    elif [ -d /proc/device-tree ]; then
        capture live-tree.tar tar -cf - -C /proc/device-tree .
    fi
fi
mkdir "$OUT/cache"
for CPU in /sys/devices/system/cpu/cpu[0-9]*; do
    [ -d "$CPU/cache" ] || continue
    CNAME=${CPU##*/}
    for INDEX in "$CPU"/cache/index[0-9]*; do
        [ -d "$INDEX" ] || continue
        INAME=${INDEX##*/}
        for FIELD in level type coherency_line_size size shared_cpu_list; do
            [ -r "$INDEX/$FIELD" ] || continue
            capture "cache/$CNAME-$INAME-$FIELD.txt" cat "$INDEX/$FIELD"
        done
    done
done
printf 'schema=1\nphase=linux-recovery-observation\nxnu_executed=false\nprivileged_entry_registers_measured=false\n' > "$OUT/scope.txt"
printf '%s\n' NOTE10_PROBE_COMPLETE > "$OUT/COMPLETE"
echo "NOTE10_PROBE_OUTPUT=$OUT"
echo "Capture stays in RAM. Pull it to the PC before rebooting."
