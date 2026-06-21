# Function Calling Schema

fc 为所有 185 个 CLI 命令提供 OpenAI Function Calling 定义，AI 通过结构化参数调用，消灭语法错误。

## 使用场景

当 AI Agent 通过 OpenAI API 调用 fc 时，使用 function calling 确保：
- 参数顺序正确
- 参数类型正确
- required 参数不遗漏
- 无拼写错误

## Schema 格式

```json
{
  "type": "function",
  "function": {
    "name": "part_add",
    "description": "Create primitive (box, cylinder, sphere, cone, torus, wedge, helix, ellipsoid, spiral) Returns: name,type.",
    "parameters": {
      "type": "object",
      "properties": {
        "type": {
          "type": "string",
          "description": "Primitive type",
          "enum": ["box", "cylinder", "sphere", "cone", "torus", "wedge", "helix", "ellipsoid", "spiral"]
        },
        "name": {
          "type": "string",
          "description": "Unique element name (e.g., Box_001)"
        },
        "json_output": {
          "type": "boolean",
          "description": "Output in JSON format (recommended for agents)",
          "default": true
        }
      },
      "required": ["type", "name"]
    },
    "example": "fc part add box --name Box --param Length=100 --json"
  }
}
```

## 类型映射

| CLI 类型 | JSON Schema 类型 | 说明 |
|----------|-----------------|------|
| STR | string | 字符串 |
| INT, COUNT, STEPS | integer | 整数 |
| FLOAT, RADIUS, SIZE, LENGTH | number | 浮点数 |
| FLAG, BOOL | boolean | 布尔值 |
| `A\|B\|C` | enum | 枚举选择 |
| `x,y,z` | string | 逗号分隔坐标 |

## 完整 Schema

所有 185 个 function 定义见 [FUNCTION_SCHEMAS.json](../FUNCTION_SCHEMAS.json)。

## 自动生成

Schema 从 TOOL_SCHEMA.json 自动生成，保持同步：

```bash
python scripts/generate_function_schemas.py
```

## 按命令组统计

| 命令组 | 函数数 |
|--------|--------|
| assembly | 10 |
| body | 20 |
| cam | 7 |
| document | 6 |
| draft | 15 |
| execute | 2 |
| export | 14 |
| fem | 8 |
| import | 11 |
| material | 9 |
| mesh | 14 |
| part | 14 |
| session | 6 |
| sketch | 21 |
| spreadsheet | 11 |
| surface | 9 |
| techdraw | 8 |
| **合计** | **185** |
