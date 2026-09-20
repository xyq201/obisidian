#!/usr/bin/env bash
# =============================================================================
# push-via-api.sh — git 协议被出网代理阻断时的兜底推送（走 api.github.com Git Data API）
# 触发场景：git push 反复失败（代理对 github.com 前端间歇性 TLS 拦截），但 api.github.com 可达。
# 流程：本地先提交 → 读远程 HEAD → 为每个差异文件造 blob → 基于 base_tree 建 tree →
#       建 commit → 更新 refs/heads/main → 本地 fetch+reset 对齐（内容一致，无丢失）。
# 用法：bash push-via-api.sh "commit message"
# =============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; cd "$REPO_DIR"
REPO="xyq201/obisidian"
BRANCH="main"
MSG="${1:-kb: API 兜底推送 $(date +%F)}"

TOK="${GITHUB_PAT:-}"
[ -z "$TOK" ] && [ -f "$HOME/.github_pat" ] && TOK="$(cat "$HOME/.github_pat")"
[ -n "$TOK" ] || { echo "[api] 错误：无 GITHUB_PAT 且 ~/.github_pat 不存在" >&2; exit 5; }

api() { curl -sS -m 30 -H "Authorization: Bearer $TOK" -H "Accept: application/vnd.github+json" "$@"; }
jqpy() { local s="$1"; shift; python3.11 -c "$s" "$@"; }  # 透传全部参数给 python sys.argv

# 0. 先本地提交（无改动则跳过）
if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -m "$MSG" >/dev/null
fi

# 1. 差异文件（写临时文件保留 -z 的 NUL 分隔，防多文件被拼接；null 分隔防文件名含空格/中文）
git fetch origin main --quiet 2>/dev/null || true
DIFF_Z="$(mktemp)"
if ! git diff --name-only -z origin/main..HEAD > "$DIFF_Z" 2>/dev/null || [ ! -s "$DIFF_Z" ]; then
  git show --name-only -z --pretty=format: HEAD 2>/dev/null > "$DIFF_Z" || true
fi
if [ ! -s "$DIFF_Z" ]; then echo "[api] 本地与 origin/main 无差异，无需兜底"; rm -f "$DIFF_Z"; exit 0; fi

for ATTEMPT in 1 2 3; do
  # 2. 远程 HEAD 与 base tree
  BASE_SHA=$(api "https://api.github.com/repos/$REPO/git/ref/heads/$BRANCH" | jqpy "import sys,json;print(json.load(sys.stdin)['object']['sha'])")
  BASE_TREE=$(api "https://api.github.com/repos/$REPO/git/commits/$BASE_SHA" | jqpy "import sys,json;print(json.load(sys.stdin)['tree']['sha'])")
  echo "[api] 远程 HEAD=$BASE_SHA base_tree=$BASE_TREE (第 $ATTEMPT 次)"

  # 3. 造 blobs + tree 条目（删除的文件用 sha:null）
  ENTRIES="[]"
  while IFS= read -r -d '' f; do
    [ -n "$f" ] || continue
    if [ -f "$f" ]; then
      B64=$(base64 -w0 "$f")
      BSHA=$(api -X POST "https://api.github.com/repos/$REPO/git/blobs" -d "{\"content\":\"$B64\",\"encoding\":\"base64\"}" \
             | jqpy "import sys,json;d=json.load(sys.stdin);print(d.get('sha') or ('ERR:'+str(d.get('message'))))")
      case "$BSHA" in ERR:*) echo "[api] blob 失败: $f $BSHA" >&2; exit 6;; esac
      MODE=100644; [ -x "$f" ] && MODE=100755
    else
      BSHA="null"; MODE=100644
    fi
    ENTRIES=$(printf '%s' "$ENTRIES" | jqpy "import sys,json
e=json.load(sys.stdin)
e.append({'path': sys.argv[1], 'mode': sys.argv[2], 'type':'blob', 'sha': sys.argv[3]})
print(json.dumps(e))" "$f" "$MODE" "$BSHA")
  done < "$DIFF_Z"
  rm -f "$DIFF_Z"
  echo "[api] 待推送文件数: $(printf '%s' "$ENTRIES" | jqpy "import sys,json;print(len(json.load(sys.stdin)))")"

  # 4. tree（基于远程 base_tree，冲突风险低）
  NEW_TREE=$(api -X POST "https://api.github.com/repos/$REPO/git/trees" -d "{\"base_tree\":\"$BASE_TREE\",\"tree\":$ENTRIES}" \
           | jqpy "import sys,json;d=json.load(sys.stdin);print(d.get('sha') or ('ERR:'+str(d.get('message'))))")
  case "$NEW_TREE" in ERR:*) echo "[api] tree 失败: $NEW_TREE" >&2; if [ "$ATTEMPT" = 3 ]; then exit 7; else sleep 5; continue; fi;; esac

  # 5. commit
  PAYLOAD=$(jqpy "import sys,json
print(json.dumps({'message': sys.argv[1], 'tree': sys.argv[2], 'parents':[sys.argv[3]]}))" "$MSG" "$NEW_TREE" "$BASE_SHA")
  NEW_COMMIT=$(api -X POST "https://api.github.com/repos/$REPO/git/commits" -d "$PAYLOAD" \
             | jqpy "import sys,json;d=json.load(sys.stdin);print(d.get('sha') or ('ERR:'+str(d.get('message'))))")
  case "$NEW_COMMIT" in ERR:*) echo "[api] commit 失败: $NEW_COMMIT" >&2; if [ "$ATTEMPT" = 3 ]; then exit 8; else sleep 5; continue; fi;; esac

  # 6. 更新 ref（非强制；远程若前移则重试整个流程）
  REF_OUT=$(api -X PATCH "https://api.github.com/repos/$REPO/git/refs/heads/$BRANCH" -d "{\"sha\":\"$NEW_COMMIT\",\"force\":false}" \
          | jqpy "import sys,json;d=json.load(sys.stdin);print(d.get('object',{}).get('sha') or ('ERR:'+str(d.get('message'))))")
  case "$REF_OUT" in
    ERR:*) echo "[api] ref 更新失败(远程可能前移): $REF_OUT"; if [ "$ATTEMPT" = 3 ]; then exit 9; else sleep 5; continue; fi ;;
    *) echo "[api] ✅ 兜底推送成功：$REF_OUT"; BREAK_OK=1; break ;;
  esac
done
[ "${BREAK_OK:-0}" = 1 ] || { echo "[api] 3 次尝试均失败" >&2; exit 10; }

# 7. 本地对齐远程（内容一致；丢弃已被 API 提交替代的本地领先提交）
git fetch origin main --quiet
git reset --hard "origin/$BRANCH" --quiet
echo "[api] 本地已对齐远程 $(git rev-parse --short HEAD)，完成。"
