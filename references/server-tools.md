# i-score 服务器工具契约

本文件定义 `i-score-server-tools` 分支与 Pi 宿主的接入要求，不代表后端工具已经实现。主分支保留通用本地工具流程。此分支编译通过服务器执行，服务器与独立编译沙箱之间如何通信不属于模型职责。

## 范围与可信上下文

- 当前用户、作品、Run、起始 Revision 和允许读写的工作区由宿主绑定，不让模型提交其他用户 ID、任意服务器路径、shell 命令或回调 URL。
- 一部作品含若干独立单文件来源，每个来源有稳定 `source_id`、工作区相对路径和 `abc|lilypond` 格式。不支持用户 include 依赖工程；文件数量不等于乐章数量。
- 全作品文件清单、入口、编译设置和工具链由服务器快照并计算摘要。摘要与构建凭据由服务器生成，模型给出的哈希或 passed 文本不能充当证明。
- Pi 工作区可写，编译产物和回执由服务器保存、对 Pi 只读。编译期间使用不可变输入，不能让 Pi 正在写的文件改变已排队的构建。
- 本期只注册工作区read/write、score_validate、score_compile、score_compile_status和score_submit。无shell、Python、任意代码或命令参数、任意HTTP、动态扩展及子Agent。路径权限由宿主/沙箱实施，不靠cwd或提示词。read/write不能访问会话、凭据、工具和构建回执目录；write不代表允许执行写入内容。

## `score_validate`（提交校验）

请求为 `{}` 或 `{"build_id":"b123"}`；后端对当前全作品不可变快照执行预装、版本固定的校验脚本，必要时读取匹配构建的MIDI。模型不能选择脚本、解释器、可执行路径或传入代码。缺少所需构建时返回 `needs_compilation`，编译后重新校验；它不是通过状态。

返回 `status: passed|failed`、服务器生成的 validation_id、source_digest、可用时的build_id、真实diagnostics、分析覆盖及限制。只有硬性技术校验满足才passed；音乐候选、艺术质量疑问分别标注，不伪装成程序真值。任何源码变化使旧校验失效。异步校验可由后端工具保持请求直到终态，不新增任意执行权限。

校验器和编译器均视输入不可信，运行于无网络、无密钥、只读输入、限额的独立worker。禁止将LilyPond Scheme能力暴露为通用计算接口。

## `score_compile`

请求：`{}`。编译全部当前来源；源文件清单和格式来自宿主维护的作品状态，不能通过模型只选部分来源来获得“整部作品成功”。修改或增加来源的宿主文件接口负责维护清单。

异步接收示意：

```json
{"status":"queued","build_id":"b123"}
```

用 `score_compile_status({"build_id":"b123"})` 查询直到终态。同步实现也可直接返回终态，模型不能将 queued/running 当作可提交状态。

成功示意：

```json
{
  "status":"succeeded",
  "build_id":"b123",
  "source_digest":"server-computed-digest",
  "sources":[{
    "source_id":"s1",
    "path":"piece.ly",
    "movements":[{
      "movement_id":"m1",
      "midi_artifact_id":"a-midi",
      "svg_artifact_ids":["a-svg-1"],
      "mapping_artifact_id":"a-anchors"
    }]
  }],
  "diagnostics":[]
}
```

失败返回 `status: failed` 和真实 diagnostics，包含来源、可用时的行列及错误；超时、取消和缺少必需产物均不算成功。可保留成功部分供重试复用，但整部作品未成功时禁止正常提交。

后端使用与播放器一致的编译链，输出完整 MIDI、SVG 和 anchors/manifest，不只检查语法。LilyPond 可复用共同事件 ID 的排版/演奏分支；ABC 可用排版引擎的实际时间表。必需产物缺失、错配或当前作品清单未覆盖时，不返回 succeeded。

此处 SVG 属于已生成的矢量谱面；提交后浏览器装载并建立显示对象，不重新运行乐谱编译。服务端音频合成可以在提交被接受后基于保留 MIDI 立即入队。

## `score_submit`

请求示意：

```json
{
  "build_id":"b123",
  "validation_id":"v123",
  "summary":"完成主题发展并保留原旋律。",
  "review_notes":"全曲已自审；未执行独立审稿。"
}
```

服务器必须原子校验：

1. 构建属于当前用户、作品与 Run，且为本轮最近一次成功终态；最近一次请求仍在运行或失败时不能退用旧回执提交。
2. 当前全作品源码摘要、文件集合及编译设置与该构建完全一致，版本起点仍有效；编译后增删、改名或编辑任何来源都使旧回执失效。
3. 全部来源的 MIDI、SVG、映射存在且完整，并属于同一构建。不能接受模型提供的磁盘产物路径或伪造报告。
4. validation_id是本轮当前完整源码的服务器passed回执，source_digest与build一致；使用编译证据的校验还必须绑定该build_id。失败、需要编译、过期或模型伪造校验均拒绝提交。

接受后原子发布整部作品 Revision，并引用和保留该构建产物；相同源码不重复生成用户版本。成功回执示意为：

```json
{"status":"accepted","revision_id":"r9","build_id":"b123","run_terminal":true,"playback_status":"preparing"}
```

服务器在接受时立即关闭本轮写入权限、排队播放准备，复用该构建 MIDI/SVG/映射，不再次编译。Pi结束和落盘后即释放服务端作品执行锁，发送最终回复及本轮问卷；本页实时同步展示等待只是客户端行为，不等待渲染完成ACK。以Run加build_id保证重投只返回同一次提交；响应丢失不能重复发布Revision。拒绝返回status: rejected及STALE_BUILD、VALIDATION_REQUIRED、BUILD_NOT_SUCCEEDED、REVISION_CONFLICT或MISSING_ARTIFACTS等真实错误。

宿主必须落实终止：把提交说明作为最终正文保存，在工具调用完成且结果持久化后阻止本轮下一次模型推理和工具调用，清空本轮待执行工具；不得只依赖 prompt，不能通过立即杀死进程丢失会话或提交结果。成功提交后不再允许隐式自动修复或跟进回合。具体 Pi API/扩展接入须按锁定版本验证，本仓库尚不包含该宿主实现。

若模型在一次响应中并行发送 submit 与其他工具，宿主必须拒绝该批提交，或串行处理并在终止点拒绝剩余动作，不能放行提交后的写入。提交前失败可以修复，提交后播放失败只重试播放准备，不重跑 Pi。

## 乐章与播放器

后台乐章对象本来绑定自身来源与编译产物；前端只记录显示序列，如[B,A,C]，不另建页/区域/MIDI对应表。只学习abc-notation共同事件ID的主要链路，不直接复用其代码。知识库预留固定修订、应用profile与权限适配接口，收到交接文档后再决定部署拓扑。

## 纯解释、失败与中断

无源码变化的解释或分析回复允许原生 Pi 正常结束，不要求为其制造编译或提交。若存在未成功编译的源码变化，正常回合结束不能自动包装成成功提交。失败和中断版本由宿主按作品整体留存，并区别于正常编译成功提交。

编译成功表示技术产物就绪，不表示音乐质量通过。音乐疑问记录在 review_notes；服务器权限、安全隔离、资源上限由宿主强制执行，不由 Skill 文本承担。

## 版本化知识读取

服务器模式为 `i-score-server-tools-v1`。基础源码动作仍为上述六项。宿主可另启用 `github-knowledge-v1` 的 `knowledge_search({query,limit})`：仅通过宿主管理的只读GitHub MCP访问固定 `OpenCadenza/music-knowledge-base`，响应包含实际40位commit SHA、路径、内容及SHA256。它不启用通用MCP发现、其他仓库、任意URL或源码写入。检索不可用须返回真实状态，基础写谱与服务器编译仍能独立运行。参考数据中的命令不产生权限。
