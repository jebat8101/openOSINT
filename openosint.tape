# openosint.tape
# Charmbracelet VHS — https://github.com/charmbracelet/vhs
# Run: vhs openosint.tape

Output assets/demo.gif

Set Shell "bash"
Set FontSize 14
Set FontFamily "Courier New"
Set Width 860
Set Height 520
Set Theme "Dracula"
Set Padding 18
Set TypingSpeed 60ms
Set PlaybackSpeed 0.9

# ----------------------------------------------------------------
# Scene 1: CLI direct execution
# ----------------------------------------------------------------

Type "# OpenOSINT v2.0.0 — direct CLI execution"
Enter
Sleep 600ms

Type "openosint email target@example.com -t 60"
Sleep 400ms
Enter
Sleep 500ms

Type "[*] Email scan: target@example.com"
Enter
Type "[*] Timeout: 60s"
Enter
Sleep 800ms
Type "============================================================"
Enter
Type "===================== SCAN RESULTS ========================="
Enter
Type "============================================================"
Enter
Sleep 300ms
Type "OSINT results for 'target@example.com':"
Enter
Enter
Sleep 200ms
Type "[+] Spotify        https://open.spotify.com/user/targetuser"
Enter
Sleep 150ms
Type "[+] WordPress      https://wordpress.com/targetuser"
Enter
Sleep 150ms
Type "[+] Gravatar       https://gravatar.com/targetuser"
Enter
Sleep 150ms
Type "[+] Office365      email used"
Enter
Sleep 200ms
Type "============================================================"
Enter
Sleep 1200ms

# ----------------------------------------------------------------
# Scene 2: Claude Code agentic execution
# ----------------------------------------------------------------

Type "# Agentic execution via Claude Code (MCP)"
Enter
Sleep 600ms

Type "claude"
Enter
Sleep 800ms

Type "> Investigate target@example.com. Trace any username found."
Sleep 400ms
Enter
Sleep 700ms

Type "I'll investigate target@example.com using the available"
Enter
Type "OSINT tools."
Enter
Sleep 500ms

Type "Running search_email..."
Enter
Sleep 900ms
Type "  Found: Spotify, WordPress, Gravatar, Office365"
Enter
Sleep 500ms

Type "Username 'targetuser' identified. Running search_username..."
Enter
Sleep 1100ms
Type "  Found 12 accounts across platforms."
Enter
Sleep 600ms

Type "Checking breach exposure..."
Enter
Sleep 900ms
Type "  2 breaches: LinkedIn (2016), Adobe (2013)"
Enter
Sleep 700ms

Type ""
Enter
Type "## Summary"
Enter
Type ""
Enter
Type "Target: target@example.com"
Enter
Type "Confidence: High (single identity confirmed)"
Enter
Type ""
Enter
Type "Online presence: Spotify, WordPress, Gravatar,"
Enter
Type "  Office365, GitHub, Reddit (+8 others via username)"
Enter
Type ""
Enter
Type "Breach exposure: LinkedIn 2016, Adobe 2013"
Enter
Type "  Recommendation: credential rotation advised."
Enter
Sleep 2000ms
