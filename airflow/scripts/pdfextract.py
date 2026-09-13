"""Разбор PDF MoneyPro: расход и доход по шапке «Дата…Сумма» и координатам слов."""

import io
import re
from datetime import datetime

import pandas as pd
import pdfplumber


class PdfText:
    """Нормализует и склеивает слова, которые pdfplumber достаёт из отчёта."""

    DATE_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")

    def norm(self, text: str) -> str:
        return (text or "").strip().lower().replace("\u0138", "к").replace("ё", "е")

    def clean(self, text: str) -> str:
        text = (text or "").replace("\u0138", "к").replace("\xa0", " ")
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"\s+,", ",", text)
        return re.sub(r"-\s+", "-", text)

    def amount(self, text: str) -> float | None:
        values = []
        for part in re.split(r"₽", text or ""):
            raw = re.sub(r"[^\d,.\s]", "", part).replace(" ", "").replace(",", ".")
            if raw and raw.count(".") <= 1:
                try:
                    values.append(float(raw))
                except ValueError:
                    pass
        return values[0] if values else None

    def date(self, text: str):
        return datetime.strptime(text, "%d.%m.%Y").date()

    def is_date(self, text: str) -> bool:
        return bool(self.DATE_RE.match(text or ""))

    def kind(self, names: list[str]) -> str | None:
        if "расход" in names:
            return "расход"
        if "доход" in names:
            return "доход"
        if "перевод" in names or "переводы" in names or ("продажа" in names and "актива" in names):
            return "skip"
        return None

    def join(self, words: list[dict], unique_lines: bool = False) -> str | None:
        if unique_lines:
            lines: dict[int, list[dict]] = {}
            for word in words:
                lines.setdefault(round(word["top"]), []).append(word)
            labels = []
            for top in sorted(lines):
                label = self.join(lines[top])
                if label and label not in labels:
                    labels.append(label)
            return " → ".join(labels) if labels else None
        if not words:
            return None
        ordered = sorted(words, key=lambda word: (word["top"], word["x0"]))
        return self.clean(" ".join(word["text"] for word in ordered)) or None

    def categories(self, words: list[dict]) -> str | None:
        phrases, buf = [], []
        for word in sorted(words, key=lambda item: (item["top"], item["x0"])):
            raw = word["text"].replace("\u0138", "к").replace("\xa0", " ")
            piece = self.clean(raw.rstrip(","))
            if piece:
                buf.append(piece)
            if raw.rstrip().endswith(",") and buf:
                phrases.append(" ".join(buf))
                buf = []
        if buf:
            phrases.append(" ".join(buf))
        seen = []
        for phrase in phrases:
            if phrase and phrase not in seen:
                seen.append(phrase)
        return ", ".join(seen) or None

    def group_by_top(self, words: list[dict]) -> dict[int, list[dict]]:
        groups: dict[int, list[dict]] = {}
        for word in words:
            groups.setdefault(round(word["top"]), []).append(word)
        return groups


class ColumnLayout:
    """Горизонтальные границы колонок по шапке таблицы."""

    HEADER = {
        "дата": "date",
        "контрагент": "payee",
        "контраге": "payee",
        "категория": "category",
        "описание": "description",
        "наличность": "envelope",
        "сумма": "amount",
    }

    def __init__(self, header: list[dict], text: PdfText):
        mapped = sorted(
            (word["x0"], self.HEADER[name])
            for word in header
            if (name := text.norm(word["text"])) in self.HEADER
        )
        xs = [x for x, _ in mapped]
        last = len(mapped) - 1
        self._edges = []
        for idx, (x0, name) in enumerate(mapped):
            left = 0.0 if idx == 0 else (xs[idx - 1] + x0) / 2 if idx == last else x0
            right = 1e9 if idx == last else (x0 + xs[idx + 1]) / 2 if idx == last - 1 else xs[idx + 1]
            self._edges.append((left, right, name))

    def column_of(self, word: dict) -> str | None:
        for left, right, name in self._edges:
            if left <= word["x0"] < right:
                return name
        return None


class TableBlock:
    """Один блок таблицы на странице: шапка, тело и тип секции."""

    Y_TOL = 20

    def __init__(self, kind: str, header: list[dict], body: list[dict], text: PdfText):
        self.kind = kind
        self._body = body
        self._text = text
        self._layout = ColumnLayout(header, text)

    def rows(self) -> list[dict]:
        dates = [
            word for word in self._body
            if self._text.is_date(word["text"]) and self._layout.column_of(word) == "date"
        ]
        dates.sort(key=lambda word: word["top"])
        return [self._row(date, dates) for date in dates]

    def _row(self, date: dict, dates: list[dict]) -> dict:
        bucket: dict[str, list[dict]] = {}
        for word in self._body:
            if abs(word["top"] - date["top"]) > self.Y_TOL:
                continue
            if min(dates, key=lambda item: abs(item["top"] - word["top"])) is not date:
                continue
            if column := self._layout.column_of(word):
                bucket.setdefault(column, []).append(word)
        return {
            "kind": self.kind,
            "date": self._text.date(self._text.join(bucket.get("date", [])) or ""),
            "payee": self._text.join(bucket.get("payee", [])),
            "category": self._text.categories(bucket.get("category", [])),
            "description": self._text.join(bucket.get("description", [])),
            "envelope": self._text.join(bucket.get("envelope", []), unique_lines=True),
            "amount": self._text.amount(self._text.join(bucket.get("amount", [])) or ""),
        }


class PDFExtractor:
    """Читает PDF MoneyPro и возвращает DataFrame расхода и дохода."""

    KEEP = {"расход", "доход"}
    COLUMNS = ["kind", "date", "payee", "category", "description", "envelope", "amount"]

    def __init__(self, pdf_bytes):
        self.pdf_bytes = pdf_bytes
        self._text = PdfText()

    def __call__(self) -> pd.DataFrame:
        return self.extract()

    def extract(self) -> pd.DataFrame:
        rows = []
        current = None
        with pdfplumber.open(io.BytesIO(self.pdf_bytes)) as pdf:
            for page in pdf.pages:
                page_rows, current = self._page(page, current)
                rows.extend(page_rows)
        return pd.DataFrame(rows, columns=self.COLUMNS)

    def _page(self, page, current: str | None) -> tuple[list[dict], str | None]:
        text = self._text
        words = page.extract_words(use_text_flow=True, keep_blank_chars=False) or []
        headers, titles, totals = [], [], []
        for group in text.group_by_top(words).values():
            names = [text.norm(word["text"]) for word in group]
            if "дата" in names and "сумма" in names:
                headers.append(sorted(group, key=lambda word: word["x0"]))
            elif kind := text.kind(names):
                titles.append((group[0]["top"], kind))
            totals.extend(word["top"] for word in group if text.norm(word["text"]) == "итого")
        headers.sort(key=lambda group: group[0]["top"])
        titles.sort()
        rows = []
        for index, header in enumerate(headers):
            top = header[0]["top"]
            prev = headers[index - 1][0]["top"] if index else -1.0
            for title_top, kind in titles:
                if prev < title_top < top:
                    current = kind
            if current not in self.KEEP:
                continue
            limits = [group[0]["top"] for group in headers[index + 1:]]
            limits.extend(y for y, _ in titles if y > top)
            limits.extend(y for y in totals if y > top)
            lower = min(limits) if limits else 1e9
            body = [
                word for word in words
                if top + 6 < word["top"] < lower and text.norm(word["text"]) != "итого"
            ]
            rows.extend(TableBlock(current, header, body, text).rows())
        return rows, current
