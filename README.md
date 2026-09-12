# 知识库 / Knowledge Base

这是一个 **兼容 Obsidian 的 Markdown 知识库**。设计目标：

- 你可以**随时、用最顺手的方式**把零散信息丢给我（一句话、一段摘录、一个网页链接、一份截图文字、一段对话要点）。
- 我负责把碎片**收集 → 归纳 → 拼接成结构化主题笔记**，而不是让你自己整理。
- 所有产出都是**标准 Markdown + 相对链接**，可在 Obsidian、VS Code、GitHub、任何文本编辑器里打开与转移，不锁死在某个工具里。

## 目录结构

```
knowledge-base/
├─ Index.md            # MOC 内容地图（入口，定期维护）
├─ Inbox/              # 原始碎片（你发来的零碎信息，原样暂存）
├─ Topics/             # 归纳后的主题笔记（知识库主体）
├─ Assets/             # 附件（图片等，按需）
└─ .obsidian/          # Obsidian 配置，让本文件夹可直接当作仓库打开
```

## 工作流程

1. **捕获（Capture）** — 你把碎片发给我。我打上时间戳、来源，存入 `Inbox/YYYY-MM-DD-<主题>.md`。
2. **归纳（Synthesize）** — 当某个主题积累足够碎片，或你要求时，我把相关碎片拼接、去重、提炼成 `Topics/<主题>.md`。
3. **索引（Index）** — 我在 `Index.md` 维护一张内容地图，按主题/时间链接所有笔记，方便浏览与回溯。
4. **导出（Export）** — 产出可转移的 `.md` 文档。可整体作为 Obsidian 仓库导入，也可单篇复制。

## 碎片怎么收集最顺手（任选）

- 直接发**文字 / 想法 / 摘录**
- 发**网页链接**，我帮你抓取并摘要（需要联网）
- 粘贴**截图里的文字**或**批量文本**
- 说“把今天这些整理一下”，我做一次汇总

## 链接约定

- 内部链接使用**标准 Markdown 相对链接** `[主题](Topics/xxx.md)`，保证在任何编辑器可读、可转移。
- 每篇笔记含 `tags:` 与 `来源:` 字段，便于检索与溯源。

---

## 与 GitHub 同步（Obsidian Git）

本知识库已托管在 GitHub：**https://github.com/xyq201/obisidian** ，可直接作为 Obsidian 仓库打开并双向同步。

**在桌面 Obsidian 中开启自动同步：**

1. 设置 → 第三方插件 → 关闭「安全模式」→ 浏览 → 搜索 **Obsidian Git** → 安装并启用。
2. 本仓库已预置自动同步配置（`.obsidian/plugins/obsidian-git/data.json`）：启用后每 10 分钟自动 `pull` + `push`，关闭 Obsidian 时也会推送。
3. 首次启用若提示插件缺失，点「重新装载/启用」一次即可（插件本体由 Obsidian 插件市场下载）。

**在终端/CI 中同步：**

```bash
./sync-obsidian-kb.sh pull                 # 仅拉取最新
./sync-obsidian-kb.sh sync "提交说明"       # 先 rebase 拉取，再提交本地改动并推送
./sync-obsidian-kb.sh status               # 查看本地/远程差异
```

> 脚本自带沙箱 DNS/代理自愈（仓库 `github.com` 解析异常时自动写入真实 IP），
> 并依赖已登录的 `gh`/`git` 凭证。请勿把 PAT 写进仓库 remote。

_本知识库由 OpenClaw 助手维护，并由 WorkBuddy 接续 GitHub 同步。碎片进来是原料，主题是成品。_
