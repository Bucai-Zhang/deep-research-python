import asyncio

from src.feedback import generate_feedback
from src.deep_research import deep_research
from src.report import write_final_report,write_final_answer,save_report

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
        print("Begin clarifying questions...", flush=True)
        questions = await generate_feedback(initial_query)
        print("Feedback returned successfully.", flush=True)

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


    research_result = await deep_research(
        combined_query,
        breadth=breadth,
        depth=depth
    )

    print("\nResearch Learnings:")

    for learning in research_result["learnings"]:
        print("-",learning)

    print("\nSources:")

    for source in research_result["sources"]:
        print("-", source)

    if is_report:
        print("\nGenerating final report...")

        output = await write_final_report(
            query = combined_query,
            learnings = research_result["learnings"],
            sources = research_result["sources"],
        )


    else:
        print("\nGenerating final answer...")

        output = await write_final_answer(
            query=combined_query,
            learnings=research_result["learnings"]
        )



    title = output["title"]
    content = output["content"]
    print("\nTitle:", title)
    print("\nFinal output:\n", content)
    prefix = "report" if is_report else "answer"
    file_path = save_report(content, title=title, prefix=prefix)
    print("\nOutput saved to:", file_path)


if __name__ == "__main__":
    asyncio.run(main())






