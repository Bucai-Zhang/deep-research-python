
"""DeepResearch 递归、并发、限流与异常处理测试。

通过 Mock 替换真实搜索和模型函数，
测试过程不会调用 Firecrawl 或 DeepSeek 接口。
"""

import asyncio
import time
import unittest
from unittest.mock import patch

from src.deep_research import deep_research, AllBranchesFailedError


class TestDeepResearch(unittest.IsolatedAsyncioTestCase):

    # ==================================================
    # 公共模拟函数：供前三项基础测试使用
    # ==================================================

    async def run_with_mock(self, depth, learnings=None, sources=None):
        received_learnings = []
        searched_queries = []

        # 模拟生成搜索词：根节点 A/B，子节点 A1/B1
        async def fake_generate(query, breadth, learnings=None):
            received_learnings.append((learnings or []).copy())

            if query == "AI Agent":
                return [
                    {"query": "A", "research_goal": "研究A"},
                    {"query": "B", "research_goal": "研究B"}
                ][:breadth]

            if query.startswith("Previous research goal: 研究A\n"):
                return [{"query": "A1", "research_goal": "研究A1"}]

            if query.startswith("Previous research goal: 研究B\n"):
                return [{"query": "B1", "research_goal": "研究B1"}]

            raise AssertionError(f"未知研究问题: {query}")

        # 模拟网页搜索
        async def fake_search(query):
            searched_queries.append(query)
            return {"query": query}

        # 模拟模型提取发现
        async def fake_process(query, search_result):
            self.assertEqual(search_result["query"], query)
            return {
                "learnings": [f"发现{query}"],
                "follow_up_questions": (
                    ["继续研究"] if len(query) == 1 else []
                ),
                "sources": [f"url_{query}"]
            }

        # 替换真实接口
        with (
            patch("src.deep_research.generate_search_queries",
                  new=fake_generate),
            patch("src.deep_research.search_web",
                  new=fake_search),
            patch("src.deep_research.process_serp_result",
                  new=fake_process)
        ):
            result = await deep_research(
                "AI Agent",
                breadth=2,
                depth=depth,
                learnings=learnings,
                sources=sources
            )

        return result, received_learnings, searched_queries

    # ==================================================
    # 测试1：只研究一层
    # ==================================================

    async def test_depth_one(self):
        result, received, searched = await self.run_with_mock(
            depth=1
        )

        self.assertEqual(result["learnings"], ["发现A", "发现B"])
        self.assertEqual(result["sources"], ["url_A", "url_B"])

        # 只生成一次查询，没有继续递归
        self.assertEqual(received, [[]])
        self.assertCountEqual(searched, ["A", "B"])

    # ==================================================
    # 测试2：两层递归和分支隔离
    # ==================================================

    async def test_depth_two(self):
        result, received, searched = await self.run_with_mock(
            depth=2
        )

        self.assertEqual(
            result["learnings"],
            ["发现A", "发现A1", "发现B", "发现B1"]
        )
        self.assertEqual(
            result["sources"],
            ["url_A", "url_A1", "url_B", "url_B1"]
        )

        # A1只能接收到发现A，B1只能接收到发现B
        self.assertCountEqual(
            received,
            [[], ["发现A"], ["发现B"]]
        )

        # 不依赖异步任务的实际启动顺序
        self.assertCountEqual(
            searched,
            ["A", "A1", "B", "B1"]
        )

    # ==================================================
    # 测试3：递归终止条件
    # ==================================================

    async def test_depth_zero(self):
        result, received, searched = await self.run_with_mock(
            depth=0,
            learnings=["已有发现"],
            sources=["已有来源"]
        )

        self.assertEqual(result["learnings"], ["已有发现"])
        self.assertEqual(result["sources"], ["已有来源"])

        # depth=0时不能发起任何搜索
        self.assertEqual(received, [])
        self.assertEqual(searched, [])

    # ==================================================
    # 测试4：并发执行与模拟性能对照
    # ==================================================

    async def test_parallel_branches(self):
        active = 0
        max_active = 0
        events = []

        async def fake_generate(query, breadth, learnings=None):
            return [
                {"query": "A", "research_goal": "研究A"},
                {"query": "B", "research_goal": "研究B"}
            ][:breadth]

        async def fake_search(query):
            nonlocal active, max_active

            active += 1
            max_active = max(max_active, active)
            events.append(f"{query}开始")

            try:
                # 模拟网络等待，不阻塞事件循环
                await asyncio.sleep(0.1)
                return {"query": query}
            finally:
                active -= 1
                events.append(f"{query}结束")

        async def fake_process(query, result):
            self.assertEqual(result["query"], query)
            return {
                "learnings": [f"发现{query}"],
                "follow_up_questions": [],
                "sources": [f"url_{query}"]
            }

        # 串行模拟基准
        start = time.perf_counter()
        await fake_search("A")
        await fake_search("B")
        serial_time = time.perf_counter() - start

        max_active = 0
        events.clear()

        # 实际使用 deep_research 的并发调度逻辑
        with (
            patch("src.deep_research.generate_search_queries",
                  new=fake_generate),
            patch("src.deep_research.search_web",
                  new=fake_search),
            patch("src.deep_research.process_serp_result",
                  new=fake_process)
        ):
            start = time.perf_counter()
            result = await deep_research(
                "AI Agent", breadth=2, depth=1
            )
            parallel_time = time.perf_counter() - start

        print(f"\n串行模拟搜索耗时: {serial_time:.3f}s")
        print(f"并发研究耗时: {parallel_time:.3f}s")
        print(f"最大同时搜索数: {max_active}")
        print(f"执行事件: {events}")

        # 证明A、B确实发生了执行重叠
        self.assertEqual(max_active, 2)
        self.assertEqual(active, 0)
        self.assertLess(
            events.index("B开始"),
            events.index("A结束")
        )

        # 并发不应该改变最终研究结果
        self.assertEqual(result["learnings"], ["发现A", "发现B"])
        self.assertEqual(result["sources"], ["url_A", "url_B"])

    # ==================================================
    # 测试5：全局搜索并发限制
    # ==================================================

    async def test_global_search_limit(self):
        active = 0
        max_active = 0
        searched = []

        # 构造两层研究：A/B/C/D -> A1/B1/C1/D1
        async def fake_generate(query, breadth, learnings=None):
            if query == "AI Agent":
                return [
                    {"query": n, "research_goal": f"研究{n}"}
                    for n in "ABCD"
                ][:breadth]

            for n in "ABCD":
                if query.startswith(
                    f"Previous research goal: 研究{n}\n"
                ):
                    self.assertEqual(learnings, [f"发现{n}"])
                    return [
                        {"query": f"{n}1",
                         "research_goal": f"研究{n}1"}
                    ]

            raise AssertionError(f"未知研究问题: {query}")

        async def fake_search(query):
            nonlocal active, max_active

            active += 1
            max_active = max(max_active, active)
            searched.append(query)

            try:
                await asyncio.sleep(0.05)
                return {"query": query}
            finally:
                active -= 1

        async def fake_process(query, result):
            self.assertEqual(result["query"], query)
            return {
                "learnings": [f"发现{query}"],
                "follow_up_questions": (
                    ["继续研究"] if len(query) == 1 else []
                ),
                "sources": [f"url_{query}"]
            }

        with (
            patch("src.deep_research.generate_search_queries",
                  new=fake_generate),
            patch("src.deep_research.search_web",
                  new=fake_search),
            patch("src.deep_research.process_serp_result",
                  new=fake_process)
        ):
            result = await deep_research(
                "AI Agent", breadth=4, depth=2
            )

        expected = [
            "A", "A1", "B", "B1",
            "C", "C1", "D", "D1"
        ]

        print(f"\n最大同时搜索数量: {max_active}")
        print(f"实际启动的搜索: {searched}")

        # 全部8个搜索都执行，但最多同时运行2个
        self.assertEqual(max_active, 2)
        self.assertEqual(active, 0)
        self.assertCountEqual(searched, expected)

        self.assertEqual(
            result["learnings"],
            [f"发现{n}" for n in expected]
        )
        self.assertEqual(
            result["sources"],
            [f"url_{n}" for n in expected]
        )

    # ==================================================
    # 测试6：全局模型并发限制
    # ==================================================

    async def test_global_model_limit(self):
        active_models = 0
        max_active_models = 0
        generate_calls = []
        process_calls = []

        # 两种模型操作共用同一个计数器
        async def fake_model_call():
            nonlocal active_models, max_active_models

            active_models += 1
            max_active_models = max(
                max_active_models, active_models
            )

            try:
                await asyncio.sleep(0.03)
            finally:
                active_models -= 1

        async def fake_generate(query, breadth, learnings=None):
            generate_calls.append(query)
            await fake_model_call()

            if query == "AI Agent":
                return [
                    {"query": n, "research_goal": f"研究{n}"}
                    for n in "ABCD"
                ][:breadth]

            for n in "ABCD":
                if query.startswith(
                    f"Previous research goal: 研究{n}\n"
                ):
                    self.assertEqual(learnings, [f"发现{n}"])
                    return [
                        {"query": f"{n}1",
                         "research_goal": f"研究{n}1"}
                    ]

            raise AssertionError(f"未知研究问题: {query}")

        async def fake_search(query):
            await asyncio.sleep(0.01)
            return {"query": query}

        async def fake_process(query, result):
            self.assertEqual(result["query"], query)
            process_calls.append(query)

            # 模拟一次模型处理请求
            await fake_model_call()

            return {
                "learnings": [f"发现{query}"],
                "follow_up_questions": (
                    ["继续研究"] if len(query) == 1 else []
                ),
                "sources": [f"url_{query}"]
            }

        with (
            patch("src.deep_research.generate_search_queries",
                  new=fake_generate),
            patch("src.deep_research.search_web",
                  new=fake_search),
            patch("src.deep_research.process_serp_result",
                  new=fake_process)
        ):
            result = await deep_research(
                "AI Agent", breadth=4, depth=2
            )

        expected = [
            "A", "A1", "B", "B1",
            "C", "C1", "D", "D1"
        ]

        print(f"\n最大同时模型处理数: {max_active_models}")
        print(f"生成查询调用次数: {len(generate_calls)}")
        print(f"处理搜索结果调用次数: {len(process_calls)}")

        # 查询生成与结果提取共同遵守并发上限2
        self.assertEqual(max_active_models, 2)
        self.assertEqual(active_models, 0)
        self.assertEqual(len(generate_calls), 5)
        self.assertCountEqual(process_calls, expected)

        self.assertEqual(
            result["learnings"],
            [f"发现{n}" for n in expected]
        )
        self.assertEqual(
            result["sources"],
            [f"url_{n}" for n in expected]
        )

    # ==================================================
    # 测试7：同层研究分支失败隔离
    # ==================================================

    async def test_branch_failure_isolation(self):
        searched = []
        processed = []

        async def fake_generate(query, breadth, learnings=None):
            return [
                {"query": n, "research_goal": f"研究{n}"}
                for n in "ABC"
            ][:breadth]

        async def fake_search(query):
            searched.append(query)
            await asyncio.sleep(0)

            # 故意让B分支搜索超时
            if query == "B":
                raise TimeoutError("模拟B搜索超时")

            return {"query": query}

        async def fake_process(query, result):
            self.assertEqual(result["query"], query)
            processed.append(query)
            return {
                "learnings": [f"发现{query}"],
                "follow_up_questions": [],
                "sources": [f"url_{query}"]
            }

        with (
            patch("src.deep_research.generate_search_queries",
                  new=fake_generate),
            patch("src.deep_research.search_web",
                  new=fake_search),
            patch("src.deep_research.process_serp_result",
                  new=fake_process)
        ):
            result = await deep_research(
                "AI Agent", breadth=3, depth=1
            )

        # B失败不能影响A、C
        self.assertCountEqual(searched, ["A", "B", "C"])
        self.assertCountEqual(processed, ["A", "C"])

        self.assertEqual(
            result["learnings"],
            ["发现A", "发现C"]
        )
        self.assertEqual(
            result["sources"],
            ["url_A", "url_C"]
        )

    # ==================================================
    # 测试8：子分支失败时保留父分支已有成果
    # ==================================================

    async def test_parent_result_preserved(self):
        searched = []
        processed = []

        # 第一层A、B；第二层分别是A1、B1
        async def fake_generate(query, breadth, learnings=None):
            if query == "AI Agent":
                return [
                    {"query": "A", "research_goal": "研究A"},
                    {"query": "B", "research_goal": "研究B"}
                ][:breadth]

            for n in "AB":
                if query.startswith(
                    f"Previous research goal: 研究{n}\n"
                ):
                    # 子层只接收到所属父分支的成果
                    self.assertEqual(learnings, [f"发现{n}"])
                    return [
                        {"query": f"{n}1",
                         "research_goal": f"研究{n}1"}
                    ]

            raise AssertionError(f"未知研究问题: {query}")

        async def fake_search(query):
            searched.append(query)
            await asyncio.sleep(0)

            # A已经成功，但A1发生网络故障
            if query == "A1":
                raise TimeoutError("模拟A1搜索超时")

            return {"query": query}

        async def fake_process(query, result):
            self.assertEqual(result["query"], query)
            processed.append(query)

            return {
                "learnings": [f"发现{query}"],
                "follow_up_questions": (
                    ["继续研究"] if query in ("A", "B") else []
                ),
                "sources": [f"url_{query}"]
            }

        with (
            patch("src.deep_research.generate_search_queries",
                  new=fake_generate),
            patch("src.deep_research.search_web",
                  new=fake_search),
            patch("src.deep_research.process_serp_result",
                  new=fake_process)
        ):
            result = await deep_research(
                "AI Agent", breadth=2, depth=2
            )

        # 四次搜索都应该被尝试
        self.assertCountEqual(
            searched,
            ["A", "A1", "B", "B1"]
        )

        # A1没有成功获取内容，不能进入结果处理
        self.assertCountEqual(
            processed,
            ["A", "B", "B1"]
        )

        # 最关键的断言：
        # A1失败，但是已经获得的发现A不能丢失
        self.assertEqual(
            result["learnings"],
            ["发现A", "发现B", "发现B1"]
        )
        self.assertEqual(
            result["sources"],
            ["url_A", "url_B", "url_B1"]
        )

    # ==================================================
    # 测试9：根节点所有分支失败时必须抛出异常
    # ==================================================

    async def test_all_root_branches_failed(self):
        searched = []

        async def fake_generate(query, breadth, learnings=None):
            return [
                {"query": "A", "research_goal": "研究A"},
                {"query": "B", "research_goal": "研究B"}
            ][:breadth]

        async def fake_search(query):
            searched.append(query)

            # A和B全部失败
            raise TimeoutError(f"模拟{query}搜索超时")

        async def fake_process(query, result):
            # 因为搜索全部失败，理论上不应执行到这里
            self.fail("搜索失败后不应该处理搜索结果")

        with (
            patch("src.deep_research.generate_search_queries",
                  new=fake_generate),
            patch("src.deep_research.search_web",
                  new=fake_search),
            patch("src.deep_research.process_serp_result",
                  new=fake_process)
        ):
            # 预期 deep_research 主动抛出指定异常
            with self.assertRaisesRegex(
                AllBranchesFailedError,
                "所有研究分支均失败"
            ):
                await deep_research(
                    "AI Agent", breadth=2, depth=1
                )

        # 两个分支都尝试执行了搜索
        self.assertCountEqual(searched, ["A", "B"])


    # ==================================================
    # 测试10：未知程序异常不能被当作普通网络故障跳过
    # ==================================================

    async def test_unexpected_exception_propagates(self):

        # 模拟生成一个搜索分支
        async def fake_generate(query, breadth, learnings=None):
            return [
                {"query": "A", "research_goal": "研究A"}
            ]

        # 模拟网页搜索正常返回
        async def fake_search(query):
            return {"query": query}

        # 故意模拟程序错误：缺少预期字段
        async def fake_process(query, search_result):
            raise KeyError("learnings")

        # 替换真实外部接口
        with (
            patch(
                "src.deep_research.generate_search_queries",
                new=fake_generate
            ),
            patch(
                "src.deep_research.search_web",
                new=fake_search
            ),
            patch(
                "src.deep_research.process_serp_result",
                new=fake_process
            )
        ):

            # 我们预期 KeyError 必须向上传播
            with self.assertRaisesRegex(KeyError, "learnings"):
                await deep_research(
                    "AI Agent",
                    breadth=1,
                    depth=1
                )


if __name__ == "__main__":
    unittest.main()
