# abc-lily-composer

[English](README.md) · [问题反馈](https://github.com/OpenCadenza/abc-lily-composer/issues)

为 Coding Agent 提供 **ABC / LilyPond 创作、编辑与分析**能力。Agent 直接写原生谱，调用本地编译和分析工具，再根据真实音符、诊断及审稿结果修订。

宿主提供模型、文件工具、终端和可用的只读审稿子 Agent；无需另配模型 API，也不需要独立 Agent 服务。Skill 指令和详细操作文档目前使用中文。

## 能力与产物

- 创作主题、发展材料、组织曲式，保留指定旋律并修改局部，或只读分析已有作品。
- ABC 经 abcMIDI 生成 MIDI；LilyPond 按谱中声明生成 PDF/MIDI。
- 可选 music21 分析音符、音域、时间位置、和声与声部进行候选。
- 通过宿主 GitHub MCP 按需读取远端知识，记录文章、示例、修订与来源。
- 根据实际谱面审稿；修改后重新编译，过期源码或产物不能复用旧报告。

编译通过不证明乐理或艺术质量通过。MIDI 是演奏数据，本工具不渲染音频；ABC PDF 排版、自动伴奏和托管作曲服务不在随附工具范围内。LilyPond 的 MIDI 分析不能恢复原谱等音拼写。

## 安装

需要 Node.js/npm 运行 [Skills CLI](https://github.com/vercel-labs/skills)：

```sh
npx skills add OpenCadenza/abc-lily-composer --skill abc-lily-composer
```

安装器会让你选择支持的 Agent。例如安装到当前项目供 Codex 使用：

```sh
npx skills add OpenCadenza/abc-lily-composer --skill abc-lily-composer --agent codex
```

加 `--global` 可安装到用户级。只查看可安装 Skill，不执行安装：

```sh
npx skills add OpenCadenza/abc-lily-composer --list
```

也可克隆或复制仓库，交给宿主的 Skill 加载器。入口是 [SKILL.md](SKILL.md)。安装直接使用 GitHub 仓库，无需另发 npm 包；安装 Skill 不会自动安装 Python、编译器、music21 或 GitHub MCP。

## 首次使用

1. 准备 Python **3.11+**。LilyPond 任务需要 LilyPond；ABC 任务需要同一 abcMIDI 发行包中的 abc2midi 和 abc2abc。
2. 需要分析时，在用户作品目录创建虚拟环境，使用 Skill 内的 scripts/requirements.txt 安装固定版本 music21。依赖和产物放在作品目录。
3. 让宿主使用 abc-lily-composer，按安装位置解析脚本的绝对路径，读取 [环境准备](references/setup.md) 和 [脚本说明](references/scripts.md)。
4. 创作、改谱和音乐分析前必须通过 GitHub MCP 实际读取相关作曲参考，不能只看目录/摘要。缺少 MCP 时先主动安装、注册官方 GitHub MCP 并验证真实读取；按 [安装与读取流程](references/github-knowledge.md) 执行，需要用户完成的登录/重载步骤完成后才继续。

可直接提出这样的任务：

> 用 abc-lily-composer 写八小节 C 大调钢琴曲，发展两小节动机，交付完整 LilyPond 源码、PDF 和 MIDI，说明未解决的审稿疑问。

> 修改这份 ABC 的第 9–16 小节，保留旋律，编译后核对与第 17 小节的接缝。

> 只读分析这份乐谱。为每项判断提供实际音符和声部依据，区分计算事实与分析解释。

### 直接使用脚本

将 `<skill>` 替换为安装目录的绝对路径，在作品目录运行。macOS/Linux 可改用 python3，分析时使用已安装 music21 的解释器。

```sh
python "<skill>/scripts/check_environment.py" --format lilypond
python "<skill>/scripts/compile_score.py" --source piece.ly --output-dir build --require pdf --require midi
python "<skill>/scripts/analyze_score.py" --source piece.ly --compile-report "<编译结果中的report_path>" --meter 4/4 --first 1 --last 8 --kind notes
```

谱中须包含所需 layout/MIDI 声明。ABC 编译使用 `--source melody.abc --require midi`。分析报告必须对应当前源码，且与编译产物保留原相对布局。编译器可通过显式参数、LILYPOND_PATH / ABC2MIDI_PATH / ABC2ABC_PATH 或 PATH 提供。脚本输出 JSON，需读取退出码和完整诊断。

## 知识库接入状态

[knowledge-source.json](knowledge-source.json) 指向公开的 [OpenCadenza/music-knowledge-base](https://github.com/OpenCadenza/music-knowledge-base) 的 main。该仓库发布 Wiki 管理员批准的固定修订。本 Skill 提供检索指引，不附带知识正文、Wiki、导入或发布服务；安装不会自动连接 GitHub MCP。

认证使用宿主 GitHub MCP，配置文件不保存凭据。需要其他兼容知识源时修改 owner/repo，或明确告知宿主；更新 Skill 时保留自己的配置。

按 [读取流程](references/github-knowledge.md) 固定 commit，读取同一快照的 manifest、TSV 目录、选中文章和来源。目录是主要入口，搜索为空不等于没有文章；只采用 manifest 列出的文章，核对实际 UTF-8 SHA-256 与修订。Git Blob SHA 不是文章 SHA-256。

目标 LilyPond 版本以 manifest 为准，ABC 保持原样。compilation_validation=not_performed 表示转换不保证编译、渲染或音乐正确，published 不能替代本次编译与审稿。交付列出实际读取的文章固定 commit 链接、谱例和来源，并说明如何用于本次写作。没有精确专题时读取适用基础参考并说明不足；任何正文都无法读取时先解决安装、授权或网络阻塞，不能静默跳过检索直接写谱。

## 分发与许可

线上分支只保留可安装运行文件及说明。开发指令、测试、CI 和打包工具保存在本地开发分支，不随运行包分发。问题反馈使用 [Issues](https://github.com/OpenCadenza/abc-lily-composer/issues)，安全边界和漏洞报告见 [SECURITY.md](SECURITY.md)。

原创代码和新指令采用 [MIT](LICENSE)。既有 setup、scripts、review 三份操作文档继续采用 **CC BY-SA 4.0**，保留 OpusLoom contributors 署名，详见 [NOTICE](NOTICE.md)。远端知识与第三方谱例保留各自许可。
