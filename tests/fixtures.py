from __future__ import annotations

import io
import zipfile

from reader.db import LibraryDB
from reader.importers import parse
from reader.models import Format


def build_txt(title: str = "Моя книга") -> bytes:
    text = (
        "Это первая глава.\n\n"
        "Первый абзац первой главы. Второе предложение.\n"
        "Второй абзац.\n\n"
        "Глава 2. Вторая глава\n\n"
        "Первый абзац второй главы.\n"
    )
    return text.encode("utf-8")


def build_fb2(title: str = "Тестовая книга", author: str = "Иван Автор", year: str = "2020") -> bytes:
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:xlink="http://www.w3.org/1999/xlink">
  <description>
    <title-info>
      <genre>sf</genre>
      <author><first-name>{author.split()[0]}</first-name><last-name>{author.split()[-1]}</last-name></author>
      <book-title>{title}</book-title>
      <annotation><p>Аннотация тестовой книги.</p></annotation>
      <date>{year}</date>
      <lang>ru</lang>
    </title-info>
  </description>
  <body>
    <section>
      <title><p>Глава первая</p></title>
      <p>Первый абзац первой главы. Второе предложение.</p>
      <p>Второй абзац первой главы.</p>
      <section>
        <title><p>Подраздел</p></title>
        <p>Абзац подраздела.</p>
      </section>
    </section>
    <section>
      <title><p>Глава вторая</p></title>
      <p>Первый абзац второй главы.</p>
    </section>
  </body>
</FictionBook>
"""
    return xml.encode("utf-8")


def build_epub(title: str = "Тестовая книга", author: str = "Иван Автор", year: str = "2020") -> bytes:
    ns_xhtml = "http://www.w3.org/1999/xhtml"
    ns_dc = "http://purl.org/dc/elements/1.1/"
    ns_opf = "http://www.idpf.org/2007/opf"
    ns_cont = "urn:oasis:names:tc:opendocument:xmlns:container"

    container = f"""<?xml version="1.0"?>
<container version="1.0" xmlns="{ns_cont}">
  <rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>"""

    opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="{ns_opf}" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="{ns_dc}">
    <dc:title>{title}</dc:title>
    <dc:creator>{author}</dc:creator>
    <dc:language>ru</dc:language>
    <dc:date>{year}</dc:date>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="c1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
    <item id="c2" href="chapter2.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine><itemref idref="c1"/><itemref idref="c2"/></spine>
</package>"""

    nav = f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="{ns_xhtml}"><body>
  <nav epub:type="toc" xmlns:epub="http://www.idpf.org/2007/ops">
    <ol>
      <li><a href="chapter1.xhtml">Первая глава</a></li>
      <li><a href="chapter2.xhtml">Вторая глава</a></li>
    </ol>
  </nav>
</body></html>"""

    ch1 = f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="{ns_xhtml}"><head><title>Первая глава</title></head><body>
<h1>Первая глава</h1>
<p>Первый абзац первой главы. Второе предложение.</p>
<p>Второй абзац первой главы.</p>
</body></html>"""

    ch2 = f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="{ns_xhtml}"><head><title>Вторая глава</title></head><body>
<h1>Вторая глава</h1>
<p>Первый абзац второй главы.</p>
</body></html>"""

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", container)
        zf.writestr("OEBPS/content.opf", opf)
        zf.writestr("OEBPS/nav.xhtml", nav)
        zf.writestr("OEBPS/chapter1.xhtml", ch1)
        zf.writestr("OEBPS/chapter2.xhtml", ch2)
    return buf.getvalue()


def write_fixture(path, content: bytes) -> None:
    path.write_bytes(content)


def import_fixture(db: LibraryDB, path, content: bytes) -> int:
    path.write_bytes(content)
    return db.upsert_book(path, parse(path), "test-hash")
