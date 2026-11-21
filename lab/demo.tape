# Terminal recording of the sandbox experiment, as code. Render it on a host where `sbx` is
# installed and signed in, from the repository root:
#
#   vhs lab/demo.tape
#
# Create the sandbox first with `bash lab/demo.sh sandbox`, which asks to approve the plan; the
# tape only starts it off camera. Review the GIF before committing it: the commands print no host
# paths, but check anyway. Wait patterns never appear in the typed commands, so a wait cannot
# match the command line instead of its output.

Output docs/assets/sandbox-demo.gif

Require sbx
Require python3

Set Shell "bash"
Set FontSize 16
Set Width 1200
Set Height 640
Set Padding 20
Set TypingSpeed 30ms
Set WaitTimeout 60s

Hide
Type "export PS1='$ ' PYTHONPATH=src && clear" Enter
Type "sbx env exec lab/sbxenv.yaml -- true </dev/null >/dev/null 2>&1 && clear && echo sandbox-'up'" Enter
Wait+Screen@5m /sandbox-up/
Type "clear" Enter
Sleep 500ms
Show

Type "# The planner runs inside a Docker Sandbox and can only propose." Enter
Sleep 1s
Type "sbx env exec lab/sbxenv.yaml -- solar-plan" Enter
Wait+Screen /"hours"/
Sleep 2s

Type "# The host verifies the proposal against its own copy of the forecast." Enter
Sleep 1s
Type "sbx env exec lab/sbxenv.yaml -- solar-plan | python3 -m solar_dispatch.entrypoints.dispatch verify lab/forecast/day.json" Enter
Wait+Screen /"decision"/
Sleep 3s

Type "# The kit denies all egress, even to a host the global policy allows." Enter
Sleep 1s
Type "sbx env exec lab/sbxenv.yaml -- curl --max-time 5 -fsS -o /dev/null https://github.com/; echo exit=$?" Enter
Wait+Screen /exit=[0-9]+/
Sleep 2s
Type "sbx policy check network --sandbox solar-dispatch github.com" Enter
Wait+Screen /kit:solar-dispatch:deny/
Sleep 3s

Type "# A worse schedule is rejected on the host." Enter
Sleep 1s
Type `echo '{"hours": [9, 12]}' | python3 -m solar_dispatch.entrypoints.dispatch verify lab/forecast/day.json` Enter
Wait+Screen /Rejected/
Sleep 4s
