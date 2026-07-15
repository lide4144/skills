#!/usr/bin/env python3
"""Batch-analyze Chinese web-fiction files by invoking `codex exec`."""

from __future__ import annotations
import argparse, re, subprocess, sys
from pathlib import Path
from split_novel import chapter_spans as split_chapter_spans, clean_text as split_clean_text, read_text as split_read_text

EXTENSIONS = {".txt", ".md"}
CHAPTER_RE = re.compile(r"(?m)^\s*(?:第[零〇一二三四五六七八九十百千万两\d]+[章节卷回集部篇]\s*[^\n]*|\d+[、.]\s*第?[^\n]{0,80})\s*$")

def read_text(path: Path) -> str:
    return split_read_text(path)[0]

def clean(text: str) -> str:
    return split_clean_text(text)

def spans(text: str):
    units, _ = split_chapter_spans(text)
    return [(u["start"], u["end"], u["title"]) for u in units]

def samples(text: str, target_chars=10000, max_chars=16000, max_radius=30):
    """Yield stratified, adaptively expanded event clusters."""
    units = spans(text); positions = (0, .03, .15, .35, .55, .75, .92, 1)
    for i in sorted({round((len(units)-1)*p) for p in positions}):
        left = right = i
        while units[right][1] - units[left][0] < target_chars:
            changed = False
            if left > 0 and i-left < max_radius:
                left -= 1; changed = True
            if units[right][1] - units[left][0] >= target_chars: break
            if right + 1 < len(units) and right-i < max_radius:
                right += 1; changed = True
            if not changed: break
        start, end = units[left][0], units[right][1]
        body = text[start:min(end, start+max_chars)]
        label = (f"事件簇 {left+1}–{right+1}/{len(units)}（中心章 {i+1}:{units[i][2]}；"
                 f"起 {units[left][2]}；止 {units[right][2]}）")
        yield label, body

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
对《{source.stem}》做跨全书“均匀位置＋相邻章节事件簇”取样分析。开头醒目标注“取样分析”并列出覆盖，不得把未读内容写成事实。
先写未经术语加工的阅读体验底稿，再提出至少两个竞争性总体解释并用证据、反例和盲区比较；不要默认作品核心一定是解释权或认知快感。检验设定新颖性、情感微反应与关系余波、价值选择及代价、情绪兑现和结构演变。必须另写无分析术语的“普通读者席”，并从证据生成 2–4 张“创作启示卡”（机制、条件、迁移原则、两个变体、故事问题、模仿风险）。正文避免重复，详细坐标放证据附录。

{material}""", output, cwd, model)

def reduce_notes(paths, skill, cwd, model, work, batch=10):
    level, current = 0, paths
    while len(current) > batch:
        nxt = []
        for i in range(0, len(current), batch):
            target = work / f"汇总_L{level}_{i//batch+1:03d}.md"
            material = "\n\n".join(p.read_text(encoding="utf-8") for p in current[i:i+batch])
            invoke(f"{skill_prompt(skill)}\n把以下连续观察压缩成阶段笔记。保留位置证据、模式变化、承诺与兑现、普通读者的追读/疲劳/记忆信号、可迁移机制、反例和不确定性；不要做全书结论。\n\n{material}", target, cwd, model)
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
先记录不带理论术语的阅读体验和触发点，包括追读问题、疲劳点、记忆画面及人物亲近/戒备变化；再记录信息状态、承诺与兑现、关系微反应及余波、设定新增约束、价值选择及代价。提出本区段至少两个可能解释，说明各自证据与盲区，并指出至少一处有效或失效机制。

{body}""", note, cwd, model)
    reduced = reduce_notes(notes, skill, cwd, model, work)
    material = "\n\n".join(p.read_text(encoding="utf-8") for p in reduced)
    invoke(f"""{skill_prompt(skill)}
根据顺序覆盖全书的阶段笔记，为《{source.stem}》写完整深度报告。先用体验底稿校验理论，再比较至少两个竞争性解释；区分持续模式、阶段变化与反例，不要拼接摘要或重复同一结论。
必须讨论设定新意是否进入因果、至少一条跨章节情感链、价值如何进入选择与代价、情绪和结构演变及开篇承诺兑现。另写无编辑术语的“普通读者席”，并生成 2–4 张可迁移创作启示卡（机制、成立条件、迁移原则、两个变体、故事问题、模仿风险）。正文精炼，坐标与置信度放证据附录，并给出保持作品类型目标的具体修改建议。

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
