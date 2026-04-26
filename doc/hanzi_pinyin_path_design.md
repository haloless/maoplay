# Hanzi Pinyin Path Design

## Concept Summary

- Game ID: hanzi_pinyin_path
- Working title: 汉字拼音小径
- Target age: 6-12
- Primary learning goal: 建立汉字与拼音（含声调）的双向映射能力，并支持按年级循序练习。
- Session length: 5-10 minutes per run.

这是一个分关卡的汉字拼音配对益智游戏。玩家先选择年级范围（一年级到六年级），再选择模式。低难度优先鼠标点击，高难度增加键盘拼音输入，但声调选择始终提供鼠标快捷按钮（1-4声 + 轻声）来降低输入门槛。

## Why It Fits This Repo

- 题目生成、判定、评分都可放在 `logic.py`，可被 `unittest` 单测覆盖。
- 动画、交互、布局在 `scene.py`，符合现有 pygame 场景分层。
- 可作为独立包放在 `maogame/games/hanzi_pinyin_path/`，并使用 lazy scene_factory 注册。
- 能复用当前提供的分年级字表数据，并支持后续扩展更高年级词汇。

## Candidate Concepts (2-4)

### Concept A: 配对连线（Mouse-first）

- 玩法：左侧汉字卡片，右侧拼音卡片，鼠标拖线或点击两端完成配对。
- 优点：直观、几乎纯鼠标操作，适合低年级。
- 风险：高难阶段挑战性不足。

### Concept B: 双向选择题（Quiz Sprint）

- 玩法：按模式出题（汉字选拼音 / 拼音选汉字），四选一，限时连答。
- 优点：节奏快，易于评分和重复游玩。
- 风险：长期玩可能模式单一。

### Concept C: 拼音输入工坊（Input Studio）

- 玩法：看到汉字后输入完整拼音；字母可键盘输入，声调可鼠标点击按钮补齐。
- 优点：高难度学习价值高，覆盖“认读”到“书写式回忆”。
- 风险：纯输入会增加挫败感，需要良好纠错体验。

### Selected Direction: A + B + C 的渐进融合

采用同一游戏内多模式，难度从鼠标优先逐步过渡到键盘输入：

1. 入门：配对连线（A）
2. 进阶：双向选择题（B）
3. 挑战：拼音输入工坊（C）

这样既满足低龄可玩性，也满足高年级训练深度。

## Final Gameplay Requirements

### 1) Grade Range Selection

玩家在开始前先选题库范围：

- 单学年：一年级、二年级、三年级、四年级、五年级、六年级
- 学段细分（可选增强）：一年级上/下、二年级上/下 ... 六年级上/下
- 混合范围：例如一年级到三年级

规则：

- 题目只从所选范围抽取。
- 混合范围默认均匀抽样，可在高难度启用“高年级权重更高”。

### 2) Game Modes

#### Mode 1: 汉字选拼音（Mouse-first）

- 展示一个汉字，给 4 个拼音选项。
- 主要鼠标点击作答。
- 可开启自动下一题（1.2 秒后切题）。

#### Mode 2: 拼音选汉字（Mouse-first）

- 展示一个拼音（含声调），给 4 个汉字选项。
- 鼠标点击作答。
- 错题可在结果页回看“正确字 + 拼音”。

#### Mode 3: 连线配对（Mouse-first）

- 一屏 4-8 对待配对项（按难度变化）。
- 交互：
  - 方案A：点击左卡再点右卡
  - 方案B：拖拽连线
- 全部配对完成后结算正确率和时间奖励。

#### Mode 4: 拼音输入（High difficulty）

- 展示汉字，玩家输入拼音字母。
- 声调输入提供鼠标按钮：`1` `2` `3` `4` `轻声`。
- 支持两段式输入：
  1. 键盘输入韵母/声母串（如 `xiao`）
  2. 鼠标点声调按钮（如 3 声）
- 同时支持快捷键：数字 `1-4` 选择声调（保留鼠标按钮作为主入口）。

### 3) Difficulty Design

统一难度：Easy / Medium / Hard

- Easy
  - 题量少，干扰项差异明显
  - 连线对数 4
  - 输入模式可关闭声调严格判定（可选）
- Medium
  - 题量中等，干扰项来自同年级近似拼音
  - 连线对数 6
  - 输入模式要求声调正确
- Hard
  - 题量大，混入跨年级近形字或近音项
  - 连线对数 8
  - 输入模式要求完整拼音 + 声调，限时更紧

### 4) Scoring, Progression, Failure

- 分数组成：
  - 基础分：答对 +10
  - 连击奖励：连续答对每层 +2（上限 +20）
  - 速度奖励：剩余时间折算
- 统计项：
  - correct_count
  - wrong_count
  - accuracy_percent
  - best_streak
  - avg_answer_ms
- 结束条件：
  - 到达题目数上限或倒计时结束
  - 连线模式可按关卡结算
- 失败处理：
  - 不使用强惩罚；默认错题仅扣分/重置连击
  - 提供“再试一次”与“仅练错题”入口

## Data And Content Rules (logic.py)

### Source Data

- 输入文件：`doc/chinese_character_elementary_school.md`
- 内容结构：按年级段分组，每行若干 `汉字(拼音)` 条目。

### Parsing Requirements

在 `logic.py` 提供解析器，将文本预处理为结构化题库：

- `CharacterEntry`
  - `hanzi: str`
  - `pinyin_raw: str` (例如 `xiao`)
  - `tone: int` (1-4, 0 表示轻声)
  - `grade_label: str` (例如 `三年级下册`)
- `Question`（按模式定义字段）

解析规则：

- 用正则提取 `字(拼音)`。
- 若拼音无声调符号，允许通过词典映射或简化规则补全为 `tone=0`（TBD）。
- 对同字多音情况，先按“在数据中出现的读音”作为当前答案。

### Required Logic APIs

- `load_entries_from_markdown(path: str) -> list[CharacterEntry]`
- `filter_entries(entries, grade_range) -> list[CharacterEntry]`
- `build_mcq_question(rng, entries, direction, difficulty) -> Question`
- `build_match_pairs(rng, entries, pair_count, difficulty) -> list[tuple[str, str]]`
- `normalize_pinyin_input(raw_text: str) -> str`
- `judge_pinyin_answer(target, typed_base, typed_tone, strict_tone: bool) -> bool`
- `score_hit(streak: int, base: int = 10) -> int`
- `compute_round_result(stats) -> RoundResult`

### Distractor Generation Rules

干扰项优先级（从高到低）：

1. 同年级内近音（同声母或同韵母）
2. 同年级内同调不同音
3. 跨年级常见字（仅 Hard）

保证：

- 选项不重复
- 正确答案随机位置
- 难度越高，近似干扰比例越高

## Scene/UI Requirements (scene.py)

### Scene Flow

1. 主菜单进入游戏
2. 选择年级范围
3. 选择模式
4. 选择难度
5. 进行回合
6. 结果页（可重开、切模式、看错题）

### Input UX (Mouse Priority)

- 所有模式都可纯鼠标完成基础流程。
- 输入模式中：
  - 字母允许键盘输入
  - 声调始终可鼠标点击
  - 声调按钮固定在输入框下方，尺寸足够大

推荐声调按钮布局：

- `[一声] [二声] [三声] [四声] [轻声] [清除]`
- 鼠标悬停高亮，点击后即时回显。

### HUD And Feedback

- 顶部：分数、连击、剩余时间
- 中央：当前题干（汉字或拼音）
- 底部：模式提示 + 当前年级范围
- 反馈：
  - 正确：绿色闪烁 + 轻微放大
  - 错误：红色抖动 + 显示正确答案 1 秒

### Accessibility

- 大字号（小学低年级可读）
- 颜色不作为唯一信息通道（配图标/文字）
- 动画时长短，不遮挡下一步操作

## Asset Needs

MVP 可零外部素材：

- 使用 pygame 文本和基础图形绘制按钮、连线、卡片
- 可选后续增强：轻量音效（答对/答错/过关）

## Package And Registration Plan

新增目录：`maogame/games/hanzi_pinyin_path/`

- `__init__.py`
  - 暴露 `GAME` 注册对象
  - `scene_factory` 内部懒加载 `scene.py`
- `logic.py`
  - 数据解析、题目生成、判定、计分
- `scene.py`
  - pygame 输入、渲染、动画、界面流程

注册信息建议：

- `game_id`: `hanzi_pinyin_path`
- `title`: `汉字拼音小径`
- `summary`: `按年级练习汉字与拼音对应，支持连线、选择与输入`
- `age_band`: `6-12`

## Implementation Milestones

1. 数据层与规则层
- 完成 markdown 解析与题库结构化
- 完成多模式题目生成与评分函数
- 建立逻辑单测

2. 最小可玩版本
- 完成年级范围选择 + 模式选择
- 实现 Mode 1/2（四选一）
- 结果页统计可见

3. 鼠标强化模式
- 实现 Mode 3 连线配对
- 打磨连线交互（吸附、撤销、错误反馈）

4. 高难输入模式
- 实现 Mode 4 拼音输入
- 增加鼠标声调按钮 + 键盘快捷键
- 增加严格/非严格声调判定开关

5. 集成与回归
- 注册到 launcher
- 运行全量 `unittest`
- 运行 headless smoke test

## Test Matrix (unittest)

建议新建：`tests/test_hanzi_pinyin_path_logic.py`

1. 数据解析
- 能正确识别 section 年级标签
- 能提取 `汉字(拼音)` 对
- 解析结果不为空，且覆盖 1-6 年级

2. 题目生成
- 四选一总能包含唯一正确答案
- 干扰项不重复
- 连线题 pair_count 与难度一致

3. 判题逻辑
- `judge_pinyin_answer` 在 strict/non-strict 下行为正确
- 轻声（tone=0）判定正确
- 输入标准化可处理空格与大小写

4. 计分与统计
- 连击加分上限生效
- 错题会重置连击
- accuracy 计算在分母为 0 时返回 0

5. 难度与范围
- grade_range 过滤正确
- Hard 模式能产生更高比例近音干扰（可通过可注入策略测试）

6. 可重复性
- 固定随机种子时，题目序列可复现

## Acceptance Criteria

- 玩家可在开始时选择一年级到六年级范围。
- 至少提供三种模式（推荐四种）并可在 UI 中切换。
- 默认流程可主要依靠鼠标完成。
- 高难输入模式支持键盘拼音 + 鼠标声调选择。
- 逻辑层拥有完整 `unittest` 覆盖核心规则。
- 游戏可从 launcher 正常进入与退出。

## Open Decisions (TBD)

- 是否将“上/下册”作为默认可选粒度，还是放入高级选项。
- 多音字是否在同一题允许多答案，或按教材读音唯一化。
- 输入模式是否接受数字声调格式（如 `ma3`）作为等价输入。
- 是否在结果页提供“按错题自动生成复习回合”。
