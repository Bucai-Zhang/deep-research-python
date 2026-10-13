import asyncio

from src.feedback import generate_feedback
from src.search_queries import generate_search_queries
from src.search import search_web
from src.process_result import process_serp_result

async def main():
    initial_query = input(
        'What would you like to research? '
    )

    try:
        breadth = int(input("please input the breadth (recommended 2-10,default 4)") or 4) or 4  # 外边的or 4 处理输入0的情况，输入0采用默认值
    except ValueError:
        breadth = 4

    try:
        depth = int(input("please input the depth (recommended 1-5,default 2)") or 2) or 2
    except ValueError:
        depth = 2

    is_report = (
            input(
                'Do you want to generate a long report or a specific answer? (report/answer, default report): '
            ) != 'answer'
    )

    combined_query = initial_query

    if is_report:
        print("Begin clarifying questions...")

        questions = await generate_feedback(initial_query)

        if questions:
            combined_query += "\n\nFollow-up questions and answers:"

        for question in questions:
            answer = input(
                f"{question}\nYour answer: "
            )
            combined_query += (
                f"\nQ:{question}"
                f"\nAnswer:{answer}"
            )

    print("\n整理后的研究需求: ")

    search_queries = await generate_search_queries(
        combined_query,
        breadth
    )

    print("\nGenerated search queries: ")


    learnings = []
    follow_up_questions = []

    for item in search_queries:

        print("\nQuery:", item["query"])
        print("Research goal:", item["research_goal"])

        results = await search_web(
            item["query"]
        )

        processed_results = await process_serp_result(
            item["query"],
            results
        )

        learnings.extend(
            processed_results["learnings"]
        )

        follow_up_questions.extend(
            processed_results["follow_up_questions"]
        )

        print("\nLearnings:")
        for learning in learnings:
            print("-",learning)

        print("\nFollow-up Questions: ")
        for question in follow_up_questions:
            print("-",question)








if __name__ == "__main__":
    asyncio.run(main())






