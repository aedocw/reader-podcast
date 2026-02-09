"""Article extraction via newspaper3k with text cleaning."""

from dataclasses import dataclass

from newspaper import Article

from app.text_clean import clean_paragraphs


@dataclass
class ScrapedArticle:
    title: str
    paragraphs: list[str]
    source_url: str


def scrape(url):
    """Download and parse an article, returning cleaned text.

    Returns a ScrapedArticle with title and cleaned paragraph list.
    """
    article = Article(url)
    article.download()
    article.parse()

    raw_paragraphs = [p for p in article.text.split("\n") if p.strip()]
    paragraphs = clean_paragraphs(raw_paragraphs)

    title = article.title or url
    return ScrapedArticle(title=title, paragraphs=paragraphs, source_url=url)
