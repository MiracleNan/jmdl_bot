"""
Shared fixtures for jmdl_bot tests
"""
import os
import sys
import json
import tempfile
import pytest

# 确保 src 在 sys.path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def tmp_dir():
    """创建临时目录"""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def sample_tags_file(tmp_dir):
    """创建示例 tags JSON 文件"""
    tags = {"萝莉": 10, "全彩": 5, "中文": 8, "巨乳": 3}
    path = os.path.join(tmp_dir, "12345.txt")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tags, f)
    return path, tags


@pytest.fixture
def sample_option_yml(tmp_dir):
    """创建示例 option.yml"""
    config = {
        "download": {"image": {"suffix": ".webp"}},
        "dir_rule": {"base_dir": tmp_dir, "rule": "Bd / Ptitle"},
        "plugins": {
            "after_album": [
                {
                    "plugin": "img2pdf",
                    "kwargs": {
                        "pdf_dir": os.path.join(tmp_dir, "pdf"),
                        "filename_rule": "Aname",
                    },
                }
            ]
        },
    }
    path = os.path.join(tmp_dir, "option.yml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True)
    return path


@pytest.fixture
def sample_pdf(tmp_dir):
    """创建一个简单的 PDF 文件用于加密测试"""
    from reportlab.pdfgen import canvas

    path = os.path.join(tmp_dir, "test.pdf")
    c = canvas.Canvas(path)
    c.drawString(100, 750, "Test PDF for encryption")
    c.save()
    return path


@pytest.fixture
def mock_jm_client():
    """Mock JM 客户端，返回可控的测试数据"""

    class MockAlbum:
        def __init__(self, album_id="114514", name="测试漫画", author="测试作者", tags=None):
            self.album_id = album_id
            self.name = name
            self.author = author
            self.tags = tags or ["萝莉", "全彩"]
            self.page_count = 27
            self.episode_list = [("photo1", 1, "第1话")]
            self.likes = 100
            self.views = 5000
            self.description = "测试描述"
            self.pub_date = "2024-01-01"
            self.authors = [author]
            self.actors = []

    class MockSearchPage:
        def __init__(self, content=None, total=1):
            self.content = content or [
                ("114514", {"name": "测试漫画", "author": "测试作者", "tag_list": ["萝莉"]}),
                ("222222", {"name": "[AI Generated] AI漫画", "author": "N/A", "tag_list": []}),
                ("333333", {"name": "中文汉化本", "author": "汉化组", "tag_list": ["中文"]}),
                ("444444", {"name": "普通漫画", "author": "作者B", "tag_list": []}),
                ("555555", {"name": "AI生成测试", "author": "N/A", "tag_list": []}),
                ("666666", {"name": "另一本漫画", "author": "作者C", "tag_list": ["萝莉"]}),
            ]
            self.total = total
            self.page_count = 1
            self.page_size = 5
            self.is_single_album = False

    class MockClient:
        def search_site(self, search_query, page=1, order_by="mr", time="a", category="0", sub_category=None):
            return MockSearchPage()

        def search_tag(self, search_query, page=1, order_by="mr"):
            # 标签搜索只返回包含该标签的结果
            content = [
                ("114514", {"name": "萝莉漫画A", "author": "作者A", "tag_list": ["萝莉"]}),
                ("222222", {"name": "萝莉漫画B", "author": "作者B", "tag_list": ["萝莉"]}),
            ]
            return MockSearchPage(content=content, total=2)

        def get_album_detail(self, album_id):
            return MockAlbum(album_id=album_id)

        def categories_filter(self, page, time, category, order_by):
            content = [
                ("111111", {"name": "排行第一", "author": "A", "tag_list": []}),
                ("222222", {"name": "排行第二", "author": "B", "tag_list": []}),
            ]
            return MockSearchPage(content=content, total=100)

    return MockClient()
