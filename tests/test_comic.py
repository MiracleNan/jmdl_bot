"""
Tests for comic.py - 搜索/排行榜/详情/标签统计
"""
import os
import json
import tempfile
import pytest
from unittest.mock import patch, MagicMock


# ============ count_tag ============

class TestCountTag:
    """标签统计测试"""

    def test_count_tag_new_file(self, tmp_dir):
        """新文件应创建并写入统计"""
        from src.plugins.onebot_plugin_jmdown.comic import count_tag

        # mock 当前目录
        with patch("src.plugins.onebot_plugin_jmdown.comic.os.path.dirname") as mock_dir:
            mock_dir.return_value = tmp_dir
            tags_dir = os.path.join(tmp_dir, "tags")
            os.makedirs(tags_dir, exist_ok=True)

            result = count_tag(tags=["萝莉", "全彩", "中文"], filename="test_group.txt")

        assert "萝莉" in result
        assert result["萝莉"] == 1
        assert "全彩" not in result  # 被过滤
        assert "中文" not in result  # 被过滤

    def test_count_tag_accumulate(self, tmp_dir):
        """多次调用应累加统计"""
        from src.plugins.onebot_plugin_jmdown.comic import count_tag

        with patch("src.plugins.onebot_plugin_jmdown.comic.os.path.dirname") as mock_dir:
            mock_dir.return_value = tmp_dir
            tags_dir = os.path.join(tmp_dir, "tags")
            os.makedirs(tags_dir, exist_ok=True)

            count_tag(tags=["萝莉", "巨乳"], filename="acc.txt")
            result = count_tag(tags=["萝莉", "学生"], filename="acc.txt")

        assert result["萝莉"] == 2
        assert result["巨乳"] == 1
        assert result["学生"] == 1

    def test_count_tag_default_none(self, tmp_dir):
        """tags=None 不崩溃"""
        from src.plugins.onebot_plugin_jmdown.comic import count_tag

        with patch("src.plugins.onebot_plugin_jmdown.comic.os.path.dirname") as mock_dir:
            mock_dir.return_value = tmp_dir
            tags_dir = os.path.join(tmp_dir, "tags")
            os.makedirs(tags_dir, exist_ok=True)

            result = count_tag(tags=None, filename="none.txt")

        assert isinstance(result, dict)


# ============ get_comic_info ============

class TestGetComicInfo:
    """漫画信息查询测试"""

    @patch("src.plugins.onebot_plugin_jmdown.comic.JmOption")
    def test_get_comic_info_success(self, mock_option, mock_jm_client):
        """正常查询返回完整信息"""
        mock_option.default.return_value.new_jm_client.return_value = mock_jm_client

        from src.plugins.onebot_plugin_jmdown.comic import get_comic_info
        result = get_comic_info("114514")

        assert "name" in result
        assert "author" in result
        assert "tags" in result
        assert "episode_count" in result
        assert isinstance(result["tags"], list)

    @patch("src.plugins.onebot_plugin_jmdown.comic.JmOption")
    def test_get_comic_info_invalid_id(self, mock_option):
        """无效 ID 返回 error"""
        mock_client = MagicMock()
        mock_client.get_album_detail.side_effect = Exception("不存在")
        mock_option.default.return_value.new_jm_client.return_value = mock_client

        from src.plugins.onebot_plugin_jmdown.comic import get_comic_info
        result = get_comic_info("999999999")

        assert "error" in result


# ============ search_comic (标题搜索) ============

class TestSearchComic:
    """标题搜索测试"""

    @patch("src.plugins.onebot_plugin_jmdown.comic.JmOption")
    def test_search_returns_results(self, mock_option, mock_jm_client):
        """正常搜索返回结果列表"""
        mock_option.default.return_value.new_jm_client.return_value = mock_jm_client

        from src.plugins.onebot_plugin_jmdown.comic import search_comic
        result = search_comic("测试", page=1)

        assert "results" in result
        assert len(result["results"]) == 5
        assert "total" in result

    @patch("src.plugins.onebot_plugin_jmdown.comic.JmOption")
    def test_search_noai_filters(self, mock_option, mock_jm_client):
        """noai=True 过滤掉 AI Generated/AI生成"""
        mock_option.default.return_value.new_jm_client.return_value = mock_jm_client

        from src.plugins.onebot_plugin_jmdown.comic import search_comic
        result = search_comic("测试", page=1, noai=True)

        for r in result["results"]:
            assert "AI Generated" not in r["name"]
            assert "AI生成" not in r["name"]

    @patch("src.plugins.onebot_plugin_jmdown.comic.JmOption")
    def test_search_max_5_results(self, mock_option, mock_jm_client):
        """每页最多返回 5 条"""
        mock_option.default.return_value.new_jm_client.return_value = mock_jm_client

        from src.plugins.onebot_plugin_jmdown.comic import search_comic
        result = search_comic("测试")

        assert len(result["results"]) <= 5

    @patch("src.plugins.onebot_plugin_jmdown.comic.JmOption")
    def test_search_error_handling(self, mock_option):
        """API 异常返回 error"""
        mock_client = MagicMock()
        mock_client.search_site.side_effect = Exception("网络错误")
        mock_option.default.return_value.new_jm_client.return_value = mock_client

        from src.plugins.onebot_plugin_jmdown.comic import search_comic
        result = search_comic("测试")

        assert "error" in result


# ============ search_comic_smart (智能搜索) ============

class TestSearchComicSmart:
    """智能搜索测试 (标题+标签双搜)"""

    @patch("src.plugins.onebot_plugin_jmdown.comic.JmOption")
    def test_smart_search_merges_results(self, mock_option, mock_jm_client):
        """智能搜索合并标题和标签结果"""
        mock_option.default.return_value.new_jm_client.return_value = mock_jm_client

        from src.plugins.onebot_plugin_jmdown.comic import search_comic_smart
        result = search_comic_smart("萝莉", page=1)

        assert "results" in result
        assert len(result["results"]) > 0
        # 应该有双命中、标题命中、标签命中
        matches = {r.get("match") for r in result["results"]}
        assert len(matches) >= 2  # 至少两种匹配类型

    @patch("src.plugins.onebot_plugin_jmdown.comic.JmOption")
    def test_smart_search_dual_hit_first(self, mock_option, mock_jm_client):
        """双命中的结果排在最前面"""
        mock_option.default.return_value.new_jm_client.return_value = mock_jm_client

        from src.plugins.onebot_plugin_jmdown.comic import search_comic_smart
        result = search_comic_smart("萝莉", page=1)

        # 检查双命中是否在前面
        first_match = result["results"][0].get("match") if result["results"] else None
        assert first_match == "双命中"

    @patch("src.plugins.onebot_plugin_jmdown.comic.JmOption")
    def test_smart_search_deduplicates(self, mock_option, mock_jm_client):
        """同一 ID 不会出现两次"""
        mock_option.default.return_value.new_jm_client.return_value = mock_jm_client

        from src.plugins.onebot_plugin_jmdown.comic import search_comic_smart
        result = search_comic_smart("测试", page=1)

        ids = [r["id"] for r in result["results"]]
        assert len(ids) == len(set(ids))


# ============ search_comic_by_tag ============

class TestSearchComicByTag:
    """标签搜索测试"""

    @patch("src.plugins.onebot_plugin_jmdown.comic.JmOption")
    def test_tag_search_returns_results(self, mock_option, mock_jm_client):
        """标签搜索返回结果"""
        mock_option.default.return_value.new_jm_client.return_value = mock_jm_client

        from src.plugins.onebot_plugin_jmdown.comic import search_comic_by_tag
        result = search_comic_by_tag("萝莉", page=1)

        assert "results" in result
        assert len(result["results"]) > 0

    @patch("src.plugins.onebot_plugin_jmdown.comic.JmOption")
    def test_tag_search_noai(self, mock_option, mock_jm_client):
        """标签搜索也支持 noai"""
        mock_option.default.return_value.new_jm_client.return_value = mock_jm_client

        from src.plugins.onebot_plugin_jmdown.comic import search_comic_by_tag
        result = search_comic_by_tag("萝莉", page=1, noai=True)

        for r in result["results"]:
            assert "AI Generated" not in r["name"]


# ============ get_ranking ============

class TestGetRanking:
    """排行榜测试"""

    @patch("src.plugins.onebot_plugin_jmdown.comic.JmOption")
    def test_ranking_week(self, mock_option, mock_jm_client):
        """周榜查询"""
        mock_option.default.return_value.new_jm_client.return_value = mock_jm_client

        from src.plugins.onebot_plugin_jmdown.comic import get_ranking
        result = get_ranking(time="w", page=1)

        assert "results" in result
        assert len(result["results"]) > 0

    @patch("src.plugins.onebot_plugin_jmdown.comic.JmOption")
    def test_ranking_month(self, mock_option, mock_jm_client):
        """月榜查询"""
        mock_option.default.return_value.new_jm_client.return_value = mock_jm_client

        from src.plugins.onebot_plugin_jmdown.comic import get_ranking
        result = get_ranking(time="m", page=1)

        assert "results" in result


# ============ get_comic_detail ============

class TestGetComicDetail:
    """详情查询测试"""

    @patch("src.plugins.onebot_plugin_jmdown.comic.JmOption")
    def test_detail_returns_all_fields(self, mock_option, mock_jm_client):
        """详情返回完整字段"""
        mock_option.default.return_value.new_jm_client.return_value = mock_jm_client

        from src.plugins.onebot_plugin_jmdown.comic import get_comic_detail
        result = get_comic_detail("114514")

        assert result["id"] == "114514"
        assert "name" in result
        assert "author" in result
        assert "tags" in result
        assert "pages" in result
        assert "chapters" in result
        assert "likes" in result
        assert "views" in result

    @patch("src.plugins.onebot_plugin_jmdown.comic.JmOption")
    def test_detail_invalid_id(self, mock_option):
        """无效 ID 返回 error"""
        mock_client = MagicMock()
        mock_client.get_album_detail.side_effect = Exception("不存在")
        mock_option.default.return_value.new_jm_client.return_value = mock_client

        from src.plugins.onebot_plugin_jmdown.comic import get_comic_detail
        result = get_comic_detail("999999999")

        assert "error" in result
