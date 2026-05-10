#!/bin/bash

clear
sleep 0.5

echo ""
echo "  OpenOSINT v2.0.0"
echo "  MCP-native OSINT framework"
echo ""
sleep 1

echo "$ openosint email target@example.com -t 60"
sleep 1.2

echo ""
echo "[*] Email scan: target@example.com"
echo "[*] Timeout: 60s"
echo ""
sleep 1

echo "============================================================"
echo "===================== SCAN RESULTS ========================="
echo "============================================================"
sleep 0.3
echo "OSINT results for 'target@example.com':"
echo ""
sleep 0.4
echo "[+] Spotify        https://open.spotify.com/user/targetuser"
sleep 0.3
echo "[+] WordPress      https://wordpress.com/targetuser"
sleep 0.3
echo "[+] Gravatar       https://gravatar.com/targetuser"
sleep 0.3
echo "[+] Office365      email used"
sleep 0.5
echo "============================================================"
echo ""
sleep 1.5

echo "$ openosint username targetuser"
sleep 1.2

echo ""
echo "[*] Username scan: targetuser"
echo "[*] Timeout: 180s"
echo ""
sleep 1

echo "============================================================"
echo "===================== SCAN RESULTS ========================="
echo "============================================================"
echo "OSINT results for username 'targetuser':"
echo ""
sleep 0.3
echo "[+] GitHub         https://github.com/targetuser"
sleep 0.2
echo "[+] Twitter        https://twitter.com/targetuser"
sleep 0.2
echo "[+] Reddit         https://reddit.com/user/targetuser"
sleep 0.2
echo "[+] HackerNews     https://news.ycombinator.com/user?id=targetuser"
sleep 0.2
echo "[+] GitLab         https://gitlab.com/targetuser"
sleep 0.5
echo "============================================================"
echo ""
sleep 2