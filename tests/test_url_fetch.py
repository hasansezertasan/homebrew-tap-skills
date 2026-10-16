"""Tests for authenticated HTTP request construction."""

from __future__ import annotations

import os
import sys
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".ai-rulez/skills/homebrew-add/scripts"))

import url_fetch  # noqa: E402


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args) -> None:
        pass


class GetJsonTest(unittest.TestCase):
    def test_decodes_json(self) -> None:
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse(b'{"a": 1}')):
            self.assertEqual(url_fetch.get_json("https://example.com/api"), {"a": 1})

    def test_invalid_json_includes_url_context(self) -> None:
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse(b"<html>Not JSON</html>")):
            with self.assertRaises(ValueError) as ctx:
                url_fetch.get_json("https://example.com/api")
        self.assertIn("https://example.com/api", str(ctx.exception))
        self.assertIn("<html>", str(ctx.exception))

    def test_requests_carry_a_timeout(self) -> None:
        with mock.patch("urllib.request.urlopen", return_value=FakeResponse(b"{}")) as urlopen:
            url_fetch.get_json("https://example.com/api")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], url_fetch.TIMEOUT)


class RequestTest(unittest.TestCase):
    def test_github_token_is_sent_only_to_exact_api_host(self) -> None:
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": "secret"}):
            api = url_fetch.request("https://api.github.com/repos/acme/widget")
            http_api = url_fetch.request("http://api.github.com/repos/acme/widget")
            spoof = url_fetch.request("https://evil.example/api.github.com/pypi.org/widget")
            download = url_fetch.request("https://github.com/acme/widget/releases/download/v1/w.zip")
            pypi = url_fetch.request("https://pypi.org/pypi/widget/json")

        self.assertTrue(api.has_header("Authorization"))
        for req in (http_api, spoof, download, pypi):
            self.assertFalse(req.has_header("Authorization"), req.full_url)

    def test_gh_token_is_the_fallback(self) -> None:
        with mock.patch.dict(os.environ, {"GH_TOKEN": "fallback"}, clear=True):
            req = url_fetch.request("https://api.github.com/repos/acme/widget")
        self.assertEqual(req.get_header("Authorization"), "Bearer fallback")

    def test_redirect_handler_strips_authorization_off_the_api_host(self) -> None:
        handler = url_fetch.SafeRedirectHandler()
        req = urllib.request.Request(
            "https://api.github.com/repos/acme/widget/releases/assets/1",
            headers={"Authorization": "Bearer secret", "User-Agent": "test"},
        )

        def redirect(url: str) -> urllib.request.Request:
            new = handler.redirect_request(req, None, 302, "Found", {}, url)
            self.assertIsNotNone(new)
            return new

        self.assertFalse(redirect("https://objects.githubusercontent.com/asset.zip").has_header("Authorization"))
        self.assertFalse(redirect("http://api.github.com/another").has_header("Authorization"))
        self.assertTrue(redirect("https://api.github.com/repos/acme/widget/releases/assets/2").has_header("Authorization"))


if __name__ == "__main__":
    unittest.main()
