import json

from src.prompt import system_prompt
from src.feedback import client

async def generate_search_queries(
        query,
        num_queries=3,
        learnings=None
):
    prompt = (
        "Generate search queries for researching the following topic. "
        f"Generate at most {num_queries} search queries. "
        "Each query should focus on a different research direction.\n"
        f"<query>{query}</query>\n"
        "Return JSON format:\n"
        '{"queries":[{"query":"...","research_goal":"..."}]}'
    )


    response = await client.chat.completions.create(
        model = "deepseek-flash",
        messages = [
            {
                "role":"system",
                "content":system_prompt()
            },

            {
                "role":"user",
                "content":prompt
            }
        ],

        response_format={
            "type":"json_object"
        }
    )

    content = response.choices[0].message.content
    data = json.loads(content)
    queries = data.get("queries")

    if not isinstance(queries,list):
        raise ValueError("queries must be a list")

    return queries[:num_queries]

