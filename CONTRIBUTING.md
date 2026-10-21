# Contributing

Thanks for helping improve ABC/LilyPond composition and review. Use [Issues](https://github.com/OpenCadenza/abc-lily-composer/issues) for reproducible bugs and focused feature proposals, or submit a pull request.

## Where changes belong

- `SKILL.md`: the host's composition, editing, review, and delivery workflow. Keep it short; put conditional detail in the appropriate reference.
- `references/`: operational guidance, including environment setup and remote knowledge reading.
- `scripts/`: deterministic compilation, analysis, and distribution helpers. Use the host's existing file, terminal, Git, and model capabilities rather than building another agent framework.
- `tests/`: observable runtime and distribution behavior. A compiler passing is not evidence of musical quality.

Music theory articles, composer examples, source collections, Wiki importers, and publication workers belong to the separately maintained knowledge project. Do not add a corpus or generated knowledge snapshot to this Skill.

## Development

Use Python 3.11+. Compilation and packaging use the standard library. Analysis additionally needs the version pinned in `scripts/requirements.txt`; install it in a workspace virtual environment. Compilers are external dependencies. Read the [setup guide](references/setup.md) for discovery options.

For relevant code changes, run:

```sh
python -m unittest discover -s tests -v
```

Tests use isolated workspaces. Missing compilers or music21 cause the corresponding integration cases to be skipped; include skips in your report. The tests do not call a model service. Report the compiler versions and actual scope separately from judgments about musical correctness.

For documentation changes, keep the English and [Chinese README](README.zh-CN.md) consistent. Preserve working installation commands and distinguish the available tools from the separate knowledge integration.

## Distribution

The Skills CLI discovers the root `SKILL.md` directly from GitHub. A `package.json`, an npm publish, and a hosted Wiki service are not needed to distribute this repository as a Skill.

To create an optional runtime ZIP:

```sh
python scripts/package_skill.py --output dist/abc-lily-composer.zip
```

The destination must be new: the packager deliberately refuses to overwrite an existing archive. Choose a new filename for a later build. The file whitelist includes public documentation and licenses, runtime scripts, and operational references. When adding a linked local document, update the whitelist so the installed archive remains self-contained. Development tests and CI files are not part of the ZIP.

The GitHub packaging workflow checks syntax and creates the archive on Linux and Windows. It does not install compilers or music21, run model evaluations, or compile musical examples. Publishing a GitHub Release, changing repository settings, and pushing commits are separate maintainer actions.

## Pull requests

Describe the concrete problem, the resulting behavior, and the relevant checks or limitations. Include a minimal synthetic score when needed; do not upload private scores, tokens, or full copyrighted collections. Keep original notation intact unless a requested musical edit requires a change.

Keep public configuration credential-free. Read [SECURITY.md](SECURITY.md) before reporting a vulnerability. Be respectful, specific, and evidence-based in discussions.

## Licensing

Contributions must be yours to license and compatible with the affected files. Original code and new instructions use [MIT](LICENSE). Inherited operational documents remain CC BY-SA 4.0, as described in [NOTICE.md](NOTICE.md). Preserve attribution and record adaptations to those documents. Do not relicense third-party scores or remote knowledge by adding them to a pull request.
