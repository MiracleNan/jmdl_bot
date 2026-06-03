"""
Tests for pdf_func.py - PDF 加密功能
"""
import os
import tempfile
import pytest


@pytest.fixture
def test_pdf(tmp_dir):
    """创建一个测试 PDF"""
    try:
        from reportlab.pdfgen import canvas
        path = os.path.join(tmp_dir, "test.pdf")
        c = canvas.Canvas(path)
        c.drawString(100, 750, "Test PDF content")
        c.save()
        return path
    except ImportError:
        pytest.skip("reportlab not installed")


class TestEncryptPdf:
    """PDF 加密测试"""

    def test_encrypt_creates_output_file(self, test_pdf):
        """加密后应创建输出文件"""
        from src.plugins.onebot_plugin_jmdown.pdf_func import encrypt_pdf

        password, output_path = encrypt_pdf(test_pdf)

        assert os.path.exists(output_path)
        assert output_path.endswith(".pdf")

    def test_encrypt_returns_password(self, test_pdf):
        """应返回有效密码"""
        from src.plugins.onebot_plugin_jmdown.pdf_func import encrypt_pdf

        password, _ = encrypt_pdf(test_pdf)

        assert isinstance(password, str)
        assert len(password) > 0

    def test_encrypt_output_different_from_input(self, test_pdf):
        """输出文件路径应不同于输入"""
        from src.plugins.onebot_plugin_jmdown.pdf_func import encrypt_pdf

        _, output_path = encrypt_pdf(test_pdf)

        assert output_path != test_pdf

    def test_encrypt_output_name_contains_password(self, test_pdf):
        """输出文件名应包含密码"""
        from src.plugins.onebot_plugin_jmdown.pdf_func import encrypt_pdf

        password, output_path = encrypt_pdf(test_pdf)

        assert password in os.path.basename(output_path)

    def test_encrypt_original_unchanged(self, test_pdf):
        """原始文件不应被修改"""
        from src.plugins.onebot_plugin_jmdown.pdf_func import encrypt_pdf
        import hashlib

        with open(test_pdf, "rb") as f:
            original_hash = hashlib.md5(f.read()).hexdigest()

        encrypt_pdf(test_pdf)

        with open(test_pdf, "rb") as f:
            after_hash = hashlib.md5(f.read()).hexdigest()

        assert original_hash == after_hash

    def test_encrypted_pdf_requires_password(self, test_pdf):
        """加密后的 PDF 应该需要密码才能读取"""
        from src.plugins.onebot_plugin_jmdown.pdf_func import encrypt_pdf
        from pikepdf import Pdf, PasswordError

        password, output_path = encrypt_pdf(test_pdf)

        # 不提供密码应报错
        with pytest.raises(PasswordError):
            Pdf.open(output_path)

        # 提供正确密码应能打开
        pdf = Pdf.open(output_path, password=password)
        assert pdf.is_encrypted
        pdf.close()
