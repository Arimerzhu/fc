"""装配图模块单元测试 — assembly_bom + assembly_drawing。

覆盖:
  - BOM 数据结构
  - STEP 文件解析
  - 装配图 SVG 生成
  - 球标 / 明细表 / 技术要求
  - DraftingAgent 集成
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


# ══════════════════════════════════════════════════════════════════
# assembly_bom 测试
# ══════════════════════════════════════════════════════════════════


class TestBOMItem:
    def test_basic_creation(self):
        from fc_core.assembly_bom import BOMItem
        item = BOMItem(item_no=1, name="机架", quantity=2, material="Q235")
        assert item.item_no == 1
        assert item.name == "机架"
        assert item.quantity == 2
        assert item.material == "Q235"

    def test_display_name_with_en(self):
        from fc_core.assembly_bom import BOMItem
        item = BOMItem(item_no=1, name="机架", name_en="Frame")
        assert item.display_name == "机架 (Frame)"

    def test_display_name_without_en(self):
        from fc_core.assembly_bom import BOMItem
        item = BOMItem(item_no=1, name="机架")
        assert item.display_name == "机架"

    def test_is_assembly_flag(self):
        from fc_core.assembly_bom import BOMItem
        item = BOMItem(item_no=1, name="减速器", is_assembly=True)
        assert item.is_assembly is True

    def test_default_values(self):
        from fc_core.assembly_bom import BOMItem
        item = BOMItem(item_no=1, name="test")
        assert item.quantity == 1
        assert item.material == ""
        assert item.mass_kg == 0.0
        assert item.children == []


class TestBOMTable:
    def test_empty_table(self):
        from fc_core.assembly_bom import BOMTable
        bom = BOMTable()
        assert bom.total_items == 0
        assert bom.total_parts == 0
        assert bom.total_mass_kg == 0.0

    def test_add_item(self):
        from fc_core.assembly_bom import BOMTable
        bom = BOMTable()
        item = bom.add_item(name="机架", quantity=2)
        assert item.item_no == 1
        assert bom.total_items == 1
        assert bom.total_parts == 2

    def test_auto_numbering(self):
        from fc_core.assembly_bom import BOMTable
        bom = BOMTable()
        bom.add_item(name="A")
        bom.add_item(name="B")
        bom.add_item(name="C")
        assert bom.items[0].item_no == 1
        assert bom.items[1].item_no == 2
        assert bom.items[2].item_no == 3

    def test_get_item(self):
        from fc_core.assembly_bom import BOMTable
        bom = BOMTable()
        bom.add_item(name="机架")
        bom.add_item(name="螺栓")
        item = bom.get_item(2)
        assert item is not None
        assert item.name == "螺栓"

    def test_get_item_not_found(self):
        from fc_core.assembly_bom import BOMTable
        bom = BOMTable()
        assert bom.get_item(99) is None

    def test_total_mass(self):
        from fc_core.assembly_bom import BOMTable
        bom = BOMTable()
        bom.add_item(name="A", quantity=2, mass_kg=5.0)
        bom.add_item(name="B", quantity=3, mass_kg=1.5)
        assert bom.total_mass_kg == pytest.approx(14.5)

    def test_sort_by_item_no(self):
        from fc_core.assembly_bom import BOMTable, BOMItem
        bom = BOMTable()
        bom.items = [
            BOMItem(item_no=3, name="C"),
            BOMItem(item_no=1, name="A"),
            BOMItem(item_no=2, name="B"),
        ]
        bom.sort_by_item_no()
        assert [i.item_no for i in bom.items] == [1, 2, 3]


class TestMakeSampleBOM:
    def test_sample_bom_has_items(self):
        from fc_core.assembly_bom import make_sample_bom
        bom = make_sample_bom()
        assert bom.total_items == 12
        assert bom.total_parts == 39

    def test_sample_bom_title(self):
        from fc_core.assembly_bom import make_sample_bom
        bom = make_sample_bom()
        assert bom.title == "进纸机构装配图"
        assert bom.assembly_name == "进纸机构"

    def test_sample_bom_materials(self):
        from fc_core.assembly_bom import make_sample_bom
        bom = make_sample_bom()
        materials = {item.material for item in bom.items}
        assert "Q235" in materials
        assert "标准件" in materials


class TestMakeBOMFromList:
    def test_from_list(self):
        from fc_core.assembly_bom import make_bom_from_list
        parts = [
            {"name": "A", "quantity": 1},
            {"name": "B", "quantity": 2, "material": "steel"},
        ]
        bom = make_bom_from_list(parts)
        assert bom.total_items == 2
        assert bom.items[1].material == "steel"


class TestDecodeStepString:
    def test_plain_text(self):
        from fc_core.assembly_bom import decode_step_string
        assert decode_step_string("hello") == "hello"

    def test_unicode_decode(self):
        from fc_core.assembly_bom import decode_step_string
        # \X2\9f7f\X0\ = 齿
        result = decode_step_string("\\X2\\9f7f\\X0\\")
        assert result == "齿"

    def test_mixed_text(self):
        from fc_core.assembly_bom import decode_step_string
        result = decode_step_string("MQ-G-\\X2\\9f7f6761\\X0\\")
        assert "齿" in result
        assert "MQ-G-" in result

    def test_multiple_sequences(self):
        from fc_core.assembly_bom import decode_step_string
        result = decode_step_string(
            "\\X2\\8f935165\\X0\\GB\\X2\\8f74\\X0\\"
        )
        assert "GB" in result


class TestParseStepBOM:
    def test_parse_real_step(self):
        from fc_core.assembly_bom import parse_step_bom
        step_path = Path(r"D:\桌面文件\fc\工程图输出\进纸机构模拟.STEP")
        if not step_path.exists():
            pytest.skip("STEP file not available")
        bom = parse_step_bom(str(step_path))
        assert bom.total_items > 100
        assert bom.total_parts > 500
        assert bom.assembly_name != ""

    def test_parse_nonexistent_file(self):
        from fc_core.assembly_bom import parse_step_bom
        with pytest.raises(FileNotFoundError):
            parse_step_bom("/nonexistent/file.STEP")


# ══════════════════════════════════════════════════════════════════
# assembly_drawing 测试
# ══════════════════════════════════════════════════════════════════


class TestLineType:
    def test_visible(self):
        from fc_core.assembly_drawing import LineType
        assert LineType.VISIBLE["stroke"] == "black"
        assert LineType.VISIBLE["stroke-width"] == "0.5"

    def test_hidden_has_dash(self):
        from fc_core.assembly_drawing import LineType
        assert "stroke-dasharray" in LineType.HIDDEN

    def test_center_has_dash(self):
        from fc_core.assembly_drawing import LineType
        assert "stroke-dasharray" in LineType.CENTER

    def test_phantom(self):
        from fc_core.assembly_drawing import LineType
        assert "stroke-dasharray" in LineType.PHANTOM


class TestBalloon:
    def test_basic_balloon(self):
        from fc_core.assembly_drawing import Balloon
        b = Balloon(item_no=1, x=100, y=200)
        assert b.item_no == 1
        assert b.x == 100
        assert b.y == 200
        assert b.radius == 5.0

    def test_balloon_with_leader(self):
        from fc_core.assembly_drawing import Balloon
        b = Balloon(item_no=2, x=50, y=80, leader_x=70, leader_y=90)
        assert b.leader_x == 70
        assert b.leader_y == 90


class TestAssemblyDrawing:
    def test_creation_a3(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        ad = AssemblyDrawing("A3", title="Test")
        assert ad.page_w > 0
        assert ad.page_h > 0
        assert ad.title == "Test"

    def test_creation_a0(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        ad = AssemblyDrawing("A0")
        assert ad.page_w == 1189.0
        assert ad.page_h == 841.0

    def test_margins(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        ad = AssemblyDrawing("A3")
        assert ad.margins["left"] == 25  # GB binding margin

    def test_set_bom(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        from fc_core.assembly_bom import make_sample_bom
        ad = AssemblyDrawing("A3")
        bom = make_sample_bom()
        ad.set_bom(bom)
        assert ad.bom is bom

    def test_add_balloon(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        ad = AssemblyDrawing("A3")
        ad.add_balloon(item_no=1, x=50, y=100)
        assert len(ad.balloons) == 1
        assert ad.balloons[0].item_no == 1

    def test_add_tech_requirement(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        ad = AssemblyDrawing("A3")
        ad.add_tech_requirement("未注倒角 C1", item_no=1)
        assert len(ad.tech_requirements) == 1

    def test_add_default_tech_requirements(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        ad = AssemblyDrawing("A3")
        ad.add_default_tech_requirements()
        assert len(ad.tech_requirements) == 6

    def test_set_title_block(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        ad = AssemblyDrawing("A3")
        ad.set_title_block(scale="1:5", material="Q235")
        assert ad.title_block_info["scale"] == "1:5"
        assert ad.title_block_info["material"] == "Q235"

    def test_generate_svg(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        from fc_core.assembly_bom import make_sample_bom
        ad = AssemblyDrawing("A3", title="Test Drawing")
        ad.set_bom(make_sample_bom())
        ad.add_balloon(item_no=1, x=50, y=100, leader_x=80, leader_y=120)
        svg = ad.generate_svg()
        assert "<svg" in svg
        assert "Test Drawing" in svg
        assert "bom-table" in svg
        assert "balloons" in svg

    def test_save_svg(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        from fc_core.assembly_bom import make_sample_bom
        ad = AssemblyDrawing("A3", title="Save Test")
        ad.set_bom(make_sample_bom())
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            path = f.name
        try:
            ad.save(path)
            assert os.path.exists(path)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "<svg" in content
        finally:
            os.unlink(path)

    def test_add_auto_balloons_left(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        from fc_core.assembly_bom import make_sample_bom
        ad = AssemblyDrawing("A3")
        ad.set_bom(make_sample_bom())
        ad.add_auto_balloons(200, 200, 100, 80, layout="left")
        assert len(ad.balloons) == ad.bom.total_items

    def test_add_auto_balloons_right(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        from fc_core.assembly_bom import make_sample_bom
        ad = AssemblyDrawing("A3")
        ad.set_bom(make_sample_bom())
        ad.add_auto_balloons(200, 200, 100, 80, layout="right")
        assert len(ad.balloons) == ad.bom.total_items

    def test_add_auto_balloons_top(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        from fc_core.assembly_bom import make_sample_bom
        ad = AssemblyDrawing("A3")
        ad.set_bom(make_sample_bom())
        ad.add_auto_balloons(200, 200, 100, 80, layout="top")
        assert len(balloons := ad.balloons) == ad.bom.total_items

    def test_empty_bom_no_balloons(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        from fc_core.assembly_bom import BOMTable
        ad = AssemblyDrawing("A3")
        ad.set_bom(BOMTable())
        ad.add_auto_balloons(200, 200, 100, 80)
        assert len(ad.balloons) == 0

    def test_svg_has_frame(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        ad = AssemblyDrawing("A3")
        svg = ad.generate_svg()
        assert "<rect" in svg

    def test_svg_has_title_block(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        ad = AssemblyDrawing("A3", title="Title Test")
        svg = ad.generate_svg()
        assert "title-block" in svg
        assert "Title Test" in svg

    def test_svg_bom_table_content(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        from fc_core.assembly_bom import make_sample_bom
        ad = AssemblyDrawing("A3")
        ad.set_bom(make_sample_bom())
        svg = ad.generate_svg()
        assert "机架" in svg
        assert "Frame" in svg

    def test_svg_tech_requirements(self):
        from fc_core.assembly_drawing import AssemblyDrawing
        ad = AssemblyDrawing("A3")
        ad.add_default_tech_requirements()
        svg = ad.generate_svg()
        assert "技术要求" in svg
        assert "未注倒角" in svg


# ══════════════════════════════════════════════════════════════════
# DraftingAgent 集成测试
# ══════════════════════════════════════════════════════════════════


class TestDraftingAgentAssembly:
    def test_generate_assembly_with_sample_bom(self):
        from fc_runtime.drafting_agent import DraftingAgent
        from fc_core.assembly_bom import make_sample_bom
        agent = DraftingAgent()
        ad = agent.generate_assembly_drawing(
            bom=make_sample_bom(),
            page_size="A3",
            title="Integration Test",
        )
        assert ad.bom is not None
        assert ad.bom.total_items == 12
        assert len(ad.balloons) > 0

    def test_generate_assembly_with_tech_req(self):
        from fc_runtime.drafting_agent import DraftingAgent
        from fc_core.assembly_bom import make_sample_bom
        agent = DraftingAgent()
        ad = agent.generate_assembly_drawing(
            bom=make_sample_bom(),
            include_tech_requirements=True,
        )
        assert len(ad.tech_requirements) > 0

    def test_generate_assembly_save(self):
        from fc_runtime.drafting_agent import DraftingAgent
        from fc_core.assembly_bom import make_sample_bom
        agent = DraftingAgent()
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            path = f.name
        try:
            ad = agent.generate_assembly_drawing(
                bom=make_sample_bom(),
                output_path=path,
            )
            assert os.path.exists(path)
        finally:
            os.unlink(path)

    def test_generate_assembly_default_bom(self):
        from fc_runtime.drafting_agent import DraftingAgent
        agent = DraftingAgent()
        ad = agent.generate_assembly_drawing(page_size="A4")
        assert ad.bom is not None
        assert ad.bom.total_items > 0
