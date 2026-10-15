from src.search_queries import generate_search_queries
from src.search import search_web
from src.process_result import process_serp_result

async def deep_research(
        query,
        breadth=4,
        depth = 2,
        learnings = None,
        sources = None
):
    if learnings is None:
        learnings=[]

    if sources is None:
        sources=[]

    if depth <= 0:
        return {
            "learnings": learnings,
            "sources": sources
        }

    print(f"\nResearch depth remaining: {depth}")
    print(f"Research breadth: {breadth}")

    search_queries = await generate_search_queries(
        query,
        breadth,
        learnings=learnings
    )

    for item in search_queries:
        search_query = item["query"]
        research_goal = item["research_goal"]

        print(f"\nSearching: {search_query}")

        search_result = await search_web(search_query)

        processed_results = await process_serp_result(
            search_query,
            search_result
        )

        new_learnings = processed_results["learnings"]
        follow_up_questions = processed_results["follow_up_questions"]
        new_sources = processed_results["sources"]

        learnings.extend(new_learnings)
        sources.extend(new_sources)

        if depth > 1 and follow_up_questions:
            next_query = (
                f"Previous research goal: {research_goal}\n"
                f"Follow-up questions:\n"
                 + '\n'.join(follow_up_questions)
             )

            next_breadth = max(1,breadth // 2)

            recursive_result = await deep_research(
                 query = next_query,
                 breadth = next_breadth,
                 depth = depth - 1,
                 learnings = learnings,
                 sources = sources
            )


            learnings = recursive_result["learnings"]
            sources = recursive_result["sources"]

    return {
        "learnings": list(dict.fromkeys(learnings)),
        "sources": list(dict.fromkeys(sources))
    }

