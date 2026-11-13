#!/usr/bin/env python3
"""Test the real Bash functions without running the host installer or services."""
import json
import os
from pathlib import Path
import shlex
import socket
import struct
import subprocess
import tempfile
import threading
import time
import unittest
from urllib.parse import unquote, urlsplit


SOURCE = (Path(__file__).resolve().parent / "install.sh").read_text()


def function(name):
    start = SOURCE.index(name + "() {")
    return SOURCE[start:SOURCE.index("\n}\n", start) + 3]


class PersonalSocks5Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="personal-socks5-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / "sing-box/conf/config"
        self.config.mkdir(parents=True)
        self.binary = self.root / "sing-box/sing-box"
        self.binary.write_text('#!/bin/bash\n[[ "$1 $2" == "generate uuid" ]] || exit 1\n'
                               'printf "%s\\n" "7870eeb9-80f5-42b5-af17-936f97cafc10"\n')
        self.binary.chmod(0o700)
        self.base = self.config / "base.json"
        self.base.write_text(json.dumps({
            "inbounds": [{"type": "mixed", "tag": "existing", "listen": "127.0.0.1",
                          "listen_port": 19080}],
            "outbounds": [{"type": "direct", "tag": "01_direct_outbound"}],
            "dns": {"servers": [{"type": "local", "tag": "local"}]},
        }))
        self.prelude = "\n".join(function(name) for name in (
            "normalizeSocks5Sources", "generateSocks5InboundConfig",
            "installPersonalSocks5", "singBoxInstall",
        )).replace("/etc/v2ray-agent", str(self.root))
        self.prelude += r'''
echoContent() { printf '%s\n' "$2"; }
for name in installSocks5InboundTools readInstallType readInstallProtocolType \
    readLastInstallationConfig unInstallSubscribe installTools handleXray \
    customPortFunction initTLSNginxConfig installTLS handleNginx removeCoreService \
    installSingBox installSingBoxService initSingBoxConfig cleanUp installCronTLS \
    handleSingBox showAccounts; do
    eval "$name() { printf '%s\n' '$name' >> '$TEST_CALLS'; }"
done
socks5PortAvailable() { return 0; }
socks5InboundShareConfig() { printf '%s\n' 'connection-details'; }
commitSocks5Inbound() {
    printf '%s\n' commit >> "$TEST_CALLS"
    generateSocks5InboundConfig "$TEST_CONFIG" "$2" "$3" "$4" "$5" "$6" "$7"
}
'''

    @staticmethod
    def free_port():
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]

    def run_bash(self, action):
        return subprocess.run(["bash", "-c", self.prelude + "\n" + action],
                              env={**os.environ, "TEST_CALLS": str(self.root / "calls"),
                                   "TEST_CONFIG": str(self.config)},
                              capture_output=True, text=True)

    def calls(self):
        path = self.root / "calls"
        return path.read_text().splitlines() if path.exists() else []

    def inbound(self):
        return json.loads((self.config / "20_socks5_inbounds.json").read_text())["inbounds"][0]

    def test_share_link_round_trips_credentials_and_endpoints(self):
        for listen, endpoint, username, password in (
            ("0.0.0.0", "140.238.66.52", "user", "secret"),
            ("::", "2001:db8::1", "a@b:/?#%", "密 码@:#/%"),
            ("proxy.example.com", "proxy.example.com", "user", "secret"),
            ("2001:db8::2", "2001:db8::2", "", ""),
        ):
            with self.subTest(listen=listen):
                path = self.config / "share.json"
                path.write_text(json.dumps({"inbounds": [{"listen": listen, "listen_port": 39527,
                    "users": [{"username": username, "password": password}]}]}))
                script = (function("socks5InboundShareConfig") +
                          '\nsocks5OutboundText() { printf "%s\\n" "$1"; }\n' +
                          'getPublicIP() { printf "%s\\n" ' + shlex.quote(endpoint) + '; }\n' +
                          'socks5InboundShareConfig ' + shlex.quote(str(path)))
                result = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                link = next(line for line in result.stdout.splitlines() if line.startswith("socks5://"))
                parsed = urlsplit(link)
                self.assertEqual((parsed.hostname, parsed.port), (endpoint, 39527))
                self.assertEqual(unquote(parsed.username or ""), username)
                self.assertEqual(unquote(parsed.password or ""), password)
                self.assertEqual(unquote(parsed.fragment), "SOCKS5-" + endpoint)
                exported = json.loads(result.stdout.splitlines()[-1])
                self.assertEqual((exported["server"], exported["username"], exported["password"]),
                                 (endpoint, username, password))

    def test_normal_install_adds_authenticated_socks_after_accounts(self):
        original = self.base.read_bytes()
        result = self.run_bash("singBoxInstall")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLess(self.calls().index("showAccounts"), self.calls().index("commit"))
        inbound = self.inbound()
        self.assertEqual((inbound["type"], inbound["listen"], inbound["listen_port"]),
                         ("socks", "0.0.0.0", 1080))
        self.assertTrue(inbound["users"][0]["username"])
        self.assertTrue(inbound["users"][0]["password"])
        self.assertEqual(self.base.read_bytes(), original)
        self.assertEqual((self.config / "20_socks5_inbounds.json").stat().st_mode & 0o777, 0o600)

    def test_failed_install_or_account_generation_does_not_add_socks(self):
        for failed in ("installTools", "installSingBox", "showAccounts"):
            with self.subTest(failed=failed):
                result = self.run_bash(f"{failed}() {{ return 1; }}\nsingBoxInstall")
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("commit", self.calls())

    def test_busy_default_port_uses_another_port(self):
        result = self.run_bash('socks5PortAvailable() { [[ "$1" != 1080 ]]; }\ninstallPersonalSocks5')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertGreaterEqual(self.inbound()["listen_port"], 10000)

    def test_all_busy_ports_and_failed_transaction_are_errors(self):
        for override in ("socks5PortAvailable() { return 1; }",
                         "commitSocks5Inbound() { return 1; }"):
            with self.subTest(override=override):
                result = self.run_bash(override + "\ninstallPersonalSocks5")
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("已就绪", result.stdout)

    def test_empty_generated_credential_never_commits(self):
        self.binary.write_text("#!/bin/bash\nexit 0\n")
        result = self.run_bash("installPersonalSocks5")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("commit", self.calls())

    def test_repeated_setup_keeps_existing_credentials(self):
        result = self.run_bash("installPersonalSocks5 && installPersonalSocks5")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls().count("commit"), 1)

    def test_existing_unauthenticated_socks_is_rejected(self):
        (self.config / "20_socks5_inbounds.json").write_text('{"inbounds":[{"users":[]}]}')
        result = self.run_bash("installPersonalSocks5")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("commit", self.calls())

    @unittest.skipUnless(os.environ.get("SOCKS5_TEST_BINARY"), "optional real sing-box binary")
    def test_real_core_loads_config_and_requires_authentication(self):
        real_binary = os.environ["SOCKS5_TEST_BINARY"]
        # Exercise the real random credential generator, not the fixed test stub.
        self.binary.write_text("#!/bin/bash\nexec " + shlex.quote(real_binary) + ' "$@"\n')
        result = self.run_bash("installPersonalSocks5")
        self.assertEqual(result.returncode, 0, result.stderr)
        inbound = self.inbound()
        inbound["listen"], inbound["listen_port"] = "127.0.0.1", self.free_port()
        (self.config / "20_socks5_inbounds.json").write_text(json.dumps({"inbounds": [inbound]}))
        merged = self.root / "merged.json"
        for args in (["merge", str(merged), "-C", str(self.config)], ["check", "-c", str(merged)]):
            checked = subprocess.run([real_binary, *args], capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stderr)
        with open(self.root / "core.log", "w") as log:
            core = subprocess.Popen([real_binary, "run", "-c", str(merged)], stdout=log, stderr=log)
            try:
                for attempt in range(100):
                    try:
                        with socket.create_connection(("127.0.0.1", inbound["listen_port"]), timeout=0.1):
                            break
                    except OSError:
                        if core.poll() is not None:
                            self.fail((self.root / "core.log").read_text())
                        time.sleep(0.02)
                user = inbound["users"][0]
                for password, expected in ((user["password"], b"\x01\x00"), ("wrong", b"\x01\x01")):
                    with socket.create_connection(("127.0.0.1", inbound["listen_port"]), timeout=3) as sock:
                        sock.sendall(b"\x05\x01\x02")
                        self.assertEqual(sock.recv(2), b"\x05\x02")
                        name, secret = user["username"].encode(), password.encode()
                        sock.sendall(b"\x01" + bytes([len(name)]) + name + bytes([len(secret)]) + secret)
                        response = sock.recv(2)
                        if password == "wrong":
                            self.assertNotEqual(response, b"\x01\x00")
                            continue
                        self.assertEqual(response, expected)
                        with socket.socket() as target:
                            target.bind(("127.0.0.1", 0))
                            target.listen(1)
                            target.settimeout(5)
                            def reply():
                                with target.accept()[0] as connection:
                                    connection.recv(4096)
                                    connection.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK")
                            worker = threading.Thread(target=reply, daemon=True)
                            worker.start()
                            sock.sendall(b"\x05\x01\x00\x01" + socket.inet_aton("127.0.0.1") +
                                         struct.pack("!H", target.getsockname()[1]))
                            self.assertEqual(sock.recv(10)[:2], b"\x05\x00")
                            sock.sendall(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
                            self.assertIn(b"200 OK", sock.recv(4096))
                            worker.join(timeout=5)
                with socket.create_connection(("127.0.0.1", inbound["listen_port"]), timeout=3) as sock:
                    sock.sendall(b"\x05\x01\x00")
                    self.assertNotEqual(sock.recv(2), b"\x05\x00")
            finally:
                core.terminate()
                core.wait(timeout=5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
