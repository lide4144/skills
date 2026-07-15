#!/usr/bin/env python3
"""Batch-analyze Chinese web-fiction files by invoking `codex exec`."""

from __future__ import annotations
import argparse, re, subprocess, sys
from pathlib import Path

EXTENSIONS = {".txt", ".md"}
CHAPTER_RE = re.compile(r"(?m)^\s*(?:第[零〇一二三四五六七八九十百千万两\d]+[章节卷回集部篇]\s*[^\n]*|\d+[、.]\s*第?[^\n]{0,80})\s*$")

def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try: return path.read_text(encoding=encoding)
        except UnicodeDecodeError: pass
    raise ValueError(f"无法识别文本编码: {path}")

def clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"(?m)^.*(?:请点击下一页继续阅读|最新网址|手机用户请浏览|本章未完).*$", "", text)

def spans(text: str):
    matches = list(CHAPTER_RE.finditer(text))
    if not matches: return [(0, len(text), "全文")]
    return [(m.start(), matches[i+1].start() if i+1 < len(matches) else len(text), m.group().strip()) for i, m in enumerate(matches)]

def samples(text: str, size=6000):
    units = spans(text); positions = (0, .03, .15, .35, .55, .75, .92, 1)
    for i in sorted({round((len(units)-1)*p) for p in positions}):
        start, end, title = units[i]
        yield f"章节单元 {i+1}/{len(units)}：{title}", text[start:min(end, start+size)]

def chunks(text: str, target: int):
    result, bodies, labels, size = [], [], [], 0
    for start, end, title in spans(text):
        body = text[start:end]
        if bodies and size + len(body) > target:
            result.append((f"{labels[0]} 至 {labels[-1]}", "".join(bodies))); bodies, labels, size = [], [], 0
        bodies.append(body); labels.append(title); size += len(body)
    if bodies: result.append((f"{labels[0]} 至 {labels[-1]}", "".join(bodies)))
    return result

def invoke(prompt: str, output: Path, cwd: Path, model: str | None):
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["codex", "--ask-for-approval", "never", "exec", "-", "--skip-git-repo-check", "--ephemeral", "--sandbox", "read-only",
           "-C", str(cwd), "-o", str(output), "--color", "never"]
    if model: cmd += ["--model", model]
    done = subprocess.run(cmd, input=prompt, text=True, encoding="utf-8")
    if done.returncode: raise RuntimeError(f"Codex 调用失败，退出码 {done.returncode}")

def skill_prompt(skill: Path):
    return f"使用位于 {skill} 的 $analyze-web-fiction Skill。完整读取 SKILL.md 及任务所需 reference。不要修改文件，只返回分析报告。"

def sample_run(source, text, output, skill, cwd, model):
    material = "\n\n".join(f"## {label}\n\n{body}" for label, body in samples(text))
    invoke(f"""{skill_prompt(skill)}
对《{source.stem}》做跨全书分层取样分析。开头醒目标注“取样分析”并列出覆盖，不得把未读内容写成事实。
检验创作发动机、信息差、冲突转译、情绪兑现、爽点/认知快感轮换与结构演变；至少提出一个反例或替代解释。

{material}""", output, cwd, model)

def reduce_notes(paths, skill, cwd, model, work, batch=10):
    level, current = 0, paths
    while len(current) > batch:
        nxt = []
        for i in range(0, len(current), batch):
            target = work / f"汇总_L{level}_{i//batch+1:03d}.md"
            material = "\n\n".join(p.read_text(encoding="utf-8") for p in current[i:i+batch])
            invoke(f"{skill_prompt(skill)}\n把以下连续观察压缩成阶段笔记。保留位置证据、模式变化、承诺与兑现、反例和不确定性；不要做全书结论。\n\n{material}", target, cwd, model)
            nxt.append(target)
        current, level = nxt, level+1
    return current

def full_run(source, text, output, skill, cwd, model, chunk_chars, keep):
    sections = chunks(text, chunk_chars); work = output.parent / f".{output.stem}_work"; work.mkdir(parents=True, exist_ok=True)
    notes = []
    for i, (label, body) in enumerate(sections, 1):
        note = work / f"区段_{i:04d}.md"; notes.append(note)
        if note.exists(): continue
        invoke(f"""{skill_prompt(skill)}
这是《{source.stem}》完整顺序阅读的第 {i}/{len(sections)} 区段（{label}）。产出综合用编辑观察，不写全书结论。
记录创作节点、信息状态、冲突层次、情绪波形、结构单元、兑现与遗留承诺，附简短位置证据，并指出至少一处有效或失效机制。

{body}""", note, cwd, model)
    reduced = reduce_notes(notes, skill, cwd, model, work)
    material = "\n\n".join(p.read_text(encoding="utf-8") for p in reduced)
    invoke(f"""{skill_prompt(skill)}
根据顺序覆盖全书的阶段笔记，为《{source.stem}》写完整深度报告。区分持续模式、阶段变化与反例；不要拼接摘要。
说明情绪和结构演变、开篇承诺的兑现，并给出保持作品类型目标的具体修改建议。

{material}""", output, cwd, model)
    if not keep:
        for p in work.iterdir(): p.unlink()
        work.rmdir()

def arguments():
    workspace = Path.cwd().resolve()
    p = argparse.ArgumentParser(description="调用 Codex 批量分析小说文本")
    p.add_argument("--input", type=Path, default=workspace/"小说文本"); p.add_argument("--output", type=Path, default=workspace/"小说分析输出")
    p.add_argument("--mode", choices=("sample", "full"), default="sample", help="sample=跨全书取样；full=覆盖全部正文（成本高）")
    p.add_argument("--pattern", default="*", help="如 *水银*"); p.add_argument("--model"); p.add_argument("--chunk-chars", type=int, default=100000)
    p.add_argument("--overwrite", action="store_true"); p.add_argument("--keep-work", action="store_true")
    return p.parse_args()

def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")
    args = arguments(); skill = Path(__file__).resolve().parents[1]; source_dir = args.input.resolve(); output_dir = args.output.resolve()
    files = sorted(p for p in source_dir.glob(args.pattern) if p.suffix.lower() in EXTENSIONS)
    if not files: print(f"未找到文本：{source_dir} / {args.pattern}", file=sys.stderr); return 2
    failures = []
    for n, source in enumerate(files, 1):
        target = output_dir / f"{source.stem}__{args.mode}分析.md"
        if target.exists() and not args.overwrite: print(f"[{n}/{len(files)}] 跳过：{target.name}"); continue
        print(f"[{n}/{len(files)}] 分析：{source.name}", flush=True)
        try:
            text = clean(read_text(source))
            if args.mode == "sample": sample_run(source, text, target, skill, source_dir.parent, args.model)
            else: full_run(source, text, target, skill, source_dir.parent, args.model, args.chunk_chars, args.keep_work)
        except Exception as exc: failures.append((source, exc)); print(f"  失败：{exc}", file=sys.stderr)
    if failures:
        for source, exc in failures: print(f"- {source.name}: {exc}", file=sys.stderr)
        return 1
    print(f"完成。报告目录：{output_dir}"); return 0

if __name__ == "__main__": raise SystemExit(main())
