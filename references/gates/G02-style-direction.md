---
gate_id: G02
after: "1"
authority: validation/lint_cards.py --gate SD
pass_authority: user
zero_cost: true
---

# G02 风格定向闸

审：`03-style/` 全套（comps / candidates / model-matrix / style-direction / style-checks）
｜写手：[../crew/style-director.md](../crew/style-director.md)

## 开工前置
novel 过 G01、Soul confirmed、charter 已批；charter 模型栏此时为占位「待 [2]」。

## 机器可查（权威实现：SD 闸，零费用）

```bash
python validation/lint_cards.py <root> --gate SD    # 等价 --gate G02
```

- `style-direction.md` 已冻结、无 UNSET
- `comps.md` 存在：检索词、命中作品、每部视觉特征齐（不是只报片名）
- `candidates.md` 候选数 ≥3、彼此真正不同、候选间不雷同
- `model-matrix.json` 符合 [../../schemas/style-matrix.schema.json](../../schemas/style-matrix.schema.json)：
  每条「候选×模型」评级挂证据；证据库无命中的条目带当场调研（query/日期/URL）；
  矩阵覆盖 `references/models/` 下**全部**模型；weight 1 的候选带探针或知情说明
- `style-checks.json` 存在（禁词/必引样板图/色锚/关键场景规则，含矩阵缓解负向词）
- style-direction.md 四件齐：画种方言/留白哲学/色系家族/异象语法，并快照模型与证据 id
- **charter 模型栏已从占位回写为选定模型**（注明由 [2] 矩阵产生）

## 人审（重点，防「错误画风」）
1. **调研真实性**：抽 comps 里 2–3 部作品，核对其视觉特征描述是否属实，
   而非凭印象编造。
2. **候选质量**：候选是否**具体、可视化、可执行**——给得出媒材/线条/色系/
   留白/光比/异象语法，而非从固定类型表/六大类对号入座的空标签。
3. **矩阵证据可信度**：评级与证据强度是否匹配（官方 skill＞官方案例＞实测＞社区）；
   无命中的候选是否真做了定向调研，而非直接写 supported。
4. 每个候选如何承载魂。
- 换一部片子仍原样成立的候选＝未衬本题，作废。

## 必过
- 用户在候选规格＋矩阵上**显式选定**一个「风格×模型」组合；不替用户拍板。
- charter 已回写锁定模型；探针（如有）单独归档、经事先确认。

## 缺陷处置
| 缺陷 | 改法 |
|---|---|
| 无 comps/调研空泛 | 回第 1 拍，多路检索并逐部记录 |
| 候选从类型表对号入座 | 以具体视觉规格重做归纳 |
| 候选雷同 | 补真正不同候选 |
| 候选描述空泛不可执行 | 补媒材/线条/色值/留白/光比等具体规格后重写 |
| 矩阵评级无证据/漏模型 | 补定向调研，覆盖全部已登记模型 |
| charter 未回写模型 | 用户选定后立即回写，[3] 才准开工 |
