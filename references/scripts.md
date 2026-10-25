> i-score 服务器分支不使用本页的本地编译/安装流程。服务器 Pi 的执行规范见 [服务器工具契约](server-tools.md)；本页保留通用上游工具参考和原有署名许可。

<!-- knowledge: operation.scripts -->
# 脚本用法与证据

三个入口支持 `--help`，正常结果 stdout 为单个 JSON；参数错误由 argparse 在 stderr 解释。成功退出 0，缺依赖、编译失败、输入无效或证据不可用退出 1，参数错误退出 2。音乐候选不直接导致失败。UTF-8 原谱只读。

用宿主解析出的 Python 和 Skill 绝对路径运行；`<report>` 来自编译 JSON 的 `report_path`，不要沿用旧报告。

## 编译

```text
python <skill>/scripts/compile_score.py --source melody.abc --output-dir build --require midi
python <skill>/scripts/compile_score.py --source piece.ly --output-dir build --require pdf --require midi
```

按 `.abc` / `.ly` 推断格式，其他文件用 `--format abc|lilypond`。可指定 `--lilypond PATH`、`--abc2midi PATH`、`--abc2abc PATH`。`--timeout 90` 是每个子进程的秒限，包括版本探测。

每次新建 `compile-*` 输出子目录，避免误用旧产物。`compile-report.json` 记录源码字节哈希、格式、引擎版本和路径、每条命令 stdout/stderr/退出码/超时、诊断、单元与产物名称/哈希/大小。失败也尽可能保存报告。报告与产物保持相对布局。

ABC 按 X: 顺序拆分，逐首执行 abc2abc 与 abc2midi，默认每首需要 MIDI；本脚本不提供 ABC PDF 或音频。LilyPond 按源码生成产物，默认至少一个非空产物，用户要求 PDF/MIDI 时用 `--require` 明确指定。

输入需自包含。编译在新目录运行，不复制本地 include、字体等用户依赖；内置 LilyPond include 由编译器处理。已有工程可整理为自包含候选，或使用其原有构建流程并单独报告证据，不能偷偷改写原文件删除依赖。

## 分析

```text
python <skill>/scripts/analyze_score.py --source melody.abc --compile-report <report> --meter 4/4 --movement 1 --first 1 --last 8 --kind overview
python <skill>/scripts/analyze_score.py --source melody.abc --compile-report <report> --meter 4/4 --kind notes --first 1 --last 8 --offset 0 --limit 160
```

- `--kind`：overview、notes、harmony、voice_leading。
- `--meter N/D` 必填。核对 MIDI 拍号；只支持所选文件固定拍号。变拍或无拍号拒绝小节定位，保留源码和产物供直接核对。
- `--pickup` 为弱起的四分音符数，可用 `1/2`；弱起是第 0 小节，查看它需 `--first 0`，数值从谱确认。
- `--first/--last` 是闭区间，一页至多 65 小节。coverage 表示查询窗口及事件数量，不证明每小节都已写全。
- notes 的 `--offset`、`--limit`（1..1000）控制分页，按 `next_offset` 继续。平行候选最多显示 30 条，另给总数。
- ABC `--movement` 按 X: 顺序。LilyPond 多个 MIDI 时用 `--artifact` 指定报告中的文件名，逐个分析；movement 仅为调用方标注，不能证明源码乐章身份。

校验当前源码及全部产物哈希，拒绝失败报告、过期源码和丢失/篡改产物。报告是可重现证据，不是防恶意伪造的签名。

ABC 原生导入与独立编译 MIDI 核对起音及时值，一致且无警告时用原生音名与分组；否则回退 MIDI 并披露限制。LilyPond 从 MIDI 取实音，不能恢复等音拼写。MIDI 轨道不保证等同于谱面独立声部。

duration_quarters 是最后音符结束位置，不含尾部休止保证；演奏性时值不总等于记谱时值。统计调性不证明局部功能，和弦快照不是和声归约，未发现平行不证明对位正确，总时长正确不证明逐小节正确。

## 修订

diff 核对实际变化后重新编译，分析使用新报告。主 Agent 与审稿者读取同一当前文件及匹配证据，不复述旧评语。技术结果、音乐判断与修改目标分别报告，无需额外状态机。
