"""
Integration tests - 需要网络访问 (在 fnos Docker 容器中运行)
标记: @pytest.mark.integration
"""
import pytest


@pytest.mark.integration
class TestIntegrationSearchComic:
    """真实 API 搜索测试"""

    def test_search_comic_returns_results(self):
        """搜索 '汉化' 应返回结果"""
        from src.plugins.onebot_plugin_jmdown.comic import search_comic

        result = search_comic("汉化", page=1)

        assert "results" in result
        assert len(result["results"]) > 0
        assert "id" in result["results"][0]
        assert "name" in result["results"][0]

    def test_search_comic_noai(self):
        """noai 过滤应移除 AI 内容"""
        from src.plugins.onebot_plugin_jmdown.comic import search_comic

        result = search_comic("汉化", page=1, noai=True)

        for r in result["results"]:
            assert "AI Generated" not in r["name"]
            assert "AI生成" not in r["name"]

    def test_search_comic_smart(self):
        """智能搜索应返回带 match 字段的结果"""
        from src.plugins.onebot_plugin_jmdown.comic import search_comic_smart

        result = search_comic_smart("萝莉", page=1)

        assert "results" in result
        assert len(result["results"]) > 0
        # 至少有一个有 match 字段
        assert any("match" in r for r in result["results"])

    def test_search_comic_by_tag(self):
        """标签搜索应返回相关结果"""
        from src.plugins.onebot_plugin_jmdown.comic import search_comic_by_tag

        result = search_comic_by_tag("萝莉", page=1)

        assert "results" in result
        assert len(result["results"]) > 0

    def test_search_empty_query(self):
        """空查询应返回结果（API 返回热门/随机）或错误"""
        from src.plugins.onebot_plugin_jmdown.comic import search_comic

        result = search_comic("", page=1)

        # API 可能返回结果也可能报错，两种都算正常
        assert "results" in result or "error" in result


@pytest.mark.integration
class TestIntegrationRanking:
    """真实 API 排行榜测试"""

    def test_week_ranking(self):
        """周榜应返回结果"""
        from src.plugins.onebot_plugin_jmdown.comic import get_ranking

        result = get_ranking(time="w", page=1)

        assert "results" in result
        # 周榜可能为空（API 限制），但不应报错
        assert "error" not in result

    def test_month_ranking(self):
        """月榜应返回结果"""
        from src.plugins.onebot_plugin_jmdown.comic import get_ranking

        result = get_ranking(time="m", page=1)

        assert "results" in result
        assert len(result["results"]) > 0

    def test_all_ranking(self):
        """总榜应返回结果"""
        from src.plugins.onebot_plugin_jmdown.comic import get_ranking

        result = get_ranking(time="a", page=1)

        assert "results" in result
        assert len(result["results"]) > 0


@pytest.mark.integration
class TestIntegrationDetail:
    """真实 API 详情查询测试"""

    def test_valid_id(self):
        """有效 ID 应返回完整详情"""
        from src.plugins.onebot_plugin_jmdown.comic import get_comic_detail

        result = get_comic_detail("114514")

        assert result["id"] == "114514"
        assert "name" in result
        assert "author" in result
        assert "tags" in result
        assert isinstance(result["tags"], list)
        assert result["chapters"] > 0

    def test_invalid_id(self):
        """无效 ID 应返回 error"""
        from src.plugins.onebot_plugin_jmdown.comic import get_comic_detail

        result = get_comic_detail("999999999")

        assert "error" in result


@pytest.mark.integration
class TestIntegrationDownload:
    """真实下载测试（不实际运行，只测试前置检查）"""

    def test_get_comic_info_valid(self):
        """有效 ID 应能获取信息"""
        from src.plugins.onebot_plugin_jmdown.comic import get_comic_info

        result = get_comic_info("114514")

        assert "name" in result
        assert "tags" in result
        assert "episode_count" in result

    def test_get_comic_info_invalid(self):
        """无效 ID 应返回 error"""
        from src.plugins.onebot_plugin_jmdown.comic import get_comic_info

        result = get_comic_info("999999999")

        assert "error" in result
