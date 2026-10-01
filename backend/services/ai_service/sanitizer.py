import re


def sanitize_document_text(text: str) -> str:
    text = re.sub(r'\b\d{3}[- ]?\d{3}[- ]?\d{3}\s?\d{2}\b', '[УДАЛЕНО]', text)
    text = re.sub(r'\b\d{2}[.\\/-]\d{2}[.\\/-]\d{4}\b|\b\d{4}-\d{2}-\d{2}\b', '[УДАЛЕНО]', text)
    text = re.sub(r'(?<!\w)[+]?\d[\d ()-]{8,}\d(?!\w)', '[УДАЛЕНО]', text)
    text = re.sub(r'\b[\w.+-]+@[\w.-]+\.[A-Za-zА-Яа-я]{2,}\b', '[УДАЛЕНО]', text)
    text = re.sub(
        r'\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:вич|вна)\b',
        '[УДАЛЕНО]',
        text,
        flags=re.IGNORECASE,
    )
    return text
