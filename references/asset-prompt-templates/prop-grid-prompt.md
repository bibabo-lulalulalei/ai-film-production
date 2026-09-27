根据以下设计要求生成{{layout_phrase}}：器物「{{name}}」（{{asset_id}}）。

【核心道具资产与质感统一控制】（器物在此彻底描述一次，全部视图逐字一致；各部件在此命名锁定，下方逐视图不重述、不重新形容）
- 器物身份：{{identity_line}}
- 视觉风格：{{visual_style}}
- 尺度：
{{scale_block}}
- 色彩锚（唯一色板）：
{{color_anchors}}
- 材质与表面处理：
{{materials}}
- 部件结构：
{{fixed_structure}}
- 装饰纹样：
{{decoration_block}}
- 成色与包浆：
{{age_block}}
- 持用分量感：{{weight_impression}}

【画面构图与背景】
{{layout_instruction}}

【逐视图内容】（铁律：同一器物，每格**只写本格差异**——观看角度＋该角度须见的已命名部件；共享部件只引用其名、不重述外观）
{{view_blocks}}

【画面卫生】
- 画面干净利落、专业规范；无文字、无水印、无 LOGO、无品牌标识。
- 负向排除：
{{negative}}
- 风格禁词（出现即废）：{{forbidden}}

<!-- === 分隔线：以下为占位取值表，渲染时不进成品 ===
{{name}}               <- identity.name
{{asset_id}}           <- asset_id
{{layout_phrase}}      <- grid.cells: 单条 single→一张完整单图；四条→一组2×2四宫格
{{identity_line}}      <- identity: category/period/use/used_by
{{visual_style}}       <- style-spec.json 槽位按道具拼装（脚本提取）
{{scale_block}}        <- dimensions.size/scale_reference/part_ratios
{{color_anchors}}      <- materials[] part+color_hex
{{materials}}          <- materials[] part: material/finish/texture
{{fixed_structure}}    <- parts[] part(shape/count/position/connection)
{{decoration_block}}   <- decoration: motifs/layout/technique/symmetry
{{age_block}}          <- age.condition/patina/wear_locations
{{weight_impression}} <- weight_impression
{{layout_instruction}} <- single: 器物居中单图＋presentation 背景/布光/尺度参照；
                          grid: Four-grid split screen layout 受控拼版句＋背景/布光
{{view_blocks}}        <- grid.cells[] 编号逐行，仅差异: 格位中文名＋观看角度＋须见已命名部件（不重述共享外观）
{{negative}}           <- acceptance.negative 逐行
{{forbidden}}          <- style-checks.json forbidden_terms
====================================================== -->
