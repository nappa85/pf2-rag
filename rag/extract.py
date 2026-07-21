import json
import os
import re
import glob

from rag.config import PDFS_DIR, MARKDOWN_DIR, CHUNKS_PATH, CHUNK_SIZE, CHUNK_OVERLAP


def convert_pdfs_to_markdown(pdfs_dir: str = PDFS_DIR, output_dir: str = MARKDOWN_DIR, use_marker: bool = True) -> list[str]:
    os.makedirs(output_dir, exist_ok=True)
    pdf_files = sorted(glob.glob(os.path.join(pdfs_dir, "*.pdf")))
    if not pdf_files:
        print(f"No PDFs found in {pdfs_dir}")
        return []

    if use_marker:
        return _convert_with_marker(pdf_files, output_dir)
    return _convert_with_pymupdf(pdf_files, output_dir)


def _convert_with_pymupdf(pdf_files: list[str], output_dir: str) -> list[str]:
    import fitz

    output_paths = []
    for pdf_path in pdf_files:
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        out_path = os.path.join(output_dir, f"{pdf_name}.md")

        if os.path.exists(out_path):
            print(f"  [skip] {pdf_name} (markdown exists)")
            output_paths.append(out_path)
            continue

        print(f"  [extract] {pdf_name}...")
        doc = fitz.open(pdf_path)
        md_parts = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text", sort=True)
            if not text.strip():
                continue

            headers = _detect_headers(page, text)
            if headers:
                md_parts.append(headers)

            lines = text.strip().split("\n")
            cleaned = []
            for line in lines:
                line = line.strip()
                if line:
                    cleaned.append(line)
            if cleaned:
                md_parts.append("\n".join(cleaned))
            md_parts.append("")

        markdown_text = "\n".join(md_parts).strip()
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(markdown_text)
        output_paths.append(out_path)
        print(f"  [done] {pdf_name}: {len(doc)} pages -> {len(markdown_text)} chars")
        doc.close()

    return output_paths


def _detect_headers(page, text: str) -> str:
    import fitz
    blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
    font_sizes = []
    for b in blocks:
        if b.get("type") != 0:
            continue
        for line in b.get("lines", []):
            for span in line.get("spans", []):
                if span.get("text", "").strip():
                    font_sizes.append(span.get("size", 0))

    if not font_sizes:
        return ""

    max_size = max(font_sizes)
    avg_size = sum(font_sizes) / len(font_sizes)
    threshold = avg_size + (max_size - avg_size) * 0.5

    header_lines = []
    for b in blocks:
        if b.get("type") != 0:
            continue
        for line in b.get("lines", []):
            line_text = ""
            line_size = 0
            for span in line.get("spans", []):
                txt = span.get("text", "").strip()
                if txt:
                    line_text += txt + " "
                    line_size = max(line_size, span.get("size", 0))
            line_text = line_text.strip()
            if line_text and line_size >= threshold and len(line_text) < 100:
                if line_size >= max_size * 0.95:
                    header_lines.append(f"## {line_text}")
                else:
                    header_lines.append(f"### {line_text}")

    return "\n".join(header_lines) if header_lines else ""


def _convert_with_marker(pdf_files: list[str], output_dir: str) -> list[str]:
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict

    converter = PdfConverter(artifact_dict=create_model_dict(), config={"force_ocr": False})
    output_paths = []
    for pdf_path in pdf_files:
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        out_path = os.path.join(output_dir, f"{pdf_name}.md")

        if os.path.exists(out_path):
            print(f"  [skip] {pdf_name} (markdown exists)")
            output_paths.append(out_path)
            continue

        print(f"  [convert] {pdf_name}...")
        rendered = converter(pdf_path)
        markdown_text = rendered.markdown

        with open(out_path, "w", encoding="utf-8") as f:
            f.write(markdown_text)
        output_paths.append(out_path)
        print(f"  [done] {pdf_name} -> {len(markdown_text)} chars")

    return output_paths


def _split_markdown_by_headers(text: str) -> list[dict]:
    sections = []
    current_headers = {1: "", 2: "", 3: "", 4: ""}
    current_lines = []

    for line in text.split("\n"):
        header_match = re.match(r"^(#{1,4})\s+(.+)$", line)
        if header_match:
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    breadcrumb = " > ".join(
                        h for h in [current_headers.get(1, ""), current_headers.get(2, "")]
                        if h
                    )
                    sections.append({"section": breadcrumb, "text": body})
                current_lines = []

            level = len(header_match.group(1))
            title = header_match.group(2).strip()
            current_headers[level] = title
            for l in range(level + 1, 5):
                current_headers[l] = ""
        else:
            current_lines.append(line)

    if current_lines:
        body = "\n".join(current_lines).strip()
        if body:
            breadcrumb = " > ".join(
                h for h in [current_headers.get(1, ""), current_headers.get(2, "")]
                if h
            )
            sections.append({"section": breadcrumb, "text": body})

    return sections


def _split_long_text(text: str, max_chars: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    paragraphs = re.split(r"\n{2,}", text)
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current = current + "\n\n" + para if current else para
        else:
            if current:
                chunks.append(current)
            if len(para) > max_chars:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                current = ""
                for sent in sentences:
                    if len(current) + len(sent) + 1 <= max_chars:
                        current = current + " " + sent if current else sent
                    else:
                        if current:
                            chunks.append(current)
                        current = sent
                if len(current) > max_chars:
                    for i in range(0, len(current), max_chars - overlap):
                        chunks.append(current[i : i + max_chars])
                    current = ""
            else:
                current = para

    if current:
        chunks.append(current)

    return chunks


def _merge_short_sections(sections: list[dict], min_chars: int = 100) -> list[dict]:
    if not sections:
        return sections

    merged = []
    buffer = sections[0].copy()

    for sec in sections[1:]:
        if len(buffer["text"]) < min_chars and buffer.get("section") == sec.get("section"):
            buffer["text"] += "\n\n" + sec["text"]
        else:
            merged.append(buffer)
            buffer = sec.copy()

    merged.append(buffer)
    return merged


def chunk_markdown_file(md_path: str, source: str) -> list[dict]:
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    sections = _split_markdown_by_headers(text)
    sections = _merge_short_sections(sections)

    chunks = []
    for sec in sections:
        sub_chunks = _split_long_text(sec["text"])
        for sc in sub_chunks:
            chunks.append({
                "source": source,
                "section": sec["section"],
                "text": sc.strip(),
            })

    return chunks


def build_chunks(pdfs_dir: str = PDFS_DIR, md_dir: str = MARKDOWN_DIR, output_path: str = CHUNKS_PATH, use_marker: bool = True) -> str:
    backend = "Marker" if use_marker else "PyMuPDF"
    print("=" * 50)
    print(f"Step 1: Convert PDFs to Markdown ({backend})")
    print("=" * 50)
    md_paths = convert_pdfs_to_markdown(pdfs_dir, md_dir, use_marker=use_marker)

    print()
    print("=" * 50)
    print("Step 2: Chunk markdown files")
    print("=" * 50)

    all_chunks = []
    for md_path in sorted(md_paths):
        source = os.path.splitext(os.path.basename(md_path))[0]
        chunks = chunk_markdown_file(md_path, source)
        print(f"  {source}: {len(chunks)} chunks")
        all_chunks.extend(chunks)

    for i, chunk in enumerate(all_chunks):
        chunk["id"] = i

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"\nTotal: {len(all_chunks)} chunks -> {output_path}")
    return output_path


if __name__ == "__main__":
    build_chunks()
