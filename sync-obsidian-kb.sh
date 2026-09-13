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
ensure_hosts() {
  local cur; cur=$(getent hosts github.com 2>/dev/null | awk '{print $1; exit}')
  # 候选放行 IP（代理放行网段，随出网策略可增减）
  local cands="140.82.114.3 140.82.116.3 140.82.121.3 140.82.112.3 140.82.113.3 140.82.113.5 140.82.113.6"
  local ok=""
  # 先测当前解析是否可达
  if [ -n "$cur" ] && curl -sS -m 10 --resolve "github.com:443:$cur" -o /dev/null "https://github.com" 2>/dev/null; then
    ok="$cur"
  fi
  # 否则遍历候选，挑第一个可达的
  if [ -z "$ok" ]; then
    local ip
    for ip in $cands; do
      if curl -sS -m 8 --resolve "github.com:443:$ip" -o /dev/null "https://github.com" 2>/dev/null; then ok="$ip"; break; fi
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

# ---- 2. 连通性自检 ----
check_conn() {
  if ! curl -sS -m 12 -o /dev/null "https://api.github.com" 2>/dev/null; then
    echo "[sync] 错误：无法连通 GitHub（api.github.com）。请检查网络/代理/PAT。" >&2
    exit 3
  fi
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
check_conn
ensure_gh

case "$MODE" in
  pull)
    echo "[sync] git pull --rebase origin main"
    git pull --rebase origin main
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
    git push origin main
    echo "[sync] 已推送：$(git rev-parse --short HEAD)"
    ;;
  *)
    echo "用法: $0 {pull|push|sync|status} [提交说明]" >&2
    exit 2
    ;;
esac
echo "[sync] done."
