# execute_code 行号污染陷阱

## 症状

使用 `execute_code` 的 `read_file` + `write_file` 组合后，文件出现行号前缀污染：

```
文件实际内容：      1|     1|---
                    2|     2|title: ...
```

第一层 `1|` 是 read_file 返回值自带的，第二层 `1|` 是上次污染的残留。wiki_op.py 的 `check_line_number_corruption()` 检测第一行是否以 `^\s*\d+\|` 开头，命中则拒绝。

## 根因

`execute_code` 内的 `hermes_tools.read_file()` 返回的 `content` 字段**包含行号前缀**（与 chat 中 `read_file` 工具的输出格式一致）。把这个 content 直接传给 `hermes_tools.write_file()` 会把行号前缀写入文件正文。

## 安全模式

### ❌ 危险
```python
from hermes_tools import read_file, write_file
result = read_file(path)
content = result["content"]  # 带行号前缀
write_file(path, content)    # 行号前缀写入文件！
```

### ✅ 安全：终端 curl / 不用 execute_code
```bash
# 直接读原始文件内容，不经过工具层
cat /path/to/file.md
```

### ✅ 安全：execute_code 只分析，不写回
```python
from hermes_tools import read_file, terminal
result = read_file(path)
# 只做分析，不用 write_file 写回
for line in result["content"].split("\n"):
    if "keyword" in line: ...
```

### ✅ 安全：用 terminal + sed 或 wiki_op.py 写回
```bash
# wiki 文件走 wiki_op.py
python3 ~/wiki/.hermes/scripts/wiki_op.py update --page entities/xxx --patch-file /tmp/p.json

# 非 wiki 文件用 patch 工具或 sed
```

## 如果已经污染了

```python
# execute_code 内修复
import re
content = re.sub(r'^\s*\d+\|', '', content, flags=re.MULTILINE)
# 重复直到干净
while re.match(r'^\s*\d+\|', content):
    content = re.sub(r'^\s*\d+\|', '', content, flags=re.MULTILINE)
content = content.lstrip('\n').lstrip()
write_file(path, content)
```
