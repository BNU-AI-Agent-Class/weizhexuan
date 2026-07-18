# c6_final.py - 整合所有功能的最终版 mini Claude Code
# 包含：search工具、code_reviewer代码审查子agent、todo_write计划、防崩加固、权限门
from dotenv import load_dotenv; load_dotenv()
from openrouter import OpenRouter
import os, json, inspect
from collections import Counter

# ============ 配置 ============
DANGER = ["rm ", "rmdir", "del ", "sudo", "mv ", "> /", "mkfs", "dd ", ":(){", "format"]
MAX_RETRIES = 5
MODEL = "anthropic/claude-opus-4.6"
LIMIT = 20  # 上下文压缩阈值

client = OpenRouter(api_key=os.getenv("OPENROUTER_API_KEY"))
TODOS = []

# ============ 工具函数 ============

def read_file(path):
    """读取文件内容"""
    return open(path, encoding="utf-8").read()

def write_file(path, text):
    """写入文件"""
    open(path, "w", encoding="utf-8").write(text)
    return f"已写入 {path}"

def bash(cmd):
    """执行shell命令，带安全检查"""
    if any(d in cmd for d in DANGER):
        if input(f"[⚠ 权限] 要执行危险命令：{cmd}\n允许吗？(y/n) ").strip().lower() != "y":
            return "用户拒绝了这条命令。"
    return os.popen(cmd).read()

def search(keyword, path="."):
    """
    在目录下递归搜索包含关键词的文件内容
    返回: 文件名:行号:该行内容，最多50条
    """
    results = []
    skip_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}
    skip_exts = {'.pyc', '.exe', '.dll', '.so', '.bin', '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip'}
    
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in skip_exts:
                continue
            filepath = os.path.join(root, file)
            try:
                with open(filepath, encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        if keyword in line:
                            line_content = line.rstrip()
                            if len(line_content) > 200:
                                line_content = line_content[:200] + "..."
                            results.append(f"{filepath}:{line_num}: {line_content}")
                            if len(results) >= 50:
                                results.append("... (结果过多，已截断)")
                                return "\n".join(results)
            except (UnicodeDecodeError, PermissionError, OSError):
                continue
    
    if not results:
        return f"在 {path} 下没有找到包含「{keyword}」的文件"
    return "\n".join(results)

def todo_write(items):
    """更新任务清单"""
    global TODOS
    TODOS = items
    board = "\n".join(f"  {'☑' if t['done'] else '☐'} {t['task']}" for t in TODOS)
    print(f"[计划]\n{board}")
    return "清单已更新"

def code_reviewer(task):
    """
    代码审查员子agent：通读代码找bug
    只报告，不修改
    """
    sub_system = """你是一位资深代码审查员，任务是仔细阅读代码，找出潜在bug和问题。
可用工具：read_file（读文件）、bash（执行ls等命令）。

审查要点：
1. 边界条件：空输入、空列表索引越界
2. 异常处理：未捕获的异常
3. 逻辑错误：条件判断、循环问题
4. 崩溃点：什么输入会让程序崩溃

工作流程：
1. 先用ls/bash浏览目录结构
2. 用read_file通读所有相关代码文件
3. 不要只看一个文件就下结论
4. 最后返回详细审查报告

报告格式：每个bug列出文件位置、问题描述、触发条件、修复建议。
没发现bug就说「未发现明显bug」。

每次只回复一个JSON：
- 读文件：{"tool":"read_file","args":{"path":"..."}}
- 执行命令：{"tool":"bash","args":{"cmd":"..."}}
- 完成：{"done":"详细审查报告"}

字符串值里别用英文双引号，用「」代替。"""

    sub = [{"role": "system", "content": sub_system},
           {"role": "user", "content": f"请审查：{task}\n请先浏览结构，再通读代码，仔细找bug。"}]
    
    while True:
        r = client.chat.send(model=MODEL, messages=sub).choices[0].message.content
        sub.append({"role": "assistant", "content": r})
        try:
            a = parse(r)
        except Exception:
            sub.append({"role": "user", "content": "上一条不是合法JSON，请只回一个JSON"}); continue
        
        if "done" in a:
            return a["done"]
        
        name = a.get("tool", "")
        args = a.get("args", {})
        
        try:
            if name == "read_file":
                out = read_file(**args)
            elif name == "bash":
                out = bash(**args)
            else:
                out = f"未知工具: {name}，可用: read_file, bash"
        except Exception as e:
            out = f"执行出错: {str(e)}"
        
        sub.append({"role": "user", "content": f"输出：\n{out}"})

TOOLS = {
    "read_file": read_file,
    "write_file": write_file, 
    "bash": bash,
    "search": search,
    "todo_write": todo_write,
    "code_reviewer": code_reviewer
}

# ============ 辅助函数 ============

def parse(s):
    """容错JSON解析"""
    s = s.strip().strip("`").removeprefix("json").strip()
    return json.loads(s[s.find("{"): s.rfind("}") + 1])

def compact(messages):
    """压缩上下文历史"""
    system = messages[0]
    body = "\n".join(f'{m["role"]}: {m["content"]}' for m in messages[1:])
    summary = client.chat.send(model=MODEL, messages=[
        {"role": "user", "content": f"用要点总结这段对话的进展和关键结论，供接力：\n{body}"}
    ]).choices[0].message.content
    print("[压缩] 历史已折叠成摘要，窗口重开")
    return [system, {"role": "user", "content": f"【之前进展摘要】\n{summary}"}]

# ============ 系统提示 ============

SYSTEM = """你是一个强大的编程助手（mini Claude Code）。每次只回复一个 JSON，不要别的文字，不要 markdown 包裹；字符串值里别用英文双引号，要引用就用「」。

可用工具：
1. todo_write - 列计划/更新待办：{"tool":"todo_write","args":{"items":[{"task":"步骤1","done":false},...]}}
2. read_file - 读文件：{"tool":"read_file","args":{"path":"..."}}
3. write_file - 写文件：{"tool":"write_file","args":{"path":"...","text":"..."}}
4. bash - 执行命令：{"tool":"bash","args":{"cmd":"..."}}
5. search - 全项目搜索关键词：{"tool":"search","args":{"keyword":"...","path":"..."}}
6. code_reviewer - 派代码审查员子agent找bug：{"tool":"code_reviewer","args":{"task":"描述要审查的项目/文件"}}
7. 完成任务：{"done":"给用户的总结"}

工作原则：
- 接到多步任务，先用 todo_write 列出计划，每完成一步更新勾选
- 查找代码位置优先用 search，比grep更方便
- 检查代码bug、做代码审查时派 code_reviewer 子agent去做
- 读写文件优先用 read_file/write_file，比bash的cat/echo更安全
- 危险命令（rm、sudo等）会先问用户确认
- 只能调用上面列出的工具，调用不存在的工具会报错"""

# ============ 主循环 ============

messages = [{"role": "system", "content": SYSTEM}]
print("=" * 60)
print("mini Claude Code - 作业2最终版")
print("功能：工具箱 + 搜索 + 计划 + 代码审查子agent + 权限门 + 防崩加固")
print("=" * 60)

while True:
    messages.append({"role": "user", "content": input("\n你：")})
    consecutive_failures = 0
    
    while True:
        # 上下文压缩检查
        if len(messages) > LIMIT:
            messages = compact(messages)
        
        # 重试次数检查
        if consecutive_failures >= MAX_RETRIES:
            print(f"[放弃] 连续 {MAX_RETRIES} 次失败，已停止。请重新输入指令。")
            break
        
        # 调用模型
        reply = client.chat.send(model=MODEL, messages=messages).choices[0].message.content
        messages.append({"role": "assistant", "content": reply})
        
        # 解析JSON
        try:
            action = parse(reply)
        except Exception as e:
            consecutive_failures += 1
            msg = f"JSON解析错误：{str(e)}。请只回一个合法JSON。这是第{consecutive_failures}次失败。"
            messages.append({"role": "user", "content": msg})
            print(f"[解析失败] {msg}")
            continue
        
        # 完成任务
        if "done" in action:
            print(f"[完成] {action['done']}")
            break
        
        # 检查工具
        name = action.get("tool", "")
        args = action.get("args", {})
        
        if name not in TOOLS:
            consecutive_failures += 1
            available = ", ".join(TOOLS.keys())
            msg = f"没有工具「{name}」。可用工具：{available}。请使用正确的工具名。这是第{consecutive_failures}次失败。"
            messages.append({"role": "user", "content": msg})
            print(f"[未知工具] {msg}")
            continue
        
        if not isinstance(args, dict):
            consecutive_failures += 1
            msg = f"工具「{name}」的args必须是对象。这是第{consecutive_failures}次失败。"
            messages.append({"role": "user", "content": msg})
            print(f"[参数错误] {msg}")
            continue
        
        # 执行工具
        try:
            print(f"[调用] {name}")
            result = TOOLS[name](**args)
            if name != "todo_write":  # todo_write已经自己打印过了
                print(f"[结果]\n{str(result)[:500]}")  # 结果太长只打印前500字符
            messages.append({"role": "user", "content": f"工具返回：\n{result}"})
            consecutive_failures = 0
        except TypeError as e:
            consecutive_failures += 1
            sig = inspect.signature(TOOLS[name])
            msg = f"工具「{name}」参数错误：{e}。参数签名：{sig}。这是第{consecutive_failures}次失败。"
            messages.append({"role": "user", "content": msg})
            print(f"[参数错误] {msg}")
        except Exception as e:
            consecutive_failures += 1
            msg = f"工具「{name}」执行出错：{e}。这是第{consecutive_failures}次失败。"
            messages.append({"role": "user", "content": msg})
            print(f"[工具错误] {msg}")
# MIT License | 郑先隽，北师大心理学部教授，人本AI设计与创新
