# 多Agent协同操作FreeCAD生成工业级图纸 — 方法论

> **Methodology v1.0** | 2026年6月 | 基于 10+ 篇顶会论文与开源项目
>
> 从自然语言需求到参数化3D模型、再到符合工业标准的2D工程图 — 一套完整的多智能体协作方法论

---

## 目录

1. [方法论总览](#01-方法论总览)
2. [系统架构设计](#02-系统架构设计)
3. [Agent角色定义](#03-agent角色定义)
4. [编排策略与通信](#04-编排策略与通信)
5. [FreeCAD技术集成](#05-freecad技术集成)
6. [工业级出图流程](#06-工业级出图流程)
7. [多层验证体系](#07-多层验证体系)
8. [快速启动路径](#08-快速启动路径)
9. [能力边界与适用场景](#09-能力边界与适用场景)
10. [技术选型参考](#10-技术选型参考)

---

## 01 方法论总览

本方法论回答一个核心问题：**如何让多个专业化AI Agent协同工作，将人类的自然语言设计需求转化为FreeCAD中的参数化3D模型，并自动输出符合工业标准的2D工程图纸**。

该方法论融合了2024-2026年间学术界和工业界的最新成果，包括ICCV、ACL、ICLR等顶会论文中提出的多Agent CAD系统架构[1][2][3]，以及FreeCAD AI工作台和MCP Server等可直接使用的开源工具[4][5]。

### 核心设计原则

- **语义与几何分离**：先确定"做什么"（设计规划），再确定"怎么做"（代码生成），避免LLM同时处理高层语义和底层几何
- **装配关系前置**：在设计阶段就定义零件间的Connector（连接点），避免在装配阶段依赖LLM的3D空间推理[2]
- **验证贯穿始终**：每个阶段都有对应的验证Agent，形成闭环反馈，而非一次性生成
- **工具驱动执行**：Agent不直接生成几何，而是生成可执行的FreeCAD Python脚本，通过CAD内核验证
- **跨阶段精准回滚**：验证失败时，将错误分类为"设计级"或"代码级"，仅回滚到负责的Agent[2]

---

## 02 系统架构设计

推荐采用**层级式 + 有向循环**的混合编排架构。层级式控制确保任务按阶段有序推进，有向循环允许验证失败后回退到特定Agent而非从头开始。

### 系统架构总览

```
                    ┌──────────────────┐
                    │   用户交互层      │  自然语言/草图/图像输入
                    └────────┬─────────┘
                             ↓
                    ┌──────────────────┐
                    │  编排器 Orchestrator│  LangGraph 控制图
                    └────────┬─────────┘
                             ↓
        ┌────────────┬──────┴──────┬────────────┐
        ↓            ↓             ↓            ↓
  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
  │需求分析   │ │设计规划   │ │CAD建模   │ │出图Agent │
  │Agent     │ │Agent     │ │Agent(s)  │ │          │
  └──────────┘ └──────────┘ └──────────┘ └──────────┘
        │            │             │            │
        └────────────┴──────┬──────┴────────────┘
                            ↓
                    ┌──────────────────┐
                    │  验证层           │
                    │  ├ 几何审查Agent  │  视觉+拓扑验证
                    │  ├ 标注合规Agent  │  GD&T/标准/可制造性
                    │  └ 可制造性Agent  │  公差链分析
                    └────────┬─────────┘
                             ↓
                    ┌──────────────────┐
                    │  反馈回路         │  跨阶段回滚
                    │  + 经验库         │  向量数据库积累设计知识
                    └──────────────────┘
```

### 架构分层说明

| 层级 | 职责 | 关键组件 |
|------|------|---------|
| **用户输入层** | 接收多模态设计需求 | 自然语言解析、草图识别、参数文件读取 |
| **编排器** | 任务路由、状态管理、反馈控制 | LangGraph控制图、动态Agent选择 |
| **Agent集群层** | 执行具体设计任务 | 需求分析、设计规划、CAD建模、出图 |
| **验证层** | 多维度质量检查 | 几何审查、标注合规、可制造性 |
| **经验库** | 知识积累与复用 | 向量数据库（ChromaDB等） |

---

## 03 Agent角色定义

### Agent 01：需求分析Agent

接收多模态输入，消除歧义，输出结构化设计需求文档（JSON Schema格式），包含零件类型、关键尺寸、材料、公差等级、适用标准。

### Agent 02：设计规划Agent

将需求转化为可执行建模计划：零件分解、特征操作序列、Connector定义（装配关系前置）、参数化约束关系。

### Agent 03：CAD建模Agent

根据建模计划生成FreeCAD Python脚本并执行。支持并行实例化（多个零件同时建模）。内置错误自纠正（最多3次重试）。

### Agent 04：出图Agent

从3D模型自动生成2D工程图：视图投影、尺寸标注、公差标注、图框模板、导出SVG/DXF。

### Agent 05：几何审查Agent

视觉验证（VLM多视角渲染检查）+ 拓扑检查（连通性、正体积）+ 视图关联一致性检查。

### Agent 06：标注合规Agent

检查GD&T标注规范性、尺寸标注完整性、公差链分析、标准符号合规性（ISO/GB/ASME）。

### 各Agent的输入/输出规范

| Agent | 输入 | 输出 | LLM角色 |
|------|------|------|---------|
| **需求分析** | 自然语言 / 草图 / 参数文件 | 结构化JSON需求文档 | 推理 + 交互澄清 |
| **设计规划** | JSON需求文档 | 建模计划（特征序列 + Connector定义） | 规划推理 |
| **CAD建模** | 建模计划 | FreeCAD Python脚本 → 3D模型 | 代码生成 + 执行 |
| **出图** | 3D模型 + 标注要求 | 2D工程图（SVG/DXF） | 代码生成 + 执行 |
| **几何审查** | 3D模型 + 2D图纸 | 审查报告（PASS/FAIL + 修正建议） | VLM视觉理解 |
| **标注合规** | 2D工程图 | 合规报告（标准符合度评分） | VLM + 规则引擎 |

---

## 04 编排策略与通信

### 编排模式选择

推荐使用 **LangGraph** 作为编排框架[3][6]。其核心优势是支持**有向循环图**（DAG + Loops），允许验证失败后精准回退。

| 编排模式 | CAD场景适用性 | 本方案使用位置 |
|----------|--------------|---------------|
| **层级式** | 高度适用 — CAD设计天然有阶段依赖 | 整体架构控制 |
| **流水线式** | 部分适用 — 适合简单零件 | 单零件建模→出图 |
| **并行扇出** | 高度适用 — 多零件同时建模 | CAD建模Agent并行实例化 |
| **有向循环** | 关键 — 验证反馈必须回退 | 验证→修正回路 |

### 跨阶段回滚机制

借鉴ArtiCAD的错误分类策略[2]，当验证Agent检测到问题时：

- **DESIGN级错误**（如Connector定义不合理、零件分解逻辑错误）→ 仅回滚到设计规划Agent
- **CODE级错误**（如参数数值错误、特征操作顺序不当）→ 仅回滚到CAD建模Agent
- **DRAWING级错误**（如标注遗漏、视图选择不当）→ 仅回滚到出图Agent

这比"从头重试"大幅减少冗余计算，提升整体效率。

### 经验库与自进化

每个验证Agent的审查结果积累到分区向量数据库（经验库），供后续任务检索[2]。例如：几何审查Agent发现某种特征组合容易导致拓扑错误，后续设计规划Agent在生成类似方案时可主动规避。

### Agent间通信协议

推荐采用 **MCP（Model Context Protocol）** 作为Agent与FreeCAD之间的通信桥梁[5]。MCP将FreeCAD的能力封装为标准化的工具调用接口，任何兼容的AI Agent都可以即插即用。

> **通信协议选型**
>
> - **Agent ↔ FreeCAD**：MCP协议（57个工具调用，覆盖建模/草图/标注/导出）[5]
> - **Agent ↔ Agent**：JSON Schema中间表示（结构化、可验证、人可读）
> - **Agent ↔ 经验库**：向量数据库查询（语义相似度检索）

---

## 05 FreeCAD技术集成

### 两条集成路径

| 方案 | 架构 | 优势 | 适用场景 |
|------|------|------|---------|
| **FreeCAD AI 工作台**[4] | Python插件嵌入FreeCAD内部 | 50个工具调用、20+ LLM支持、Plan/Act双模式、错误自纠正、Skills系统 | FreeCAD内部交互式设计 |
| **FreeCAD MCP Server**[5] | Node.js MCP Server ↔ HTTP ↔ FreeCAD Python宏 | 57个MCP工具、支持Claude/Codex/Claude Code、外部Agent操控 | 外部Agent编排自动化流水线 |

### FreeCAD Python API 核心模块

| 模块 | 功能 | Agent使用场景 |
|------|------|--------------|
| `FreeCAD` (App) | 文档管理、对象创建、重计算 | 创建文档、添加对象、管理状态 |
| `Part` | 几何体创建与布尔运算 | makeBox/Cylinder/Sphere、融合、切割 |
| `Sketcher` | 参数化草图 | 程序化创建草图、添加约束 |
| `PartDesign` | 特征建模 | 挤出、旋转、扫掠、放样、倒角 |
| `TechDraw` | 工程图生成 | 创建图纸页面、视图投影、尺寸标注 |
| `Assembly` | 装配体管理 | 零件装配、约束求解 |
| `Fem` | 有限元分析 | 结构仿真验证（可选） |

### Headless模式

FreeCAD支持**headless模式**运行（命令行执行脚本，无需GUI），这是多Agent自动化流水线的关键基础。Agent生成的Python脚本可通过以下方式执行：

```bash
# Headless执行FreeCAD脚本
freecadcmd -c build_part.py
freecadcmd -c generate_drawing.py
```

---

## 06 工业级出图流程

出图Agent通过FreeCAD的TechDraw工作台API自动生成2D工程图。以下是标准出图流程：

### 六步出图流程

1. **选择图纸模板**：根据标准要求选择模板（ISO5457 A0-A4 / ANSI A-D）。如需GB国标，使用自定义SVG模板。
2. **创建图纸页面**：通过TechDraw API创建DrawPage对象，加载模板，设置投影方式（第一角/第三角）。
3. **插入视图组**：自动生成主视图 + 投影视图（前/左/俯/仰），支持剖视图。视图与3D模型参数关联。
4. **添加尺寸标注**：自动识别并标注关键尺寸（长度、直径、角度、公差）。标注值与模型关联，修改后自动更新。
5. **添加辅助元素**：中心线、剖面线、基准符号、表面粗糙度符号、焊接标识、标题栏信息。
6. **导出**：导出为SVG（矢量可编辑）或DXF（兼容AutoCAD），也可导出PDF用于审阅打印。

### TechDraw出图代码示例

```python
import FreeCAD as App
import TechDraw

doc = App.ActiveDocument

# 1. 创建图纸页面
page = doc.addObject('TechDraw::DrawPage', 'DrawingPage')
template = doc.addObject('TechDraw::DrawSVGTemplate', 'Template')
template.Template = 'ISO_A3_Landscape.svg'
page.Template = template

# 2. 插入主视图
view = doc.addObject('TechDraw::DrawViewPart', 'FrontView')
view.Source = doc.getObject('MyPart')
view.Direction = (0, 0, 1)
view.Scale = 2.0
page.addView(view)

# 3. 创建投影视图组
proj = doc.addObject('TechDraw::DrawProjGroup', 'ProjGroup')
proj.Source = doc.getObject('MyPart')
proj.addProjection('Front')
proj.addProjection('Left')
proj.addProjection('Top')
page.addView(proj)

doc.recompute()
```

---

## 07 多层验证体系

质量验证分为四个层级，贯穿整个设计流程：

```
第一层：代码验证          第二层：几何验证          第三层：视觉验证          第四层：工程合规
├─ 语法检查               ├─ 拓扑完整性            ├─ VLM多视角渲染         ├─ GD&T规范
├─ 运行时异常             ├─ 连通性                ├─ 形状符合性            ├─ 公差链分析
└─ 超时限制               └─ 正体积                └─ 视图一致性            └─ 可制造性
```

### 验证策略详解

- **代码执行验证**：CAD建模Agent生成的Python脚本先经过语法检查和沙盒执行，失败则自动重试（最多3次）[4]
- **几何有效性验证**：检查模型的拓扑完整性（≥7个B-Rep面）、连通性、正体积[7]
- **视觉验证**：通过VLM渲染多视角图像，检查几何形状是否符合设计意图[1]
- **工程标准合规**：GD&T标注规范、公差链分析（跨装配体公差累积检测）、可制造性规则检查[8]

> **注意**：AI审查的最佳定位是**预检（Pre-check）**而非替代人工审查。让人工审查聚焦于架构判断和设计决策，AI负责检查标注遗漏、公差累积等机械性工作[8]。

---

## 08 快速启动路径

1. **安装FreeCAD 1.0+**：1.0版本（2024年11月发布）修复了拓扑命名问题，参数化工作流更可靠。推荐使用1.0.2或1.1.0。
2. **部署FreeCAD AI工作台**：安装ghbalf/freecad-ai工作台，支持Claude/DeepSeek/Qwen等20+ LLM，50个结构化工具调用[4]。
3. **或部署FreeCAD MCP Server**：通过MCP协议让Claude Desktop/Codex/Claude Code直接操控FreeCAD，57个MCP工具[5]。
4. **定义Agent角色分工**：参照本方法论第三章的六Agent架构，用LangGraph编排控制图。
5. **准备企业模板**：自定义SVG模板实现GB国标图框和标题栏（FreeCAD无内置GB模板）。
6. **建立经验库**：部署向量数据库（如ChromaDB），积累设计知识和审查经验，实现持续优化。

---

## 09 能力边界与适用场景

### FreeCAD出图能力评估

| 能力项 | 支持情况 | 备注 |
|--------|---------|------|
| 正交投影视图 | ✅ 完整支持 | 主视图 + 投影视图组，第一角/第三角可切换 |
| ISO/ANSI标准模板 | ✅ 内置支持 | ISO5457、ANSI A-D系列 |
| GB国标模板 | ⚠️ 需自定义 | 需手动制作SVG国标图框模板 |
| 尺寸标注关联 | ✅ 支持 | 标注值与3D模型参数关联，修改后自动更新 |
| 剖视图 | ✅ 基本支持 | 标准剖面功能 |
| GD&T标注 | ⚠️ 基本支持 | 符号库不如商业CAD丰富 |
| BOM物料清单 | ⚠️ 基本功能 | 自动化程度不及SolidWorks |
| 导出格式 | ✅ SVG/DXF/PDF | SVG矢量可编辑，DXF兼容AutoCAD |
| 复杂装配体稳定性 | ⚠️ 一般 | 大规模装配体视图关联可能不稳定 |

### 适用场景判断

- **FreeCAD适合**：单个/小批量零件的参数化设计和出图、内部技术交流用图纸、3D打印和机加工模型准备、STEP交换和几何清理。
- **需要商业CAD**：超大型装配体、高吞吐量图纸生产（严格标准下）、高级曲面（Class-A）、PDM/PLM集成需求。

---

## 10 技术选型参考

| 组件 | 推荐方案 | 备选方案 | 选型理由 |
|------|---------|---------|---------|
| **编排框架** | LangGraph | CrewAI / AutoGen | 学术界主流，支持有向循环[3] |
| **CAD后端** | FreeCAD | CadQuery | 支持装配体+出图，CadQuery更适合单零件 |
| **Agent通信** | MCP协议 | FreeCAD AI工具调用 | 标准化、可扩展[5] |
| **推理LLM** | Claude 4.5 Sonnet | GPT-4o / DeepSeek / Qwen | 代码生成与推理能力均衡 |
| **视觉VLM** | Claude 4.5 Opus | Gemini 3 Pro | 多视角渲染检查 |
| **中间表示** | JSON Schema | 自定义DSL | 人可读、可验证、工具链友好 |
| **经验库** | ChromaDB | FAISS / Milvus | 轻量级、易部署 |

### 参考文献与学术基础

本方法论基于以下学术研究和开源项目的成果构建：

- **From Idea to CAD**（Honda研究院，2025）— 三Agent协作系统，V-Model开发流程[1]
- **ArtiCAD**（北航/浙大/港大，2026）— 四Agent装配设计，Connector机制 + 跨阶段回滚[2]
- **Physics-in-the-Loop**（德累斯顿工业大学 + MAN卡车，2026）— 四Agent + FEA闭环 + LangGraph[3]
- **FreeCAD AI**（ghbalf，2026）— FreeCAD AI工作台，50个工具调用[4]
- **FreeCAD MCP Server**（tomo1230，2026）— 57个MCP工具[5]
- **NVIDIA GTC 2026** — Reasoner/Planner/Compiler/Repair + JSON Schema[6]
- **Zero-to-CAD**（Autodesk研究院，2026）— 四道验证关 + 百万级CAD程序合成[7]
- **Leo AI** — AI CAD设计审查，公差链分析[8]

---

## Sources

[1] Honda Research, "From Idea to CAD: A Language Model-Driven Multi-Agent System for Collaborative Design", arXiv:2503.04417, 2025. https://arxiv.org/html/2503.04417v1

[2] ArtiCAD: Articulated CAD Assembly Design via Multi-Agent Code Generation, arXiv:2604.10992v2, 2026. https://arxiv.org/pdf/2604.10992v2

[3] Physics-in-the-Loop: A Hybrid Agentic Architecture for Validated CAD Engineering Design, arXiv:2605.19717v1, 2026. https://arxiv.org/html/2605.19717v1

[4] ghbalf/freecad-ai — FreeCAD AI Assistant Workbench, GitHub, 2026. https://github.com/ghbalf/freecad-ai

[5] tomo1230/freecad_mcp_server — FreeCAD MCP Server, GitHub, 2026. https://github.com/tomo1230/freecad_mcp_server

[6] NVIDIA GTC 2026, "Natural Language to 3D Geometric CAD: A Multi-Agent LLM Framework", Session P81308. https://www.nvidia.com/ja-jp/gtc/session-catalog/sessions/gtc26-p81308/

[7] Zero-to-CAD: Autodesk Research, arXiv:2604.24479, 2026. https://arxiv.org/abs/2604.24479

[8] Leo AI, "AI CAD Design Review: Automated Error Checking", 2026. https://www.getleo.ai/blog/ai-cad-design-review-automated-guide
