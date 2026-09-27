# 资产生产提示词 · {{name}}（{{asset_id}}）· Sheet {{sheet_id}}

## ① 任务
根据以下设计要求，生成角色「{{name}}」{{state_phrase}}的一张 1×4 横向定妆图；4 个视图全部为同一人，一次生成。
{{first_article_line}}

## ② 统一控制（人物在此彻底描述一次，四格共同遵守；五官、发式、服饰在此命名锁定，下方逐视图不重述、不重新形容）
- 身份：{{identity_line}}
- 视觉风格：
{{visual_style}}
- 色彩锚（四格逐字一致）：
{{color_anchors}}
- 材质（四格逐字一致）：
{{materials}}
- 固定结构：
{{fixed_structure}}
- 面部形貌（四格同一张脸，逐字一致）：
{{face_block}}
- 身材轮廓（四格同一体型）：
{{shape_block}}
- 手足：
{{hands_feet_block}}
- 发际与发质：
{{hair_block}}
- 服装细节：
{{costume_detail_block}}
{{variant_note}}

## ③ 排版构图（严格遵守）
- 一张 1×4 横向均分条，从左到右固定：A 正脸头肩特写 → B 全身正面 → C 全身侧面 → D 全身背面。
- 四格等高、等宽；干净利落的分隔线；无重叠、无偏移；素净背景；同一人，风格、身份、比例、色彩完全一致。
- B/C/D 三个全身格的头顶与足底对齐。
{{dependency_line}}

## ④ 逐视图（铁律：同一人，每格**只写本格差异**——视角/取景；身份细节只引用 ② 已锁定的命名，不重述外观）
- **A 正脸头肩特写**：正面、平视、均匀布光；中性、放松、非戏剧化表情（眉不皱、无眉间纹）。
- **B 全身正面**：直立、正面视角。
- **C 全身侧面**：标准 90° 侧面视角。
- **D 全身背面**：完全背对视角。
- 各格只引用 ② 已锁定的五官、发式、饰物、衣色，不得变色、变形、增减或重新形容。

## ⑤ 画面卫生
- 四格均中性表情；无笑、哭等戏剧化情绪；无多余首饰。
- 无文字、无水印、无 LOGO、无品牌标识。
- 全局负向（画风规格＋本卡负向，统一排除）：
{{global_negative}}
- 风格禁词（出现即废）：{{forbidden}}

<!-- === 分隔线：以下为占位取值表，渲染时不进成品 ===
{{name}}            <- identity.name
{{asset_id}}        <- asset_id
{{sheet_id}}        <- sheets[].sheet_id（main 或变体）
{{state_phrase}}    <- main: 默认定妆；变体: sheets[].state
{{first_article_line}} <- main: 角色首件/身份根，小批量4选1、用户批准；变体: 垫已批main，未批拒绝投产
{{visual_style}}    <- style-spec.json 槽位按人物拼装（脚本提取）
{{identity_line}}   <- identity: name/age/sex/station/period_region/health
{{color_anchors}}   <- 机械收集: hair.color_hex / skin.color_hex(+tone_note) /
                       costume[] garment+color_hex / ornaments[] item+color_hex
{{materials}}       <- costume[] garment+material
{{fixed_structure}} <- hair.style / ornaments[](item,worn_position,description,prop_ref?) /
                       head_face eyes,brows / distinguishing_marks[](mark,location) /
                       proportions head_body_ratio,shoulder_head_widths / stature.posture
{{face_block}}      <- head_face: face_shape/forehead/nose/mouth/cheeks/chin/ears +
                       proportions.face_ratio three_courts/five_eyes
{{shape_block}}     <- stature: build/shoulders/waist_hips/visual_weight
{{hands_feet_block}}<- hands_feet: hands/feet
{{hair_block}}      <- hair: hairline/texture
{{costume_detail_block}} <- costume[] cut/pattern/fastening/condition
{{global_negative}} <- style-spec negative + medium.not + line.forbidden + 卡 negative（去重合并）
{{variant_note}}    <- 非 main: sheets[].note；main 时为空
{{dependency_line}} <- 非 main: 投产依赖 main 的 target_path（BOM depends_on）；main 时为空
{{negative}}        <- 已并入 {{global_negative}}（acceptance.negative 统一在全局负向）
{{forbidden}}       <- style-checks.json forbidden_terms
====================================================== -->
