"""Checks on the kit's own files: the one-click install links in README.md, the client configs and the plugin's directory listing."""
import base64, json, pathlib, re, struct, unittest, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "publish-fun"


def readme_links(prefix):
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    return re.findall(r"\]\((" + re.escape(prefix) + r"[^)\s]+)\)", text)


def query(url):
    """A URL's query parameters, decoded once as URLSearchParams does. A '+' would turn into a space, so none may appear."""
    q = urllib.parse.urlsplit(url).query
    assert "+" not in q, url
    return dict(urllib.parse.parse_qsl(q, keep_blank_values=True, strict_parsing=True))


class InstallLinksTest(unittest.TestCase):
    """Each link is decoded the way its editor decodes it and must give back the config file in clients/."""

    def test_vscode_link_installs_clients_vscode_mcp_json(self):
        links = readme_links("https://vscode.dev/redirect?url=")
        self.assertEqual(len(links), 1)
        inner = query(links[0])["url"]  # vscode.dev answers with a redirect to this URL
        self.assertTrue(inner.startswith("vscode:mcp/install?"), inner)
        once = urllib.parse.unquote(inner.split("?", 1)[1])  # VS Code's URI.parse decodes the query,
        self.assertNotIn("%", once)  # then its mcp/install handler decodes it again: a literal % would break
        payload = json.loads(urllib.parse.unquote(once))
        name, inputs = payload.pop("name"), payload.pop("inputs")
        config = json.loads((ROOT / "clients" / "vscode-mcp.json").read_text(encoding="utf-8"))
        self.assertEqual({"inputs": inputs, "servers": {name: payload}}, config)

    def test_cursor_link_installs_clients_cursor_mcp_json(self):
        links = readme_links("https://cursor.com/en/install-mcp?")
        self.assertEqual(len(links), 1)
        params = query(links[0])  # the page passes name and config on to cursor://anysphere.cursor-deeplink/mcp/install
        server = json.loads(base64.b64decode(params["config"], validate=True))
        config = json.loads((ROOT / "clients" / "cursor-mcp.json").read_text(encoding="utf-8"))
        self.assertEqual({"mcpServers": {params["name"]: server}}, config)


class ClientConfigsTest(unittest.TestCase):
    """The setup files in clients/."""

    def test_each_is_linked_from_the_readme_and_names_the_plugins_server(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        url = json.loads((PLUGIN / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["publish-fun"]["url"]
        for f in sorted(p for p in (ROOT / "clients").iterdir() if not p.name.startswith(".")):
            with self.subTest(f.name):
                self.assertIn(f"](clients/{f.name})", readme)
                self.assertIn(url, f.read_text(encoding="utf-8"))

    def test_cline_uses_streamable_http(self):
        # Without a type, Cline connects with the legacy SSE transport, whose GET publish.fun answers with 405.
        server = json.loads((ROOT / "clients" / "cline-mcp.json").read_text(encoding="utf-8"))["mcpServers"]["publish-fun"]
        self.assertEqual(server["type"], "streamableHttp")


class PluginListingTest(unittest.TestCase):
    """What Anthropic's plugin directory reads from the plugin folder."""

    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))

    def test_readme_has_at_least_40_words_outside_code(self):
        text = (PLUGIN / "README.md").read_text(encoding="utf-8")
        prose = re.sub(r"^```.*?^```", " ", text, flags=re.S | re.M)  # words in code blocks don't count
        prose = re.sub(r"`[^`]*`", " ", prose)  # nor, to be safe, inline code
        self.assertGreaterEqual(len(re.findall(r"[A-Za-z][\w'.-]*", prose)), 40)

    def test_icon_is_a_400px_png_inside_the_plugin(self):
        self.assertTrue(self.manifest["icon"].startswith("./"))
        icon = (PLUGIN / self.manifest["icon"]).resolve()
        self.assertTrue(icon.is_relative_to(PLUGIN.resolve()))
        head = icon.read_bytes()[:24]
        self.assertEqual(head[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", head[16:24]), (400, 400))

    def test_listing_urls_are_https(self):
        for key in ("documentationUrl", "supportUrl", "privacyPolicyUrl", "termsOfServiceUrl"):
            self.assertTrue(self.manifest[key].startswith("https://"), key)

    def test_api_key_is_sensitive_and_defaults_to_empty(self):
        key = self.manifest["userConfig"]["api_key"]
        self.assertIs(key["sensitive"], True)
        # Cowork skips an MCP server whose referenced option has no default; empty still reads and cites.
        self.assertEqual(key["default"], "")


if __name__ == "__main__":
    unittest.main()
