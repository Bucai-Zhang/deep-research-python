
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.text_processing import (
    select_chunks,
    select_global_candidates,
    build_candidates,
)

import src.process_result as module


def make_document(markdown, description=None, url=None, title="测试网页"):
    return SimpleNamespace(
        markdown=markdown,
        metadata=SimpleNamespace(
            title=title,
            url=url,
            description=description,
        ),
    )


class TestProcessResult(unittest.IsolatedAsyncioTestCase):

    # 测试1：长文章末尾信息筛选、摘要回退和来源收集
    async def test_chunk_selection_and_fallback(self):
        long_text = "无关背景。" * 1600 + "隐私风险研究的重要发现"

        result = SimpleNamespace(web=[
            make_document(long_text, url="https://example.com/a"),
            make_document(
                None,
                "备用摘要内容",
                "https://example.com/b"
            ),
            make_document(
                None,
                None,
                "https://example.com/c"
            ),
        ])

        response = SimpleNamespace(choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=(
                        '{"learnings":["发现1"],'
                        '"follow_up_questions":["继续研究什么？"]}'
                    )
                ),
                finish_reason="stop",
            )
        ])

        fake_create = AsyncMock(return_value=response)

        fake_client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=fake_create
                )
            )
        )

        with (
            patch.object(module, "client", fake_client),
            patch.object(
                module,
                "extract_keywords",
                return_value=["隐私", "风险"]
            ),
            patch.object(
                module,
                "system_prompt",
                return_value="测试系统提示词"
            ),
        ):
            output = await module.process_serp_result(
                "医疗风险",
                result
            )

        prompt = fake_create.await_args.kwargs["messages"][1]["content"]

        self.assertIn("隐私风险研究的重要发现", prompt)
        self.assertIn("备用摘要内容", prompt)
        self.assertNotIn("No content available", prompt)
        self.assertNotIn("https://example.com/c", prompt)
        self.assertNotIn(long_text, prompt)

        self.assertEqual(output["learnings"], ["发现1"])

        self.assertEqual(
            output["follow_up_questions"],
            ["继续研究什么？"]
        )

        self.assertEqual(
            output["sources"],
            [
                "https://example.com/a",
                "https://example.com/b",
            ]
        )

        fake_create.assert_awaited_once()

    # 测试2：没有有效网页内容时，不调用大模型
    async def test_empty_content(self):
        result = SimpleNamespace(web=[
            make_document(
                None,
                None,
                "https://example.com/empty"
            )
        ])

        fake_create = AsyncMock()

        fake_client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=fake_create
                )
            )
        )

        with (
            patch.object(module, "client", fake_client),
            patch.object(
                module,
                "extract_keywords",
                return_value=["风险"]
            ),
        ):
            output = await module.process_serp_result(
                "医疗风险",
                result
            )

        self.assertEqual(
            output,
            {
                "learnings": [],
                "follow_up_questions": [],
                "sources": [],
            }
        )

        fake_create.assert_not_awaited()

    # 测试3：相关性筛选后恢复原文顺序
    def test_chunk_order(self):
        chunks = [
            "介绍风险",
            "无关背景",
            "隐私和风险"
        ]

        keywords = ["风险", "隐私"]

        selected = select_chunks(
            chunks,
            keywords,
            max_chunks=2
        )

        self.assertEqual(
            selected,
            [chunks[0], chunks[2]]
        )

    # 测试4：全局字符预算和来源多样性
    def test_global_budget_and_diversity(self):
        candidates = [
            {
                "text": "A" * 2000,
                "score": 10,
                "url": "A",
                "index": 0
            },
            {
                "text": "A" * 2000,
                "score": 9,
                "url": "A",
                "index": 1
            },
            {
                "text": "B" * 2000,
                "score": 8,
                "url": "B",
                "index": 0
            },
            {
                "text": "C" * 2000,
                "score": 7,
                "url": "C",
                "index": 0
            },
        ]

        selected = select_global_candidates(
            candidates,
            max_chars=6000
        )

        self.assertEqual(
            [item["url"] for item in selected],
            ["A", "B", "C"]
        )

        self.assertLessEqual(
            sum(len(item["text"]) for item in selected),
            6000
        )

    # 测试5：文章末尾重要信息与头部截断方案对比
    def test_tail_vs_head_truncation(self):
        text = "普通背景。" * 1000 + "隐私风险：患者数据泄露"
        keywords = ["隐私", "风险"]
        budget = 2000

        # 方案A：直接保留文章前2000个字符
        baseline = text[:budget]

        # 方案B：分块、关键词评分和全局筛选
        candidates = build_candidates(
            text,
            "https://example.com",
            keywords
        )

        selected = select_global_candidates(
            candidates,
            max_chars=budget
        )

        optimized = "\n".join(
            candidate["text"] for candidate in selected
        )

        # 检查重要信息是否保留
        self.assertNotIn("隐私风险", baseline)
        self.assertIn("隐私风险", optimized)

        # 检查新方案没有超过正文字符预算
        self.assertLessEqual(
            sum(len(item["text"]) for item in selected),
            budget
        )


if __name__ == "__main__":
    unittest.main()
