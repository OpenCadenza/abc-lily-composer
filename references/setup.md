<!-- knowledge: operation.setup -->
# 环境准备

先复用已有工具。Python 3.11+；只有 music21 分析需要 Python 包，编译只用标准库。脚本不会安装程序或编辑配置。依赖放在用户工作区，不往 Skill 安装目录写文件。

## 检测

将 `<skill>` 替换为安装目录绝对路径，路径含空格需加引号。Windows 用 `python` 或 `py -3`，Unix 用 `python3`。

```text
python <skill>/scripts/check_environment.py --format abc --analysis
python <skill>/scripts/check_environment.py --format lilypond --analysis
```

JSON 列出所有工具；退出码只取决于选定格式的必需项及 `--analysis`。不分析可省略该参数。默认 `--format all` 要求两种格式的编译器。工具发现顺序：显式 `--lilypond` / `--abc2midi` / `--abc2abc`，对应环境变量 `LILYPOND_PATH` / `ABC2MIDI_PATH` / `ABC2ABC_PATH`，最后 PATH。编译时 abc2abc 还会尝试 abc2midi 的同目录位置。

## music21

在用户作品目录创建虚拟环境，无需激活，不需配置外部谱面查看器。

Windows PowerShell：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r "<skill>\scripts\requirements.txt"
```

macOS / Linux：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r "<skill>/scripts/requirements.txt"
```

之后脚本用这个解释器运行。依赖固定为已验证的 music21 9.9.1；版本不兼容先检查 pip 错误，不忽略安装失败。参见 [music21 安装指南](https://music21.org/music21docs/usersGuide/usersGuide_01_installing.html)。

## 编译器

[LilyPond 官方发布页](https://lilypond.org/download.html) 提供 Windows、macOS、Linux 包。解压到用户工具目录并传可执行文件路径，不必改全局 PATH。源码 version 按实际兼容版本；当前验证版本 2.26.0。已有 Homebrew 的 macOS 可 `brew install lilypond`，Debian/Ubuntu 可 `sudo apt install lilypond`；先遵守宿主权限并检查发行版版本，不自动升级整个系统。

ABC 需同一 abcMIDI 发行包中的 abc2midi 和 abc2abc。macOS/Homebrew：`brew install abcmidi`；Debian/Ubuntu：`sudo apt install abcmidi`。Windows 从 [abcMIDI 上游](https://ifdo.ca/~seymour/runabc/top.html) 选择 Windows 包并解压，保留依赖文件布局，传两个 exe 路径。参考 [Homebrew 包说明](https://formulae.brew.sh/formula/abcmidi)。

安装后重新检测。程序存在不等于可用；编译仍需检查退出码与日志。脚本是受信任本机工具，不是隔离服务；LilyPond Scheme 可执行程序，陌生来源谱遵循宿主的执行和隔离规则。
