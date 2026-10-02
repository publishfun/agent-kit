"""Checks on the kit's own files: the one-click install links in README.md, the client configs, the plugin's directory listing and the manifests for other agents."""
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

    def test_icon_is_a_square_png_inside_the_plugin(self):
        self.assertTrue(self.manifest["icon"].startswith("./"))
        icon = (PLUGIN / self.manifest["icon"]).resolve()
        self.assertTrue(icon.is_relative_to(PLUGIN.resolve()))
        self.assertFalse(icon.is_relative_to((PLUGIN / ".claude-plugin").resolve()))  # only plugin.json goes there
        data = icon.read_bytes()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", data[16:24])
        self.assertEqual(width, height)
        self.assertTrue(512 <= width <= 2048, width)  # what listings ask for; the README and Cline use the 400 px logo.png
        self.assertLess(len(data), 2 * 1024 * 1024)

    def test_listing_urls_are_https(self):
        for key in ("documentationUrl", "supportUrl", "privacyPolicyUrl", "termsOfServiceUrl"):
            self.assertTrue(self.manifest[key].startswith("https://"), key)

    def test_api_key_is_sensitive_and_defaults_to_empty(self):
        key = self.manifest["userConfig"]["api_key"]
        self.assertIs(key["sensitive"], True)
        # Cowork skips an MCP server whose referenced option has no default; empty still reads and cites.
        self.assertEqual(key["default"], "")


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class OtherAgentsTest(unittest.TestCase):
    """The Agent Plugins manifest (VS Code, Copilot, Cursor), Cursor's marketplace and the Gemini CLI extension describe the same plugin."""

    claude = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    url = json.loads((PLUGIN / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["publish-fun"]["url"]

    def test_agent_plugins_manifest_matches_the_claude_one(self):
        agent = load("plugins/publish-fun/plugin.json")
        self.assertEqual(agent["$schema"], "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json")
        # The schema is closed: any other field makes the manifest invalid.
        allowed = {"$schema", "name", "version", "description", "author", "homepage", "repository", "license", "keywords", "extensions"}
        self.assertLessEqual(set(agent), allowed)
        self.assertRegex(agent["name"], r"^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$")
        for key in ("name", "version", "description", "author", "homepage", "repository", "license", "keywords"):
            self.assertEqual(agent[key], self.claude[key], key)

    def test_agent_plugins_mcp_config_has_no_headers(self):
        # Agent Plugins sends headers literally and forbids secrets in them, so the
        # plugin connects without a key there: reading and citing work.
        mcp = load("plugins/publish-fun/mcp.json")
        self.assertEqual(mcp["$schema"], "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json")
        self.assertEqual(mcp["mcpServers"], {"publish-fun": {"type": "streamable-http", "url": self.url}})

    def test_cursor_marketplace_lists_the_plugin(self):
        market = load(".cursor-plugin/marketplace.json")
        self.assertLessEqual(set(market["owner"]), {"name", "email"})  # Cursor's schema allows no other owner field
        claude_market = load(".claude-plugin/marketplace.json")
        self.assertEqual(market["name"], claude_market["name"])
        [entry] = market["plugins"]
        self.assertEqual(entry["name"], self.claude["name"])
        self.assertTrue((ROOT / entry["source"] / "plugin.json").is_file())

    def test_gemini_extension_asks_for_the_key_and_sends_it(self):
        ext = load("gemini-extension.json")
        self.assertRegex(ext["name"], r"^[a-zA-Z0-9-]+$")
        self.assertEqual(ext["name"], self.claude["name"])
        [setting] = ext["settings"]
        self.assertIs(setting["sensitive"], True)  # kept in the system keychain
        server = ext["mcpServers"]["publish-fun"]
        self.assertEqual(server["httpUrl"], self.url)  # httpUrl is streamable HTTP in every Gemini CLI version
        # Unset, the variable becomes empty and publish.fun treats "Bearer" alone as no key.
        self.assertEqual(server["headers"], {"Authorization": "Bearer ${%s}" % setting["envVar"]})

    def test_every_manifest_has_the_same_version(self):
        versions = {p: load(p)["version"] for p in ("plugins/publish-fun/.claude-plugin/plugin.json", "plugins/publish-fun/plugin.json", "gemini-extension.json")}
        self.assertEqual(len(set(versions.values())), 1, versions)

    def test_no_marketplace_file_that_copilot_reads_before_claudes(self):
        # Copilot and VS Code read these before .claude-plugin/marketplace.json.
        for p in ("marketplace.json", ".plugin/marketplace.json", ".github/plugin/marketplace.json", "plugin.json"):
            self.assertFalse((ROOT / p).exists(), p)


class SkillTest(unittest.TestCase):
    """The skill as mirrored from publish.fun."""

    def test_copies_are_identical(self):
        a = (ROOT / "skills" / "publish-fun" / "SKILL.md").read_bytes()
        self.assertEqual(a, (PLUGIN / "skills" / "publish-fun" / "SKILL.md").read_bytes())

    def test_frontmatter_names_the_skill(self):
        text = (ROOT / "skills" / "publish-fun" / "SKILL.md").read_text(encoding="utf-8")
        front = text.split("---", 2)[1]
        self.assertRegex(front, r"(?m)^name: publish-fun$")
        self.assertRegex(front, r"(?m)^description: \S")

    def test_no_text_that_gemini_would_substitute(self):
        # Gemini CLI replaces $NAME and ${NAME} in skill text with the extension's
        # settings or environment variables: the API key would reach the model.
        text = (ROOT / "skills" / "publish-fun" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"\$\{?[A-Za-z_]", text))


if __name__ == "__main__":
    unittest.main()
