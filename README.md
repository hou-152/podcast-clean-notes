# 播客洗稿溯源 · 直播转写 → 笔记 → 概念 → 飞书

一套给直播/课程转写用的内容加工 skill 族：把粗糙的 ASR 转写洗成给人读的干净稿，再顺链产出三级笔记与概念提取，最后打包成飞书文档交付。**每站可单独调用，也可链式串接**——站与站之间靠文件规约连接，不硬链。

## 安装

```bash
npx -y skills add hou-152/podcast-clean-notes -g --all
```

## 流水线

```
00 原始转写（腾讯会议/通义听悟导出）
   ↓ ① transcript-clean-provenance  洗稿溯源
01 清洗稿（干净、给人读）+ 修订记录 + 待对清单 + 结论行
   ↓ ② note-taking-pro              三级笔记
02 三级笔记（骨架＋血肉）
   ↓ ③ concept-learning            概念提取
03 概念提取（逐字 context＋费曼解释＋分层架构图）
   ↓ ④ course-feishu-pack          打包交付
飞书文档 + 交付回执
```

## Skill 一览

| Skill | 站 | 干什么 | 关键产物 |
|---|---|---|---|
| `transcript-clean-provenance` | ① | ASR 转写清洗成干净直播转写，并保持可审查的溯源链 | `01_*.md`＋修订记录＋待对清单＋结论行 |
| `note-taking-pro` | ② | 「骨架＋血肉」三级笔记 | `02_*.md` |
| `concept-learning` | ③ | 概念基石提取＋费曼解释＋Mermaid 架构图 | `03_*.md` |
| `course-feishu-pack` | ④ | DOCX 打包＋飞书导入＋回执 | `*_飞书导入版.docx`＋回执 |

> 总入口 `推敲`（Tuiqiao）在设计稿阶段：一句话＋一份转写即可串起全链（洗稿站停车人工确认、其余连跑）。首版随下次实战发布。

## 两道质量门（①站自带脚本，可复跑）

```bash
python3 skills/transcript-clean-provenance/scripts/clean_lint.py "<01 清洗稿>"
python3 skills/transcript-clean-provenance/scripts/trace_check.py "<00 原文>" "<01 清洗稿>"
python3 skills/transcript-clean-provenance/scripts/quote_gate.py "<01 清洗稿>" "<02/03 产出>"
```

- `clean_lint.py`：形状门——产物齐全、源哈希在、工具行清干净
- `trace_check.py`：覆盖门——零增删核对（字符清单覆盖＋体量比＋长块检测）
- `quote_gate.py`：引文门——笔记的引号内容必须逐字回溯清洗稿

## 设计原则

- **零删减**：清洗只修错别字、断句、重复、口误；不改写、不压缩、不总结
- **不猜**：无法确证的内容原样保留并标注，一条不猜改
- **单源**：下游（②③）都以清洗稿为唯一输入，互不喂入
- **溯源四条链**：改动可对账（修订记录）／源冻结（SHA-256）／位置可回指／跨场口径统一（词表）

## License

MIT
