> 本分支为 i-score 服务器适配：Pi 通过 score_compile 请求编译，成功后用 score_submit 提交并立即结束本轮；暂不支持用户多文件依赖工程。执行以 [服务器工具契约](references/server-tools.md) 为准。下方本地脚本说明属于通用上游工具，不是服务器执行流程。

# abc-lily-composer

[English](README.md) · [贡献指南](CONTRIBUTING.md)

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
4. 需要知识检索时，在宿主中连接只读 GitHub MCP，并按 [读取流程](references/github-knowledge.md) 接入。

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

[knowledge-source.json](knowledge-source.json) 默认指向 `OpenCadenza/music-knowledge-base` 的 main 分支。**当前尚未确认该知识端点可用。** Wiki.js、数据库导入和 GitHub 发布服务由独立项目建设，安装本 Skill 不会部署这些服务，也不会附带知识快照。

认证使用宿主 GitHub MCP，配置文件不保存凭据。需要其他兼容知识源时修改 owner/repo，或明确告知宿主；更新 Skill 时保留自己的配置。

读取时尽量固定 commit，从目录与索引选择正文，记录知识/示例 ID、修订和来源。搜索片段仅作定位；仓库不可达时明确说明，已有乐谱仍可使用本地工具编译、分析。

## 参与开发与许可

开发、可选测试和分发打包见 [CONTRIBUTING.md](CONTRIBUTING.md)。打包工作流只检查 Python 语法并在 Linux/Windows 构建分发包，不运行模型、不编译整库谱例，也不证明音乐质量。问题反馈使用 [Issues](https://github.com/OpenCadenza/abc-lily-composer/issues)，安全边界和漏洞报告见 [SECURITY.md](SECURITY.md)。

原创代码和新指令采用 [MIT](LICENSE)。既有 setup、scripts、review 三份操作文档继续采用 **CC BY-SA 4.0**，保留 OpusLoom contributors 署名，详见 [NOTICE](NOTICE.md)。远端知识与第三方谱例保留各自许可。
