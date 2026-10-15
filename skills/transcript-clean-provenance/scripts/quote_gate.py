#!/usr/bin/env python3
"""引文门：02/03 的引号内容必须是 01 清洗稿的逐字子串（窗口退化容忍）。

标准：引文与清洗稿做逐字比对；若整条未命中，允许「清洗稿相对我方源稿的窗口退化」
（同一引文在清洗稿中散布的片段各自逐字存在，中间被清洗改动打断）。
退化阈值：引文长度 - 最长命中窗口 <= 20 字（经验值，源自本链路的清洗改动粒度）。

用法：
    python3 quote_gate.py <01_清洗稿.md> <02 或 03 产出.md> [更多产出...]

输出：每条未命中/退化引文的明细；TOTAL_UNMATCHED 为硬失败数。
退出码：0 = 全部逐字命中或有界退化；1 = 有硬失败（伪引文）。
"""
import argparse
import difflib
import os
import re
import sys

QCN = re.compile(r"「([^」]+)」")
QEN = re.compile(r"[“”]([^“”]{4,})[“”]")
FENCE = re.compile(r"```.*?```", re.S)
DEGRADE = 20


def read_text_file(path):
    if not isinstance(path, str) or not path or "\x00" in path:
        raise ValueError("非法路径")
    if not os.path.isfile(path):
        raise ValueError("不是常规文件或不存在：%s" % path)
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except UnicodeDecodeError:
        raise ValueError("无法按 UTF-8 解码（文件疑似不完整或被截断）：%s" % path)


def longest_match_ratio(q, src):
    """返回 (匹配字符数, 引文长度)。用 SequenceMatcher 找最长匹配块。"""
    sm = difflib.SequenceMatcher(None, q, src, autojunk=False)
    best = 0
    for block in sm.get_matching_blocks():
        best = max(best, block.size)
    return best, len(q)


def main():
    ap = argparse.ArgumentParser(description="引文门：02/03 引号内容逐字回溯 01 清洗稿")
    ap.add_argument("clean_file", help="01 清洗稿")
    ap.add_argument("outputs", nargs="+", help="02/03 产出文件")
    args = ap.parse_args()

    try:
        src = read_text_file(args.clean_file)
    except ValueError as e:
        print("FAIL 清洗稿校验未通过：" + str(e))
        sys.exit(1)
    src_flat = re.sub(r"\s+", "", src)

    total_bad = 0
    for path in args.outputs:
        try:
            text = read_text_file(path)
        except ValueError as e:
            print("FAIL 产出文件校验未通过：" + str(e))
            sys.exit(1)
        text = FENCE.sub("", text)  # 剥代码块（图表语法不参与引文核对）
        quotes = QCN.findall(text) + QEN.findall(text)
        bad = deg = 0
        for q in quotes:
            qf = re.sub(r"\s+", "", q)
            if qf in src_flat:
                continue
            best, ln = longest_match_ratio(qf, src_flat)
            if ln - best <= DEGRADE:
                deg += 1
                print("%s: 退化（最长块 %d/%d，差 %d≤%d）→ %s" % (
                    os.path.basename(path), best, ln, ln - best, DEGRADE, q[:50]))
            else:
                bad += 1
                print("%s: 伪引文（最长块仅 %d/%d）→ %s" % (
                    os.path.basename(path), best, ln, q[:50]))
        print("%s: 引文 %d 条，逐字命中 %d，有界退化 %d，未命中 %d" % (
            os.path.basename(path), len(quotes), len(quotes) - bad - deg, deg, bad))
        total_bad += bad
    print("TOTAL_UNMATCHED", total_bad)
    sys.exit(1 if total_bad else 0)


if __name__ == "__main__":
    main()
