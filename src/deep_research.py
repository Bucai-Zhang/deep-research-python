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

    base_learnings = learnings.copy()
    all_learnings = learnings.copy()

    base_sources = sources.copy()
    all_sources = sources.copy()



    for item in search_queries:
        search_query = item["query"]
        research_goal = item["research_goal"]

        branch_learnings = base_learnings.copy()
        branch_sources = base_sources.copy()

        print(f"\nSearching: {search_query}")

        search_result = await search_web(search_query)

        #processed_results返回learnings follow_up_questions sources
        processed_results = await process_serp_result(
            search_query,
            search_result
        )

        new_learnings = processed_results["learnings"]
        follow_up_questions = processed_results["follow_up_questions"]
        new_sources = processed_results["sources"]

        branch_learnings.extend(new_learnings)
        branch_sources.extend(new_sources)

#下一层的query是由这一层的research_goal和follow_up_questions组成的
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
                 learnings = branch_learnings,
                 sources = branch_sources
            )


            branch_learnings = recursive_result["learnings"]
            branch_sources = recursive_result["sources"]

        all_learnings.extend(branch_learnings)
        all_sources.extend(branch_sources)



    return {
        "learnings": list(dict.fromkeys(all_learnings)),
        "sources": list(dict.fromkeys(all_sources))
    }

