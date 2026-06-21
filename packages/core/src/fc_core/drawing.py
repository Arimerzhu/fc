"""工程图 SVG 生成器。

不依赖 FreeCAD TechDraw，基于 Part.Shape 的几何数据（顶点、边、边界框）
纯 Python 实现三视图投影、尺寸标注、标题栏等功能。
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any
from xml.etree import ElementTree as ET

PAGE_SIZES: dict[str, tuple[float, float]] = {
    "A4": (210.0, 297.0),
    "A3": (297.0, 420.0),
    "A2": (420.0, 594.0),
    "A1": (594.0, 841.0),
    "A0": (841.0, 1189.0),
}


@dataclass(frozen=True)
class Vector3:
    """三维向量，用于几何计算。"""

    x: float
    y: float
    z: float

    def __add__(self, other: Vector3) -> Vector3:
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vector3) -> Vector3:
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> Vector3:
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)

    def dot(self, other: Vector3) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vector3) -> Vector3:
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def normalize(self) -> Vector3:
        length = self.length()
        if length < 1e-12:
            return Vector3(0.0, 0.0, 0.0)
        return Vector3(self.x / length, self.y / length, self.z / length)

    def to_dict(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y, "z": self.z}

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> Vector3:
        return cls(data["x"], data["y"], data["z"])


@dataclass(frozen=True)
class BoundBox:
    """三维边界框。"""

    x_min: float
    y_min: float
    z_min: float
    x_max: float
    y_max: float
    z_max: float

    @property
    def width(self) -> float:
        return self.x_max - self.x_min

    @property
    def height(self) -> float:
        return self.y_max - self.y_min

    @property
    def depth(self) -> float:
        return self.z_max - self.z_min

    @property
    def center(self) -> Vector3:
        return Vector3(
            (self.x_min + self.x_max) / 2,
            (self.y_min + self.y_max) / 2,
            (self.z_min + self.z_max) / 2,
        )

    @property
    def diagonal(self) -> float:
        return math.sqrt(self.width ** 2 + self.height ** 2 + self.depth ** 2)

    def to_dict(self) -> dict[str, float]:
        return {
            "x_min": self.x_min,
            "y_min": self.y_min,
            "z_min": self.z_min,
            "x_max": self.x_max,
            "y_max": self.y_max,
            "z_max": self.z_max,
        }

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> BoundBox:
        return cls(
            data["x_min"],
            data["y_min"],
            data["z_min"],
            data["x_max"],
            data["y_max"],
            data["z_max"],
        )


@dataclass(frozen=True)
class Edge3D:
    """三维空间中的线段。"""

    p1: Vector3
    p2: Vector3

    def length(self) -> float:
        return (self.p2 - self.p1).length()

    def midpoint(self) -> Vector3:
        return Vector3(
            (self.p1.x + self.p2.x) / 2,
            (self.p1.y + self.p2.y) / 2,
            (self.p1.z + self.p2.z) / 2,
        )

    def to_dict(self) -> dict[str, dict[str, float]]:
        return {"p1": self.p1.to_dict(), "p2": self.p2.to_dict()}

    @classmethod
    def from_dict(cls, data: dict[str, dict[str, float]]) -> Edge3D:
        return cls(Vector3.from_dict(data["p1"]), Vector3.from_dict(data["p2"]))


@dataclass(frozen=True)
class Edge2D:
    """二维投影边。"""

    x1: float
    y1: float
    x2: float
    y2: float
    hidden: bool = False  # True if edge is hidden (back-facing/occluded)
    adjacent: bool = False  # True if edge belongs to adjacent part contour

    def length(self) -> float:
        return math.sqrt((self.x2 - self.x1) ** 2 + (self.y2 - self.y1) ** 2)

    def midpoint(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)


@dataclass
class ShapeData:
    """从 Part.Shape 提取的几何数据抽象。

    这样不依赖 FreeCAD 也可以用于测试。
    """

    edges: list[Edge3D]
    vertices: list[Vector3]
    bound_box: BoundBox

    @classmethod
    def from_part_shape(cls, shape: Any) -> ShapeData:
        """从 FreeCAD Part.Shape 提取几何数据。"""
        bb = shape.BoundBox
        bound_box = BoundBox(bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)

        vertices: list[Vector3] = []
        edges: list[Edge3D] = []

        for edge in shape.Edges:
            curve = edge.Curve
            p1 = edge.Vertexes[0].Point
            p2 = edge.Vertexes[-1].Point
            v1 = Vector3(p1.x, p1.y, p1.z)
            v2 = Vector3(p2.x, p2.y, p2.z)

            # 处理线段
            if curve.TypeId == "Part::GeomLine":
                edges.append(Edge3D(v1, v2))
            # 对于复杂曲线，采样为多段线段
            else:
                points = edge.discretize(20)
                for i in range(len(points) - 1):
                    a = Vector3(points[i].x, points[i].y, points[i].z)
                    b = Vector3(points[i + 1].x, points[i + 1].y, points[i + 1].z)
                    edges.append(Edge3D(a, b))

            for v in edge.Vertexes:
                vertices.append(Vector3(v.Point.x, v.Point.y, v.Point.z))

        return cls(edges=edges, vertices=vertices, bound_box=bound_box)

    def to_dict(self) -> dict[str, Any]:
        return {
            "edges": [e.to_dict() for e in self.edges],
            "vertices": [v.to_dict() for v in self.vertices],
            "bound_box": self.bound_box.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ShapeData:
        return cls(
            edges=[Edge3D.from_dict(e) for e in data["edges"]],
            vertices=[Vector3.from_dict(v) for v in data["vertices"]],
            bound_box=BoundBox.from_dict(data["bound_box"]),
        )

    def save_json(self, path: str) -> None:
        """将几何数据保存为 JSON 文件。"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_json(cls, path: str) -> ShapeData:
        """从 JSON 文件加载几何数据。"""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)


class EngineeringDrawingSVG:
    """工程图 SVG 生成器。

    支持：
    - 三视图投影（front/top/side）
    - 尺寸标注（线性、直径、半径）
    - 标题栏（GB/T 样式）
    - 不依赖 FreeCAD TechDraw

    Example:
        shape_data = ShapeData(...)  # 或从 Part.Shape 提取
        drawing = EngineeringDrawingSVG(shape_data, scale=0.4, page_size="A3")
        drawing.add_view("front", direction=(0, -1, 0), x=50, y=100)
        drawing.add_view("top", direction=(0, 0, -1), x=50, y=250)
        drawing.add_dimension("linear", (0, 0, 0), (100, 0, 0), "100", offset=20)
        drawing.add_title_block("DBY250箱体", scale="1:2.5", material="HT200")
        drawing.save("drawing.svg")
    """

    def __init__(
        self,
        shape: ShapeData | Any,
        scale: float = 0.4,
        page_size: str = "A3",
        title: str | None = None,
    ):
        if isinstance(shape, ShapeData):
            self._shape = shape
        else:
            # 假设是 FreeCAD Part.Shape
            self._shape = ShapeData.from_part_shape(shape)

        self._scale = scale
        self._page_size = page_size.upper()
        self._title = title
        self._views: list[dict[str, Any]] = []
        self._dimensions: list[dict[str, Any]] = []
        self._symbols: list[dict[str, Any]] = []
        self._title_block_info: dict[str, str] = {}

        if self._page_size not in PAGE_SIZES:
            raise ValueError(f"不支持的图幅: {page_size}")

        self._page_w, self._page_h = PAGE_SIZES[self._page_size]

    @property
    def page_size(self) -> tuple[float, float]:
        """返回图纸尺寸 (width, height)，单位 mm。"""
        return (self._page_w, self._page_h)

    def add_view(
        self,
        name: str,
        direction: tuple[float, float, float],
        x: float,
        y: float,
    ) -> EngineeringDrawingSVG:
        """添加一个投影视图。

        Args:
            name: 视图名称（front/top/side 等）
            direction: 观察方向（从该方向看向原点）
            x: 视图左下角在图纸上的 x 坐标（mm）
            y: 视图左下角在图纸上的 y 坐标（mm）
        """
        self._views.append({
            "name": name,
            "direction": Vector3(*direction),
            "x": x,
            "y": y,
        })
        return self

    def add_dimension(
        self,
        dim_type: str,
        p1: tuple[float, float, float],
        p2: tuple[float, float, float],
        label: str,
        position: tuple[float, float] | None = None,
        offset: float = 8.0,
        p3: tuple[float, float, float] | None = None,
    ) -> EngineeringDrawingSVG:
        """添加尺寸标注。

        Args:
            dim_type: "linear", "diameter", "radius", "angle"
            p1: 第一点（3D）
            p2: 第二点（3D）
            label: 标注文字
            position: 标注文字位置（2D 图纸坐标），None 则自动计算
            offset: 尺寸线偏离被测点的距离（仅用于线性标注）
            p3: 角度标注的第三点（3D），仅在 dim_type="angle" 时使用
        """
        dim: dict[str, Any] = {
            "type": dim_type,
            "p1": Vector3(*p1),
            "p2": Vector3(*p2),
            "label": label,
            "position": position,
            "offset": offset,
        }
        if p3 is not None:
            dim["p3"] = Vector3(*p3)
        self._dimensions.append(dim)
        return self

    def add_title_block(
        self,
        title: str,
        scale: str,
        material: str = "",
        weight: str = "",
        drawn_by: str = "AI",
        unit: str = "",
        drawing_no: str = "",
        version: str = "",
        date: str = "",
        quantity: str = "",
        checked_by: str = "",
    ) -> EngineeringDrawingSVG:
        """添加 GB/T 样式标题栏信息。"""
        self._title_block_info = {
            "title": title,
            "scale": scale,
            "material": material,
            "weight": weight,
            "drawn_by": drawn_by,
            "unit": unit,
            "drawing_no": drawing_no,
            "version": version,
            "date": date,
            "quantity": quantity,
            "checked_by": checked_by,
        }
        return self

    def add_surface_roughness(
        self,
        point: tuple[float, float, float],
        value: str,
        position: tuple[float, float],
        method: str = "",
    ) -> EngineeringDrawingSVG:
        """添加表面粗糙度符号（GB/T 131 基本图形）。

        Args:
            point: 3D 附着点
            value: Ra 值，如 "3.2"
            position: 符号左下角在图纸上的 2D 坐标（mm）
            method: 加工方法说明（可选）
        """
        self._symbols.append({
            "type": "surface_roughness",
            "point": Vector3(*point),
            "value": value,
            "position": position,
            "method": method,
        })
        return self

    def add_geometric_tolerance(
        self,
        symbol: str,
        tolerance: str,
        datum: str,
        position: tuple[float, float],
        leader_point: tuple[float, float, float] | None = None,
    ) -> EngineeringDrawingSVG:
        """添加形位公差框格。

        Args:
            symbol: 公差特征符号，如 "⊥"（垂直度）、"∥"（平行度）、"◎"（同轴度）
            tolerance: 公差值，如 "0.05" 或 "φ0.1"
            datum: 基准字母，如 "A"
            position: 框格左上角在图纸上的 2D 坐标（mm）
            leader_point: 3D 附着点（可选）
        """
        item: dict[str, Any] = {
            "type": "geometric_tolerance",
            "symbol": symbol,
            "tolerance": tolerance,
            "datum": datum,
            "position": position,
        }
        if leader_point is not None:
            item["leader_point"] = Vector3(*leader_point)
        self._symbols.append(item)
        return self

    def add_weld_symbol(
        self,
        symbol: str,
        position: tuple[float, float],
        side: str = "both",
        leader_point: tuple[float, float, float] | None = None,
    ) -> EngineeringDrawingSVG:
        """添加焊接符号。

        Args:
            symbol: 焊缝类型，如 "V"、"Y"、"角焊"
            position: 参考线左端在图纸上的 2D 坐标（mm）
            side: "both"（箭头侧和其他侧都焊）、"arrow"（仅箭头侧）、"other"（仅其他侧）
            leader_point: 3D 附着点（可选）
        """
        item: dict[str, Any] = {
            "type": "weld_symbol",
            "symbol": symbol,
            "position": position,
            "side": side,
        }
        if leader_point is not None:
            item["leader_point"] = Vector3(*leader_point)
        self._symbols.append(item)
        return self

    def _build_projection_matrix(self, direction: Vector3) -> tuple[Vector3, Vector3]:
        """根据观察方向构建投影坐标系的 X/Y 基向量。

        返回 (u, v)，其中投影点 p' = (p·u, p·v)。
        """
        # 观察方向归一化（朝向观察者）
        n = direction.normalize()

        # 选择 up 向量：优先使用世界 Z 轴，若与 n 平行则使用 Y 轴
        world_up = Vector3(0.0, 0.0, 1.0)
        if abs(n.dot(world_up)) > 0.99:
            world_up = Vector3(0.0, 1.0, 0.0)

        # u = up × n（水平向右）
        u = world_up.cross(n).normalize()
        # v = n × u（垂直向上）
        v = n.cross(u).normalize()

        return u, v

    def _project_point(self, point: Vector3, u: Vector3, v: Vector3) -> tuple[float, float]:
        """将 3D 点投影到 2D 平面。"""
        return (point.x * u.x + point.y * u.y + point.z * u.z,
                point.x * v.x + point.y * v.y + point.z * v.z)

    def _project_edge(self, edge: Edge3D, u: Vector3, v: Vector3) -> Edge2D:
        """将 3D 边投影到 2D 平面。"""
        px1, py1 = self._project_point(edge.p1, u, v)
        px2, py2 = self._project_point(edge.p2, u, v)
        return Edge2D(px1, py1, px2, py2)

    def _svg_line(self, x1: float, y1: float, x2: float, y2: float,
                  stroke: str = "black", width: float = 0.35,
                  attrs: dict[str, str] | None = None) -> ET.Element:
        """创建 SVG 线段元素。"""
        line = ET.Element("line")
        line.set("x1", f"{x1:.3f}")
        line.set("y1", f"{y1:.3f}")
        line.set("x2", f"{x2:.3f}")
        line.set("y2", f"{y2:.3f}")
        line.set("stroke", stroke)
        line.set("stroke-width", f"{width:.3f}")
        line.set("stroke-linecap", "round")
        if attrs:
            for k, v in attrs.items():
                line.set(k, v)
        return line

    def _svg_text(self, x: float, y: float, text: str, size: float = 3.5,
                  anchor: str = "middle", attrs: dict[str, str] | None = None) -> ET.Element:
        """创建 SVG 文字元素。"""
        element = ET.Element("text")
        element.set("x", f"{x:.3f}")
        element.set("y", f"{y:.3f}")
        element.set("font-size", f"{size:.2f}")
        element.set("font-family", "monospace")
        element.set("text-anchor", anchor)
        element.set("fill", "black")
        if attrs:
            for k, v in attrs.items():
                element.set(k, v)
        element.text = text
        return element

    def _svg_arrow(self, x: float, y: float, direction: float,
                   size: float = 2.0, width: float = 0.25) -> ET.Element:
        """创建 SVG 箭头（V 形）。

        Args:
            x, y: 箭头尖端位置
            direction: 箭头指向角度（弧度，0 指向右）
            size: 箭头长度
            width: 箭头开口宽度的一半
        """
        group = ET.Element("g")
        group.set("class", "arrow-head")

        # 两条短线形成 V 形
        dx = math.cos(direction) * size
        dy = math.sin(direction) * size
        wx = -math.sin(direction) * width
        wy = math.cos(direction) * width

        group.append(self._svg_line(x, y, x - dx + wx, y - dy + wy, width=0.25))
        group.append(self._svg_line(x, y, x - dx - wx, y - dy - wy, width=0.25))
        return group

    def _project_to_front(self, point: Vector3) -> tuple[float, float]:
        """将 3D 点投影到 front 视图（Y 轴朝里，Z 轴朝上）。"""
        u, v = self._build_projection_matrix(Vector3(0.0, -1.0, 0.0))
        return self._project_point(point, u, v)

    def _perpendicular_2d(self, dx: float, dy: float) -> tuple[float, float]:
        """返回 2D 向量的单位垂直向量（逆时针旋转 90 度）。"""
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1e-12:
            return (0.0, 0.0)
        return (-dy / length, dx / length)

    def _render_view(self, view: dict[str, Any], root: ET.Element) -> None:
        """渲染单个视图。"""
        direction = view["direction"]
        origin_x = view["x"]
        origin_y = view["y"]

        u, v = self._build_projection_matrix(direction)

        # 计算所有投影边的边界框，用于居中
        projected_edges: list[Edge2D] = []
        for edge in self._shape.edges:
            pe = self._project_edge(edge, u, v)
            projected_edges.append(pe)

        if not projected_edges:
            return

        x_min = min(min(e.x1, e.x2) for e in projected_edges)
        x_max = max(max(e.x1, e.x2) for e in projected_edges)
        y_min = min(min(e.y1, e.y2) for e in projected_edges)
        y_max = max(max(e.y1, e.y2) for e in projected_edges)

        view_center_x = (x_min + x_max) / 2
        view_center_y = (y_min + y_max) / 2

        # 绘制视图名称
        group = ET.SubElement(root, "g")
        group.set("class", f"view-{view['name']}")

        for pe in projected_edges:
            # 投影坐标 -> 图纸坐标（SVG 中 y 向下，需要翻转）
            sx = origin_x + (pe.x1 - view_center_x) * self._scale
            sy = origin_y - (pe.y1 - view_center_y) * self._scale
            ex = origin_x + (pe.x2 - view_center_x) * self._scale
            ey = origin_y - (pe.y2 - view_center_y) * self._scale
            group.append(self._svg_line(sx, sy, ex, ey))

        # 视图名称标签
        label_y = origin_y + (y_max - view_center_y) * self._scale + 7
        group.append(self._svg_text(origin_x, label_y, view["name"],
                                    size=3.5, anchor="middle"))

    def _render_dimensions(self, root: ET.Element) -> None:
        """渲染所有尺寸标注。"""
        for dim in self._dimensions:
            dim_type = dim["type"]
            group = ET.SubElement(root, "g")
            group.set("class", f"dimension-{dim_type}")

            if dim_type == "linear":
                self._render_linear_dimension(group, dim)
            elif dim_type == "diameter":
                self._render_diameter_dimension(group, dim)
            elif dim_type == "radius":
                self._render_radius_dimension(group, dim)
            elif dim_type == "angle":
                self._render_angle_dimension(group, dim)
            else:
                # 未知类型按线性处理
                self._render_linear_dimension(group, dim)

    def _render_linear_dimension(self, group: ET.Element, dim: dict[str, Any]) -> None:
        """渲染线性尺寸标注。"""
        x1, y1 = self._project_to_front(dim["p1"])
        x2, y2 = self._project_to_front(dim["p2"])
        offset = dim["offset"]
        label = dim["label"]
        position = dim["position"]

        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx * dx + dy * dy)

        # 尺寸线偏离方向（垂直于测量线，取一侧）
        px, py = self._perpendicular_2d(dx, dy)

        # 尺寸线端点
        sx1 = x1 + px * offset
        sy1 = y1 + py * offset
        sx2 = x2 + px * offset
        sy2 = y2 + py * offset

        # 引线：从被测点连接到尺寸线端点
        group.append(self._svg_line(x1, y1, sx1, sy1, stroke="black", width=0.18))
        group.append(self._svg_line(x2, y2, sx2, sy2, stroke="black", width=0.18))

        # 尺寸线
        group.append(self._svg_line(sx1, sy1, sx2, sy2, stroke="black", width=0.25))

        # 箭头方向：指向尺寸线中点
        if length > 1e-9:
            angle = math.atan2(dy, dx)
            group.append(self._svg_arrow(sx1, sy1, angle))
            group.append(self._svg_arrow(sx2, sy2, angle + math.pi))

        # 文字位置
        if position is None:
            tx, ty = (sx1 + sx2) / 2, (sy1 + sy2) / 2 - 2.5
        else:
            tx, ty = position

        # 打断尺寸线放置文字（简单实现：白色背景矩形遮罩）
        text_elem = self._svg_text(tx, ty, label, size=2.5, anchor="middle")
        group.append(text_elem)

    def _render_diameter_dimension(self, group: ET.Element, dim: dict[str, Any]) -> None:
        """渲染直径尺寸标注。"""
        cx, cy = self._project_to_front(dim["p1"])
        ex, ey = self._project_to_front(dim["p2"])
        label = dim["label"]
        position = dim["position"]

        dx = ex - cx
        dy = ey - cy
        radius = math.sqrt(dx * dx + dy * dy)

        # 尺寸线穿过圆心，沿直径方向，两端略超出圆
        if radius < 1e-9:
            return

        ux, uy = dx / radius, dy / radius
        margin = 2.0
        sx1, sy1 = cx - ux * (radius + margin), cy - uy * (radius + margin)
        sx2, sy2 = cx + ux * (radius + margin), cy + uy * (radius + margin)

        group.append(self._svg_line(sx1, sy1, sx2, sy2, stroke="black", width=0.25))

        angle = math.atan2(dy, dx)
        group.append(self._svg_arrow(sx1, sy1, angle))
        group.append(self._svg_arrow(sx2, sy2, angle + math.pi))

        if position is None:
            tx, ty = cx, cy - 3.0
        else:
            tx, ty = position

        text = f"φ{label}"
        group.append(self._svg_text(tx, ty, text, size=2.5, anchor="middle"))

    def _render_radius_dimension(self, group: ET.Element, dim: dict[str, Any]) -> None:
        """渲染半径尺寸标注。"""
        cx, cy = self._project_to_front(dim["p1"])
        ex, ey = self._project_to_front(dim["p2"])
        label = dim["label"]
        position = dim["position"]

        dx = ex - cx
        dy = ey - cy
        radius = math.sqrt(dx * dx + dy * dy)

        if radius < 1e-9:
            return

        # 引线从圆心到圆弧，箭头在圆弧端
        group.append(self._svg_line(cx, cy, ex, ey, stroke="black", width=0.25))

        angle = math.atan2(dy, dx)
        group.append(self._svg_arrow(ex, ey, angle))

        if position is None:
            tx, ty = (cx + ex) / 2, (cy + ey) / 2 - 2.5
        else:
            tx, ty = position

        text = f"R{label}"
        group.append(self._svg_text(tx, ty, text, size=2.5, anchor="middle"))

    def _render_angle_dimension(self, group: ET.Element, dim: dict[str, Any]) -> None:
        """渲染角度尺寸标注。"""
        ox, oy = self._project_to_front(dim["p1"])
        ax, ay = self._project_to_front(dim["p2"])
        bx, by = self._project_to_front(dim["p3"])
        label = dim["label"]
        position = dim["position"]

        angle_a = math.atan2(ay - oy, ax - ox)
        angle_b = math.atan2(by - oy, bx - ox)

        # 归一化到 [-pi, pi] 并计算小角
        diff = angle_b - angle_a
        while diff <= -math.pi:
            diff += 2 * math.pi
        while diff > math.pi:
            diff -= 2 * math.pi

        # 弧线半径：取两条边较短者的 0.6 倍
        ra = math.sqrt((ax - ox) ** 2 + (ay - oy) ** 2)
        rb = math.sqrt((bx - ox) ** 2 + (by - oy) ** 2)
        arc_r = min(ra, rb) * 0.6
        if arc_r < 1e-9:
            return

        start_angle = angle_a
        end_angle = angle_a + diff

        # SVG path 弧线
        x1 = ox + arc_r * math.cos(start_angle)
        y1 = oy + arc_r * math.sin(start_angle)
        x2 = ox + arc_r * math.cos(end_angle)
        y2 = oy + arc_r * math.sin(end_angle)
        large_arc = 1 if abs(diff) > math.pi else 0
        sweep = 1 if diff > 0 else 0

        path = ET.SubElement(group, "path")
        d_value = (
            f"M {x1:.3f} {y1:.3f} "
            f"A {arc_r:.3f} {arc_r:.3f} 0 {large_arc} {sweep} "
            f"{x2:.3f} {y2:.3f}"
        )
        path.set("d", d_value)
        path.set("fill", "none")
        path.set("stroke", "black")
        path.set("stroke-width", "0.25")

        # 两条短引线从顶点到弧线端点
        group.append(self._svg_line(ox, oy, x1, y1, stroke="black", width=0.18))
        group.append(self._svg_line(ox, oy, x2, y2, stroke="black", width=0.18))

        # 文字位置：弧线中点外侧
        if position is None:
            mid_angle = start_angle + diff / 2
            tx = ox + (arc_r + 4.0) * math.cos(mid_angle)
            ty = oy + (arc_r + 4.0) * math.sin(mid_angle) - 1.0
        else:
            tx, ty = position

        group.append(self._svg_text(tx, ty, label, size=2.5, anchor="middle"))

    def _render_symbols(self, root: ET.Element) -> None:
        """渲染所有工程符号。"""
        for symbol in self._symbols:
            sym_type = symbol["type"]
            group = ET.SubElement(root, "g")
            group.set("class", f"symbol-{sym_type}")

            if sym_type == "surface_roughness":
                self._render_surface_roughness(group, symbol)
            elif sym_type == "geometric_tolerance":
                self._render_geometric_tolerance(group, symbol)
            elif sym_type == "weld_symbol":
                self._render_weld_symbol(group, symbol)

    def _render_surface_roughness(self, group: ET.Element, symbol: dict[str, Any]) -> None:
        """渲染表面粗糙度符号。"""
        x, y = symbol["position"]
        value = symbol["value"]
        method = symbol.get("method", "")

        # 基本符号：底边 4mm，高 6mm 的等腰三角形 + 右侧水平线
        base_w = 4.0
        height = 6.0
        extension = 4.0

        # 三角形三个顶点
        px1, py1 = x, y
        px2, py2 = x + base_w, y
        apex_x, apex_y = x + base_w / 2, y - height

        group.append(self._svg_line(px1, py1, apex_x, apex_y, width=0.25))
        group.append(self._svg_line(px2, py2, apex_x, apex_y, width=0.25))
        group.append(self._svg_line(apex_x, apex_y, apex_x + extension, apex_y, width=0.25))

        # Ra 值放在符号右侧
        group.append(self._svg_text(x + base_w + extension + 1, apex_y + 1.5,
                                    f"Ra {value}", size=2.5, anchor="start"))

        if method:
            group.append(self._svg_text(x + base_w + extension + 1, y - 1,
                                        method, size=2.0, anchor="start"))

    def _render_geometric_tolerance(self, group: ET.Element, symbol: dict[str, Any]) -> None:
        """渲染形位公差框格。"""
        x, y = symbol["position"]
        sym = symbol["symbol"]
        tolerance = symbol["tolerance"]
        datum = symbol["datum"]
        leader_point = symbol.get("leader_point")

        cell_w = 6.0
        cell_h = 5.0
        cols = 3

        # 外框
        rect = ET.SubElement(group, "rect")
        rect.set("x", f"{x:.3f}")
        rect.set("y", f"{y:.3f}")
        rect.set("width", f"{cell_w * cols:.3f}")
        rect.set("height", f"{cell_h:.3f}")
        rect.set("fill", "none")
        rect.set("stroke", "black")
        rect.set("stroke-width", "0.25")

        # 分隔线
        for i in range(1, cols):
            sx = x + cell_w * i
            group.append(self._svg_line(sx, y, sx, y + cell_h, width=0.25))

        # 内容居中
        cy = y + cell_h / 2 + 1.0
        group.append(self._svg_text(x + cell_w / 2, cy, sym, size=3.0, anchor="middle"))
        group.append(self._svg_text(x + cell_w * 1.5, cy, tolerance, size=2.5, anchor="middle"))
        group.append(self._svg_text(x + cell_w * 2.5, cy, datum, size=2.5, anchor="middle"))

        # 引线
        if leader_point is not None:
            lx, ly = self._project_to_front(leader_point)
            group.append(self._svg_line(lx, ly, x, y + cell_h / 2, width=0.18))

    def _render_weld_symbol(self, group: ET.Element, symbol: dict[str, Any]) -> None:
        """渲染焊接符号。"""
        x, y = symbol["position"]
        sym = symbol["symbol"]
        side = symbol.get("side", "both")
        leader_point = symbol.get("leader_point")

        ref_len = 12.0
        arrow_len = 6.0

        # 参考线
        group.append(self._svg_line(x, y, x + ref_len, y, width=0.25))

        # 箭头向下
        ax = x
        ay_top = y - arrow_len
        group.append(self._svg_line(ax, ay_top, ax, y, width=0.25))
        group.append(self._svg_arrow(ax, y, math.pi / 2, size=2.0))

        # 焊缝符号：V 形或 Y 形放在参考线上方，角焊放在下方
        if sym in {"V", "Y"}:
            # V 形
            vx1, vy1 = x + ref_len / 2 - 2, y - 4
            vx2, vy2 = x + ref_len / 2, y - 1
            vx3, vy3 = x + ref_len / 2 + 2, y - 4
            group.append(self._svg_line(vx1, vy1, vx2, vy2, width=0.25))
            group.append(self._svg_line(vx3, vy3, vx2, vy2, width=0.25))
            if sym == "Y":
                group.append(self._svg_line(vx1, vy1, vx3, vy1, width=0.25))
        elif sym in {"角焊", "fillet"}:
            fx, fy = x + ref_len / 2 - 2, y + 1
            group.append(self._svg_line(fx, fy, fx, fy + 3, width=0.25))
            group.append(self._svg_line(fx, fy, fx + 3, fy, width=0.25))
            group.append(self._svg_line(fx, fy + 3, fx + 3, fy, width=0.25))

        # 根据 side 标记其他侧（简单用一个小三角表示）
        if side in {"both", "other"}:
            ox = x + ref_len / 2 - 1
            oy = y + 2
            group.append(self._svg_line(ox, oy, ox + 2, oy, width=0.25))
            group.append(self._svg_line(ox + 1, oy, ox + 1, oy + 2, width=0.25))

        if leader_point is not None:
            lx, ly = self._project_to_front(leader_point)
            group.append(self._svg_line(lx, ly, ax, ay_top, width=0.18))

    def _render_title_block_cell(
        self,
        group: ET.Element,
        x: float,
        y: float,
        w: float,
        h: float,
        label: str,
        value: str,
        value_size: float = 2.5,
    ) -> None:
        """绘制标题栏中的一个单元格。"""
        rect = ET.SubElement(group, "rect")
        rect.set("x", f"{x:.3f}")
        rect.set("y", f"{y:.3f}")
        rect.set("width", f"{w:.3f}")
        rect.set("height", f"{h:.3f}")
        rect.set("fill", "none")
        rect.set("stroke", "black")
        rect.set("stroke-width", "0.25")

        # 左上角标签小字
        group.append(self._svg_text(x + 1.5, y + 3.5, label,
                                    size=2.0, anchor="start"))
        # 中间值
        group.append(self._svg_text(x + w / 2, y + h / 2 + 1.5, value,
                                    size=value_size, anchor="middle"))

    def _render_title_block(self, root: ET.Element) -> None:
        """渲染 GB/T 样式标题栏（180mm × 56mm）。"""
        if not self._title_block_info:
            return

        tb_w = 180.0
        tb_h = 56.0
        x = self._page_w - tb_w - 10
        y = self._page_h - tb_h - 10

        group = ET.SubElement(root, "g")
        group.set("class", "title-block")

        row1_h = 28.0
        row2_h = 28.0

        # 第一行：单位名称 | 图样名称 | 设计 | 审核
        self._render_title_block_cell(
            group, x, y, 54.0, row1_h, "单位名称",
            self._title_block_info.get("unit", ""), value_size=3.0,
        )
        self._render_title_block_cell(
            group, x + 54.0, y, 66.0, row1_h, "图样名称",
            self._title_block_info.get("title", ""), value_size=4.0,
        )
        self._render_title_block_cell(
            group, x + 120.0, y, 30.0, row1_h, "设计",
            self._title_block_info.get("drawn_by", ""), value_size=2.5,
        )
        self._render_title_block_cell(
            group, x + 150.0, y, 30.0, row1_h, "审核",
            self._title_block_info.get("checked_by", ""), value_size=2.5,
        )

        # 第二行：材料 | 比例 | 重量 | 数量 | 图号 | 版本 | 日期
        row2_y = y + row1_h
        cells = [
            (36.0, "材料", "material"),
            (24.0, "比例", "scale"),
            (24.0, "重量", "weight"),
            (18.0, "数量", "quantity"),
            (42.0, "图号", "drawing_no"),
            (18.0, "版本", "version"),
            (18.0, "日期", "date"),
        ]
        cx = x
        for width, label, key in cells:
            self._render_title_block_cell(
                group, cx, row2_y, width, row2_h, label,
                self._title_block_info.get(key, ""), value_size=2.2,
            )
            cx += width

    def _render_frame(self, root: ET.Element) -> None:
        """渲染图框。"""
        margin = 10.0
        rect = ET.SubElement(root, "rect")
        rect.set("x", f"{margin:.3f}")
        rect.set("y", f"{margin:.3f}")
        rect.set("width", f"{self._page_w - 2 * margin:.3f}")
        rect.set("height", f"{self._page_h - 2 * margin:.3f}")
        rect.set("fill", "none")
        rect.set("stroke", "black")
        rect.set("stroke-width", "0.5")

    def to_string(self) -> str:
        """生成 SVG 字符串。"""
        root = ET.Element("svg")
        root.set("xmlns", "http://www.w3.org/2000/svg")
        root.set("width", f"{self._page_w}mm")
        root.set("height", f"{self._page_h}mm")
        root.set("viewBox", f"0 0 {self._page_w} {self._page_h}")

        self._render_frame(root)

        for view in self._views:
            self._render_view(view, root)

        self._render_dimensions(root)
        self._render_symbols(root)
        self._render_title_block(root)

        # 图纸标题
        if self._title:
            root.append(self._svg_text(self._page_w / 2, 20, self._title,
                                       size=5.0, anchor="middle"))

        return ET.tostring(root, encoding="unicode")

    def save(self, path: str) -> None:
        """保存 SVG 到文件。"""
        svg_string = self.to_string()
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg_string)
