# 飞书交付细节（站 6、7）

本文件只在执行「站 6 飞书导入」「站 7 回读核验与回执」时读取。目标位置：个人云盘（我的文档）根目录，导入为飞书在线文档（docx 类型）。

## 前置检查

```bash
lark-cli auth status          # 确认 user identity ready；缺权限按缺失 scope 处理
# 必需 scope：docs:document:import、drive:file:upload、drive:drive.metadata:readonly
```

## 导入命令

```bash
# 1. 先检查同名（避免重复文档）
lark-cli drive +search --query "<标题>"

# 2. dry-run 检查请求形状
lark-cli drive +import --file "<成品docx>" --type docx --name "<标题>" --dry-run

# 3. 真实导入到个人云盘根目录
lark-cli drive +import --file "<成品docx>" --type docx --name "<标题>"
```

- 大文件自动走 multipart 上传，无需手工分片。
- 导入是异步任务：返回 `ticket` 时用 `lark-cli drive +task_result --ticket <ticket>` 轮询到完成，拿到 `document_id` / `url`。
- 取真实链接：`lark-cli drive +inspect <token或url>` 展开类型与规范 token；`/docx/<token>` 直接可用，`/wiki/` 链接保留即可，两者都写进回执。

## 在线回读核验（站 7）

导入完成后，回读在线文档做抽查（不全量重读）：

1. 标题与正文第一段存在；
2. 三大部分标题存在：「第一部分｜三级笔记」「第二部分｜概念提取」「第三部分｜原文」；
3. 每部分至少 1 个关键锚点：三级笔记的主题句或一级标题、概念提取的核心概念名、原文的起始句；
4. 笔记／概念里嵌入的图片抽查 1–3 张（能读回或导出看到图）。

可用：

```bash
# 读 docx 内容（lark-doc 的读取方法）
lark-cli docs +fetch --url "<链接>"          # 按本机 lark-doc skill 的实际命令形态执行
# 或导出为 docx 后抽查段落
lark-cli drive +export <token> --type docx
```

命令形态以本机 `lark-doc` / `lark-drive` skill 为准，不硬编码。

## 回执模板（FEISHU_DELIVERY_RECEIPT.md）

```markdown
# 飞书交付回执

- 交付时间：YYYY-MM-DD
- 飞书标题：<标题>
- 飞书链接：<链接>
- 导入状态：<全部上传成功，N 个任务，大小> 或 <部分失败·原因>
- 在线正文回读：标题、三大部分、关键锚点 <均存在 / 缺失项>
- 在线图片回读：<N 张抽查均存在 / 缺失项>
- 原链接处理：<仅作上下文参考，未修改原页面 / 覆盖说明>
- 本地成品 SHA-256：<与 manifest.json 一致的散列>

说明：飞书导入成功仅证明云端对象已创建并可回读；不等同于用户最终验收。
```

## 失败处理

| 现象 | 处理 |
|---|---|
| 导入返回 ticket 但无结果 | `+task_result` 轮询；超时后重试导入（同一标题会新建，先查重） |
| 权限不足（`permission denied`） | 报缺失 scope，需要时走 `lark-shared` 重新授权，不绕过 |
| 标题重名 | 报告既有链接，由用户决定新建或跳过，不覆盖 |
| 导入成功但回读缺段落 | 保留在线文档，标记 `Held`，报告差异，不擅自改线上内容 |
| 文档过大导入失败 | 报告建议拆分为笔记／概念／原文三份再导，由用户选择 |

## 边界

- 导入成功 ≠ 用户验收；回执里必须写边界说明。
- 不做导入之外的线上操作（移动、改名、删旧、改权限均需用户另要求）。
- 目标从「我的文档根目录」改为文件夹或知识空间时，需要 `--folder-token` 或 wiki 创建节点，先向用户取目标再执行。