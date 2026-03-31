"""
Tests for research tools (wechat_search and wechat_spider).

Covers:
- WeChatSearchTool init, is_available, search, parsing
- WeChatArticleSpider init, is_available, check_login_status, search_account, scrape, batch_scrape
- Pydantic models
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.tools.research.wechat_search import (
    WeChatSearchResponse,
    WeChatSearchResult,
    WeChatSearchTool,
    search_wechat_articles,
)
from src.tools.research.wechat_spider import (
    WeChatAccount,
    WeChatArticle,
    WeChatArticleSpider,
    WeChatSpiderResponse,
)


# ============ WeChatSearchResult Model ============

class TestWeChatSearchResult:
    def test_create_result(self):
        r = WeChatSearchResult(
            title="Test Article",
            url="https://example.com",
            author="TestAccount",
            account_id="test_id",
            publish_time="2026-01-01",
        )
        assert r.title == "Test Article"
        assert r.summary == ""
        assert r.content == ""

    def test_create_result_with_content(self):
        r = WeChatSearchResult(
            title="Test",
            url="https://example.com",
            author="Author",
            account_id="id",
            publish_time="2026-01-01",
            summary="Summary text",
            content="Full content",
        )
        assert r.summary == "Summary text"
        assert r.content == "Full content"


class TestWeChatSearchResponse:
    def test_create_response(self):
        now = datetime.now()
        r = WeChatSearchResponse(
            keyword="test",
            total=0,
            results=[],
            searched_at=now,
        )
        assert r.keyword == "test"
        assert r.total == 0
        assert r.searched_at == now

    def test_create_with_results(self):
        result = WeChatSearchResult(
            title="A", url="http://a.com", author="X", account_id="1", publish_time="2026-01-01"
        )
        r = WeChatSearchResponse(
            keyword="test", total=1, results=[result], searched_at=datetime.now()
        )
        assert len(r.results) == 1
        assert r.results[0].title == "A"


# ============ WeChatSearchTool ============

class TestWeChatSearchTool:
    def test_init_default(self):
        tool = WeChatSearchTool()
        assert tool.name == "wechat_search"

    def test_init_with_skill_path(self, tmp_path):
        tool = WeChatSearchTool(skill_path=tmp_path)
        assert tool.skill_path == tmp_path

    def test_is_available_false(self):
        tool = WeChatSearchTool(skill_path=Path("/nonexistent/path"))
        assert tool.is_available() is False

    def test_is_available_true(self, tmp_path):
        scripts = tmp_path / "scripts"
        scripts.mkdir()
        script = scripts / "keyword_search.py"
        script.write_text("# script")

        tool = WeChatSearchTool(skill_path=tmp_path)
        assert tool.is_available() is True

    def test_search_not_available(self):
        tool = WeChatSearchTool(skill_path=Path("/nonexistent"))
        with pytest.raises(RuntimeError, match="wechat-search-skill not installed"):
            tool.search("test")

    @patch("subprocess.run")
    def test_search_success_with_csv(self, mock_run, tmp_path):
        # Create script
        scripts = tmp_path / "scripts"
        scripts.mkdir()
        script = scripts / "keyword_search.py"
        script.write_text("# script")

        # Create CSV output
        csv_path = tmp_path / "output.csv"
        csv_path.write_text(
            "title,url,author,account_id,publish_time,summary,content\n"
            "Test Article,https://example.com,Author1,acc1,2026-01-01,Summary,Content\n"
        )

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=str(csv_path),
            stderr="",
        )

        tool = WeChatSearchTool(skill_path=tmp_path)
        result = tool.search("test keyword")

        assert result.keyword == "test keyword"
        assert result.total == 1
        assert result.results[0].title == "Test Article"

    @patch("subprocess.run")
    def test_search_failure(self, mock_run, tmp_path):
        scripts = tmp_path / "scripts"
        scripts.mkdir()
        (scripts / "keyword_search.py").write_text("# script")

        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error occurred",
        )

        tool = WeChatSearchTool(skill_path=tmp_path)
        with pytest.raises(RuntimeError, match="Search failed"):
            tool.search("test")

    @patch("subprocess.run")
    def test_search_stdout_fallback(self, mock_run, tmp_path):
        scripts = tmp_path / "scripts"
        scripts.mkdir()
        (scripts / "keyword_search.py").write_text("# script")

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="some output without file path",
            stderr="",
        )

        tool = WeChatSearchTool(skill_path=tmp_path)
        result = tool.search("test")
        assert result.total == 0

    def test_parse_stdout(self):
        tool = WeChatSearchTool(skill_path=Path("/fake"))
        result = tool._parse_stdout("some output", "keyword")
        assert result.keyword == "keyword"
        assert result.total == 0

    @patch("subprocess.run")
    def test_search_with_json_output(self, mock_run, tmp_path):
        scripts = tmp_path / "scripts"
        scripts.mkdir()
        (scripts / "keyword_search.py").write_text("# script")

        json_path = tmp_path / "output.json"
        json_path.write_text(json.dumps([
            {"title": "Article 1", "url": "http://a.com", "author": "Auth", "account_id": "id1", "publish_time": "2026-01-01"},
        ]))

        mock_run.return_value = MagicMock(returncode=0, stdout=str(json_path), stderr="")

        tool = WeChatSearchTool(skill_path=tmp_path)
        # Need to patch the file ending check since stdout line ends with .json
        result = tool._parse_output_file(str(json_path), "test")
        assert result.total == 1

    def test_parse_output_file_unknown_format(self, tmp_path):
        txt_file = tmp_path / "output.txt"
        txt_file.write_text("some text")

        tool = WeChatSearchTool(skill_path=Path("/fake"))
        result = tool._parse_output_file(str(txt_file), "keyword")
        assert result.total == 0


class TestSearchWechatArticlesConvenience:
    @patch.object(WeChatSearchTool, "search")
    @patch.object(WeChatSearchTool, "__init__", return_value=None)
    def test_search_convenience(self, mock_init, mock_search):
        mock_search.return_value = WeChatSearchResponse(
            keyword="test", total=0, results=[], searched_at=datetime.now()
        )
        result = search_wechat_articles("test")
        assert result.total == 0


# ============ WeChatArticle Model ============

class TestWeChatArticle:
    def test_create(self):
        a = WeChatArticle(title="Test", url="http://a.com", author="Auth", publish_time="2026-01-01")
        assert a.read_count == 0
        assert a.like_count == 0
        assert a.cover_image == ""


class TestWeChatAccount:
    def test_create(self):
        a = WeChatAccount(name="Test Account", fakeid="fake123")
        assert a.alias == ""
        assert a.description == ""


class TestWeChatSpiderResponse:
    def test_create(self):
        r = WeChatSpiderResponse(account=None, articles=[], total=0, scraped_at=datetime.now())
        assert r.account is None
        assert r.total == 0


# ============ WeChatArticleSpider ============

class TestWeChatArticleSpider:
    def test_init(self):
        spider = WeChatArticleSpider()
        assert spider.name == "wechat_spider"

    @patch("shutil.which", return_value=None)
    def test_not_available(self, mock_which):
        spider = WeChatArticleSpider()
        assert spider.is_available() is False

    @patch("shutil.which", return_value="/usr/bin/wechat-spider")
    def test_available(self, mock_which):
        spider = WeChatArticleSpider()
        assert spider.is_available() is True

    @patch("shutil.which", return_value=None)
    def test_check_login_not_installed(self, mock_which):
        spider = WeChatArticleSpider()
        status = spider.check_login_status()
        assert status["logged_in"] is False
        assert "not installed" in status["error"]

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/wechat-spider")
    def test_check_login_success(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"logged_in": True, "username": "test"}),
            stderr="",
        )
        spider = WeChatArticleSpider()
        status = spider.check_login_status()
        assert status["logged_in"] is True

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/wechat-spider")
    def test_check_login_failure(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        spider = WeChatArticleSpider()
        status = spider.check_login_status()
        assert status["logged_in"] is False

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/wechat-spider")
    def test_check_login_bad_json(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="not json", stderr="")
        spider = WeChatArticleSpider()
        status = spider.check_login_status()
        assert status["logged_in"] is False

    @patch("shutil.which", return_value=None)
    def test_search_account_not_available(self, mock_which):
        spider = WeChatArticleSpider()
        with pytest.raises(RuntimeError, match="not installed"):
            spider.search_account("test")

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/wechat-spider")
    def test_search_account_success(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"accounts": [
                {"nickname": "Test Account", "fakeid": "fake123", "alias": "test_alias"}
            ]}),
            stderr="",
        )
        spider = WeChatArticleSpider()
        accounts = spider.search_account("test")
        assert len(accounts) == 1
        assert accounts[0].name == "Test Account"

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/wechat-spider")
    def test_search_account_failure(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        spider = WeChatArticleSpider()
        with pytest.raises(RuntimeError, match="Search failed"):
            spider.search_account("test")

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/wechat-spider")
    def test_search_account_bad_json(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="not json", stderr="")
        spider = WeChatArticleSpider()
        accounts = spider.search_account("test")
        assert accounts == []

    @patch("shutil.which", return_value=None)
    def test_scrape_not_available(self, mock_which):
        spider = WeChatArticleSpider()
        with pytest.raises(RuntimeError, match="not installed"):
            spider.scrape_account("test")

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/wechat-spider")
    def test_scrape_success(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "account": {"nickname": "Test", "fakeid": "f1"},
                "articles": [
                    {"title": "Article 1", "url": "http://a.com", "author": "Auth", "create_time": "2026-01-01",
                     "digest": "Summary", "read_num": 100, "like_num": 10}
                ],
            }),
            stderr="",
        )
        spider = WeChatArticleSpider()
        result = spider.scrape_account("test", pages=3, days=7, with_content=True)
        assert result.total == 1
        assert result.account is not None
        assert result.account.name == "Test"
        assert result.articles[0].read_count == 100

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/wechat-spider")
    def test_scrape_failure(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        spider = WeChatArticleSpider()
        with pytest.raises(RuntimeError, match="Scrape failed"):
            spider.scrape_account("test")

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/wechat-spider")
    def test_scrape_bad_json(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="not json", stderr="")
        spider = WeChatArticleSpider()
        result = spider.scrape_account("test")
        assert result.total == 0

    @patch("shutil.which", return_value=None)
    def test_batch_scrape_not_available(self, mock_which):
        spider = WeChatArticleSpider()
        with pytest.raises(RuntimeError, match="not installed"):
            spider.batch_scrape(["acc1", "acc2"])

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/wechat-spider")
    def test_batch_scrape_success(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({
                "account1": {"articles": [{"title": "A1", "url": "http://a.com", "author": "Auth", "publish_time": "2026-01-01"}]},
                "account2": {"articles": []},
            }),
            stderr="",
        )
        spider = WeChatArticleSpider()
        results = spider.batch_scrape(["account1", "account2"])
        assert "account1" in results
        assert results["account1"].total == 1
        assert results["account2"].total == 0

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/wechat-spider")
    def test_batch_scrape_failure(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        spider = WeChatArticleSpider()
        with pytest.raises(RuntimeError, match="Batch scrape failed"):
            spider.batch_scrape(["acc1"])

    @patch("subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/wechat-spider")
    def test_batch_scrape_bad_json(self, mock_which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="not json", stderr="")
        spider = WeChatArticleSpider()
        results = spider.batch_scrape(["acc1"])
        assert results == {}
