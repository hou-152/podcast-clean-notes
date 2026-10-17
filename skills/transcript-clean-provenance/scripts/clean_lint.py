#!/usr/bin/env python3
"""清洗稿形状门：检查产物是否齐全、哈希是否在、工具行是否清干净。

用法：
    python3 clean_lint.py <清洗稿.md>

退出码：0 = 全部通过；1 = 有硬失败。警告不改变退出码。
"""
import argparse
import os
import re
import sys

SHA = re.compile(r"[0-9a-f]{64}")
# 工具行：整行是「发言人N 00:00」或纯时间戳「00:00 / 00:00:00」（字幕转换产物）
TS_HEADER = re.compile(r"^(?:发言人\s*\d*\s+)?\d{1,2}:\d{2}(?::\d{2})?\s*$", re.M)
TS_ANY = re.compile(r"\d{1,2}:\d{2}(?::\d{2})?")  # 用于警告提示


def find_attachment(clean_file, kind):
    """在清洗稿同目录找 <会话名>_<kind>.md（会话名＝清洗稿名去掉 _清洗稿 后缀与前缀序号）。"""
    base = os.path.basename(clean_file)
    stem = re.sub(r"^0*\d+_", "", base)
    stem = stem.replace("_清洗稿.md", "")
    d = os.path.dirname(os.path.abspath(clean_file))
    for name in os.listdir(d):
        if kind in name and name.endswith(".md") and stem in name:
            return os.path.join(d, name)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clean_file", help="清洗稿 .md 路径")
    args = ap.parse_args()

    path = args.clean_file
    fails, warns, oks = [], [], []

    if not os.path.isfile(path):
        print("FAIL 清洗稿不存在: " + path)
        sys.exit(1)

    text = open(path, encoding="utf-8").read()

    # 1. 哈希
    if SHA.search(text):
        oks.append("清洗稿含 64 位 SHA-256")
    else:
        fails.append("清洗稿未见 64 位 SHA-256（源文件哈希应写在清洗说明块）")

    # 2. 工具行残留
    hits = TS_HEADER.findall(text)
    if hits:
        fails.append("发现「发言人N＋时间戳」残留行 %d 处（工具行未清）" % len(hits))
    else:
        oks.append("无「发言人N＋时间戳」残留")

    # 3. 头部结构
    for key, label, hard in [
        ("清洗说明", "清洗说明", True),
        ("校订表", "统一校订表", True),
        ("存疑", "存疑保留清单", True),
    ]:
        if key in text:
            oks.append(label + "块存在")
        else:
            (fails if hard else warns).append("缺「" + label + "」块")

    # 4. 时间戳线报（可能是正文里引用的时刻，仅警告）
    n_ts = len(TS_ANY.findall(text))
    if n_ts:
        warns.append(
            "全文含时间戳样式文本 %d 处——确认都是正文合理引用（如「01:35:09 处截断」），非工具行残留" % n_ts
        )

    # 5. 正文非空（剥离头部引用块后）
    body_lines = [
        l
        for l in text.splitlines()
        if l.strip() and not l.strip().startswith(">") and not l.strip().startswith("|")
    ]
    if len(body_lines) < 5:
        fails.append("正文过短（<5 行有效内容），疑似空稿")

    # 6. 附件齐否
    for kind in ("修订记录", "待对清单"):
        found = find_attachment(path, kind)
        if found:
            oks.append(kind + "附件存在：" + os.path.basename(found))
        else:
            warns.append("未在目录中找到「" + kind + "」附件（单人场可说明豁免）")

    # 输出
    print("== clean_lint: " + os.path.basename(path) + " ==")
    for o in oks:
        print("  OK   " + o)
    for w in warns:
        print("  WARN " + w)
    for f in fails:
        print("  FAIL " + f)
    print("== 结果：%d OK / %d WARN / %d FAIL ==" % (len(oks), len(warns), len(fails)))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
