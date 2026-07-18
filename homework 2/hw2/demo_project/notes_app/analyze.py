"""analyze.py — 对笔记做一些统计。"""
from collections import Counter
from .store import all_notes


def tag_counts():
    """统计每个标签出现了多少次,返回按次数排序的列表。"""
    counter = Counter()
    for note in all_notes():
        counter.update(note["tags"])
    return counter.most_common()


def summary():
    """生成一段统计摘要。"""
    notes = all_notes()
    counts = tag_counts()
    lines = [f"共有 {len(notes)} 条笔记。"]
    
    if not counts:
        # 修复：当没有任何带标签的笔记时，友好提示而不是崩溃
        lines.append("还没有任何标签。")
        lines.append("给笔记加上 #标签 后就能看到标签统计啦！")
    else:
        top_tag = counts[0][0]
        lines.append(f"最常用的标签是 #{top_tag}。")
        lines.append(f"一共用过 {len(counts)} 个不同标签。")
    
    return "\n".join(lines)
