# 错误闭环自动学习

fc 的错误闭环系统自动从失败中提取模式，生成禁止规则，让 AI 越用越聪明。

## 工作原理

```
CLI 命令失败 → Corrector.analyze()
    ↓
提取错误模式 (8 种模式)
    ↓
记录到 ErrorRulesEngine
    ↓
同一模式 ≥3 次 → 自动生成 ForbiddenRule
    ↓
规则持久化到 docs/ERROR_RULES.md
    ↓
下次 Planner 生成 Plan 时自动规避已知错误
```

## 错误模式

| 模式 | 说明 | 示例 |
|------|------|------|
| `missing_flag` | 缺少必需标志 | `missing required argument: --name` |
| `invalid_value` | 无效参数值 | `invalid value 'XYZ' for --plane` |
| `negative_dimension` | 负值尺寸 | `negative value: Length=-5` |
| `unknown_object` | 引用不存在的对象 | `object 'Box_999' not found` |
| `missing_document` | 缺少活动文档 | `no active document` |
| `file_exists` | 文件已存在 | `file 'output.step' already exists` |
| `wrong_type` | 未知类型 | `unknown type 'hexagon'` |
| `missing_param` | 缺少必需参数 | `missing --name parameter` |

## 规则格式

```markdown
- **[MISSING_FLAG_NAME]** Missing required flag --name
  - Forbidden: `Omitting --name in CLI commands`
  - Fix: Always include --name parameter
  - Occurrences: 5
```

## 跨会话持久化

规则可导出/导入 JSON 文件：

```python
# 导出
corrector.export_rules()

# 导入
corrector.rules_engine.import_rules("path/to/ERROR_RULES.json")
```

## 配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| threshold | 3 | 同一模式出现次数达到此值时生成规则 |
| rules_path | docs/ERROR_RULES.json | 规则文件路径 |

## 查看当前规则

```bash
# 查看自动生成的规则
cat docs/ERROR_RULES.md

# 通过 Python API 查看
python -c "from fc_runtime.corrector import Corrector; c = Corrector(); print(c.get_rules_text())"
```
