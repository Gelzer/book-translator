"""Собирает минимальный EPUB с одной переведённой страницей."""
import uuid
import zipfile
from pathlib import Path
from typing import List, Dict

from app.parsers.base import TextSegment
from app.placeholders.restorer import restore_placeholders


EPUB_MIMETYPE = "application/epub+zip"

CONTAINER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


def _escape(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _build_xhtml(
    segments: List[TextSegment],
    translations: Dict[str, str],
    title: str,
    subtitle: str,
) -> str:
    parts = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<!DOCTYPE html>',
        '<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ru" lang="ru">',
        '<head>',
        '<meta charset="utf-8"/>',
        f'<title>{_escape(title)}</title>',
        '<link href="style.css" rel="stylesheet" type="text/css"/>',
        '</head>',
        '<body>',
        '<header class="page-header">',
        f'<h1 class="book-title">{_escape(title)}</h1>',
        f'<p class="page-subtitle">{_escape(subtitle)}</p>',
        '</header>',
    ]

    for seg in segments:
        translated = translations.get(seg.id)
        if not translated:
            # fallback — оставляем оригинал
            parts.append(f'<p class="segment">{_escape(seg.text)}</p>')
            continue
        translated_html = restore_placeholders(translated, seg.mapping or {})
        parts.append(f'<div class="segment">{translated_html}</div>')

    parts.append('<footer class="page-footer">')
    parts.append('<p>Переведено Book Translator · первая страница — бесплатно</p>')
    parts.append('</footer>')
    parts.append('</body></html>')

    return "\n".join(parts)


def _build_content_opf(title: str, image_items: List[tuple]) -> str:
    book_id = "bt-" + uuid.uuid4().hex[:12]
    manifest_items = [
        '<item id="page" href="page.xhtml" media-type="application/xhtml+xml"/>',
        '<item id="css" href="style.css" media-type="text/css"/>',
    ]
    for i, (name, _) in enumerate(image_items):
        # Определяем media-type по расширению
        lower = name.lower()
        if lower.endswith(".png"):
            mtype = "image/png"
        elif lower.endswith(".gif"):
            mtype = "image/gif"
        elif lower.endswith(".svg"):
            mtype = "image/svg+xml"
        else:
            mtype = "image/jpeg"
        manifest_items.append(
            f'<item id="img{i}" href="images/{name}" media-type="{mtype}"/>'
        )

    return f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>{_escape(title)}</dc:title>
    <dc:language>ru</dc:language>
    <dc:identifier id="bookid">{book_id}</dc:identifier>
    <dc:creator>Book Translator</dc:creator>
  </metadata>
  <manifest>
    {chr(10).join("    " + item for item in manifest_items)}
  </manifest>
  <spine>
    <itemref idref="page"/>
  </spine>
</package>
"""


DEFAULT_CSS = """\
body {
  font-family: Georgia, "PT Serif", serif;
  line-height: 1.7;
  padding: 1em 1.5em;
  color: #1a1a1a;
}
.page-header {
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 1em;
  margin-bottom: 1.5em;
}
.book-title {
  font-size: 1.3em;
  margin: 0 0 0.3em 0;
}
.page-subtitle {
  font-size: 0.9em;
  color: #666;
  margin: 0;
}
.segment {
  margin-bottom: 1.1em;
  text-align: justify;
}
.segment i, .segment em { font-style: italic; }
.segment b, .segment strong { font-weight: 700; }
.segment a { color: #7a1f4a; }
.page-footer {
  margin-top: 3em;
  padding-top: 1.5em;
  border-top: 1px solid #e5e7eb;
  font-size: 0.85em;
  color: #888;
  text-align: center;
}
"""


def build_single_page_epub(
    book,
    page_segments: List[TextSegment],
    translations: Dict[str, str],
    output_path: str,
    page_number: int,
    total_pages: int,
) -> str:
    """Собирает EPUB только с одной переведённой страницей."""
    source_epub = book.metadata.get("file_path")
    title = book.title or "Переведённая страница"
    subtitle = f"Страница {page_number} из {total_pages}"

    css_parts: List[str] = []
    images: List[tuple] = []  # (name, bytes)

    if source_epub and Path(source_epub).exists():
        with zipfile.ZipFile(source_epub, "r") as z:
            for name in z.namelist():
                lower = name.lower()
                if lower.endswith(".css"):
                    try:
                        css_parts.append(z.read(name).decode("utf-8", errors="ignore"))
                    except Exception:
                        pass
                elif any(lower.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".gif", ".svg")):
                    try:
                        images.append((name.split("/")[-1], z.read(name)))
                    except Exception:
                        pass

    css = "\n\n".join(css_parts) if css_parts else DEFAULT_CSS
    # Добавляем наши стили поверх, чтобы наш шаблон выглядел одинаково
    css = DEFAULT_CSS + "\n\n" + css

    xhtml = _build_xhtml(page_segments, translations, title, subtitle)
    content_opf = _build_content_opf(title, images)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as z:
        # 1) mimetype — ПЕРВЫЙ, БЕЗ сжатия
        zi = zipfile.ZipInfo("mimetype")
        zi.compress_type = zipfile.ZIP_STORED
        z.writestr(zi, EPUB_MIMETYPE)

        # 2) container.xml
        z.writestr("META-INF/container.xml", CONTAINER_XML)

        # 3) content.opf
        z.writestr("OEBPS/content.opf", content_opf)

        # 4) CSS
        z.writestr("OEBPS/style.css", css)

        # 5) страница
        z.writestr("OEBPS/page.xhtml", xhtml)

        # 6) картинки
        for name, data in images:
            z.writestr(f"OEBPS/images/{name}", data)

    return output_path