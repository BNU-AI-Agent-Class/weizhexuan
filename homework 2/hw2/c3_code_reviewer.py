# 选项B：给子agent装一个"代码审查员"人设 - 专门检查代码bug
from dotenv import load_dotenv; load_dotenv()
from openrouter import OpenRouter
import os, json

client = OpenRouter(api_key=os.getenv("OPENROUTER_API_KEY"))
MODEL = "anthropic/claude-opus-4.6"

def read_file(path):  return open(path, encoding="utf-8").read()
def write_file(path, text):
    open(path, "w", encoding="utf-8").write(text); return f"已写入 {path}"
def bash(cmd):        return os.popen(cmd).read()

def code_reviewer(task):
    """
    代码审查员子agent：专门负责通读代码、查找潜在bug
    只报告问题，不修改代码
    """
    sub_system = """你是一位资深代码审查员，你的任务是仔细阅读代码，找出潜在的bug、逻辑漏洞和代码质量问题。
你可以使用 read_file 工具读取文件，使用 bash 工具执行 ls 等命令浏览目录结构。

审查要点：
1. 边界条件处理：空输入、空列表、索引越界（如 list[0] 当列表可能为空时）
2. 异常处理：是否有未捕获的异常
3. 逻辑错误：条件判断、循环、变量使用是否正确
4. 资源泄漏：文件是否正确关闭
5. 潜在的崩溃点：什么输入会让程序崩溃

工作流程：
1. 先用 ls 和 read_file 通读项目结构和所有相关代码文件
2. 仔细分析每个函数可能出问题的地方
3. 不要只看一个文件就下结论，要通读所有相关文件
4. 最后用 {"done": "审查报告"} 返回完整的审查结果

审查报告格式：
- 每个bug单独列出，包含：文件位置、问题描述、触发条件、修复建议
- 如果没发现bug，明确说明"未发现明显bug"

每次只回复一个 JSON，不要别的文字，不要 markdown；字符串值里别用英文双引号，要引用就用「」：
- 读文件：{"tool": "read_file", "args": {"path": "..."}}
- 执行命令：{"tool": "bash", "args": {"cmd": "..."}}
- 完成审查：{"done": "详细的审查报告，列出所有发现的问题"}"""

    sub = [{"role": "system", "content": sub_system},
           {"role": "user", "content": f"请审查以下任务相关的代码：{task}\n请先浏览项目结构，然后通读所有相关代码文件，仔细查找潜在bug。"}]
    
    while True:
        r = client.chat.send(model=MODEL, messages=sub).choices[0].message.content
        sub.append({"role": "assistant", "content": r})
        try:
            a = parse(r)
        except Exception:
            sub.append({"role": "user", "content": "上一条不是合法 JSON，请只回一个 JSON，别的都不要"}); continue
        
        if "done" in a:
            return a["done"]
        
        name = a.get("tool", "")
        args = a.get("args", {})
        
        # 子agent也有自己的工具集
        if name == "read_file":
            try:
                out = read_file(**args)
            except Exception as e:
                out = f"读取文件失败: {str(e)}"
        elif name == "bash":
            out = bash(**args)
        else:
            out = f"未知工具: {name}，可用工具: read_file, bash"
        
        sub.append({"role": "user", "content": f"输出：\n{out}"})

TOOLS = {"read_file": read_file, "write_file": write_file, "bash": bash, "code_reviewer": code_reviewer}

def parse(s):
    s = s.strip().strip("`").removeprefix("json").strip(); return json.loads(s[s.find("{"): s.rfind("}") + 1])

SYSTEM = """你是主编程助手。每次只回复一个 JSON，不要别的文字，不要 markdown；字符串值里别用英文双引号，要引用就用「」：
- 读文件：{"tool": "read_file", "args": {"path": "..."}}
- 写文件：{"tool": "write_file", "args": {"path": "...", "text": "..."}}
- 执行命令：{"tool": "bash", "args": {"cmd": "..."}}
- 派代码审查员：{"tool": "code_reviewer", "args": {"task": "描述要审查的项目或文件，例如「审查 demo_project 目录下的所有Python代码，查找潜在bug」"}}
- 完成：{"done": "总结"}

当需要检查代码质量、查找bug、做代码审查时，派 code_reviewer 子agent去做，它会通读代码后返回详细的审查报告。
主agent拿到审查报告后，要把审查结果完整转达给用户。"""

messages = [{"role": "system", "content": SYSTEM}]
while True:
    messages.append({"role": "user", "content": input("\n你：")})
    while True:
        reply = client.chat.send(model=MODEL, messages=messages).choices[0].message.content
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
