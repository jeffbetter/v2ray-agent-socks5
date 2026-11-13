"""Exercise installer startup without changing packages or SELinux on the host."""
import subprocess
import unittest

from test_personal_socks5 import function


class PreflightTests(unittest.TestCase):
    def run_shell(self, code, user_input=""):
        return subprocess.run(["bash", "-c", code], input=user_input,
                              capture_output=True, text=True)

    def dependencies(self, manager, missing="wget jq", fail=False, stays_missing=False):
        code = function("prepareMenuDependencies")
        # Use synthetic certificates so these tests are portable to macOS.
        code = code.replace("[[ ! -s /etc/ssl/certs/ca-certificates.crt && ! -s /etc/pki/tls/certs/ca-bundle.crt ]]", "false")
        code = code.replace("[[ -s /etc/ssl/certs/ca-certificates.crt || -s /etc/pki/tls/certs/ca-bundle.crt ]]", "true")
        code = code.replace('[[ "${EUID}" -eq 0 ]]', 'true')
        prelude = """
ready=false
command() {
    [[ "$1" == -v ]] || return 1
    case "$2" in
        apt-get|dnf|yum|apk) [[ "$2" == "$manager" ]] ;;
        *) if [[ "$ready" == false && " $missing " == *" $2 "* ]]; then return 1; fi ;;
    esac
}
"""
        prelude += f"manager={manager!r}\nmissing={missing!r}\n"
        for name in ("apt-get", "dnf", "yum", "apk"):
            prelude += name + '() { printf "PKG:%s\\n" "$*"; '
            prelude += "return 42; }\n" if fail else (
                ("true; }\n" if stays_missing else "[[ $1 == update ]] || ready=true; }\n"))
        return self.run_shell(prelude + code + "\nprepareMenuDependencies")

    def test_each_package_manager_installs_missing_tools_in_one_batch(self):
        for manager, expected in (("apt-get", "PKG:install -y wget jq"),
                                  ("dnf", "PKG:install -y wget jq"),
                                  ("yum", "PKG:install -y wget jq"),
                                  ("apk", "PKG:add --no-cache wget jq")):
            with self.subTest(manager=manager):
                result = self.dependencies(manager)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(expected, result.stdout)
                self.assertEqual(result.stdout.count("PKG:"), 2 if manager == "apt-get" else 1)

    def test_existing_tools_skip_package_operations(self):
        result = self.dependencies("dnf", missing="")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("PKG:", result.stdout)

    def test_package_failure_or_still_missing_tool_stops_startup(self):
        for kwargs in ({"fail": True}, {"stays_missing": True}):
            result = self.dependencies("dnf", **kwargs)
            self.assertNotEqual(result.returncode, 0)

    def test_debian_which_package_mapping(self):
        result = self.dependencies("apt-get", missing="which")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PKG:install -y debianutils", result.stdout)

    def test_enforcing_changes_only_after_explicit_yes(self):
        for answer in ("y\n", "n\n", ""):
            with self.subTest(answer=answer):
                code = """
mode=Enforcing
echoContent() { printf '%s\\n' "$2"; }
getenforce() { printf '%s\\n' "$mode"; }
setenforce() { printf 'SET:%s\\n' "$1"; mode=Permissive; }
""" + function("checkCentosSELinux") + "\ncheckCentosSELinux"
                result = self.run_shell(code, answer)
                if answer.startswith("y"):
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("SET:0", result.stdout)
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn("SET:", result.stdout)

    def test_permissive_and_disabled_require_no_prompt_or_change(self):
        for mode in ("Permissive", "Disabled"):
            code = f"getenforce() {{ echo {mode}; }}\n"
            code += "setenforce() { echo UNEXPECTED; return 1; }\n"
            code += function("checkCentosSELinux") + "\ncheckCentosSELinux"
            result = self.run_shell(code)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
