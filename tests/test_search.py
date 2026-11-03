import asyncio
import unittest

from firecrawl import AsyncFirecrawl
from unittest.mock import AsyncMock, patch

import src.search as search_module


class TestSearchWeb(unittest.IsolatedAsyncioTestCase):

    async def test_async_client(self):
        # 验证使用的是异步客户端
        self.assertIsInstance(
            search_module.firecrawl, AsyncFirecrawl
        )

        fake_result = object()
        fake_search = AsyncMock(return_value=fake_result)

        with patch.object(
            search_module.firecrawl,
            "search",
            new=fake_search
        ):
            result = await search_module.search_web("测试问题")

        self.assertIs(result, fake_result)
        fake_search.assert_awaited_once_with(
            "测试问题",
            limit=5,
            scrape_options={"formats": ["markdown"]}
        )

    async def test_non_blocking(self):
        order = []

        async def fake_search(query, **kwargs):
            order.append("A开始")
            await asyncio.sleep(0.05)
            order.append("A结束")
            return "模拟搜索结果"

        async def task_b():
            await asyncio.sleep(0.01)
            order.append("B执行")

        with patch.object(
            search_module.firecrawl,
            "search",
            new=fake_search
        ):
            result_a, _ = await asyncio.gather(
                search_module.search_web("A"),
                task_b()
            )

        self.assertEqual(result_a, "模拟搜索结果")
        self.assertEqual(
            order,
            ["A开始", "B执行", "A结束"]
        )