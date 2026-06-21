"""GB/T 标准装配图 SVG 生成器。

基于 fc_core.drawing.DrawingSheet，增加装配图专用要素：
  - 零件球标（序号 + 引线）
  - 明细表（GB/T 10609.2）
  - 线型区分（粗实线/虚线/点划线）
  - 技术要求

用法:
    from fc_core.drawing import DrawingSheet, View2D, Edge2D
    from fc_core.assembly_bom import make_sample_bom
    from fc_core.assembly_drawing import AssemblyDrawing

    ad = AssemblyDrawing("A0", title="进纸机构装配图")
    ad.add_view(view, "front")
    ad.set_bom(bom)
    ad.add_balloon(item_no=1, x=150, y=200, leader_x=120, leader_y=180)
    ad.save("assembly.svg")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from xml.etree import ElementTree as ET

from fc_core.drawing import PAGE_SIZES, Edge2D, BoundBox
from fc_core.step_projector import StepProjector, BoundBox3D, Vec3

from fc_core.assembly_bom import BOMItem, BOMTable


# ── 线型定义 (GB/T 4457.4) ─────────────────────────────────────

class LineType:
    """国标线型定义。"""
    # 粗实线 - 可见轮廓线
    VISIBLE = {"stroke": "black", "stroke-width": "0.5"}
    # 细实线 - 尺寸线、引出线、剖面线
    THIN = {"stroke": "black", "stroke-width": "0.25"}
    # 虚线 - 不可见轮廓线
    HIDDEN = {"stroke": "black", "stroke-width": "0.25", "stroke-dasharray": "4,2"}
    # 细点划线 - 轴线、对称中心线
    CENTER = {"stroke": "black", "stroke-width": "0.18", "stroke-dasharray": "12,2,3,2"}
    # 粗点划线 - 表面处理范围
    SPECIAL = {"stroke": "black", "stroke-width": "0.5", "stroke-dasharray": "12,2,3,2"}
    # 双点划线 - 相邻零件、极限位置
    PHANTOM = {"stroke": "black", "stroke-width": "0.18", "stroke-dasharray": "15,2,3,2,3,2"}


# ── 球标 ────────────────────────────────────────────────────────

@dataclass
class Balloon:
    """零件球标 - 序号圆圈 + 引线。"""
    item_no: int
    x: float  # 球标圆心 x (mm)
    y: float  # 球标圆心 y (mm)
    leader_x: float = 0.0  # 引线起点 x
    leader_y: float = 0.0  # 引线起点 y
    radius: float = 5.0    # 球标半径 (mm)
    font_size: float = 3.5  # 字号 (mm)
    has_horizontal_bar: bool = True  # 底部横线


@dataclass
class TechnicalRequirement:
    """技术要求条目。"""
    text: str
    item_no: int = 0  # 0 表示无编号


# ── 装配图生成器 ────────────────────────────────────────────────

class AssemblyDrawing:
    """GB/T 标准装配图生成器。

    在 DrawingSheet 基础上增加：
      - 球标系统 (balloons)
      - 明细表 (BOM table)
      - 线型支持
      - 技术要求
    """

    # 图幅边距 (mm) - GB/T 14689
    MARGINS = {
        "A4": {"left": 25, "right": 10, "top": 10, "bottom": 10},
        "A3": {"left": 25, "right": 10, "top": 10, "bottom": 10},
        "A2": {"left": 25, "right": 10, "top": 10, "bottom": 10},
        "A1": {"left": 25, "right": 10, "top": 10, "bottom": 10},
        "A0": {"left": 25, "right": 10, "top": 10, "bottom": 10},
    }

    # 标题栏尺寸 (mm) - GB/T 10609.1
    TITLE_BLOCK_W = 180.0
    TITLE_BLOCK_H = 56.0

    # 明细表尺寸 (mm) - GB/T 10609.2
    BOM_COL_WIDTHS = {
        "item_no": 10, "name": 50, "qty": 12,
        "material": 30, "mass": 20, "remark": 58,
    }
    BOM_ROW_H = 8.0
    BOM_HEADER_H = 10.0

    def __init__(
        self,
        page_size: str = "A0",
        title: str = "",
        landscape: bool = True,
    ) -> None:
        self.page_size = page_size
        self.title = title
        self.landscape = landscape

        # 获取图幅尺寸
        from fc_core.drawing import PAGE_SIZES
        w, h = PAGE_SIZES.get(page_size, (841.0, 1189.0))
        if landscape and w < h:
            w, h = h, w
        self.page_w = w
        self.page_h = h

        self.margins = self.MARGINS.get(page_size, self.MARGINS["A0"])
        self.drawing_area = {
            "x": self.margins["left"],
            "y": self.margins["top"],
            "w": self.page_w - self.margins["left"] - self.margins["right"],
            "h": self.page_h - self.margins["top"] - self.margins["bottom"],
        }

        self.views: list[dict[str, Any]] = []
        self.balloons: list[Balloon] = []
        self.bom: BOMTable | None = None
        self.tech_requirements: list[TechnicalRequirement] = []
        self.title_block_info: dict[str, str] = {
            "title": title,
            "scale": "",
            "material": "",
            "drawn_by": "",
            "checked_by": "",
            "date": "",
            "drawing_no": "",
            "version": "A",
            "unit": "mm",
            "quantity": "1",
            "weight": "",
        }

    # ── 配置方法 ────────────────────────────────────────────

    def set_bom(self, bom: BOMTable) -> None:
        self.bom = bom
        if bom.title and not self.title:
            self.title_block_info["title"] = bom.title

    def set_title_block(self, **kwargs: str) -> None:
        for k, v in kwargs.items():
            if k in self.title_block_info:
                self.title_block_info[k] = v

    def add_view(
        self,
        name: str,
        edges: list[Edge2D] | None = None,
        center_x: float = 0.0,
        center_y: float = 0.0,
        width: float = 100.0,
        height: float = 100.0,
        bound_box: BoundBox | None = None,
    ) -> None:
        self.views.append({
            "name": name,
            "edges": edges or [],
            "center_x": center_x,
            "center_y": center_y,
            "width": width,
            "height": height,
            "bound_box": bound_box,
        })

    def add_balloon(
        self,
        item_no: int,
        x: float, y: float,
        leader_x: float = 0.0, leader_y: float = 0.0,
        radius: float = 5.0,
    ) -> None:
        self.balloons.append(Balloon(
            item_no=item_no, x=x, y=y,
            leader_x=leader_x, leader_y=leader_y,
            radius=radius,
        ))

    def add_tech_requirement(self, text: str, item_no: int = 0) -> None:
        self.tech_requirements.append(TechnicalRequirement(
            text=text, item_no=item_no,
        ))

    def add_default_tech_requirements(self) -> None:
        defaults = [
            "未注倒角 C1",
            "未注圆角 R1~R3",
            "零件去毛刺、锐边倒钝",
            "装配前各零件清洗干净",
            "各运动副涂润滑脂",
            "装配后进行空载试运行 30 分钟",
        ]
        for i, text in enumerate(defaults, 1):
            self.add_tech_requirement(text, item_no=i)

    # ── SVG 生成 ────────────────────────────────────────────

    def _svg_element(
        self, tag: str, attrib: dict[str, str], **extra: str
    ) -> ET.Element:
        elem = ET.Element(tag)
        for k, v in attrib.items():
            elem.set(k, str(v))
        for k, v in extra.items():
            elem.set(k, str(v))
        return elem

    def _svg_line(
        self, x1: float, y1: float, x2: float, y2: float,
        line_type: dict[str, str] | None = None,
    ) -> ET.Element:
        attrib = {
            "x1": f"{x1:.3f}", "y1": f"{y1:.3f}",
            "x2": f"{x2:.3f}", "y2": f"{y2:.3f}",
        }
        if line_type:
            attrib.update(line_type)
        else:
            attrib.update(LineType.THIN)
        return self._svg_element("line", attrib)

    def _svg_circle(
        self, cx: float, cy: float, r: float,
        line_type: dict[str, str] | None = None,
        fill: str = "none",
    ) -> ET.Element:
        attrib = {
            "cx": f"{cx:.3f}", "cy": f"{cy:.3f}", "r": f"{r:.3f}",
            "fill": fill,
        }
        if line_type:
            attrib.update(line_type)
        else:
            attrib.update(LineType.THIN)
        return self._svg_element("circle", attrib)

    def _svg_text(
        self, x: float, y: float, text: str,
        size: float = 2.5, anchor: str = "middle",
        weight: str = "normal", fill: str = "black",
    ) -> ET.Element:
        elem = ET.Element("text")
        elem.set("x", f"{x:.3f}")
        elem.set("y", f"{y:.3f}")
        elem.set("text-anchor", anchor)
        elem.set("font-family", "SimSun, SimHei, Arial, sans-serif")
        elem.set("font-size", f"{size:.2f}")
        elem.set("font-weight", weight)
        elem.set("fill", fill)
        elem.text = text
        return elem

    def _svg_rect(
        self, x: float, y: float, w: float, h: float,
        fill: str = "none", stroke: str = "black",
        stroke_width: str = "0.35",
    ) -> ET.Element:
        return self._svg_element("rect", {
            "x": f"{x:.3f}", "y": f"{y:.3f}",
            "width": f"{w:.3f}", "height": f"{h:.3f}",
            "fill": fill, "stroke": stroke, "stroke-width": stroke_width,
        })

    def _svg_path(
        self, d: str, line_type: dict[str, str] | None = None,
        fill: str = "none",
    ) -> ET.Element:
        attrib = {"d": d, "fill": fill}
        if line_type:
            attrib.update(line_type)
        else:
            attrib.update(LineType.VISIBLE)
        return self._svg_element("path", attrib)

    # ── 渲染方法 ────────────────────────────────────────────

    def _render_frame(self, root: ET.Element) -> None:
        """渲染 GB/T 标准图框（含装订边）。"""
        m = self.margins
        # 外框（纸张边界）
        root.append(self._svg_rect(0, 0, self.page_w, self.page_h,
                                   stroke="black", stroke_width="0.35"))
        # 内框（图框线）
        root.append(self._svg_rect(
            m["left"], m["top"],
            self.page_w - m["left"] - m["right"],
            self.page_h - m["top"] - m["bottom"],
            stroke="black", stroke_width="0.7",
        ))

    def _render_title_block(self, root: ET.Element) -> None:
        """渲染 GB/T 10609.1 标题栏（右下角）。"""
        tb_w = self.TITLE_BLOCK_W
        tb_h = self.TITLE_BLOCK_H
        x = self.page_w - self.margins["right"] - tb_w
        y = self.page_h - self.margins["bottom"] - tb_h

        group = ET.SubElement(root, "g")
        group.set("class", "title-block")

        # 外框
        group.append(self._svg_rect(x, y, tb_w, tb_h, stroke_width="0.5"))

        # 行分割
        row1_h = 28.0
        group.append(self._svg_line(x, y + row1_h, x + tb_w, y + row1_h,
                                     {"stroke": "black", "stroke-width": "0.35"}))

        # 第一行：单位名称(54) | 图样名称(66) | 设计(30) | 审核(30)
        col1_w, col2_w, col3_w, col4_w = 54.0, 66.0, 30.0, 30.0
        cx = x
        for i, (cw, label, key) in enumerate([
            (col1_w, "单位名称", "unit"),
            (col2_w, "图样名称", "title"),
            (col3_w, "设计", "drawn_by"),
            (col4_w, "审核", "checked_by"),
        ]):
            group.append(self._svg_rect(cx, y, cw, row1_h, stroke_width="0.25"))
            group.append(self._svg_text(cx + 2, y + 4, label, size=2.0,
                                        anchor="start", fill="gray"))
            val = self.title_block_info.get(key, "")
            vsz = 3.0 if key == "title" else 2.2
            group.append(self._svg_text(cx + cw / 2, y + row1_h / 2 + 2, val,
                                        size=vsz, weight="bold" if key == "title" else "normal"))
            cx += cw

        # 第二行：材料 | 比例 | 重量 | 数量 | 图号 | 版本 | 日期
        row2_y = y + row1_h
        row2_h = tb_h - row1_h
        cells2 = [
            (36.0, "材料", "material"),
            (24.0, "比例", "scale"),
            (24.0, "重量", "weight"),
            (18.0, "数量", "quantity"),
            (42.0, "图号", "drawing_no"),
            (18.0, "版本", "version"),
            (18.0, "日期", "date"),
        ]
        cx = x
        for cw, label, key in cells2:
            group.append(self._svg_rect(cx, row2_y, cw, row2_h, stroke_width="0.25"))
            group.append(self._svg_text(cx + 2, row2_y + 4, label, size=1.8,
                                        anchor="start", fill="gray"))
            val = self.title_block_info.get(key, "")
            group.append(self._svg_text(cx + cw / 2, row2_y + row2_h / 2 + 1, val,
                                        size=2.0))
            cx += cw

    def _render_bom_table(self, root: ET.Element) -> None:
        """渲染 GB/T 10609.2 明细表（标题栏上方，从下往上排列）。"""
        if not self.bom or not self.bom.items:
            return

        col_widths = self.BOM_COL_WIDTHS
        row_h = self.BOM_ROW_H
        header_h = self.BOM_HEADER_H
        total_w = sum(col_widths.values())

        # 位置：标题栏正上方，从下往上生长
        tb_x = self.page_w - self.margins["right"] - self.TITLE_BLOCK_W
        tb_y = self.page_h - self.margins["bottom"] - self.TITLE_BLOCK_H
        bom_x = self.page_w - self.margins["right"] - total_w
        n_items = len(self.bom.items)
        bom_h = header_h + n_items * row_h
        bom_y = tb_y - bom_h

        group = ET.SubElement(root, "g")
        group.set("class", "bom-table")

        # 外框
        group.append(self._svg_rect(bom_x, bom_y, total_w, bom_h, stroke_width="0.5"))

        # 表头
        header_y = bom_y
        group.append(self._svg_rect(bom_x, header_y, total_w, header_h,
                                     stroke_width="0.35"))
        col_names = ["序号", "名称", "数量", "材料", "质量", "备注"]
        cx = bom_x
        for name, cw in zip(col_names, col_widths.values()):
            group.append(self._svg_line(cx, header_y, cx, header_y + header_h,
                                         {"stroke": "black", "stroke-width": "0.25"}))
            group.append(self._svg_text(cx + cw / 2, header_y + header_h / 2 + 1,
                                        name, size=2.0, weight="bold"))
            cx += cw

        # 数据行（从下往上，序号从底部开始）
        for i, item in enumerate(reversed(self.bom.items)):
            row_y = bom_y + header_h + i * row_h
            # 行分隔线
            group.append(self._svg_line(bom_x, row_y + row_h,
                                         bom_x + total_w, row_y + row_h,
                                         {"stroke": "black", "stroke-width": "0.18"}))
            # 列数据
            cx = bom_x
            values = [
                str(item.item_no),
                item.display_name,
                str(item.quantity),
                item.material,
                f"{item.mass_kg:.1f}" if item.mass_kg else "",
                item.remark,
            ]
            for val, cw in zip(values, col_widths.values()):
                group.append(self._svg_line(cx, header_y, cx, bom_y + bom_h,
                                             {"stroke": "black", "stroke-width": "0.18"}))
                anchor = "middle" if cw <= 20 else "start"
                tx = cx + cw / 2 if anchor == "middle" else cx + 2
                group.append(self._svg_text(tx, row_y + row_h / 2 + 1, val,
                                            size=1.8, anchor=anchor))
                cx += cw

    def _render_balloons(self, root: ET.Element) -> None:
        """渲染零件球标（序号圆圈 + 引线）。"""
        group = ET.SubElement(root, "g")
        group.set("class", "balloons")

        for b in self.balloons:
            # 引线
            if b.leader_x != 0.0 or b.leader_y != 0.0:
                # 引线从零件指向球标
                group.append(self._svg_line(
                    b.leader_x, b.leader_y, b.x, b.y,
                    LineType.THIN,
                ))
                # 引线起点小圆点
                group.append(self._svg_circle(
                    b.leader_x, b.leader_y, 0.8,
                    fill="black", line_type={"stroke": "black", "stroke-width": "0"},
                ))

            # 球标圆圈
            group.append(self._svg_circle(b.x, b.y, b.radius, LineType.THIN))

            # 序号文字
            group.append(self._svg_text(
                b.x, b.y + b.font_size * 0.35,
                str(b.item_no),
                size=b.font_size, weight="bold",
            ))

            # 底部横线（标准球标样式）
            if b.has_horizontal_bar:
                bar_w = b.radius * 0.8
                bar_y = b.y + b.radius
                group.append(self._svg_line(
                    b.x - bar_w, bar_y, b.x + bar_w, bar_y,
                    LineType.THIN,
                ))

    def _render_tech_requirements(self, root: ET.Element) -> None:
        """渲染技术要求（标题栏左侧或图纸空白区）。"""
        if not self.tech_requirements:
            return

        group = ET.SubElement(root, "g")
        group.set("class", "tech-requirements")

        # 位置：标题栏左侧
        tb_x = self.page_w - self.margins["right"] - self.TITLE_BLOCK_W
        tr_x = self.margins["left"] + 10
        tr_y = self.page_h - self.margins["bottom"] - 80
        line_spacing = 5.0

        # 标题
        group.append(self._svg_text(tr_x, tr_y, "技术要求", size=3.5,
                                     anchor="start", weight="bold"))
        group.append(self._svg_line(
            tr_x, tr_y + 1.5, tr_x + 30, tr_y + 1.5,
            LineType.THIN,
        ))

        # 条目
        for i, req in enumerate(self.tech_requirements):
            y = tr_y + 8 + i * line_spacing
            prefix = f"{req.item_no}. " if req.item_no > 0 else ""
            group.append(self._svg_text(
                tr_x, y, f"{prefix}{req.text}",
                size=2.5, anchor="start",
            ))

    def _render_views(self, root: ET.Element) -> None:
        """渲染投影视图（带线型区分 + 尺寸标注 + 路径合并 + 分层）。

        优化：
        - 按线型分层（可见/不可见/双点划线/中心线）
        - 同层路径合并为单个 <path> 元素（减少 DOM 节点数）
        """
        if not self.views:
            return

        for v in self.views:
            cx, cy = v["center_x"], v["center_y"]
            view_group = ET.SubElement(root, "g")
            view_group.set("class", f"view-{v['name']}")
            view_group.set("transform", f"translate({cx:.3f},{cy:.3f})")

            # 按线型分组收集路径数据
            paths_by_type: dict[str, list[str]] = {
                "visible": [],
                "hidden": [],
                "adjacent": [],
            }
            edges = v.get("edges", [])
            visible_count = 0
            hidden_count = 0

            for edge in edges:
                path_d = f"M{edge.x1:.3f},{edge.y1:.3f} L{edge.x2:.3f},{edge.y2:.3f}"
                is_hidden = getattr(edge, "hidden", False)
                is_adjacent = getattr(edge, "adjacent", False)
                if is_adjacent:
                    paths_by_type["adjacent"].append(path_d)
                elif is_hidden:
                    paths_by_type["hidden"].append(path_d)
                    hidden_count += 1
                else:
                    paths_by_type["visible"].append(path_d)
                    visible_count += 1

            # 按层渲染（可见轮廓 -> 虚线 -> 双点划线）
            if paths_by_type["visible"]:
                layer_g = ET.SubElement(view_group, "g")
                layer_g.set("class", "layer-visible")
                merged = " ".join(paths_by_type["visible"])
                layer_g.append(self._svg_path(merged, LineType.VISIBLE))
            if paths_by_type["hidden"]:
                layer_g = ET.SubElement(view_group, "g")
                layer_g.set("class", "layer-hidden")
                merged = " ".join(paths_by_type["hidden"])
                layer_g.append(self._svg_path(merged, LineType.HIDDEN))
            if paths_by_type["adjacent"]:
                layer_g = ET.SubElement(view_group, "g")
                layer_g.set("class", "layer-adjacent")
                merged = " ".join(paths_by_type["adjacent"])
                layer_g.append(self._svg_path(merged, LineType.PHANTOM))

            # 尺寸标注（包围盒尺寸）
            w = v.get("width", 0)
            h = v.get("height", 0)
            if w > 0 and h > 0 and v.get("show_dimensions", True):
                self._render_view_dimensions(view_group, v, w, h)

            # 中心线（圆孔轴线）- 单独一层
            circles = v.get("circles", [])
            if circles:
                center_group = ET.SubElement(view_group, "g")
                center_group.set("class", "layer-center")
                center_paths = []
                for circle in circles:
                    cx_c, cy_c = circle.cx, circle.cy
                    r = circle.radius
                    length = r + 5.0
                    center_paths.append(
                        f"M{cx_c - length:.3f},{cy_c:.3f} L{cx_c + length:.3f},{cy_c:.3f}"
                    )
                    center_paths.append(
                        f"M{cx_c:.3f},{cy_c - length:.3f} L{cx_c:.3f},{cy_c + length:.3f}"
                    )
                merged = " ".join(center_paths)
                center_group.append(self._svg_path(merged, LineType.CENTER))

            # 视图标签（下方）
            label_y = h / 2 + 10
            view_group.append(self._svg_text(
                0, label_y, v["name"], size=3.5, weight="bold",
            ))
            dim_label = v.get("dim_label", "")
            if dim_label:
                view_group.append(self._svg_text(
                    0, label_y + 5, dim_label, size=2.0,
                ))
    def _render_view_dimensions(
        self, group: ET.Element, v: dict[str, Any], w: float, h: float
    ) -> None:
        """渲染视图的包围盒尺寸标注（显示真实模型尺寸）。"""
        hw = w / 2
        hh = h / 2
        offset = 8.0

        # 真实尺寸（如果有的话，否则用缩放后的尺寸）
        real_w = v.get("real_width", w)
        real_h = v.get("real_height", h)

        # 水平尺寸（宽度）- 底部
        y_dim = hh + offset
        group.append(self._svg_line(-hw, y_dim, hw, y_dim, LineType.THIN))
        group.append(self._svg_line(-hw, y_dim - 1.5, -hw, y_dim + 1.5, LineType.THIN))
        group.append(self._svg_line(hw, y_dim - 1.5, hw, y_dim + 1.5, LineType.THIN))
        group.append(self._svg_text(0, y_dim - 1.5, f"{real_w:.0f}", size=2.5))

        # 垂直尺寸（高度）- 右侧
        x_dim = hw + offset
        group.append(self._svg_line(x_dim, -hh, x_dim, hh, LineType.THIN))
        group.append(self._svg_line(x_dim - 1.5, -hh, x_dim + 1.5, -hh, LineType.THIN))
        group.append(self._svg_line(x_dim - 1.5, hh, x_dim + 1.5, hh, LineType.THIN))
        txt = self._svg_text(x_dim + 2, 0, f"{real_h:.0f}", size=2.5, anchor="start")
        txt.set("transform", f"rotate(-90,{x_dim + 2:.3f},0)")
        group.append(txt)

    # ── STEP 投影集成 ────────────────────────────────────────

    def project_views_from_step(
        self,
        projector: StepProjector,
        views: list[str] | None = None,
        scale_factor: float = 0.0,
    ) -> None:
        """从 STEP 投影器加载视图并自动布局。

        Args:
            projector: StepProjector 实例（已加载 STEP 文件）
            views: 视图名称列表，默认 ["front", "top", "left", "iso"]
            scale_factor: 缩放因子（0 = 自动计算以适配图幅）
        """
        if views is None:
            views = ["front", "top", "left", "iso"]

        # 获取所有投影边和尺寸（使用并行投影加速）
        view_data: list[dict[str, Any]] = []

        # 尝试并行投影（多线程）
        try:
            parallel_results = projector.project_parallel(views)
        except Exception:
            parallel_results = None

        for view_name in views:
            if parallel_results and view_name in parallel_results:
                edges = parallel_results[view_name]
            else:
                edges = projector.project_with_visibility(view_name)
            bounds = projector.project_bounds(edges)
            w = bounds[2] - bounds[0]
            h = bounds[3] - bounds[1]
            # 归一化边线到视图中心
            cx_3d = (bounds[0] + bounds[2]) / 2
            cy_3d = (bounds[1] + bounds[3]) / 2
            normalized = []
            for e in edges:
                normalized.append(Edge2D(
                    x1=e.x1 - cx_3d, y1=e.y1 - cy_3d,
                    x2=e.x2 - cx_3d, y2=e.y2 - cy_3d,
                    hidden=getattr(e, "hidden", False),
                    adjacent=getattr(e, "adjacent", False),
                ))

            # Detect circles
            circles = projector.detect_circles(view_name, min_radius=10.0, max_radius=300.0, tolerance=3.0)
            normalized_circles = []
            for c in circles:
                from fc_core.step_projector import Circle2D
                normalized_circles.append(Circle2D(
                    cx=c.cx - cx_3d,
                    cy=c.cy - cy_3d,
                    radius=c.radius,
                    hidden=c.hidden,
                ))

            view_data.append({
                "name": view_name,
                "edges": normalized,
                "circles": normalized_circles,
                "width": w,
                "height": h,
            })

        if not view_data:
            return

        # 自动缩放
        if scale_factor <= 0:
            da = self.drawing_area
            # 4 视图布局：2x2 网格
            # 上排：主视图 + 俯视图
            # 下排：左视图 + 轴测图
            max_w = max(v["width"] for v in view_data)
            max_h = max(v["height"] for v in view_data)
            avail_w = (da["w"] - 80) / 2  # 两列，留间距
            avail_h = (da["h"] - 100) / 2  # 两行
            scale_factor = min(avail_w / max_w, avail_h / max_h) if max_w > 0 and max_h > 0 else 0.1

        # 2x2 布局
        da = self.drawing_area
        col_w = da["w"] / 2
        row_h = (da["h"] - 56) / 2  # 减去标题栏高度

        positions = [
            (da["x"] + col_w * 0.5, da["y"] + row_h * 0.5),       # 主视图：左上
            (da["x"] + col_w * 1.5, da["y"] + row_h * 0.5),       # 俯视图：右上
            (da["x"] + col_w * 0.5, da["y"] + row_h * 1.5),       # 左视图：左下
            (da["x"] + col_w * 1.5, da["y"] + row_h * 1.5),       # 轴测图：右下
        ]

        bb = projector.bound_box
        view_labels = {
            "front": f"{bb.width:.0f} x {bb.height:.0f} mm (宽 x 高)",
            "top": f"{bb.width:.0f} x {bb.depth:.0f} mm (宽 x 深)",
            "left": f"{bb.depth:.0f} x {bb.height:.0f} mm (深 x 高)",
            "iso": "Isometric Projection",
        }

        view_name_cn = {
            "front": "主视图", "top": "俯视图",
            "left": "左视图", "iso": "轴测图",
        }

        for i, vd in enumerate(view_data):
            if i >= len(positions):
                break
            cx, cy = positions[i]
            sw = vd["width"] * scale_factor
            sh = vd["height"] * scale_factor

            # 缩放边线（保留 hidden 属性）
            scaled_edges = []
            for e in vd["edges"]:
                scaled_edges.append(Edge2D(
                    x1=e.x1 * scale_factor, y1=-e.y1 * scale_factor,
                    x2=e.x2 * scale_factor, y2=-e.y2 * scale_factor,
                    hidden=getattr(e, "hidden", False),
                    adjacent=getattr(e, "adjacent", False),
                ))

            # 缩放圆（用于中心线）
            from fc_core.step_projector import Circle2D
            scaled_circles = []
            for c in vd.get("circles", []):
                scaled_circles.append(Circle2D(
                    cx=c.cx * scale_factor,
                    cy=-c.cy * scale_factor,
                    radius=c.radius * scale_factor,
                    hidden=c.hidden,
                ))

            cn_name = view_name_cn.get(vd["name"], vd["name"])
            dim_label = view_labels.get(vd["name"], "")

            self.add_view(
                name=cn_name,
                edges=scaled_edges,
                center_x=cx,
                center_y=cy,
                width=sw,
                height=sh,
            )
            # 存储缩放后的圆用于中心线渲染
            if self.views:
                self.views[-1]["circles"] = scaled_circles
            # 附加真实尺寸和标注信息
            if self.views:
                self.views[-1]["show_dimensions"] = True
                self.views[-1]["dim_label"] = dim_label
                self.views[-1]["scale"] = scale_factor
                # Use 3D bounding box real dimensions for annotation
                if vd["name"] == "front":
                    self.views[-1]["real_width"] = bb.width
                    self.views[-1]["real_height"] = bb.height
                elif vd["name"] == "top":
                    self.views[-1]["real_width"] = bb.width
                    self.views[-1]["real_height"] = bb.depth
                elif vd["name"] == "left":
                    self.views[-1]["real_width"] = bb.depth
                    self.views[-1]["real_height"] = bb.height
                elif vd["name"] == "iso":
                    self.views[-1]["real_width"] = bb.width
                    self.views[-1]["real_height"] = bb.height
                else:
                    self.views[-1]["real_width"] = vd["width"]
                    self.views[-1]["real_height"] = vd["height"]

        # 自动布置球标（主视图左侧）
        if self.bom and self.views:
            main_view = self.views[0]
            self.add_auto_balloons(
                view_center_x=main_view["center_x"],
                view_center_y=main_view["center_y"],
                view_width=main_view["width"],
                view_height=main_view["height"],
                layout="left",
            )

        # 设置比例
        if scale_factor > 0:
            ratio = 1.0 / scale_factor
            self.set_title_block(scale=f"1:{ratio:.0f}")

    # ── 主生成方法 ──────────────────────────────────────────

    def generate_svg(self) -> str:
        """生成完整的标准装配图 SVG。"""
        root = ET.Element("svg")
        root.set("xmlns", "http://www.w3.org/2000/svg")
        root.set("width", f"{self.page_w}mm")
        root.set("height", f"{self.page_h}mm")
        root.set("viewBox", f"0 0 {self.page_w} {self.page_h}")
        root.set("style", "background-color:white;")

        # 1. 图框
        self._render_frame(root)

        # 2. 投影视图
        self._render_views(root)

        # 3. 球标
        self._render_balloons(root)

        # 4. 标题栏（右下角）
        self._render_title_block(root)

        # 5. 明细表（标题栏上方）
        self._render_bom_table(root)

        # 6. 技术要求
        self._render_tech_requirements(root)

        return ET.tostring(root, encoding="unicode")

    def save(self, path: str) -> None:
        """保存 SVG 到文件。"""
        svg = self.generate_svg()
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)

    def add_auto_balloons(
        self,
        view_center_x: float, view_center_y: float,
        view_width: float, view_height: float,
        layout: str = "left",
    ) -> None:
        """Auto-layout balloons with collision detection.

        Uses a greedy algorithm:
        1. Generate candidate positions with uniform spacing
        2. Detect balloon overlaps
        3. Auto-adjust positions to resolve collisions
        """
        if not self.bom:
            return
        items = self.bom.items
        n = len(items)
        if n == 0:
            return

        r = 5.0
        min_spacing = r * 3 + 2

        candidates = self._compute_balloon_positions(
            view_center_x, view_center_y, view_width, view_height,
            n, r, min_spacing, layout,
        )
        positions = self._resolve_balloon_collisions(
            candidates, r, min_spacing, layout,
        )

        for i, (bx, by, lx, ly) in enumerate(positions):
            if i < len(items):
                self.add_balloon(
                    item_no=items[i].item_no,
                    x=bx, y=by,
                    leader_x=lx, leader_y=ly,
                    radius=r,
                )

    def _compute_balloon_positions(
        self, cx, cy, vw, vh, n, r, min_spacing, layout,
    ):
        """Generate candidate balloon positions."""
        positions = []
        if layout in ("left", "right"):
            spacing = max(min_spacing, (vh + 40) / n)
            total_h = (n - 1) * spacing
            start_y = cy - total_h / 2
            for i in range(n):
                by = start_y + i * spacing
                if layout == "left":
                    bx = cx - vw / 2 - 20
                    lx = cx - vw / 2 + 5
                else:
                    bx = cx + vw / 2 + 20
                    lx = cx + vw / 2 - 5
                positions.append((bx, by, lx, by))
        else:
            spacing = max(min_spacing, (vw + 40) / n)
            total_w = (n - 1) * spacing
            start_x = cx - total_w / 2
            for i in range(n):
                bx = start_x + i * spacing
                if layout == "top":
                    by = cy + vh / 2 + 15
                    ly = cy + vh / 2 - 5
                else:
                    by = cy - vh / 2 - 15
                    ly = cy - vh / 2 + 5
                positions.append((bx, by, bx, ly))
        return positions

    def _resolve_balloon_collisions(self, candidates, r, min_spacing, layout):
        """Detect and resolve balloon collisions via iterative push-apart."""
        import math
        positions = [list(p) for p in candidates]
        n = len(positions)
        if n <= 1:
            return [tuple(p) for p in positions]
        for _ in range(50):
            moved = False
            for i in range(n):
                for j in range(i + 1, n):
                    dx = positions[j][0] - positions[i][0]
                    dy = positions[j][1] - positions[i][1]
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist < min_spacing and dist > 0:
                        overlap = min_spacing - dist
                        px = (dx / dist) * overlap * 0.5
                        py = (dy / dist) * overlap * 0.5
                        if layout in ("left", "right"):
                            py *= 1.5
                        else:
                            px *= 1.5
                        positions[i][0] -= px
                        positions[i][1] -= py
                        positions[j][0] += px
                        positions[j][1] += py
                        moved = True
                    elif dist < 0.001:
                        offset = min_spacing / 2
                        if layout in ("left", "right"):
                            positions[i][1] -= offset
                            positions[j][1] += offset
                        else:
                            positions[i][0] -= offset
                            positions[j][0] += offset
                        moved = True
            if not moved:
                break
        return [tuple(p) for p in positions]
