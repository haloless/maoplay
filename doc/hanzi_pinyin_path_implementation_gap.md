# 汉字拼音小径 — 设计文档 vs 实现 差距分析

> 最后审查日期：2026-04-30  
> 原始审查日期：2026-04-26  
> 对照文件：`doc/hanzi_pinyin_path_design.md`  
> 审查范围：`maogame/games/hanzi_pinyin_path/`、`tests/test_hanzi_pinyin_path_logic.py`

---

## ✅ 已正确实现

| 模块 | 详细说明 |
|---|---|
| **数据层** | `load_entries_from_markdown`、`CharacterEntry`、`filter_entries`、`grades_for_years`、`ALL_GRADE_LABELS` |
| **声调工具** | `apply_tone_mark`、`_split_pinyin`、`_pinyin_full_to_display`，声调位置规则（a/e 优先、ou→o、末位元音）均正确 |
| **MCQ 生成** | `build_mcq_question`（`hz2py` 和 `py2hz`），干扰项优先级桶（近声母、近韵母、同调） |
| **连线题逻辑 + Scene** | `build_match_pairs` 完整实现，返回 `list[MatchPair]`；scene 全功能：点击配对、难度对数（Easy=4/Medium=6/Hard=8）、错误配对红色闪现反馈（0.5秒）|
| **输入校验** | `judge_pinyin_answer`（strict/lenient 模式）、`normalize_pinyin_input`（lowercase、strip、`v` 保留） |
| **模式四 — 拼音输入** | 完整 scene：键盘输入声母/韵母、鼠标点击声调按钮（一二三四声+轻声+清除），strict/lenient 开关（非 easy 时为 strict） |
| **计分** | `score_hit`（基础 10 + 连击加成上限 +20）、`score_speed_bonus`（按剩余时间折算 0-10 分） |
| **倒计时 + 速度奖励** | `QUESTION_TIME_LIMITS` 按难度设置（Easy=20s/Medium=12s/Hard=8s），HUD 实时显示剩余时间，速度加分已集成计分 |
| **模式一 — 汉字选拼音** | 完整 scene：提示卡、4 选项格、键盘（方向键 / 1-4 / Enter）+ 鼠标点击 |
| **模式二 — 拼音选汉字** | 完整 scene：与模式一相同，方向取反 |
| **设置流程** | 年级范围 → 模式 → 难度，键盘 + 鼠标，每步均支持 Esc 返回 |
| **HUD** | 题号、分数、连击、倒计时、年级/模式/难度标签 |
| **答题反馈** | 颜色高亮（绿色正确 / 红色选错 + 显示正确答案），1 秒后自动切题 |
| **结果页** | 总分、答对/答错数、正确率、最高连击、**平均用时**；"再来一局"、**"练错题"**（当有 ≥4 错题时）、"返回菜单"（键盒 + 鼠标） |
| **错题重练** | scene 跟踪 `_wrong_entries`，结果页提供"练错题"按钮（≥4 错题时）；点击按钮限制题库为错题集并重新开局 |
| **Hard 跨年级干扰** | `build_mcq_question` 在 hard 模式下使用全年级 pool 作 distractor_pool，允许跨年级干扰项 |
| **游戏注册** | game_id 格式已修正为 `"hanzi_pinyin_path"`（下划线）、lazy `scene_factory`、正确 `age_band` 和 `summary` |
| **单元测试** | 解析、过滤、MCQ 生成、连线对数、`judge_pinyin_answer`、`normalize_pinyin_input`、计分、`RoundStats`、固定种子可复现性、hard 模式跨年级干扰均通过 |

---

## ⚠️ 部分实现 / 存在缺陷

| 功能 | 已有 | 缺失或不正确 |
|---|---|---|
| **反馈动画** | 仅静态颜色变化 + 短时显示（1 秒） | 设计要求"正确绿色闪烁+轻微放大"、"错误红色抖动"，目前无关键帧/几何变换动画 |
| **自动切题开关** | 始终在 1 秒后强制切题 | 设计标注为"可开启自动下一题"，暗示可配置；目前硬编码无法关闭 |
| **测试：Hard 模式近音干扰比例** | 已实现 Hard 跨年级干扰 | 设计测试矩阵要求对比 Easy/Medium/Hard 的近音比例分布；目前无详细分类统计测试 |

---

## ❌ 尚未实现

| 功能 | 设计要求 | 原因 / 备注 |
|---|---|---|
| **上/下册粒度选择** | 年级选择支持上册/下册细分（设计标注 TBD） | 设计中标注为 TBD（待议），数据源已支持上下册，UI 仍为整年级选项 |
| **Hard 加权年级采样** | Hard 模式时高年级权重更高 | 目前为均匀采样；可考虑在 `_pick_entries` 中加权（低优先级） |

---

## 汇总

| 类别 | 数量 |
|---|---|
| ✅ 已正确实现 | 20 项 |
| ⚠️ 部分实现 / 存在缺陷 | 3 项 |
| ❌ 尚未实现 | 2 项 |

**完成情况：** 核心功能已完成，设计文档中的主要机制均已落地。

**后续可选项：**
1. **反馈动画** — 可考虑添加关键帧动画（绿色闪烁 + 缩放、红色抖动），需额外的动画框架。
2. **自动切题开关** — 可在设置中添加可选项，让玩家选择手动/自动推进。  
3. **Hard 加权采样** — 可精化 Hard 模式，高年级条目权重更高（当前为均匀采样，影响不大）。
4. **上下册细分** — 数据层已支持，UI 改进后可支持更精细的年级筛选。

---

## 自 2026-04-26 以来的实现清单

自原始审查以来，已提交以下 8 个 commit，完成了绝大多数关键功能缺口：

| Commit | 功能 | 状态 |
|---|---|---|
| `be2c2b8` | 修复鼠标事件路由（MOUSEBUTTONDOWN → handle_event） | ✅ |
| `b7ec6d2` | game_id 格式标准化为 `hanzi_pinyin_path`（下划线） | ✅ |
| `89628cb` | Hard 模式跨年级干扰项 — 使用全年级 pool 作 distractor_pool | ✅ |
| `e1b2878` | 添加固定种子可复现性 + Hard 跨年级干扰测试 | ✅ |
| `d0b5493` | 倒计时 + 速度奖励计分 + QUESTION_TIME_LIMITS | ✅ |
| `93a032b` | **模式三（连线配对）** — 完整 scene + 难度对数 + 错对闪现反馈 | ✅ |
| `8b2b158` | **模式四（拼音输入）** — 键盘输入 + 声调按钮 UI + strict/lenient | ✅ |
| `cf58cdb` | 错题跟踪 + 结果页"练错题"按钮 + 错题重练模式 | ✅ |