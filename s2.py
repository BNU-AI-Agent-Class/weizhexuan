from dotenv import load_dotenv; load_dotenv()      # 读取 .env 文件中的 API 密钥
from openrouter import OpenRouter                    # 导入 OpenRouter SDK
import os                                            # 用于读取环境变量

client = OpenRouter(                                 # 创建客户端
    api_key=os.getenv("OPENROUTER_API_KEY")
)

messages = [{"role": "system", "content": "你是一个有帮助的助手。"}]

while True:                                         # 外层循环持续对话
    user_input = input("\n你：")                    # 等待用户输入
    messages.append({"role": "user", "content": user_input})  # 追加用户消息

    response = client.chat.send(                    # 发送历史消息
        model="anthropic/claude-opus-4.6",
        messages=messages
    )

    reply = response.choices[0].message.content
    print(f"AI：{reply}")                            # 打印模型回复

    messages.append({"role": "assistant", "content": reply})  # 追加模型回复，形成记忆
