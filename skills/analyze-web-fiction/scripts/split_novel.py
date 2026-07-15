#!/usr/bin/env python3
"""Split Chinese novels on chapter boundaries and emit Markdown chunks plus manifest.json."""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

DEFAULT_PATTERN = r"(?m)^\s*(?:第[零〇一二三四五六七八九十百千万两\d]+[章节卷回集部篇]\s*[^\n]*|\d+[、.]\s*第?[^\n]{0,80})\s*$"

def read_text(path: Path):
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try: return path.read_text(encoding=enc), enc
        except UnicodeDecodeError: pass
    raise ValueError(f"无法识别编码：{path}")

def clean_text(text: str):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"(?m)^.*(?:请点击下一页继续阅读|最新网址|手机用户请浏览|本章未完).*$", "", text)

def chapter_spans(text: str, pattern: str = DEFAULT_PATTERN):
    ms = list(re.finditer(pattern, text))
    if not ms: return [{"index": 1, "title": "全文（未识别章节）", "start": 0, "end": len(text)}], 0
    items=[]
    for i,m in enumerate(ms):
        end = ms[i+1].start() if i+1 < len(ms) else len(text)
        items.append({"index": i+1, "title": m.group().strip(), "start": m.start(), "end": end})
    return items, ms[0].start()

def paragraph_pieces(text, start, end, limit):
    cursor=start
    while end-cursor > limit:
        ceiling=cursor+limit
        cut=text.rfind("\n\n", cursor+limit//2, ceiling)
        if cut <= cursor: cut=text.rfind("\n", cursor+limit//2, ceiling)
        if cut <= cursor: cut=ceiling
        yield cursor,cut; cursor=cut
    if cursor < end: yield cursor,end

def build_chunks(text, chapters, target):
    chunks=[]; parts=[]; labels=[]; size=0; split=False
    def flush():
        nonlocal parts,labels,size,split
        if parts: chunks.append({"chapter_start":labels[0],"chapter_end":labels[-1],"start":parts[0][0],"end":parts[-1][1],"chars":sum(b-a for a,b in parts),"oversized_chapter_split":split})
        parts=[]; labels=[]; size=0; split=False
    for ch in chapters:
        pieces=list(paragraph_pieces(text,ch["start"],ch["end"],target))
        for n,(a,b) in enumerate(pieces,1):
            if parts and size+b-a > target: flush()
            suffix=f" [片段{n}/{len(pieces)}]" if len(pieces)>1 else ""
            labels.append(f'{ch["index"]}:{ch["title"]}{suffix}'); parts.append((a,b)); size += b-a
            split = split or len(pieces)>1
    flush(); return chunks

def write_split(source,text,encoding,chapters,prefix,chunks,output):
    folder=output/"chunks"; folder.mkdir(parents=True,exist_ok=True)
    for i,item in enumerate(chunks,1):
        name=f"{i:04d}.md"; item["file"]=f"chunks/{name}"
        header=f"# 区块 {i}/{len(chunks)}\n\n范围：{item['chapter_start']} → {item['chapter_end']}\n\n"
        (folder/name).write_text(header+text[item["start"]:item["end"]],encoding="utf-8")
    for ch in chapters: ch["chars"]=ch["end"]-ch["start"]
    manifest={"source":str(source.resolve()),"source_encoding":encoding,"total_chars":len(text),"chapter_count":len(chapters),"unmatched_prefix_chars":prefix,"chapters":chapters,"chunk_count":len(chunks),"chunks":chunks}
    (output/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")

def parse_args():
    p=argparse.ArgumentParser(description="按章节边界拆分中文小说并生成 manifest")
    p.add_argument("source",type=Path); p.add_argument("--output",type=Path); p.add_argument("--chunk-chars",type=int,default=80000)
    p.add_argument("--chapter-pattern",default=DEFAULT_PATTERN); p.add_argument("--dry-run",action="store_true"); return p.parse_args()

def main():
    if hasattr(sys.stdout,"reconfigure"): sys.stdout.reconfigure(encoding="utf-8",errors="backslashreplace")
    a=parse_args(); raw,enc=read_text(a.source); text=clean_text(raw); chapters,prefix=chapter_spans(text,a.chapter_pattern); chunks=build_chunks(text,chapters,a.chunk_chars)
    print(json.dumps({"source":str(a.source),"chars":len(text),"chapters":len(chapters),"chunks":len(chunks),"unmatched_prefix_chars":prefix},ensure_ascii=False,indent=2))
    if not a.dry_run:
        out=a.output or a.source.with_name(a.source.stem+"_chunks"); write_split(a.source,text,enc,chapters,prefix,chunks,out); print(f"已写入：{out.resolve()}")
    return 0
if __name__ == "__main__": raise SystemExit(main())