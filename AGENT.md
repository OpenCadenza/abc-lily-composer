# abc-lily-composer 开发入口

运行入口为 [SKILL.md](SKILL.md)，操作说明在 references/，确定性的编译和分析工具在 scripts/。脚本用安装位置解析路径；用户作品、依赖和输出写入用户工作区。

本仓库独立运行，不依赖外层 MusicKnowledgeBase、Wiki 数据库或原始语料。音乐知识只通过宿主 GitHub MCP 读取，接口见 [知识读取流程](references/github-knowledge.md)。宿主已有的文件、Git、终端和会话能力不另建框架。

修改后运行 README 中的测试与打包检查。测试应覆盖真实行为，不以编译成功替代音乐验收。只读审稿直接查看实际谱面、diff 和对应证据；无独立审稿时明确标注。

维护指南文件名沿用 AGENT.md；自动扫描宿主也可读取 [AGENTS.md](AGENTS.md)。
