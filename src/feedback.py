import os
import json

from dotenv import load_dotenv
from openai import AsyncOpenAI
from src.prompt import system_prompt

load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key or api_key == "DEEPSEEK_API_KEY":
    raise RuntimeError("请正确配置 DEEPSEEK_API_KEY")

client = AsyncOpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)

async def generate_feedback(query,num_questions=3):
    prompt = (
        "Given the user's research topic,generate follow-up "
        "questions that help clarify their research needs. "
        f"Generate at most {num_questions} questions. "
        "If the topic is already sufficiently clear,return fewer questions. "
        f"<query>{query}</query>\n "
        'Return only valid JSON in this format: '
        '{"questions":["question 1","question 2"]}.'
    )

    response = await client.chat.completions.create(
        model = "deepseek-flash",
        messages=[
            {"role":"system","content":system_prompt()},
            {"role":"user","content":prompt},
        ],
        response_format = {"type": "json_object"},
        max_tokens=500
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError("模型返回了空内容")

    data = json.loads(content)

    if not isinstance(data,dict):
        raise ValueError("模型没有返回 JSON 对象0")

    questions = data.get("questions")

    if not isinstance(questions,list):
        raise ValueError("questions 必须是列表")

    if not all(isinstance(q,str) for q in questions):
        raise ValueError("questions 中的元素必须是字符串")

    return questions[:num_questions]









