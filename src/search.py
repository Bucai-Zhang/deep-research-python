import os
import asyncio

from dotenv import load_dotenv
from firecrawl import AsyncFirecrawl



load_dotenv()

firecrawl_key = os.getenv("FIRECRAWL_KEY")

if not firecrawl_key:
    raise RuntimeError("FIRECRAWL_KEY is missing")

firecrawl = AsyncFirecrawl(
    api_key = firecrawl_key
)

async def search_web(query):
    result = await firecrawl.search(
        query,
        limit=5,
        scrape_options={
            "formats": ["markdown"]
    }
    )


    return result


if __name__ == "__main__":
    asyncio.run(search_web("人工智能在医疗领域的应用"))
