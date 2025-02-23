from newspaper import Article

def fetch(url):
    # Create an Article object
    article = Article(url)\
    # Download and parse the article
    article.download()
    article.parse()
    text = article.text
    paragraphs = text.split('\n')
    paragraphs = [p for p in paragraphs if p.strip()]
    return article.title, paragraphs
