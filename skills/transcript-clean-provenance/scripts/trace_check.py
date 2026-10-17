#!/usr/bin/env python3
"""覆盖门：清洗稿必须完整覆盖源转写（零增删核对，只抓增、抓丢，不判对错）。

三把尺子：
  1. 字符清单覆盖——剥离角色名/标点/空白后，源文字符的 80%+ 应能在清洗稿找到。
     零删减下字符清单基本守恒（清洗只换标点、清工具行、拆数字），丢大段会立刻掉。
  2. 体量比——清洗稿字数 / 源文字数，抓改写与总结。
  3. 长块检测——difflib 对齐后源文连续 >60 字匹配不上的块（去掉标点空白后比对）。
     长块＝疑似丢内容或重排，逐块人查。

用法：
    python3 trace_check.py <原文.txt> <清洗稿.md>

退出码：0 = 通过（含警告）；1 = 有硬失败。
阈值（2026-10-15 基于 10-12／09-22／10-10 正例标定）：
    字符清单覆盖 < 80% → FAIL；< 90% → WARN
    体量比 < 0.70 或 > 1.60 → FAIL；< 0.85 或 > 1.25 → WARN
    长块（>60字未匹配）≥3 处 → FAIL；1–2 处 → WARN（放歌段收敛是合法策略，逐块人查）
"""
import argparse
import difflib
import os
import re
import sys
from collections import Counter

ROLE = re.compile(r"^[A-Za-z0-9\u4e00-\u9fff]{1,6}[：:]")
PUNCT = re.compile(r"[\s，。！？、；：「」『』（）()《》【】—…·,.!?;:\"'“”‘’\-—~～*#>|]+")
# 工具行：整行是「发言人N 00:00」或纯时间戳（字幕转换产物）
TOOL = re.compile(r"^(?:发言人\s*\d*\s+)?\d{1,2}:\d{2}(?::\d{2})?\s*$")


def read_text_file(path):
    """只读常规文件：校验存在与类型后再读，拒绝目录、空字节与符号链接异常。"""
    if not isinstance(path, str) or not path or "\x00" in path:
        raise ValueError("非法路径")
    if not os.path.isfile(path):
        raise ValueError("不是常规文件或不存在：%s" % path)
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except UnicodeDecodeError:
        raise ValueError("无法按 UTF-8 解码（文件疑似不完整或被截断）：%s" % path)


def normalize(text, strip_role=True):
    lines = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s or s.startswith(">") or s.startswith("|"):
            continue
        if s.startswith("#") or s.startswith("---"):
            continue
        if TOOL.match(s):
            continue
        s = s.lstrip("- ").strip()
        if strip_role:
            prev = None
            while prev != s:
                prev = s
                s = ROLE.sub("", s).strip()
        lines.append(s)
    t = "\n".join(lines)
    if strip_role:
        t = PUNCT.sub("", t)
    return t


def inventory_coverage(a, b):
    """源文（去重字符清单计数）被清洗稿覆盖的比例。"""
    ca, cb = Counter(a), Counter(b)
    if not ca:
        return 0.0
    hit = sum(min(v, cb[k]) for k, v in ca.items())
    return hit / sum(ca.values()) * 100.0


def long_gaps(a, b, block=60):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    gaps = []
    for tag, i1, i2, _j1, _j2 in sm.get_opcodes():
        if tag in ("delete", "replace") and (i2 - i1) > block:
            gaps.append(a[i1:i2])
    return gaps


def main():
    ap = argparse.ArgumentParser(description="覆盖门：清洗稿完整覆盖源转写（零增删核对）")
    ap.add_argument("source", help="源转写文件（00_原文.txt）")
    ap.add_argument("clean_file", help="清洗稿文件")
    args = ap.parse_args()

    try:
        src_raw = read_text_file(args.source)
    except ValueError as e:
        print("FAIL 源文件校验未通过：" + str(e))
        sys.exit(1)
    try:
        out_raw = read_text_file(args.clean_file)
    except ValueError as e:
        print("FAIL 清洗稿校验未通过：" + str(e))
        sys.exit(1)

    a = normalize(src_raw)
    b = normalize(out_raw)
    if not a or not b:
        print("FAIL 归一化后为空（检查输入）")
        sys.exit(1)

    cov = inventory_coverage(a, b)
    vol = len(b) / max(len(a), 1)
    gaps = long_gaps(a, b)

    fails, warns = [], []
    if cov < 80:
        fails.append("字符清单覆盖 %.1f%% < 80%%（疑似丢内容）" % cov)
    elif cov < 90:
        warns.append("字符清单覆盖 %.1f%%（抽查未覆盖字符来源）" % cov)

    if vol < 0.70 or vol > 1.60:
        fails.append("体量比 %.2f 超出 [0.70, 1.60]（疑似改写/总结）" % vol)
    elif vol < 0.85 or vol > 1.25:
        warns.append("体量比 %.2f 偏离 1 较多（确认零增删无例外）" % vol)

    if len(gaps) >= 3:
        fails.append("长块（>60字未匹配）%d 处——逐块人查是否真丢内容" % len(gaps))
    elif gaps:
        warns.append("长块（>60字未匹配）%d 处——逐块人查（放歌段收敛合法）" % len(gaps))

    print("源 %d 字 / 清洗稿 %d 字（剥离标点与角色名后）" % (len(a), len(b)))
    print("字符清单覆盖 %.1f%%  体量比 %.2f  长块 %d 处" % (cov, vol, len(gaps)))
    for g in gaps[:3]:
        print("  长块样本: " + g[:70].replace("\n", "") + ("…" if len(g) > 70 else ""))
    for w in warns:
        print("WARN " + w)
    for f in fails:
        print("FAIL " + f)
    if not fails:
        print("== 覆盖门通过 ==")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
