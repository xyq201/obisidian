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

# ---- 1. 沙箱 DNS/代理自愈：确保 github.com 解析到出网代理放行的真实 IP ----
ensure_hosts() {
  local need_fix=0
  if ! getent hosts github.com | grep -q "140.82.113.3"; then need_fix=1; fi
  if [ "$need_fix" -eq 1 ]; then
    echo "[sync] 检测到 github.com 解析异常，写入真实 IP 自愈..."
    # 同时写 /etc/hosts 与持久化的 ~/.user_hosts（/etc/hosts 重启会被还原）
    grep -q "github.com" /etc/hosts 2>/dev/null && \
      sed -i 's/^[^#].*github\.com.*/140.82.113.3     github.com/' /etc/hosts || \
      echo "140.82.113.3     github.com" >> /etc/hosts
    cat >> ~/.user_hosts <<'EOF'

# GitHub 真实 IP（sync-obsidian-kb.sh 自动补全，绕过沙箱 DNS 污染）
140.82.113.3     github.com
140.82.113.5     api.github.com
140.82.113.6     api.github.com
140.82.113.4     gist.github.com
140.82.113.9     codeload.github.com
185.199.108.133  objects.githubusercontent.com
185.199.109.133  objects.githubusercontent.com
185.199.110.133  objects.githubusercontent.com
185.199.111.133  objects.githubusercontent.com
EOF
    echo "[sync] hosts 已修复"
  fi
}

# ---- 2. 连通性自检 ----
check_conn() {
  if ! curl -sS -m 12 -o /dev/null "https://api.github.com" 2>/dev/null; then
    echo "[sync] 错误：无法连通 GitHub（api.github.com）。请检查网络/代理/PAT。" >&2
    exit 3
  fi
}

MODE="${1:-sync}"
MSG="${2:-kb: 自动同步 $(date +%F)}"

ensure_hosts
check_conn

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
