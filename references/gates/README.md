# 闸门 Gates

每环产出落盘后过对应闸；**FAIL 禁止 hop**。闸命名统一为 G01–G07；各文件带
精简 YAML 元数据头（gate_id / after / authority / pass_authority / zero_cost），
检查项全部在正文。

## 两类检查
- **机器项（脚本）**：ID/路径/已审、字段齐全、槽位契约、依赖无环、魂与风格机器项。
- **人审项**：可感性、气质、潜台词、图片内容/视角是否匹配、声音/尾帧观感。

G01/G03 的「可逐项核对」清单由人工执行、不设脚本——检查对象是散文与对白，
措辞启发式会产生误杀；G01/G03 的通过权在用户。

> 脚本**查不了图片内容与味道**，逐张开图人审不可因「ID ready」而省略。

## 闸表
| 闸 | 卡哪步 | 写手 | 权威 |
|---|---|---|---|
| [G01-novel.md](G01-novel.md) | [0] 小说 | novelist | 人工 |
| [G02-style-direction.md](G02-style-direction.md) | [2] 风格定向 | style-director | `lint_cards.py --gate SD` |
| [G03-screenplay.md](G03-screenplay.md) | [3] 剧本 | screenwriter | 人工 |
| [G04-shot-selfcheck.md](G04-shot-selfcheck.md) | [6]→[7] 镜头自检 | storyboard / cinematographer | `--gate S` |
| [G05-design-freeze.md](G05-design-freeze.md) | [7]→[8] 设计冻结 | asset-designer | `--gate A` |
| [G06-readiness.md](G06-readiness.md) | [11] 资产齐套 | producer | `coverage.py`＋人审 |
| [G07-prompt-freeze.md](G07-prompt-freeze.md) | [13]→[14] 提示词冻结 | prompt-writer | `--gate B` |

别名：`SD/G02`、`S/G04`、`A/G05`、`B/G07`、`lock` 均被 `--gate` 接受。

## 处置权
- 文稿 FAIL 打回写手；图片/音频/尾帧只列疑点，**通过权在用户**。
- FAIL 先定位「采样/回弹/设计/风格」再决定回哪，不条件反射重跑。
