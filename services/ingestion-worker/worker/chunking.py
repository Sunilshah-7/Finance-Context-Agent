"""Paragraph-aware chunking for normalized SEC filing sections.

The chunker keeps paragraph evidence readable, isolates tables into standalone
chunks, computes stable text hashes, and assigns citation anchors such as
``AMD 10-K Item 1A paragraph 42`` before anything is embedded or stored.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from collections.abc import Iterable

from .models import ChunkInput, NormalizedDocument, NormalizedSection

TARGET_MIN_TOKENS = 600
TARGET_MAX_TOKENS = 1000
MAX_TOKENS = 1200
MIN_TOKENS = 200
OVERLAP_TOKENS = 100


class TokenCounter:
    def __init__(self) -> None:
        try:
            import tiktoken

            self._encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:  # noqa: BLE001 - fallback keeps tests/dev usable without tiktoken
            self._encoding = None

    def count(self, text: str) -> int:
        if self._encoding is not None:
            return len(self._encoding.encode(text))
        return len(text.split())

    def tail(self, text: str, token_count: int) -> str:
        if token_count <= 0:
            return ""
        if self._encoding is not None:
            tokens = self._encoding.encode(text)
            return self._encoding.decode(tokens[-token_count:])
        return " ".join(text.split()[-token_count:])

    def windows(self, text: str, max_tokens: int, overlap_tokens: int) -> list[str]:
        if self.count(text) <= max_tokens:
            return [text]
        if self._encoding is not None:
            tokens = self._encoding.encode(text)
            windows = []
            start = 0
            while start < len(tokens):
                end = min(start + max_tokens, len(tokens))
                windows.append(self._encoding.decode(tokens[start:end]))
                if end == len(tokens):
                    break
                start = max(0, end - overlap_tokens)
            return windows

        words = text.split()
        windows = []
        start = 0
        while start < len(words):
            end = min(start + max_tokens, len(words))
            windows.append(" ".join(words[start:end]))
            if end == len(words):
                break
            start = max(0, end - overlap_tokens)
        return windows


def chunk_document(
    document: NormalizedDocument,
    *,
    target_min_tokens: int = TARGET_MIN_TOKENS,
    target_max_tokens: int = TARGET_MAX_TOKENS,
    max_tokens: int = MAX_TOKENS,
    min_tokens: int = MIN_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> list[ChunkInput]:
    counter = TokenCounter()
    chunks: list[ChunkInput] = []
    next_chunk_index = 0
    for section in document.sections:
        section_chunks = chunk_section(
            document,
            section,
            start_chunk_index=next_chunk_index,
            token_counter=counter,
            target_min_tokens=target_min_tokens,
            target_max_tokens=target_max_tokens,
            max_tokens=max_tokens,
            min_tokens=min_tokens,
            overlap_tokens=overlap_tokens,
        )
        chunks.extend(section_chunks)
        next_chunk_index += len(section_chunks)
    return chunks


def chunk_section(
    document: NormalizedDocument,
    section: NormalizedSection,
    *,
    start_chunk_index: int = 0,
    token_counter: TokenCounter | None = None,
    target_min_tokens: int = TARGET_MIN_TOKENS,
    target_max_tokens: int = TARGET_MAX_TOKENS,
    max_tokens: int = MAX_TOKENS,
    min_tokens: int = MIN_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> list[ChunkInput]:
    counter = token_counter or TokenCounter()
    chunks: list[ChunkInput] = []
    paragraph_chunks = _chunk_text(
        section.text,
        counter,
        target_min_tokens=target_min_tokens,
        target_max_tokens=target_max_tokens,
        max_tokens=max_tokens,
        min_tokens=min_tokens,
        overlap_tokens=overlap_tokens,
    )

    for paragraph_number, text in enumerate(paragraph_chunks, start=1):
        chunks.append(
            _build_chunk(
                document,
                section,
                text,
                chunk_index=start_chunk_index + len(chunks),
                citation_kind="paragraph",
                citation_number=paragraph_number,
                token_counter=counter,
                is_table=False,
            )
        )

    for table_number, table in enumerate(section.tables, start=1):
        table_text = table.strip()
        if not table_text:
            continue
        chunks.append(
            _build_chunk(
                document,
                section,
                table_text,
                chunk_index=start_chunk_index + len(chunks),
                citation_kind="table",
                citation_number=table_number,
                token_counter=counter,
                is_table=True,
            )
        )

    return chunks


def citation_anchor(
    ticker: str, filing_type: str, section_label: str, kind: str, number: int
) -> str:
    return f"{ticker.upper()} {filing_type} {section_label} {kind} {number}"


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _chunk_text(
    text: str,
    counter: TokenCounter,
    *,
    target_min_tokens: int,
    target_max_tokens: int,
    max_tokens: int,
    min_tokens: int,
    overlap_tokens: int,
) -> list[str]:
    units = list(_iter_text_units(text, counter, max_tokens=max_tokens))
    chunks: list[str] = []
    current_parts: list[str] = []
    current_tokens = 0

    for unit in units:
        unit_tokens = counter.count(unit)
        should_flush = (
            current_parts
            and current_tokens >= target_min_tokens
            and current_tokens + unit_tokens > target_max_tokens
        )
        would_exceed_hard_max = current_parts and current_tokens + unit_tokens > max_tokens
        if should_flush or would_exceed_hard_max:
            emitted = "\n\n".join(current_parts).strip()
            if emitted:
                chunks.append(emitted)
            overlap = counter.tail(emitted, overlap_tokens)
            current_parts = [overlap, unit] if overlap else [unit]
            if counter.count("\n\n".join(current_parts)) > max_tokens:
                current_parts = [unit]
            current_tokens = counter.count("\n\n".join(current_parts))
        else:
            current_parts.append(unit)
            current_tokens += unit_tokens

    if current_parts:
        emitted = "\n\n".join(current_parts).strip()
        if emitted and (counter.count(emitted) >= min_tokens or not chunks):
            chunks.append(emitted)
        elif emitted and chunks:
            chunks[-1] = f"{chunks[-1]}\n\n{emitted}".strip()

    return chunks


def _iter_text_units(
    text: str, counter: TokenCounter, *, max_tokens: int
) -> Iterable[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    for paragraph in paragraphs:
        if counter.count(paragraph) <= max_tokens:
            yield paragraph
            continue
        for sentence_group in _split_long_paragraph(paragraph, counter, max_tokens):
            yield sentence_group


def _split_long_paragraph(
    paragraph: str, counter: TokenCounter, max_tokens: int
) -> list[str]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", paragraph) if s.strip()]
    groups: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = counter.count(sentence)
        if sentence_tokens > max_tokens:
            if current:
                groups.append(" ".join(current))
                current = []
                current_tokens = 0
            groups.extend(counter.windows(sentence, max_tokens=max_tokens, overlap_tokens=0))
            continue
        if current and current_tokens + sentence_tokens > max_tokens:
            groups.append(" ".join(current))
            current = [sentence]
            current_tokens = sentence_tokens
        else:
            current.append(sentence)
            current_tokens += sentence_tokens

    if current:
        groups.append(" ".join(current))
    return groups


def _build_chunk(
    document: NormalizedDocument,
    section: NormalizedSection,
    text: str,
    *,
    chunk_index: int,
    citation_kind: str,
    citation_number: int,
    token_counter: TokenCounter,
    is_table: bool,
) -> ChunkInput:
    normalized_text = text.strip()
    return ChunkInput(
        chunk_id=str(uuid.uuid4()),
        document_id=document.document_id,
        ticker=document.ticker.upper(),
        cik=document.cik,
        company_name=document.company_name,
        filing_type=document.filing_type,
        accession_number=document.accession_number,
        filed_at=document.filed_at,
        fiscal_period=document.fiscal_period,
        section=section.section_id,
        item_label=section.item_label,
        section_title=section.title,
        chunk_index=chunk_index,
        text=normalized_text,
        text_hash=text_hash(normalized_text),
        token_count=token_counter.count(normalized_text),
        citation_anchor=citation_anchor(
            document.ticker,
            document.filing_type,
            section.item_label,
            citation_kind,
            citation_number,
        ),
        source_url=document.source_url,
        is_table=is_table,
    )
