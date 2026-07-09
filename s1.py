from dotenv import load_dotenv; load_dotenv()      # 读取 .env 文件中的 API 密钥
from openrouter import OpenRouter                    # 导入 OpenRouter SDK
import os                                            # 用于读取环境变量

client = OpenRouter(                                 # 创建客户端
    api_key=os.getenv("OPENROUTER_API_KEY")
)

user_input = input("你：")                          # 用户输入一次

messages = [                                        # system + user
    {"role": "system", "content": "你是一个有帮助的助手。"},
    {"role": "user", "content": user_input}
]

response = client.chat.send(                        # 模型回答一次
    model="anthropic/claude-opus-4.6",
    messages=messages
)

reply = response.choices[0].message.content
print(f"AI：{reply}")                                # 打印回复
