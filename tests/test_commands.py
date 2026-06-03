"""
Tests for command regex parsing and rate limiting
"""
import re
import time
import pytest


# ============ /jm 正则 ============

class TestJmRegex:
    """测试 /jm 命令正则匹配"""

    PATTERN = r'^/jm\s+(\d+)$'

    def test_valid_id(self):
        match = re.match(self.PATTERN, "/jm 114514")
        assert match is not None
        assert match.group(1) == "114514"

    def test_large_id(self):
        match = re.match(self.PATTERN, "/jm 1444066")
        assert match is not None
        assert match.group(1) == "1444066"

    def test_no_space(self):
        match = re.match(self.PATTERN, "/jm114514")
        assert match is None

    def test_no_id(self):
        match = re.match(self.PATTERN, "/jm")
        assert match is None

    def test_extra_args(self):
        match = re.match(self.PATTERN, "/jm 114514 extra")
        assert match is None

    def test_non_digit(self):
        match = re.match(self.PATTERN, "/jm abc")
        assert match is None


# ============ /jms 正则 ============

class TestJmsRegex:
    """测试 /jms 命令正则匹配"""

    PATTERN = r'^/jms\s+(.+)$'

    def test_simple_keyword(self):
        match = re.match(self.PATTERN, "/jms 汉化")
        assert match is not None
        assert "汉化" in match.group(1)

    def test_noai_keyword(self):
        match = re.match(self.PATTERN, "/jms noai 汉化")
        assert match is not None
        assert "noai" in match.group(1)

    def test_multi_keyword(self):
        match = re.match(self.PATTERN, "/jms 汉化 萝莉")
        assert match is not None
        args = match.group(1).split()
        assert "汉化" in args
        assert "萝莉" in args

    def test_no_args(self):
        match = re.match(self.PATTERN, "/jms")
        assert match is None

    def test_with_page_and_order(self):
        match = re.match(self.PATTERN, "/jms noai 汉化 萝莉 2 mv")
        assert match is not None


# ============ /jmstag 正则 ============

class TestJmstagRegex:
    """测试 /jmstag 命令正则匹配"""

    PATTERN = r'^/jmstag\s+(.+)$'

    def test_simple_tag(self):
        match = re.match(self.PATTERN, "/jmstag 萝莉")
        assert match is not None

    def test_noai_tag(self):
        match = re.match(self.PATTERN, "/jmstag noai 萝莉")
        assert match is not None

    def test_tag_with_order(self):
        match = re.match(self.PATTERN, "/jmstag 萝莉 mv")
        assert match is not None


# ============ /jmrank 正则 ============

class TestJmrankRegex:
    """测试 /jmrank 命令正则匹配"""

    PATTERN = r'^/jmrank(\s+.*)?$'

    def test_no_args(self):
        match = re.match(self.PATTERN, "/jmrank")
        assert match is not None

    def test_week(self):
        match = re.match(self.PATTERN, "/jmrank week")
        assert match is not None

    def test_month_page(self):
        match = re.match(self.PATTERN, "/jmrank month 2")
        assert match is not None


# ============ /jminfo 正则 ============

class TestJminfoRegex:
    """测试 /jminfo 命令正则匹配"""

    PATTERN = r'^/jminfo\s+(\S+)$'

    def test_valid_id(self):
        match = re.match(self.PATTERN, "/jminfo 114514")
        assert match is not None
        assert match.group(1) == "114514"

    def test_no_id(self):
        match = re.match(self.PATTERN, "/jminfo")
        assert match is None


# ============ /help 正则 ============

class TestHelpRegex:
    """测试 /help 命令正则匹配"""

    PATTERN = r'^/(help|Help|帮助)\s*$|^帮助\s*$'

    def test_help(self):
        assert re.match(self.PATTERN, "/help") is not None

    def test_Help(self):
        assert re.match(self.PATTERN, "/Help") is not None

    def test_help_with_slash_chinese(self):
        assert re.match(self.PATTERN, "/帮助") is not None

    def test_help_no_slash_chinese(self):
        assert re.match(self.PATTERN, "帮助") is not None

    def test_help_trailing_space(self):
        assert re.match(self.PATTERN, "/help ") is not None

    def test_help_no_match_extra(self):
        assert re.match(self.PATTERN, "/help me") is None


# ============ /xp 正则 ============

class TestXpRegex:
    """测试 /xp 命令正则匹配"""

    PATTERN = r'^/xp$|^/tags$|^/Xp$'

    def test_xp(self):
        assert re.match(self.PATTERN, "/xp") is not None

    def test_tags(self):
        assert re.match(self.PATTERN, "/tags") is not None

    def test_Xp(self):
        assert re.match(self.PATTERN, "/Xp") is not None

    def test_no_match_extra(self):
        assert re.match(self.PATTERN, "/xp something") is None


# ============ 频率限制 ============

class TestRateLimit:
    """测试频率限制逻辑"""

    def test_rate_limit_allows_first_call(self):
        """首次调用应放行"""
        _last_request = {}
        key = "user1:jm"
        now = time.time()
        limit = 10

        if key in _last_request:
            elapsed = now - _last_request[key]
            allowed = elapsed >= limit
        else:
            allowed = True

        assert allowed is True

    def test_rate_limit_blocks_within_window(self):
        """冷却期内应拒绝"""
        _last_request = {"user1:jm": time.time()}
        key = "user1:jm"
        now = time.time()
        limit = 10

        elapsed = now - _last_request[key]
        allowed = elapsed >= limit

        assert allowed is False

    def test_rate_limit_allows_after_window(self):
        """冷却期后应放行"""
        _last_request = {"user1:jm": time.time() - 11}
        key = "user1:jm"
        now = time.time()
        limit = 10

        elapsed = now - _last_request[key]
        allowed = elapsed >= limit

        assert allowed is True

    def test_rate_limit_independent_users(self):
        """不同用户独立计数"""
        _last_request = {"user1:jm": time.time()}
        key = "user2:jm"

        allowed = key not in _last_request

        assert allowed is True
