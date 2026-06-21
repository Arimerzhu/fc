# 改进计划：让 fc 真正适合 AI 精密 CAD 设计

> 基于 DBY250 二级减速器任务的真实教训制定

## 现状与目标

**现状**：fc CLI 能执行 FreeCAD 命令，但无法保证输出正确。AI 跑完脚本 → 文件"成功生成" → 用户打开是空的 → AI 无法感知。

**目标**：AI 生成的 CAD 文件经过**自动验证**，正确性有保障，错误当场发现而非用户打开后才暴露。

---

## 改进一：输出验证层（优先级：P0）

### 问题
AI 运行 `macro_dby250.py` 后，脚本打印 `FCStd: 14412 bytes`，没有报错。但 FreeCAD GUI 打开是空的。AI 无法感知这个失败。

### 方案：保存后自动验证

```python
# 在 HeadlessBackend 中，保存/导出后自动执行验证
def verify_output(output_path, expected_checks):
    """验证输出文件的几何正确性"""
    checks = {
        'fcstd': verify_fcstd,
        'step': verify_step,
        'svg': verify_svg,
    }
    result = checks[ext](output_path)
    if not result.pass:
        raise VerificationError(f"验证失败: {result.reason}")
    return result

def verify_fcstd(path):
    """验证 FCStd：对象数、体积、边界框"""
    doc = FreeCAD.open(path)
    objs = [o for o in doc.Objects if hasattr(o, 'Shape') and o.Shape]
    if len(objs) < expected_count:
        return CheckResult(False, f"只有 {len(objs)} 个零件，期望 >= {expected_count}")
    for obj in objs:
        bb = obj.Shape.BoundBox
        if bb.isEmpty():
            return CheckResult(False, f"{obj.Name} 边界框为空")
    return CheckResult(True, f"{len(objs)} 个零件，体积={total_volume:.2f}mm³")
```

### 触发时机
- `fc document save` 后
- `Part.export` 后
- 任何 `.FCStd/.step/.stl` 文件写入后

### 预期效果
```
fc part add box --name Box --param length=100
  → 验证: Box 零件数=1, 体积=1000000mm³ ✅
fc export step --output model.step
  → 验证: STEP 实体数=1, 边界框=(0,0,0)-(100,100,100) ✅
```

---

## 改进二：持久化会话模式（优先级：P0）

### 问题
每个 `fc` CLI 调用是独立的子进程，文档状态不共享。复杂模型需要 AI 在每条命令中加 `--project`，一条出错影响后续所有命令。

### 方案：GUI 子进程 + Socket 通信

```bash
# 启动持久化会话（不关闭 FreeCAD 窗口）
fc session start --name reducer --mode gui
  # FreeCAD GUI 启动，保持运行，监听 localhost:9229

# 通过 JSON-RPC 发送命令
curl -X POST http://localhost:9229/execute -d '{
  "command": "fc part add cylinder",
  "args": {"name": "Shaft_1", "radius": 14, "height": 320}
}'
  # 返回: {"status": "ok", "object": "Shaft_1", "time_ms": 123}

# 关闭会话
fc session stop --name reducer
```

### 与 HeadlessBackend 的关系

| 模式 | 适用场景 | 状态 |
|------|---------|------|
| HeadlessBackend（当前） | 简单零件、快速验证 | ✅ 已完成 |
| GUI subprocess + RPC（新增） | 复杂装配、工程图 | 🟡 待实现 |
| 批处理 batch（当前） | 多文件导出 | ✅ 已完成 |

### 优势
- 文档状态持久，不用每条命令带 `--project`
- 支持交互式查看（FreeCAD GUI 可见）
- TechDraw 命令可用（GUI 模式原生支持）

---

## 改进三：SVG 工程图自动标注（优先级：P1）

### 问题
当前 `TechDraw.projectToSVG` 只输出线条，没有尺寸标注、表面粗糙度、形位公差。生成的 SVG 不是真正的工程图。

### 方案：分层 SVG 生成器

```python
class EngineeringDrawingSVG:
    """生成符合 GB/T 的工程图 SVG"""

    def __init__(self, shape, scale=0.4, page_size='A3'):
        self.shape = shape
        self.scale = scale
        self.page_w, self.page_h = {'A3': (420, 297)}[page_size]

    def add_dimension(self, dim_type, p1, p2, label, position=None):
        """添加尺寸标注"""
        # 线性尺寸、直径、半径、角度
        pass

    def add_gdt(self, symbol_type, position, value):
        """添加形位公差"""
        # 同轴度、垂直度、平行度、跳动
        pass

    def add_roughness(self, position, value):
        """添加表面粗糙度"""
        pass

    def add_weld_symbol(self, position, symbol):
        """添加焊接符号"""
        pass

    def add_title_block(self, title, scale, material, weight):
        """添加标题栏"""
        pass

# 使用示例
svg = EngineeringDrawingSVG(assembly_shape)
svg.add_view('front', direction=(0,-1,0), x=50, y=100)
svg.add_view('top', direction=(0,0,-1), x=50, y=200)
svg.add_view('side', direction=(-1,0,0), x=250, y=100)
svg.add_dimension('diameter', p1=center1, p2=center2, label='φ75')
svg.add_gdt('coaxiality', position=(x,y), value='Ø0.02 A')
svg.add_roughness(position=(x,y), value='Ra1.6')
svg.add_title_block(title='DBY250减速器箱体', scale='1:2.5',
                    material='HT200', weight='120kg')
svg.save('output.svg')
```

### 不依赖 FreeCAD TechDraw
纯 Python 实现，基于 `Part.Shape` 的 BoundBox、顶点、边数据计算标注位置，不调用 FreeCAD TechDraw 模块。Headless 模式可用。

---

## 改进四：参数化设计 DSL（优先级：P1）

### 问题
当前 AI 需要描述**建模步骤**（"先画箱体、再画轴、再画齿轮..."），而不是**设计目标**（"设计一个中心距 100+150mm 的二级减速器"）。这对 AI 来说不自然，容易出错。

### 方案：设计目标 → 自动建模

```python
# fc model reducer --spec "a1=100,a2=150,m1=2.5,z1=30,z2=50,m2=3,z3=30,z4=70"

class ReducerSpec:
    """减速器设计规范"""
    def __init__(self, a1, a2, m1, z1, z2, m2, z3, z4):
        self.a1 = a1        # 高速级中心距
        self.a2 = a2        # 低速级中心距
        self.d_gear1 = m1 * z1
        self.d_gear2 = m1 * z2
        self.d_gear3 = m2 * z3
        self.d_gear4 = m2 * z4
        self.validate()

    def validate(self):
        """验证几何约束"""
        assert abs((self.d_gear1 + self.d_gear2)/2 - self.a1) < 0.01
        assert abs((self.d_gear3 + self.d_gear4)/2 - self.a2) < 0.01

    def to_params(self):
        """转换为建模参数"""
        return {
            'base_l': self.a1 + self.a2 + self.d_gear4 + 60,  # 箱体长度
            'width': self.d_gear4 + 30,
            'height': self.d_gear4 + 40,
            'housing_thick': 12,
            'bolt_d': 12,
            'x1': 60,
            'x2': 60 + self.a1,
            'x3': 60 + self.a1 + self.a2,
        }
```

### 命令设计
```bash
# 自然语言 → 自动拆分
fc model reducer --describe "设计一个DBY250二级减速器，中心距100+150，总传动比11.7"

# 参数化（AI 只需提供设计参数）
fc model reducer --a1 100 --a2 150 --m1 2.5 --z1 30 --z2 50 --m2 3 --z3 30 --z4 70 --output DBY250

# 模板模式
fc model reducer --template gear_reducer --scale medium --material ht200
```

### 优势
- AI 描述**设计目标**，DSL 自动计算**建模参数**
- 约束验证内置，不会产生几何矛盾
- 可复用模板库（减速器、法兰、箱体、轴系...）

---

## 改进五：FreeCAD 版本兼容检测（优先级：P2）

### 问题
FreeCADCmd 和 FreeCAD GUI 的 API 行为不一致（如 `TechDraw.exportPageAsSvg` 在 Cmd 中不存在）。AI 踩到这类坑时只知道 "Unknown exception"，无法知道原因。

### 方案：功能可用性检测

```python
class FreeCADCapabilities:
    """FreeCAD 能力检测"""
    def __init__(self):
        self.version = self._detect_version()
        self.features = self._detect_features()

    def _detect_features(self):
        return {
            'techdraw_page': self._check('TechDraw.Page'),
            'techdraw_export_svg': self._check('TechDraw.exportPageAsSvg'),
            'techdraw_dim': self._check('TechDraw.DrawViewDimension'),
            'rpc_backend': self._check_rpc_port(),
        }

    def warn_if_missing(self, feature):
        if not self.features.get(feature):
            print(f"⚠️ 功能 '{feature}' 在 FreeCAD {self.version} 中不可用")
            print(f"   建议: 使用备选方案或升级 FreeCAD")

# 在 fc runtime 启动时执行
caps = FreeCADCapabilities()
if not caps.features['techdraw_export_svg']:
    print("注意: TechDraw SVG 导出在 headless 模式不可用")
    print("  → 使用 SVG 工程图生成器（纯 Python）")
    print("  → 或切换到 GUI 会话模式")
```

---

## 实施顺序

| 阶段 | 改进项 | 工作量 | 优先级 | 产出 |
|------|--------|--------|--------|------|
| **Phase 1** | 输出验证层 | 2-3 天 | P0 | `HeadlessBackend.verify()` |
| **Phase 2** | 持久化会话模式 | 5-7 天 | P0 | `fc session start/stop` + RPC |
| **Phase 3** | SVG 工程图 DSL | 3-5 天 | P1 | `EngineeringDrawingSVG` 类 |
| **Phase 4** | 参数化设计 DSL | 5-7 天 | P1 | `fc model` 命令组 |
| **Phase 5** | 能力检测 | 1-2 天 | P2 | `fc info --capabilities` |

---

## Phase 1 详细设计（立即可做）

**目标**：让 AI 知道生成的 CAD 文件是否正确，不等用户打开才发现问题。

**实现位置**：`packages/core/src/fc_core/verify.py`

```python
"""验证模块：自动检查 CAD 输出正确性"""
from dataclasses import dataclass
from typing import Optional, List
import FreeCAD

@dataclass
class CheckResult:
    passed: bool
    message: str
    details: Optional[dict] = None

class CADVerifier:
    def verify_fcstd(self, path: str, expected: dict) -> CheckResult:
        """
        验证 FCStd 文件
        expected: {'min_objects': 1, 'max_objects': 100, 'min_volume': 0}
        """
        doc = FreeCAD.open(path)
        shapes = [o for o in doc.Objects if self._has_valid_shape(o)]
        FreeCAD.closeDocument(doc.Name)

        if len(shapes) < expected.get('min_objects', 0):
            return CheckResult(False, f"零件数 {len(shapes)} < {expected['min_objects']}")
        if len(shapes) > expected.get('max_objects', 9999):
            return CheckResult(False, f"零件数 {len(shapes)} > {expected['max_objects']}")

        volumes = [s.Volume for s in shapes if s.Volume > 0]
        if not volumes:
            return CheckResult(False, "所有零件体积为 0，可能是空模型")

        return CheckResult(True, f"{len(shapes)} 个零件，总体积 {sum(volumes):.0f} mm³")

    def verify_step(self, path: str, expected: dict) -> CheckResult:
        """验证 STEP 文件"""
        import Part
        shape = Part.read(path)
        if shape.isNull():
            return CheckResult(False, "STEP 文件为空或无效")

        bb = shape.BoundBox
        if bb.isEmpty():
            return CheckResult(False, "STEP 边界框为空")

        return CheckResult(True, f"{len(shape.Solids)} 实体, 边界框 {bb}")
```

**集成到 HeadlessBackend**：

```python
# packages/core/src/fc_core/backend.py
class HeadlessBackend:
    def export(self, format, output, verify=True):
        result = self._do_export(format, output)
        if verify and result.success:
            verifier = CADVerifier()
            if format == 'step':
                check = verifier.verify_step(output, self._expected_check)
            elif format == 'fcstd':
                check = verifier.verify_fcstd(output, self._expected_check)
            if not check.passed:
                return ToolResponse(success=False,
                    error=f"验证失败: {check.message}",
                    data=check.details)
        return result
```

**Agent 集成**（fc_runtime/executor.py）：

```python
class Executor:
    def execute(self, task):
        result = self.backend.execute(task)
        if task.expected_output:
            # 保存后自动验证
            if task.output_file:
                verifier = CADVerifier()
                check = verifier.verify(task.output_file)
                if not check.passed:
                    return ToolResponse(
                        success=False,
                        error=f"CAD 验证失败: {check.message}",
                        suggestion=f"检查 {task.output_file} 的几何正确性"
                    )
        return result
```

---

## 验收标准

每项改进完成后，用 DBY250 减速器任务验证：

| 验证项 | 检查点 |
|--------|--------|
| 验证层 | 运行 `fc model reducer --a1 100 --a2 150 ...`，输出包含 `验证: 15 个零件，总体积 XXX mm³ ✅` |
| 会话模式 | `fc session start --mode gui` 后，`fc part add cylinder` × 10 条命令，模型在 FreeCAD GUI 中实时可见 |
| SVG 工程图 | 生成的 SVG 包含：尺寸标注（φ75、100mm）、标题栏（DBY250、比例1:2.5）、技术要求文字 |
| 参数化 DSL | `fc model reducer --z1 30 --z2 50`，自动计算中心距 100mm，不需 AI 手动算 |
| 能力检测 | `fc info --capabilities` 输出 TechDraw 支持状态，缺失功能有警告和建议 |
