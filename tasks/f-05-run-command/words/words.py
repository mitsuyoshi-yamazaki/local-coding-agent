"""文を語に分ける。"""


def split_words(text: str) -> list[str]:
    """スペースで区切った語の並び。スペースが続いても、空の語は作らない。"""
    words = []
    start = 0
    while start < len(text):
        end = text.find(" ", start)
        if end == -1:
            end = len(text)
        if end > start:
            words.append(text[start:end])
        start = end
    return words
