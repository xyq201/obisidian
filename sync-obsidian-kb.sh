#!/usr/bin/env bash
# =============================================================================
# sync-obsidian-kb.sh — Obsidian 知识库（xyq201/obisidian）双向同步脚本
# 用途：在沙箱/本机保持本地 vault 与 GitHub 一致
# 用法：
#   ./sync-obsidian-kb.sh pull            # 仅拉取最新（rebase）
#   ./sync-obsidian-kb.sh push "提交说明" # 提交本地改动并推送
#   ./sync-obsidian-kb.sh sync "提交说明" # 先 pull --rebase 再提交+推送（默认）
#   ./sync-obsidian-kb.sh status          # 查看本地/远程差异
# 注意：仓库 remote 不含 token（已抹除）；本脚本依赖已登录的 gh / git 凭证。
# =============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

# 沙箱出网代理对 git 大文件传输偶发限速/中断，放宽 http 限速阈值避免被掐断
git config http.lowSpeedLimit 0 2>/dev/null
git config http.lowSpeedTime 0 2>/dev/null
git config http.postBuffer 524288000 2>/dev/null

# ---- 1. 沙箱 DNS/代理自愈：动态探测出网代理放行的 GitHub 前端 IP 并覆盖写 ----
# 关键：用真实 git 上传包流量（info/refs?service=git-upload-pack）测连通，
#       而非 tiny 首页请求——避免挑中"能过小请求、扛不住推送"的假活 IP。
REPO_PATH="$(git config --get remote.origin.url 2>/dev/null | sed -E 's#https://github.com/##; s#\.git$##')"
REPO_PATH="${REPO_PATH:-xyq201/obisidian}"
gh_probe() { # $1=ip；返回0表示可稳定承载真实 git 流量（含重试，避免瞬时限流误判）
  local ip="$1" s=0 try=0
  for try in 1 2 3; do
    s=$(curl -sS --retry 1 -m 15 --resolve "github.com:443:$ip" -o /tmp/_ghprobe \
          "https://github.com/${REPO_PATH}.git/info/refs?service=git-upload-pack" 2>/dev/null \
          && wc -c < /tmp/_ghprobe)
    [ "${s:-0}" -gt 300 ] && return 0
  done
  return 1
}
ensure_hosts() {
  local cur; cur=$(getent hosts github.com 2>/dev/null | awk '{print $1; exit}')
  # 优先 proven IP：~/.user_hosts 中已验证稳定的 github.com 解析（持久、可靠，避免盲选假活 IP）
  local proven=""; proven=$(awk '$2=="github.com"{print $1; exit}' ~/.user_hosts 2>/dev/null)
  local cands="140.82.116.3 140.82.112.3 140.82.113.3 140.82.114.3 140.82.121.3 140.82.113.5 140.82.113.6"
  [ -n "$proven" ] && cands="$proven $cands"
  local ok=""
  # 先测当前解析是否可达（真实 git 流量 + 重试）
  if [ -n "$cur" ] && gh_probe "$cur"; then
    ok="$cur"
  fi
  # 否则遍历候选（proven 优先），挑第一个能稳定承载 git 流量的
  if [ -z "$ok" ]; then
    local ip
    for ip in $cands; do
      if gh_probe "$ip"; then ok="$ip"; break; fi
    done
  fi
  if [ -z "$ok" ]; then
    echo "[sync] 警告：所有候选 IP 均不可达，保留原解析（github.com=$cur）。" >&2
    return 0
  fi
  if [ "$cur" = "$ok" ]; then return 0; fi
  echo "[sync] 自愈：github.com $cur -> $ok"
  local tmp; tmp=$(mktemp)
  # /etc/hosts 为 bind mount，sed -i 不可用，改用"过滤旧行 + 追加 + 覆盖写"
  awk '$2!="github.com"' /etc/hosts > "$tmp" 2>/dev/null || true
  echo "$ok    github.com" >> "$tmp"
  cat "$tmp" > /etc/hosts
  awk '$2!="github.com"' ~/.user_hosts > "$tmp" 2>/dev/null || true
  echo "$ok    github.com" >> "$tmp"
  cat "$tmp" > ~/.user_hosts
  rm -f "$tmp"
  echo "[sync] hosts 已修复为 $ok"
}

# ---- 2. 连通性自检（带重试：代理对 GitHub 前端为间歇性瞬时限流，单次探测会误杀）----
check_conn() {
  local ip; ip=$(getent hosts github.com 2>/dev/null | awk '{print $1; exit}')
  local ok=0 i
  # api.github.com 连通（重试 3 次）
  for i in 1 2 3; do
    if curl -sS -m 15 -o /dev/null "https://api.github.com" 2>/dev/null; then ok=1; break; fi
  done
  [ "$ok" = 0 ] && { echo "[sync] 警告：暂无法连通 GitHub（api.github.com），稍后实际 git 操作会重试。" >&2; return 1; }
  # github.com 主站（用当前解析 IP + --resolve，重试 3 次，容忍瞬时限流）
  ok=0
  for i in 1 2 3; do
    if curl -sS -m 15 --resolve "github.com:443:${ip}" -o /dev/null "https://github.com/${REPO_PATH}.git/info/refs?service=git-upload-pack" 2>/dev/null; then ok=1; break; fi
  done
  [ "$ok" = 0 ] && { echo "[sync] 警告：github.com 主站暂不可达，实际 git 操作将重试/兜底。" >&2; return 1; }
}

# ---- 2.5 确保 gh 已登录（自动化独立会话可能无登录态）----
ensure_gh() {
  if gh auth status >/dev/null 2>&1; then
    return 0
  fi
  echo "[sync] 检测到 gh 未登录，尝试自动登录..."
  local tok="${GITHUB_PAT:-}"
  if [ -z "$tok" ] && [ -f "$HOME/.github_pat" ]; then tok="$(cat "$HOME/.github_pat")"; fi
  if [ -z "$tok" ]; then
    echo "[sync] 错误：无 GITHUB_PAT 且 ~/.github_pat 不存在，无法登录 GitHub。" >&2
    exit 5
  fi
  printf '%s' "$tok" | gh auth login --with-token 2>&1 | head -3
  gh auth setup-git 2>&1 | head -1
  echo "[sync] gh 自动登录完成"
}

MODE="${1:-sync}"
MSG="${2:-kb: 自动同步 $(date +%F)}"

ensure_hosts
check_conn || true
ensure_gh

case "$MODE" in
  pull)
    echo "[sync] git pull --rebase origin main"
    git pull --rebase origin main
    ;;
  hosts)
    # 仅重新探测可用 IP 并写回 /etc/hosts + ~/.user_hosts（供推送循环轮换，不报错退出）
    ensure_hosts
    exit 0
    ;;
  status)
    echo "[sync] 本地 vs 远程："
    git fetch origin main --quiet
    git log --oneline --left-right --graph HEAD...origin/main | head -20
    git status -sb
    ;;
  push|sync)
    # 先提交本地改动（clean tree），再 rebase 拉取，最后推送 —— 避免 pull 因脏工作树被拒
    if [ -n "$(git status --porcelain)" ]; then
      echo "[sync] 提交本地改动..."
      git add -A
      git commit -m "$MSG" >/dev/null
    fi
    echo "[sync] git pull --rebase origin main"
    git pull --rebase origin main || { echo "[sync] pull/rebase 失败，请手动解决冲突后重试。" >&2; exit 4; }
    # 重试推送：出网代理对 GitHub 前端为间歇性瞬时限流，单次 push 易被 GnuTLS 中断
    n=0; ok=1
    for n in 1 2 3 4 5; do
      if git push origin main 2>/tmp/_pusherr; then ok=0; echo "[sync] push 成功（第 $n 次）"; break; fi
      echo "[sync] push 第 $n 次失败：$(tail -2 /tmp/_pusherr)"
      ensure_hosts   # 重新探测当前可用 IP 写回 /etc/hosts
      sleep 5
    done
    [ "$ok" = 0 ] || { echo "[sync] push 反复失败，请手动重试。" >&2; exit 6; }
    echo "[sync] 已推送：$(git rev-parse --short HEAD)"
    ;;
  *)
    echo "用法: $0 {pull|push|sync|status} [提交说明]" >&2
    exit 2
    ;;
esac
echo "[sync] done."
