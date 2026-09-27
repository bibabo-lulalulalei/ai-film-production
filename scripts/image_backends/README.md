# Image backend adapters

`produce_asset.py --submit` 在真实投产时加载这里的一个适配器，文件名由
profile 的 `asset_image.backend` 推导（小写、去点、空格变 `_`），例如 backend
`Qwen Image 2.1` → `qwen_image_21.py`。这样生图后端的差异（端点、鉴权、请求
格式、返回形态）全部隔离在适配器内，流水线脚本保持模型无关。

## 适配器接口（必须实现）

```python
def generate(*, prompt_text, reference_paths, target_path, asset_image, root):
    """Submit one image job.

    prompt_text     : 生产提示词正文（str）
    reference_paths : 真要送入请求的参考图路径列表（Style Key 等；不是文字提及）
    target_path     : member 落点（相对项目根），用于命名/日志，不在此自行改路径
    asset_image     : profile.asset_image 后端事实（steps_default、resolution_preset…）
    root            : 项目根（绝对路径）

    return          : 图片二进制 bytes（推荐，由 runner 落盘），或可直接写文件的 str
    """
```

## 约定

- 适配器负责读凭证（环境变量），缺凭证须明确报错，不静默失败；
- 不得在适配器内改动 BOM 或其他资产——状态由 produce_asset/mark_review 统一回写；
- 端点、模型名、步长、分辨率等只能取自 `asset_image` 与环境，不硬编码；
- 一个后端一个文件；新增后端不改 produce_asset.py。
