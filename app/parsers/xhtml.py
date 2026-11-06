def _check_xml(cleaned_html: str) -> Optional[str]:
    """Возвращает None если XML валиден, иначе текст ошибки."""
    try:
        parser = etree.XMLParser(load_dtd=False, no_network=True,
                                 resolve_entities=False, huge_tree=True)
        etree.fromstring(cleaned_html.encode("utf-8"), parser=parser)
        return None
    except etree.XMLSyntaxError as e:
        print(f"🚨 LXML SYNTAX ERROR: {e}") # <--- ОТЛАДКА
        return str(e)
    except Exception as e:
        print(f"🚨 LXML OTHER ERROR: {e}")  # <--- ОТЛАДКА
        return str(e)


def parse_xhtml(html: str) -> Tuple[BeautifulSoup, Optional[str]]:
    cleaned = _clean_entities(html)
    error = _check_xml(cleaned)

    if error is None:
        print(f"✅ LXML: Ошибок нет. Длина файла: {len(cleaned)} символов.") # <--- ОТЛАДКА
        try:
            return BeautifulSoup(cleaned, "lxml-xml"), None
        except Exception as e:
            error = str(e)

    return BeautifulSoup(html, "lxml"), error
