# abc-lily-composer

[中文说明](README.zh-CN.md) · [Install](#install) · [Issues](https://github.com/OpenCadenza/abc-lily-composer/issues)

An Agent Skill for composing, editing, and analyzing **ABC and LilyPond scores**. Your coding agent writes the native notation, uses local tools for compilation and measurable facts, and revises the actual music using those results.

Works with a host that supports Agent Skills, file editing, and shell commands. Independent review uses the host's subagents when available. No separate model API or custom agent runtime is required. The Skill instructions and detailed operational references are currently written in Chinese.

## What it does

- Compose and develop musical material, edit selected passages, or analyze an existing score without changing it.
- Compile ABC with abcMIDI, or LilyPond with the LilyPond compiler; keep diagnostics and a report tied to the source and output hashes.
- Use optional music21 analysis for notes, register, timing, harmony candidates, and voice-leading candidates.
- Read relevant theory and examples from a separate GitHub knowledge repository through the host's GitHub MCP connection.
- Review the actual notation and evidence, distinguish confirmed problems from uncertain musical judgments, and recompile after changes.

| Format | Output from the included tools | Analysis |
| --- | --- | --- |
| ABC | MIDI, including multiple `X:` tunes | Native ABC facts where consistent with MIDI; otherwise disclosed MIDI fallback |
| LilyPond | PDF and MIDI when requested and present in the score | MIDI-based facts; original enharmonic spelling is not recovered |

Compilation does not establish musical correctness or artistic quality. MIDI is performance data; this Skill does not render audio. ABC PDF engraving, automatic accompaniment, and a hosted composition service are outside the included tools.

## Install

Use Node.js/npm to run the [Skills CLI](https://github.com/vercel-labs/skills):

```sh
npx skills add OpenCadenza/abc-lily-composer --skill abc-lily-composer
```

The installer lets you select a supported agent. For example, install for Codex in the current project:

```sh
npx skills add OpenCadenza/abc-lily-composer --skill abc-lily-composer --agent codex
```

Add `--global` if you want a user-wide installation instead. To inspect available skills without installing:

```sh
npx skills add OpenCadenza/abc-lily-composer --list
```

For manual installation, clone or copy the repository to a location your host can load as a Skill. [SKILL.md](SKILL.md) is the entry point. This repository is installed directly from GitHub; there is no separate npm package to install.

Installing the Skill does **not** install compilers, Python packages, or GitHub MCP. See the [Skills CLI command reference](https://github.com/vercel-labs/skills/blob/main/docs/commands.md) for agent selection and installation scope.

## First use

1. Install Python **3.11+** and the tools needed for your task: [LilyPond](https://lilypond.org/download.html) for `.ly`, or `abc2midi` and `abc2abc` from [abcMIDI](https://ifdo.ca/~seymour/runabc/top.html) for `.abc`.
2. For musical analysis, install the pinned music21 dependency into a virtual environment in your **score workspace**, using the installed Skill's `scripts/requirements.txt`.
3. Ask the host to use `abc-lily-composer`. It should resolve the installed Skill path, read the [setup guide](references/setup.md), and run the [appropriate scripts](references/scripts.md).
4. For knowledge retrieval, connect a read-only GitHub MCP in your host and follow the [knowledge reading guide](references/github-knowledge.md).

Example prompts:

> Use abc-lily-composer to write an eight-bar piano piece in C major. Develop a two-bar motive, deliver a complete LilyPond file with PDF and MIDI, and explain any unresolved review findings.

> Revise bars 9–16 of this ABC score while preserving the melody. Compile the result and check the transition into bar 17.

> Analyze this score without editing it. Cite the actual notes and voices behind each claim, and separate measured facts from interpretation.

### Optional analysis environment

Create the virtual environment in your score workspace. Replace `<skill>` with the installed Skill path.

Windows PowerShell:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r "<skill>\scripts\requirements.txt"
```

macOS/Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r "<skill>/scripts/requirements.txt"
```

Run analysis with that environment's Python interpreter. Compilation alone does not require music21.

### Use the scripts directly

Replace `<skill>` with the **absolute installation path**. Run these commands from your score workspace. On macOS/Linux, use `python3` or your virtual environment's interpreter.

```sh
python "<skill>/scripts/check_environment.py" --format lilypond
python "<skill>/scripts/compile_score.py" --source piece.ly --output-dir build --require pdf --require midi
python "<skill>/scripts/analyze_score.py" --source piece.ly --compile-report "<report-path-from-compilation>" --meter 4/4 --first 1 --last 8 --kind notes
```

The LilyPond score must include the layout/MIDI declarations needed for the requested outputs. For ABC, use `--source melody.abc --require midi`. Analysis requires music21 and the successful report for the **current** source. Keep the report and its artifacts together; changed or missing artifacts invalidate it.

Compiler discovery supports explicit command options, `LILYPOND_PATH`, `ABC2MIDI_PATH`, and `ABC2ABC_PATH`, then `PATH`. Commands emit JSON; inspect their exit status and diagnostics. See [script usage](references/scripts.md) for selection, paging, pickups, and analysis limitations.

## Knowledge repository

[knowledge-source.json](knowledge-source.json) points to the public [OpenCadenza/music-knowledge-base](https://github.com/OpenCadenza/music-knowledge-base), branch `main`. It publishes administrator-approved Wiki revisions. This Skill includes retrieval instructions, not the corpus, Wiki.js, an importer, or a publisher. Installing it does not install GitHub MCP.

The host reads the repository using its own GitHub MCP credentials. No token belongs in the configuration file. To use another compatible knowledge source, change the owner/repository in your installation or tell the host which source to use; preserve custom settings when updating the Skill.

Follow the [knowledge reading guide](references/github-knowledge.md): resolve the branch to a commit, read its manifest and TSV catalog, then fetch selected articles and source records at that same commit. The catalog is the primary entry point; an empty code-search result does not mean the repository has no articles. Use only manifest-listed articles and verify their actual UTF-8 SHA-256 and revision metadata. Git Blob SHAs are not article SHA-256 values.

The manifest defines the current LilyPond target; ABC is preserved. `compilation_validation=not_performed` means conversion has not established compilation, rendering, or musical correctness, even if an example is labelled published. Compile and review any reused material in the actual work. Record the commit, article revision, example IDs, and sources used. If retrieval or verification is incomplete, disclose it; local composition, compilation and analysis remain available.

## Runtime layout

```text
SKILL.md                 Agent entry point
knowledge-source.json    Remote knowledge location; no credentials
references/              Setup, script, review, and retrieval guidance
scripts/                 Local compilation and analysis tools
```

The online branch contains the installable runtime and its documentation. Development instructions, tests, CI definitions and packaging tools are maintained on a local development branch and are not included in this distribution. Report reproducible problems through [GitHub Issues](https://github.com/OpenCadenza/abc-lily-composer/issues). Read [SECURITY.md](SECURITY.md) for execution boundaries and vulnerability reports.

## License

Original code and new Skill instructions are [MIT licensed](LICENSE). The inherited `references/setup.md`, `references/scripts.md`, and `references/review.md` remain **CC BY-SA 4.0**, with attribution to OpusLoom contributors. See [NOTICE.md](NOTICE.md) for the file-level distinction. Remote theory text, scores, and examples retain their own licenses and attribution requirements.
