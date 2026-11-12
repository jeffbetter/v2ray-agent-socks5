# v2ray-agent：安装 sing-box 后自动添加 SOCKS5

这是 [mack-a/v2ray-agent](https://github.com/mack-a/v2ray-agent) 的个人定制版，保留原作者署名和 AGPL-3.0 许可证。

## 个人版本安装步骤

Ubuntu / Debian 使用 root 执行：

```bash
apt update && apt install -y curl ca-certificates &&
curl -fL https://raw.githubusercontent.com/jeffbetter/v2ray-agent-socks5/master/install.sh -o /root/install.sh &&
chmod 700 /root/install.sh && /root/install.sh
```

选择 **1.安装 → 2.sing-box**，继续按原流程设置域名、证书等。普通安装成功后，脚本自动添加 SOCKS5，不需要再进分流菜单。

- 监听公网 IPv4 `0.0.0.0`，优先使用 TCP `1080`；如端口已占用，自动选择空闲高位端口。
- 强制用户名和密码认证，每次新建入站生成随机 UUID，同时作为用户名和密码，不内置固定密码。
- 安装结束显示端口、用户名、密码和连接 JSON。允许所有 IPv4 来源、所有目标，DNS 使用 IPv4。
- 复用原有 sing-box 核心；配置先校验，失败时使用上游事务回滚机制恢复添加 SOCKS5 前的配置。
- 如有云安全组，请放行安装结果显示的 TCP 端口。SOCKS5 自身不提供传输加密。
- 可通过 `vasma → 11 → 4 → 2 → 4` 再次查看 SOCKS5 连接信息；普通重新安装会重新生成入站及账号。
- 菜单 `17.更新脚本` 从本仓库更新，以保留定制功能。其他核心、组合安装、Reality 独立安装及 Docker 流程沿用上游行为。

修改日期：2026-11-12。验证脚本：`python3 test_personal_socks5.py`。尚未进行 Linux VPS 上的域名、证书与完整安装实测。

---

# 上游项目说明

- [感谢 JetBrains 提供的非商业开源软件开发授权](https://www.jetbrains.com/?from=v2ray-agent)


[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Telegram Channel](https://img.shields.io/badge/Telegram-Channel-blue)](https://t.me/v2rayAgentChannel)
[![Telegram Group](https://img.shields.io/badge/Telegram-Group-blue)](https://t.me/technologyshare)
[![Official Website](https://img.shields.io/badge/Website-v2ray--agent.com-blue)](https://www.v2ray-agent.com/)
[![English Version](https://img.shields.io/badge/English-Version-blue)](documents/en/README_EN.md)

基于 Bash 的 Xray-core / sing-box 安装与管理脚本，支持普通主机部署和 Docker Reality 独立部署。

## 功能

*   **多核心支持:** 支持 Xray-core 和 sing-box，可按需安装单核心或组合使用.
*   **多协议支持:** 支持 VLESS（TLS、Reality、XHTTP）、VMess、Trojan、Hysteria2、Tuic、NaiveProxy、AnyTLS，以及独立 SOCKS5 入站.
*   **TLS 与 Reality:** TLS 协议可通过 acme.sh 自动申请和续订证书；Reality 支持无域名部署.
*   **易于管理:** 提供菜单管理用户、端口、配置、核心版本、日志和证书，并支持二维码及客户端节点信息输出.
*   **订阅支持:** 生成和管理订阅链接，支持远程订阅配置.
*   **分流管理:** 提供 WARP/WireGuard（IPv4/IPv6）、IPv6、SOCKS5、DNS、VMess+WS、SNI 反向代理等分流能力，可用于流媒体等场景.
*   **网络策略管理:** 支持 Hysteria2 端口跳跃、域名黑名单和 BT/P2P 下载限制.
*   **Docker Reality:** 无需域名即可通过 Docker 部署 VLESS-Reality，支持 Vision、XHTTP 或同时启用两种模式，并提供交互式和命令行参数模式.
*   **更多内容请访问[官方网站](https://www.v2ray-agent.com/categories/jiao-cheng)、[备用](https://www.592083.com/categories/jiao-cheng)、[X](https://x.com/v2rayagent)**

## 环境要求

*   **脚本版:** Linux、root 权限，支持 CentOS、Debian、Ubuntu 和 Alpine；支持 amd64/x86_64、arm64/aarch64.
*   **Docker Reality:** Linux、root 或 sudo 权限，以及正在运行的 Docker；脚本可在交互模式下提示安装 Docker.

## 快速开始

### 安装脚本版

```
curl -fL https://raw.githubusercontent.com/jeffbetter/v2ray-agent-socks5/master/install.sh -o /root/install.sh && chmod 700 /root/install.sh && /root/install.sh
```

### 使用

安装后，运行以下命令可再次打开管理菜单:

```
vasma
```

### 安装Docker版
```
wget -P /root -N --no-check-certificate "https://raw.githubusercontent.com/mack-a/v2ray-agent/master/shell/docker_reality.sh" && chmod 700 /root/docker_reality.sh && /root/docker_reality.sh
```

### 使用 

* [Docker Reality 使用说明](https://www.v2ray-agent.com/archives/019e1b57-92b3-70ab-8919-cdf8c0bb4fe9)
 
安装后，运行以下命令可再次打开管理菜单:

```
vasmad
```

## 文档和指南

*   [SOCKS5 入站与分流出站：简明教程](https://www.v2ray-agent.com/archives/01a1b212-d16c-743c-a4b1-d6150a948bda)

*   [八合一脚本从入门到精通](https://www.v2ray-agent.com/archives/1710141233)
*   [脚本快速搭建教程](https://www.v2ray-agent.com/archives/1682491479771)
*   [脚本使用注意事项](https://www.v2ray-agent.com/archives/1679931532764)
*   [脚本异常处理](https://www.v2ray-agent.com/archives/1684115970026)   
*   [VPS选购攻略](https://www.v2ray-agent.com/archives/1679975663984)
*   [垃圾VPS大救星，hysteria2最新协议一键搭建](https://www.v2ray-agent.com/archives/1697162969693)
*   [RackNerd低价 联通AS4837套餐，年付10美起](https://www.v2ray-agent.com/archives/racknerdtao-can-zheng-li-nian-fu-10mei-yuan)
*   [搬瓦工优质套餐推荐](https://www.v2ray-agent.com/archives/2023nian-ban-wa-gong-ji-fang-tui-jian)
*   [DMIT优质套餐推荐](https://www.v2ray-agent.com/archives/1679159868033)

## 社区与支持

*   **Telegram:** [频道](https://t.me/v2rayAgentChannel) | [群组](https://t.me/technologyshare)
*   **网站:** [官网](https://www.v2ray-agent.com/) | [备用](https://www.592083.xyz/)
*   **反馈:** [提交 issue](https://github.com/mack-a/v2ray-agent/issues)
*   **X:** [链接](https://x.com/v2rayagent)

## 捐赠

感谢您对开源项目的关注和支持。如果您觉得这个项目对您有帮助，欢迎通过以下方式进行捐赠。

*   [购买VPS捐赠](https://www.v2ray-agent.com/categories/vps)
*   [通过虚拟币向我捐赠](https://www.v2ray-agent.com/1679123834836)

## 许可证

本项根据 [AGPL-3.0 许可证](LICENSE) 授权.
