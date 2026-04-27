# 汉字拼音小径 — 设计文档 vs 实现 差距分析

> 审查日期：2026-04-26  
> 对照文件：`doc/hanzi_pinyin_path_design.md`  
> 审查范围：`maogame/games/hanzi_pinyin_path/`、`tests/test_hanzi_pinyin_path_logic.py`

---

## ✅ 已正确实现

| 模块 | 详细说明 |
|---|---|
| **数据层** | `load_entries_from_markdown`、`CharacterEntry`、`filter_entries`、`grades_for_years`、`ALL_GRADE_LABELS` |
| **声调工具** | `apply_tone_mark`、`_split_pinyin`、`_pinyin_full_to_display`，声调位置规则（a/e 优先、ou→o、末位元音）均正确 |
| **MCQ 生成** | `build_mcq_question`（`hz2py` 和 `py2hz`），干扰项优先级桶（近声母、近韵母、同调） |
| **连线题逻辑** | `build_match_pairs` 在 `logic.py` 中已实现，返回 `list[MatchPair]` |
| **输入校验** | `judge_pinyin_answer`（strict/lenient 模式）、`normalize_pinyin_input`（lowercase、strip、`v` 保留） |
| **计分** | `score_hit`（基础 10 + 连击加成上限 +20）、`compute_round_result` |
| **模式一 — 汉字选拼音** | 完整 scene：提示卡、4 选项格、键盘（方向键 / 1-4 / Enter）+ 鼠标点击 |
| **模式二 — 拼音选汉字** | 完整 scene：与模式一相同，方向取反 |
| **设置流程** | 年级范围 → 模式 → 难度，键盘 + 鼠标，每步均支持 Esc 返回 |
| **HUD** | 题号、分数、连击、年级/模式/难度标签 |
| **答题反馈** | 颜色高亮（绿色正确 / 红色选错 + 显示正确答案），1 秒后自动切题 |
| **结果页** | 总分、答对/答错数、正确率、最高连击；"再来一局"+"返回菜单"（键盘 + 鼠标） |
| **游戏注册** | lazy `scene_factory`、正确 `age_band`、正确 `summary` |
| **单元测试** | 解析、过滤、MCQ 生成、连线对数、`judge_pinyin_answer`、`normalize_pinyin_input`、计分、`RoundStats` 均通过 |

---

## ⚠️ 部分实现 / 存在缺陷

| 功能 | 已有 | 缺失或不正确 |
|---|---|---|
| **难度 → 连线对数** | `build_match_pairs` 接受 `pair_count` 参数 | scene 中从未调用（模式三未实现），Easy=4/Medium=6/Hard=8 的默认值未落地 |
| **Hard 模式跨年级干扰项** | `_pick_distractors_pinyin` 使用过滤后的 `pool` | 设计要求 Hard 模式引入跨年级条目作为额外干扰，目前只在当前年级范围内选取 |
| **反馈动画** | 仅静态颜色变化 | 设计要求"正确绿色闪烁+轻微放大"、"错误红色抖动"，目前无任何动画 |
| **自动切题开关** | 始终在 1 秒后强制切题 | 设计为可选项（"可开启自动下一题"），目前不可关闭 |
| **结果页 `avg_answer_ms`** | `RoundResult` 中已计算 | 结果页渲染中**从未显示**该统计项 |
| **`game_id` 格式** | 注册为 `"hanzi-pinyin-path"`（连字符） | 设计规定 `"hanzi_pinyin_path"`（下划线），与包目录名不一致 |
| **鼠标事件处理（已修复）** | `handle_mouse` 方法存在，逻辑正确 | 原 `update()` 通过 `pygame.event.get()` 二次取队列，游戏主循环已耗尽队列导致鼠标点击无效；已通过将 `MOUSEBUTTONDOWN` 路由至 `handle_event` 修复 |
| **测试：固定种子可复现性** | 测试中使用了固定种子 | 无显式断言"固定种子时题目序列严格一致"的测试用例 |
| **测试：Hard 模式近音干扰比例** | 未测试 | 设计测试矩阵要求验证 Hard 模式近音干扰比例高于 Easy/Medium |

---

## ❌ 尚未实现

| 功能 | 设计要求 | 状态 |
|---|---|---|
| **模式三 — 连线配对** | 点击左卡再点右卡完成配对（4/6/8 对，按难度），按组结算 | 仅有 `logic.py` 中的 `build_match_pairs`；无 scene 状态、渲染、交互 |
| **模式四 — 拼音输入** | 键盘输入声母/韵母 + 鼠标点击声调按钮（一声～四声 + 轻声 + 清除），strict/lenient 开关 | 仅有 `logic.py` 中的 `judge_pinyin_answer`；无输入框、声调按钮 UI、scene 状态 |
| **倒计时** | HUD 显示"剩余时间"，时间压力随难度变化 | scene 和 logic 中均无计时器 |
| **速度奖励** | "剩余时间折算"加入分数组成 | `score_hit` 和 `_submit_answer` 均未实现 |
| **"仅练错题"入口** | 结果页提供"按错题生成复习回合"按钮 | 无错题列表记录，结果页无该按钮 |
| **Hard 混合年级加权采样** | 合并年级 pool 时高年级权重更高（Hard 模式） | `build_mcq_question` 和 `_start_round` 均为均匀采样 |
| **上/下册粒度选择** | 年级选择支持上册/下册细分（设计标注 TBD） | 年级选择器仅提供整学年选项，无学期粒度 |

---

## 汇总

| 类别 | 数量 |
|---|---|
| ✅ 已正确实现 | 14 项 |
| ⚠️ 部分实现 / 存在缺陷 | 9 项 |
| ❌ 尚未实现 | 7 项 |

**优先级建议：**  
1. **模式三（连线）** 和 **模式四（拼音输入）** 是设计核心差异化功能，优先级最高。  
2. **倒计时 + 速度奖励** 完成后游戏循环才具备完整张力。  
3. `game_id` 格式、结果页 `avg_answer_ms`、"仅练错题"按钮为小型补丁，可随时修复。
