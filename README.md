# abc-lily-composer

为 Coding Agent 提供 ABC/LilyPond 创作、编辑、编译和分析。宿主提供模型、文件工具、终端与可用的独立审稿者。音乐知识通过 GitHub MCP 从独立的 music-knowledge-base 仓库按需读取。

## 安装与首次使用

独立公开仓库发布后运行（替换 `<owner>`）：

```sh
npx skills add <owner>/abc-lily-composer --skill abc-lily-composer
```

也可将本目录交给宿主的 Skill 加载器。入口是 [SKILL.md](SKILL.md)。安装不会安装 Python、music21、编译器或 GitHub MCP。

先读 [环境准备](references/setup.md) 与 [脚本用法](references/scripts.md)。设置 [知识来源配置](knowledge-source.json) 中的 owner；默认 repo 为 music-knowledge-base、branch 为 main。owner 初始为 null，表示尚未配置。宿主的 MCP 认证独立配置，凭据不写入此文件。

按 [知识读取流程](references/github-knowledge.md) 接入远端。随附资料只包含操作说明；包内不附音乐知识快照。环境检测脚本不负责判断宿主 MCP 是否可用。

示例：写八小节旋律，发展两小节动机，生成 MIDI，核查实际音符，再按 [审稿指引](references/review.md) 复核。

## 开发与验证

```sh
python -m unittest discover -s tests -v
python scripts/package_skill.py --output dist/abc-lily-composer.zip
```

打包采用白名单，不需要知识库、数据库或相邻工作目录。GitHub 读取、鉴权和完整创作流程需在实际宿主中验证。编译成功和模型审稿不证明艺术质量。

原创代码及新指令采用 [MIT](LICENSE)。既有操作资料保留原许可，详见 [NOTICE](NOTICE.md)。
