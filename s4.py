from dotenv import load_dotenv; load_dotenv()      # 读取 .env 文件中的 API 密钥
from openrouter import OpenRouter                    # 导入 OpenRouter SDK
import os                                            # 用于读取环境变量和执行命令

client = OpenRouter(                                 # 创建客户端
    api_key=os.getenv("OPENROUTER_API_KEY")
)

with open("agent.md", "r", encoding="utf-8") as f:  # 从外部读取系统提示词
    agent_prompt = f.read()

messages = [{"role": "system", "content": agent_prompt}]

while True:                                         # 外层循环：等待用户输入新任务
    user_input = input("\n你：")
    messages.append({"role": "user", "content": user_input})

    while True:                                     # 内层循环：Agent 自主执行
        response = client.chat.send(
            model="anthropic/claude-opus-4.6",
            messages=messages
        )
        reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": reply})
        print(f"[AI] {reply}")

        if reply.strip().startswith("完成:"):        # 任务完成则结束
            break

        command = reply.strip().split("命令:")[1].strip()  # 提取命令
        result = os.popen(command).read()           # 执行命令
        print(f"[系统] {result}")
        messages.append({"role": "user", "content": f"执行完毕:{result}"})
