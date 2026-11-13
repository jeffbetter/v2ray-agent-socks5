#!/bin/sh
# Stable entry point: save a complete installer, then retain terminal input.
set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo '请使用 root 用户运行此命令' >&2
    exit 1
fi

# Do not replace an existing curl-minimal package just to download the installer.
if ! command -v bash >/dev/null 2>&1 ||
    { ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; }; then
    if command -v apt-get >/dev/null 2>&1; then
        apt-get update && apt-get install -y wget ca-certificates bash
    elif command -v dnf >/dev/null 2>&1; then
        dnf install -y wget ca-certificates bash
    elif command -v yum >/dev/null 2>&1; then
        yum install -y wget ca-certificates bash
    elif command -v apk >/dev/null 2>&1; then
        apk add --no-cache wget ca-certificates bash
    else
        echo '未找到受支持的包管理器，安装已停止' >&2
        exit 1
    fi
fi

installer=$(mktemp /root/.v2ray-agent-install.XXXXXX)
trap 'rm -f "$installer"' EXIT
trap 'exit 1' HUP INT TERM
url=https://raw.githubusercontent.com/jeffbetter/v2ray-agent-socks5/master/install.sh
if command -v curl >/dev/null 2>&1; then
    curl -fL --retry 3 --connect-timeout 15 "$url" -o "$installer"
else
    wget --tries=3 --timeout=30 -O "$installer" "$url"
fi
test -s "$installer"
bash -n "$installer"
chmod 700 "$installer"
mv -f "$installer" /root/install.sh
trap - EXIT HUP INT TERM
exec bash /root/install.sh
