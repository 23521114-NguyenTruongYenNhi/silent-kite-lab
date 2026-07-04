from src.cleaner import ArticleMeta, clean_article_html, render_markdown, slugify


def test_slugify_includes_article_id():
    assert slugify("How to Add a YouTube Video?", 123) == "123-how-to-add-a-youtube-video"


def test_clean_article_html_preserves_code_and_relative_article_links():
    html = """
    <nav>noise</nav>
    <h2>Setup</h2>
    <p>Open <a href="https://support.optisigns.com/hc/en-us/articles/123-Other">this guide</a>.</p>
    <pre><code>print("ok")</code></pre>
    """
    markdown = clean_article_html(
        html,
        {"https://support.optisigns.com/hc/en-us/articles/123-Other": "123-other"},
    )
    assert "noise" not in markdown
    assert "## Setup" in markdown
    assert "[this guide](./123-other.md)" in markdown
    assert 'print("ok")' in markdown


def test_render_markdown_adds_article_url():
    meta = ArticleMeta(7, "Title", "https://support.optisigns.com/hc/en-us/articles/7", "2026-01-01T00:00:00Z")
    markdown = render_markdown(meta, "<p>Hello</p>", {})
    assert markdown.startswith("# Title")
    assert "Article URL: https://support.optisigns.com/hc/en-us/articles/7" in markdown
