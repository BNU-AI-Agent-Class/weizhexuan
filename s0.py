from dotenv import load_dotenv; load_dotenv()    # 读取 .env 文件中的 API 密钥
from openrouter import OpenRouter                   # 导入 OpenRouter SDK
import os                                           # 用于读取环境变量

client = OpenRouter(                                # 创建客户端
    api_key=os.getenv("OPENROUTER_API_KEY")
)

messages = [{"role": "user", "content": "你好"}]    # 一条固定消息

response = client.chat.send(                        # 向模型发送一次请求
    model="anthropic/claude-opus-4.6",
    messages=messages
)

print(response.choices[0].message.content)          # 打印模型回复
