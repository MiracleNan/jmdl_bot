"""
Tests for func.py - 配置读取和磁盘清理
"""
import os
import tempfile
import pytest


class TestReadOptionYml:
    """配置文件读取测试"""

    def test_valid_config(self, tmp_dir):
        """正常配置文件应返回两个路径"""
        import yaml

        config = {
            "dir_rule": {"base_dir": "/tmp/base"},
            "plugins": {
                "after_album": [
                    {"plugin": "img2pdf", "kwargs": {"pdf_dir": "/tmp/pdf"}}
                ]
            },
        }
        path = os.path.join(tmp_dir, "option.yml")
        with open(path, "w") as f:
            yaml.dump(config, f)

        from src.plugins.onebot_plugin_jmdown.func import read_option_yml

        result = read_option_yml(path)

        assert result is not None
        base_dir, pdf_dir = result
        assert base_dir == "/tmp/base"
        assert pdf_dir == "/tmp/pdf"

    def test_missing_file(self):
        """文件不存在应返回 None"""
        from src.plugins.onebot_plugin_jmdown.func import read_option_yml

        result = read_option_yml("/nonexistent/option.yml")

        assert result is None

    def test_malformed_yaml(self, tmp_dir):
        """格式错误的 YAML 应返回 None"""
        path = os.path.join(tmp_dir, "bad.yml")
        with open(path, "w") as f:
            f.write("{{invalid yaml}}: [")

        from src.plugins.onebot_plugin_jmdown.func import read_option_yml

        result = read_option_yml(path)

        assert result is None

    def test_missing_keys(self, tmp_dir):
        """缺少必要键应返回 None"""
        import yaml

        config = {"dir_rule": {"base_dir": "/tmp/base"}}  # 缺少 pdf_dir
        path = os.path.join(tmp_dir, "incomplete.yml")
        with open(path, "w") as f:
            yaml.dump(config, f)

        from src.plugins.onebot_plugin_jmdown.func import read_option_yml

        result = read_option_yml(path)

        assert result is None

    def test_empty_after_album(self, tmp_dir):
        """after_album 为空列表应返回 None"""
        import yaml

        config = {
            "dir_rule": {"base_dir": "/tmp/base"},
            "plugins": {"after_album": []},
        }
        path = os.path.join(tmp_dir, "empty.yml")
        with open(path, "w") as f:
            yaml.dump(config, f)

        from src.plugins.onebot_plugin_jmdown.func import read_option_yml

        result = read_option_yml(path)

        assert result is None


class TestGetFileLock:
    """文件锁测试"""

    def test_same_group_returns_same_lock(self):
        """同一 group_id 应返回同一个锁"""
        from src.plugins.onebot_plugin_jmdown.comic import get_file_lock

        locks = {}
        lock1 = get_file_lock(12345, locks)
        lock2 = get_file_lock(12345, locks)

        assert lock1 is lock2

    def test_different_group_returns_different_lock(self):
        """不同 group_id 应返回不同锁"""
        from src.plugins.onebot_plugin_jmdown.comic import get_file_lock

        locks = {}
        lock1 = get_file_lock(12345, locks)
        lock2 = get_file_lock(67890, locks)

        assert lock1 is not lock2

    def test_thread_safety(self):
        """并发获取同一 group_id 的锁应是同一对象"""
        from src.plugins.onebot_plugin_jmdown.comic import get_file_lock
        import threading

        locks = {}
        results = []

        def get_lock():
            results.append(get_file_lock(12345, locks))

        threads = [threading.Thread(target=get_lock) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(r is results[0] for r in results)
