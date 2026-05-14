# Endpoint 脚本说明

每个业务能力对应一个 endpoint 脚本。脚本负责加载对应规则配置并调用公共 runner。

推荐入口形态：

```python
from pathlib import Path

from common.runner import main


RULE_FILE = Path(__file__).resolve().parents[2] / "rules" / "read-example.json"


if __name__ == "__main__":
    main(RULE_FILE)
```

脚本应支持：

- `--input '<json>'`
- `--input-file path/to/input.json`
- `--dry-run`

校验失败时必须在 MCP 调用前返回。
