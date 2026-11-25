#!/bin/bash
# X session for the kiosk: no screen blanking, Firefox full screen on the on-screen Neuron panel.
# (Firefox from Mozilla's APT repository: Ubuntu's own Firefox and Chromium are snaps, which a live stick can't run.)
xset s off -dpms s noblank 2>/dev/null
# wait until the panel relay answers; a page opened too early stays blank white
for i in $(seq 1 60); do (exec 3<>/dev/tcp/127.0.0.1/8080) 2>/dev/null && break; sleep 1; done
sleep 2
P=/tmp/firefox-kiosk
new_profile(){ rm -rf "$P"; mkdir -p "$P"; cat > "$P/user.js" <<'EOF'
user_pref("browser.aboutwelcome.enabled", false);
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("startup.homepage_welcome_url", "");
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);
user_pref("browser.sessionstore.resume_from_crash", false);
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("app.update.enabled", false);
user_pref("browser.gesture.swipe.left", "");
user_pref("browser.gesture.swipe.right", "");
user_pref("apz.allow_zooming", false);
user_pref("layers.acceleration.disabled", true);
EOF
}
export MOZ_USE_XINPUT2=1          # touch screens send touch events, not mouse emulation
echo "  screen $(xrandr 2>/dev/null | awk '/\*/{print $1; exit}'), firefox (software drawing)"
# A browser sometimes comes up with a blank white page right after boot. The page holds a live
# connection to the panel relay once it has loaded, so if there is none after 25 s, start it again.
for attempt in 1 2 3 4 5; do
  new_profile
  /usr/bin/firefox --kiosk --new-instance --profile "$P" http://127.0.0.1:8080/panel &
  pid=$!; ok=0
  for i in $(seq 1 25); do sleep 1; kill -0 $pid 2>/dev/null || break
    ss -Htn state established '( sport = :8080 )' 2>/dev/null | grep -q . && { ok=1; break; }; done
  if [ $ok = 1 ]; then echo "  panel page connected (attempt $attempt)"; wait $pid; exit $?; fi
  echo "  panel page not connected after attempt $attempt; restarting Firefox"
  kill $pid 2>/dev/null; sleep 2; kill -9 $pid 2>/dev/null
done
exit 1
