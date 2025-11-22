from openai import OpenAI

client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="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",
)

completion = client.chat.completions.create(
  model="meituan/longcat-flash-chat:free",
  messages=[
              {
                "role": "user",
                "content": "Can you act as Chatbot for disaster aid website?"
              }
            ]
)
print(completion.choices[0].message.content)