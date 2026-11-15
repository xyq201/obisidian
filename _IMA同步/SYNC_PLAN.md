# IMA 知识库 ⇄ GitHub 同步方案

> 生成日期：2026-11-15 ｜ 本次为无人值守定时任务，无用户应答，故按最合理默认推进，假设见下。

## 一、本次执行假设

用户请求为「同步 IMA 知识库和 GitHub 知识库的内容」。执行时遇到两个硬约束：

1. **GitHub 通道不可用**：连接器列表中 `github` 显示 `connected`，但实际调用报「工具未注册 / 服务端超时」，`gh` 未登录、无 `GH_TOKEN`、无本地仓库；重新连接的请求被系统挡回（客户端无法显示授权卡片）。
2. **无用户应答**：这是无人值守定时任务，无法询问目标仓库地址与同步方向。

因此采用如下**默认假设**推进，不盲目向未知仓库写入：

> 以唯一可访问的 **IMA 知识库为源**，导出全量清单与内容，打包成 GitHub 可直接推送的同步包；待 GitHub 连接恢复、并明确 `owner/repo` 与方向后，用包内脚本一键落地。

## 二、当前状态

| 项目 | 状态 |
|---|---|
| IMA 知识库 | ✅ 可访问，`ima_kb_BoQkXLT2` 全量 300 条已导出 |
| 本地归档 | ✅ `/workspace/知识库/`，32 个文件（11 篇 docx + 提炼 MD + 索引 + 备份） |
| GitHub 连接器 | ❌ 已连接但工具无法调用（索引未注册 / 资源读取超时） |
| 目标仓库 | ⚠️ 未提供 `owner/repo` |
| 同步方向 | ⚠️ 未明确，默认 `IMA → GitHub` |

## 三、同步包内容

| 文件 | 用途 |
|---|---|
| `manifest.json` | 机器可读全量清单（300 条，含 media_id / 类型 / 路径 / 时间 / 标签），供程序化比对 |
| `IMA内容清单.md` | 人类可读清单，按 15 个主题文件夹分组 |
| `知识库/` | 本地归档产物完整副本（32 文件），可直接入库 |
| `push_to_github.sh` | 一键推送脚本，参数化 `owner/repo/branch`，支持 gh CLI 与 token 双通道 |
| `SYNC_PLAN.md` | 本方案说明 |

## 四、两种同步方向的落地步骤

### 方向 A：IMA → GitHub（本次默认，异地备份 / 版本管理）

1. 恢复 GitHub：到 App 连接器设置重新授权，或本机执行 `gh auth login` / 设置 `GH_TOKEN`。
2. 确定仓库：`owner/repo`（不存在时脚本会自动创建私有仓库）。
3. 执行推送：
   ```bash
   cd /workspace/github-sync
   ./push_to_github.sh <owner> <repo> main "sync: IMA 周度归档 $(date +%F)"
   ```
4. 脚本会 clone 远端保留历史 → 覆盖为同步包内容 → commit → push，避免误删历史。

### 方向 B：GitHub → IMA（把仓库内容导入知识库）

1. 恢复 GitHub 后，用 `mcp__github__get_file_contents` 或 `gh api` 遍历仓库文件。
2. 对每份文件调用 IMA 的 `create_media` → 上传（预签名 URL 或 COS 手签）→ `add_knowledge`。
   - 参考已调通实现：`/root/.codebuddy/artifact/2f8a7d30-9c21-4f0b-1d60-b70dc4b6b000/sync15b.py`
   - md → `content_type: text/markdown`；去重策略 `DUPLICATE_NAME_STRATEGY_REPLACE`。
3. 用 `search_knowledge` 逐篇检索复验（列表接口曾出现假阴性，检索更可靠）。

### 方向 C：双向增量合并

- 以 `manifest.json` 的 `media_id` 与 GitHub 侧文件的路径/标题做主键比对。
- 新增/更新以「修改时间较新者」为准；冲突时保留双方版本并标记，不静默覆盖。
- 建议先跑 A 建立基线，再做周期性的差异同步。

## 五、IMA 内容概览（300 条）

| 类型 | 数量 |
|---|---|
| MARKDOWN | 177 |
| TXT | 81 |
| FOLDER | 18 |
| PDF | 13 |
| 微信文章 | 5 |
| WORD | 3 |
| EXCEL | 2 |
| PPT | 1 |

主要主题目录：原料代码库(50)、抗衰紧致(37)、控油祛痘(27)、抗氧化光保护(26)、保湿屏障(23)、舒缓抗敏(18)、基础基质表活(14)、合规安全(11)、美白淡斑(10) 等。

## 六、待办（需用户/环境配合）

1. **恢复 GitHub 连接**（硬前提）：App 连接器设置重新授权，或提供 `GH_TOKEN`。
2. **提供目标仓库** `owner/repo`。
3. **确认同步方向**：默认按方向 A 执行；如需 B/C 请告知。
4. 可选：将 `github-sync` 目录纳入每周日定时任务，实现 IMA ⇄ GitHub 自动双向同步。
