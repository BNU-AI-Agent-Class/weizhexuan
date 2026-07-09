from dotenv import load_dotenv; load_dotenv()                      # 1. 读取 .env 文件中的 API 密钥
from openrouter import OpenRouter                                  # 2. 导入 OpenRouter SDK
import os                                                          # 3. 用于读取环境变量和执行命令

with OpenRouter(                                                   # 4. 创建客户端
    api_key=os.getenv("OPENROUTER_API_KEY")
) as client:
    messages = [{"role":"system","content":"""你必须用以下两种格式之一回复：
- 需要执行命令：命令:XXX（纯命令，不要解释，每次一条）
- 任务完成时：完成:XXX（总结信息）"""}]                                # 5. 系统提示词：定义 AI 的输出格式（命令 or 完成）

    while True:                                                    # 6. 外层循环：等待用户输入新任务
        user_input = input("\n你：")                                # 7. 等待用户输入
        messages.append({"role": "user", "content": user_input})   # 8. 存入对话历史

        while True:                                                # 9. 内层循环：Agent 自主执行，直到任务完成
            response = client.chat.send(                           # 10. 发送对话历史给 AI
                model="anthropic/claude-opus-4.6",
                messages=messages
            )
            reply = response.choices[0].message.content            # 11. 提取 AI 回复
            messages.append({"role": "assistant", "content": reply})# 12. 存入历史
            print(f"[AI] {reply}")                                 # 13. 打印 AI 的决策

            if reply.strip().startswith("完成:"):                   # 14. 如果 AI 说"完成" → 跳出内层循环
                break

            command = reply.strip().split("命令:")[1].strip()       # 15. 提取 AI 想执行的命令
            result = os.popen(command).read()                      # 16. 执行命令，获取输出
            print(f"[系统] {result}")                               # 17. 打印命令结果
            messages.append({"role": "user", "content": f"执行完毕:{result}"})  # 18. 把结果反馈给 AI
# MIT License | 郑先隽，北师大心理学部教授，人本AI设计与创新
