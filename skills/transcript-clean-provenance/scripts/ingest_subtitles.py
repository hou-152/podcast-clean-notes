#!/usr/bin/env python3
"""SRT/VTT → 00 原文：把字幕文件转换成清洗链路可直读的 `00_*_原文.txt`。

支持：
- .srt（序号 + 时间轴 + 文本）
- .vtt（WEBVTT + 时间轴 + 文本，含 <v>/<c>/<00:00:00.000> 标签与实体）

处理规则：
1. 去序号、时间轴、VTT 头与 NOTE/STYLE/REGION 块、HTML/VTT/ASS 标签、实体；
2. 相邻重复/重叠字幕去重（滚动字幕常见）；
3. 按「累计时长≈40s / 间隔>2s / 字数>220」合并成块；
4. 每块首行输出时间戳（HH:MM:SS 或 MM:SS），供清洗站按工具行剥离；
5. 输出与输入同目录的 `00_<名>_原文.txt`，并打印输出 SHA-256。

用法：
    python3 ingest_subtitles.py <输入.srt|.vtt>
"""
import argparse
import hashlib
import html
import os
import re
import sys
from datetime import date
from pathlib import Path

TIME = re.compile(
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{3})"
)
TAG = re.compile(r"<[^>]+>")
ASS = re.compile(r"\{\\[^}]*\}")


def read_text_file(path):
    """只读常规文件：校验存在与类型后再读，拒绝目录、空字节与目录穿越。"""
    if not isinstance(path, str) or not path or "\x00" in path:
        raise ValueError("非法路径")
    if ".." in os.path.abspath(path).split(os.sep):
        raise ValueError("路径含 .. 段：%s" % path)
    if not os.path.isfile(path):
        raise ValueError("不是常规文件或不存在：%s" % path)
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except UnicodeDecodeError:
        raise ValueError("无法按 UTF-8 解码（文件疑似损坏）：%s" % path)


def parse_ts(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_cues(text):
    """返回 [(start,end,text)]。兼容 SRT 与 VTT。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    cues = []
    for block in re.split(r"\n\s*\n", text):
        lines = [l for l in block.split("\n") if l.strip()]
        if not lines:
            continue
        head = lines[0].strip()
        if head.upper().startswith("WEBVTT") or head.upper().startswith(("NOTE", "STYLE", "REGION")):
            continue
        m = None
        body = []
        for i, line in enumerate(lines):
            m = TIME.search(line)
            if m:
                body = lines[i + 1 :]
                break
        if not m:
            continue
        start = parse_ts(*m.group(1, 2, 3, 4))
        end = parse_ts(*m.group(5, 6, 7, 8))
        cleaned = [html.unescape(ASS.sub("", TAG.sub("", l))).strip() for l in body]
        cleaned = [x for x in cleaned if x]
        if not cleaned:
            continue
        cues.append((start, end, "".join(cleaned)))
    return cues


def group_cues(cues, max_seconds=40.0, max_chars=220, gap_limit=2.0):
    blocks = []
    cur = None
    prev_text = None
    for start, end, text in cues:
        if text == prev_text:
            continue
        prev_text = text
        if cur is None:
            cur = {"start": start, "end": end, "texts": [text], "chars": len(text)}
            continue
        gap = start - cur["end"]
        if (cur["end"] - cur["start"] >= max_seconds) or (cur["chars"] + len(text) > max_chars) or (gap > gap_limit):
            blocks.append(cur)
            cur = {"start": start, "end": end, "texts": [text], "chars": len(text)}
        else:
            cur["end"] = end
            cur["texts"].append(text)
            cur["chars"] += len(text)
    if cur:
        blocks.append(cur)
    return blocks


def fmt_ts(seconds):
    s = int(round(seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"


def convert_text(raw, stem, ext):
    cues = parse_cues(raw)
    if not cues:
        raise ValueError("未解析到任何字幕块（检查文件是否为 SRT/VTT）")
    blocks = group_cues(cues)
    lines = [f"{stem}_原文", f"字幕转换：{stem}{ext}（{date.today().isoformat()}）", ""]
    for b in blocks:
        lines.append(fmt_ts(b["start"]))
        lines.append("".join(b["texts"]))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main():
    ap = argparse.ArgumentParser(description="SRT/VTT → 00 原文转换（清洗链路输入）")
    ap.add_argument("source", help="输入字幕文件（.srt / .vtt；输出写到同目录）")
    args = ap.parse_args()

    try:
        raw = read_text_file(args.source)
    except ValueError as e:
        print("FAIL 输入校验未通过：" + str(e))
        sys.exit(1)

    src = os.path.abspath(args.source)
    ext = os.path.splitext(src)[1].lower()
    if ext not in (".srt", ".vtt"):
        print("FAIL 只支持 .srt / .vtt：" + ext)
        sys.exit(1)
    stem = os.path.splitext(os.path.basename(src))[0]

    try:
        content = convert_text(raw, stem, ext)
    except ValueError as e:
        print("FAIL " + str(e))
        sys.exit(1)

    out = Path(src).parent / f"00_{stem}_原文.txt"
    if out.exists():
        print("FAIL 目标已存在，不覆盖：" + str(out))
        sys.exit(1)
    out.write_text(content, encoding="utf-8")

    h = hashlib.sha256(content.encode("utf-8")).hexdigest()
    blocks = content.count("\n\n")
    print(f"OK 已转换：{out}")
    print(f"   字符数 {len(content)} · 块数 {blocks} · SHA-256 {h}")


if __name__ == "__main__":
    main()
