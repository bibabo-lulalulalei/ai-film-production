# 生成模型层（models/）

本流水线模型无关。模型差异**不进脚本、不进 schema 硬编码**，全部隔离在
`models/<模型>/` 一个目录内。脚本与通用文档只和 profile 对话。

## 目录约定

```
models/
├── README.md             本文件：模型选择 + 适配清单
├── input-conditions.md   通用输入条件五分类（选型思路）
└── <model>/              同一模型的全部资源放同一目录
    ├── profile.json      机器读的能力档案（脚本加载；契约见 ../../../schemas/model-profile.schema.json）
    ├── <model>.md        人读的模型知识：调用契约 / 模式判别 / 音频口径 / 坑
    └── *.txt             官方提示词模板（逐字收录，不手工修改）
```

## 怎么选模型

模型**不**在 [1] 立项时锁定——此时 charter 写占位：

```
目标模型：待 [2]
```

在 [2] 风格定向：据小说简要调研同类型作品、归纳候选后，拿候选对照**全部**
已登记模型 profile 的 `style_evidence` 出能力矩阵，用户选定「风格×模型」
组合，再回写 charter 锁定：

```
目标模型：H3
```

- 脚本按此行加载 `models/<模型>/profile.json`；模型名大小写不敏感，须与目录名对应；
  脚本读到占位值会明确报错（防在锁定前误跑下游）。无此行的旧项目仍默认 H3。
- 全片默认一个模型；单镜换模型时在该镜 gen.json 的 `model` 注明
  （值须在 profile 的 `gen_model_values` 内）。
- 换模型＝改风格组合：按风格级 ECN 回 [2] 重算矩阵，不直接改 charter 一行。

## 已有模型

| 目录 | 模型 | 说明 |
|---|---|---|
| [`h3/`](h3/) | MiniMax H3 | 默认参考实现：4–15s、立体声、两个物理 checkpoint（FL2VA 图 0–2；Ref2VA ≤9 图 ≤3 音）；详见 [h3/h3.md](h3/h3.md) |

## 适配新模型清单

接入一个新生成模型时**不改任何脚本**，按下列步骤做：

1. **建目录** `models/<model>/`；同一模型的知识、模板、档案全部放进去。
2. **收模板**：取得该模型官方提示词写法（字段名、段序、标签、时间格式），
   逐字存为模板文件；没有官方模板时，据实测归纳并注明来源与日期。
3. **填 profile.json**：复制 [h3/profile.json](h3/profile.json) 改写——
   - 能力上限：`max_duration_s` / `max_ref_images` / `max_ref_audios` /
     `resolutions` / `gen_model_values`；
   - `conditions`：该模型支持的输入条件（通用五分类见 [input-conditions.md](input-conditions.md)），
     每个条件给 `template`（对应第 2 步收的模板文件）、`core_fields`
     （段名＋段序）与 `first_line`（结构化首行类型：none / first_frame /
     last_frame / first_last，逐字英文不进 profile）；
   - `tag_policy`：`role_tag`（role→标签类别）、`slot_order`（各 checkpoint
     的槽位类别顺序）、同资产多图编号规则；
   - `style_evidence`：该模型画风能力的证据库——只登记有证据的自由描述词
     （native/supported/experimental/unsupported 四档＋证据＋缓解），
     无证据默认 experimental；[2] 的跨模型矩阵以此为源，随真实探针只增不改；
   - **不设写法词表字段**：脚本不评判 prompt 措辞，只从正文提取封闭结构
     token（段首/标签/首行锚点）做确定性核对，其余核 gen.json 结构、枚举
     与参考槽；逐字写法以官方模板为权威，G07 由人对照模板审核。
4. **写知识文档**：调用/鉴权契约、模式判别规则（尤其首帧/尾帧链的映射）、
   逐字首行、音频口径、真实翻车坑。
5. **真实验证**：在一个真实项目上跑全四道闸，确认脚本行为符合该模型实际；
   不造 fixture。

如果该模型带来全新的结构化输入（例如新的必填槽位类型），
先扩充 [model-profile.schema.json](../../../schemas/model-profile.schema.json)
与脚本的通用分派逻辑，再写该模型的 profile——声明性规则留在 profile 里，
不要在脚本中出现模型名分支。正则只允许用于提取封闭结构 token（标签、
段首、首行锚点），不得用于评判正文措辞。
