# 选项C：防崩加强版 - 堵住未知工具和无限重试两个洞
from dotenv import load_dotenv; load_dotenv()
from openrouter import OpenRouter
import os, json

DANGER = ["rm ", "rmdir", "del ", "sudo", "mv ", "> /", "mkfs", "dd ", ":(){"]
MAX_RETRIES = 5  # 最大连续失败次数，超过就放弃

def read_file(path):  return open(path, encoding="utf-8").read()
def write_file(path, text):
    open(path, "w", encoding="utf-8").write(text); return f"已写入 {path}"
def bash(cmd):
    if any(d in cmd for d in DANGER):
        if input(f"[⚠ 权限] 要执行危险命令：{cmd}\n允许吗？(y/n) ").strip().lower() != "y":
            return "用户拒绝了这条命令。"
    return os.popen(cmd).read()

TOOLS = {"read_file": read_file, "write_file": write_file, "bash": bash}

def parse(s):
    s = s.strip().strip("`").removeprefix("json").strip(); return json.loads(s[s.find("{"): s.rfind("}") + 1])

SYSTEM = """你是一个编程助手。每次只回复一个 JSON，不要别的文字，不要 markdown 包裹；字符串值里别用英文双引号，要引用就用「」：
- 读文件：{"tool": "read_file", "args": {"path": "..."}}
- 写文件：{"tool": "write_file", "args": {"path": "...", "text": "..."}}
- 执行命令：{"tool": "bash", "args": {"cmd": "..."}}
- 完成时：{"done": "总结"}
优先用 read_file / write_file 处理文件，它们比 bash 更安全可控。
注意：只能调用上面列出的工具，调用不存在的工具会报错。"""

with OpenRouter(api_key=os.getenv("OPENROUTER_API_KEY")) as client:
    messages = [{"role": "system", "content": SYSTEM}]
    while True:
        messages.append({"role": "user", "content": input("\n你：")})
        consecutive_failures = 0  # 连续失败计数器
        
        while True:
            # 检查是否连续失败太多次
            if consecutive_failures >= MAX_RETRIES:
                print(f"[放弃] 连续 {MAX_RETRIES} 次失败，已停止当前任务。请重新输入指令。")
                break
                
            reply = client.chat.send(model="anthropic/claude-opus-4.6",
                                     messages=messages).choices[0].message.content
            messages.append({"role": "assistant", "content": reply})
            
            try:
                action = parse(reply)
            except Exception as e:
                # JSON解析失败
                consecutive_failures += 1
                error_msg = f"上一条不是合法 JSON（解析错误：{str(e)}），请只回一个格式正确的 JSON，不要有其他文字。这是第 {consecutive_failures} 次失败，最多允许 {MAX_RETRIES} 次。"
                messages.append({"role": "user", "content": error_msg})
                print(f"[解析失败] {error_msg}")
                continue
            
            if "done" in action:
                print(f"[完成] {action['done']}")
                consecutive_failures = 0  # 成功完成，清零计数器
                break
            
            # 检查工具是否存在
            name = action.get("tool", "")
            args = action.get("args", {})
            
            if name not in TOOLS:
                # 未知工具 - 不崩溃，告诉AI可用的工具列表
                consecutive_failures += 1
                available_tools = ", ".join(TOOLS.keys())
                error_msg = f"没有叫「{name}」的工具。可用的工具有：{available_tools}。请使用正确的工具名重新回复。这是第 {consecutive_failures} 次失败，最多允许 {MAX_RETRIES} 次。"
                messages.append({"role": "user", "content": error_msg})
                print(f"[未知工具] {error_msg}")
                continue
            
            # 参数检查（args必须是字典）
            if not isinstance(args, dict):
                consecutive_failures += 1
                error_msg = f"工具「{name}」的args必须是一个对象（字典）。请修正格式。这是第 {consecutive_failures} 次失败，最多允许 {MAX_RETRIES} 次。"
                messages.append({"role": "user", "content": error_msg})
                print(f"[参数错误] {error_msg}")
                continue
            
            # 执行工具
            try:
                print(f"[调用] {name}({args})")
                result = TOOLS[name](**args)
                print(f"[结果]\n{result}")
                messages.append({"role": "user", "content": f"工具返回：\n{result}"})
                consecutive_failures = 0  # 工具执行成功，清零计数器
            except TypeError as e:
                # 参数不匹配
                consecutive_failures += 1
                import inspect
                sig = inspect.signature(TOOLS[name])
                error_msg = f"工具「{name}」参数错误：{str(e)}。该工具的参数签名是：{sig}。请修正参数。这是第 {consecutive_failures} 次失败，最多允许 {MAX_RETRIES} 次。"
                messages.append({"role": "user", "content": error_msg})
                print(f"[参数错误] {error_msg}")
            except Exception as e:
                # 工具执行出错
                consecutive_failures += 1
                error_msg = f"工具「{name}」执行出错：{str(e)}。请检查后重试，或换一种方式。这是第 {consecutive_failures} 次失败，最多允许 {MAX_RETRIES} 次。"
                messages.append({"role": "user", "content": error_msg})
                print(f"[工具错误] {error_msg}")
# MIT License | 郑先隽，北师大心理学部教授，人本AI设计与创新
