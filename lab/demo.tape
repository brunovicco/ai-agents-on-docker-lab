# Terminal recording of the sandbox experiment, as code. Render it on a host where `sbx` is
# installed and signed in, from the repository root:
#
#   vhs lab/demo.tape
#
# It writes the GIF the README embeds and an MP4 for sites that take video, such as LinkedIn.
# Create the sandbox first with `bash lab/demo.sh sandbox`, which asks to approve the plan; the
# tape only starts it off camera. Narration and colors come from lab/tape-helpers.sh. Review the
# output before committing it: the commands print no host paths, but check anyway. Wait patterns
# never appear in the typed commands, so a wait cannot match the command line instead of its
# output.

Output docs/assets/sandbox-demo.gif
Output docs/assets/sandbox-demo.mp4

Require sbx
Require python3

Set Shell "bash"
Set Theme "Catppuccin Mocha"
Set FontSize 20
Set Width 1200
Set Height 640
Set Padding 18
Set Margin 24
Set MarginFill "#313244"
Set WindowBar Colorful
Set BorderRadius 10
Set TypingSpeed 20ms
Set WaitTimeout 60s

Hide
Type "sbx env exec lab/sbxenv.yaml -- true </dev/null >/dev/null 2>&1 && clear && echo sandbox-'up'" Enter
Wait+Screen@5m /sandbox-up/
Type "source lab/tape-helpers.sh && banner" Enter
Sleep 500ms
Type "say 'The planner runs inside a Docker Sandbox and can only propose.'" Enter
Sleep 300ms
Show
Sleep 2s

Type "sbx env exec lab/sbxenv.yaml -- solar-plan" Enter
Wait+Screen /"hours"/
Sleep 1500ms

Hide
Type "say 'The host checks it against its own copy of the forecast.'" Enter
Sleep 300ms
Show
Sleep 1s
Type "sbx env exec lab/sbxenv.yaml -- solar-plan | verify" Enter
Wait+Screen /"decision"/
Sleep 2s

Hide
Type "say 'The kit denies all egress, even to a host the global policy allows.'" Enter
Sleep 300ms
Show
Sleep 1s
Type "sbx env exec lab/sbxenv.yaml -- curl -fsS -o /dev/null https://github.com/" Enter
Wait+Screen /returned error/
Sleep 1500ms
Type "sbx policy check network --sandbox solar-dispatch github.com | grep ." Enter
Wait+Screen /kit:solar-dispatch:deny/
Sleep 2s

Hide
Type "say 'A worse schedule is rejected on the host.'" Enter
Sleep 300ms
Show
Sleep 1s
Type `echo '{"hours": [9, 12]}' | verify` Enter
Wait+Screen /Rejected/
Sleep 5s
