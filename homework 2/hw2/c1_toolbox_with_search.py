# 选项A：给工具箱加一件"搜索"工具 - 在项目里按关键词搜文件内容
from dotenv import load_dotenv; load_dotenv()
from openrouter import OpenRouter
import os, json

def read_file(path):  return open(path, encoding="utf-8").read()
def write_file(path, text):
    open(path, "w", encoding="utf-8").write(text); return f"已写入 {path}"
def bash(cmd):        return os.popen(cmd).read()

def search(keyword, path="."):
    """
    在指定目录下递归搜索包含关键词的文件内容
    返回: 文件名:行号:该行内容 的列表，最多返回50条结果
    """
    results = []
    # 要跳过的目录和文件类型
    skip_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}
    skip_exts = {'.pyc', '.pyo', '.exe', '.dll', '.so', '.bin', '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.zip'}
    
    for root, dirs, files in os.walk(path):
        # 跳过不需要的目录
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        
        for file in files:
            # 跳过二进制文件
            ext = os.path.splitext(file)[1].lower()
            if ext in skip_exts:
                continue
                
            filepath = os.path.join(root, file)
            try:
                with open(filepath, encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        if keyword in line:
                            # 截断过长的行
                            line_content = line.rstrip()
                            if len(line_content) > 200:
                                line_content = line_content[:200] + "..."
                            results.append(f"{filepath}:{line_num}: {line_content}")
                            if len(results) >= 50:  # 限制结果数量，避免上下文爆炸
                                results.append("... (结果过多，已截断)")
                                return "\n".join(results)
            except (UnicodeDecodeError, PermissionError, OSError):
                # 跳过无法读取的文件（二进制、权限问题等）
                continue
    
    if not results:
        return f"在 {path} 下没有找到包含「{keyword}」的文件"
    return "\n".join(results)

TOOLS = {"read_file": read_file, "write_file": write_file, "bash": bash, "search": search}

def parse(s):
    s = s.strip().strip("`").removeprefix("json").strip(); return json.loads(s[s.find("{"): s.rfind("}") + 1])

SYSTEM = """你是一个编程助手。每次只回复一个 JSON，不要别的文字，不要 markdown 包裹；字符串值里别用英文双引号，要引用就用「」：
- 读文件：{"tool": "read_file", "args": {"path": "..."}}
- 写文件：{"tool": "write_file", "args": {"path": "...", "text": "..."}}
- 执行命令：{"tool": "bash", "args": {"cmd": "..."}}
- 搜索关键词：{"tool": "search", "args": {"keyword": "要搜索的关键词", "path": "搜索路径（默认当前目录）"}}
- 完成时：{"done": "总结"}
优先用 read_file / write_file 处理文件，用 search 在项目中查找代码位置，它们比 bash 更安全可控。"""

with OpenRouter(api_key=os.getenv("OPENROUTER_API_KEY")) as client:
    messages = [{"role": "system", "content": SYSTEM}]
    while True:
        messages.append({"role": "user", "content": input("\n你：")})
        while True:
            reply = client.chat.send(model="anthropic/claude-opus-4.6",
                                     messages=messages).choices[0].message.content
            messages.append({"role": "assistant", "content": reply})
            try:
                action = parse(reply)
            except Exception:
                messages.append({"role": "user", "content": "上一条不是合法 JSON，请只回一个 JSON，别的都不要"}); continue
            if "done" in action:
                print(f"[完成] {action['done']}"); break
            name, args = action["tool"], action["args"]
            print(f"[调用] {name}({args})")
            result = TOOLS[name](**args)
            print(f"[结果]\n{result}")
            messages.append({"role": "user", "content": f"工具返回：\n{result}"})
# MIT License | 郑先隽，北师大心理学部教授，人本AI设计与创新
