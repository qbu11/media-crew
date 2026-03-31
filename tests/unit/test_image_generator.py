"""
Tests for image_generator module.

Covers:
- Platform enum and config
- ColorScheme enum and configs
- FontManager
- BaseRenderer
- CoverImageGenerator
- InfoImageGenerator
- CardImageGenerator
- SummaryImageGenerator
- ImageGenerator (unified entry)
- generate_for_platform convenience function
"""

from unittest.mock import MagicMock, patch

import pytest

from src.services.image_generator import (
    BaseRenderer,
    CardImageGenerator,
    ColorScheme,
    COLOR_SCHEMES,
    CoverImageGenerator,
    FontManager,
    ImageGenerator,
    InfoImageGenerator,
    Platform,
    PlatformConfig,
    PLATFORM_CONFIGS,
    SummaryImageGenerator,
    generate_for_platform,
)


# ============ Enums ============

class TestPlatform:
    def test_values(self):
        assert Platform.XIAOHONGSHU.value == "xiaohongshu"
        assert Platform.WEIBO.value == "weibo"
        assert Platform.ZHIHU.value == "zhihu"
        assert Platform.BILIBILI.value == "bilibili"
        assert Platform.DOUYIN.value == "douyin"

    def test_from_string(self):
        assert Platform("xiaohongshu") == Platform.XIAOHONGSHU


class TestColorScheme:
    def test_values(self):
        assert ColorScheme.TECH.value == "tech"
        assert ColorScheme.BUSINESS.value == "business"
        assert ColorScheme.VIBRANT.value == "vibrant"
        assert ColorScheme.MINIMAL.value == "minimal"

    def test_all_schemes_have_configs(self):
        for scheme in ColorScheme:
            assert scheme in COLOR_SCHEMES
            colors = COLOR_SCHEMES[scheme]
            assert "primary" in colors
            assert "text_dark" in colors
            assert "text_light" in colors


class TestPlatformConfig:
    def test_all_platforms_have_configs(self):
        for platform in Platform:
            assert platform in PLATFORM_CONFIGS
            config = PLATFORM_CONFIGS[platform]
            assert config.width > 0
            assert config.height > 0
            assert config.font_scale > 0

    def test_xiaohongshu_config(self):
        config = PLATFORM_CONFIGS[Platform.XIAOHONGSHU]
        assert config.name == "小红书"
        assert config.width == 1080
        assert config.height == 1080


# ============ FontManager ============

class TestFontManager:
    def test_get_font_returns_font(self):
        # Should return something (either truetype or default)
        font = FontManager.get_font(24)
        assert font is not None

    def test_get_font_caching(self):
        FontManager._cache.clear()
        font1 = FontManager.get_font(30)
        font2 = FontManager.get_font(30)
        assert font1 is font2

    def test_get_font_different_sizes(self):
        FontManager._cache.clear()
        font_small = FontManager.get_font(12)
        font_large = FontManager.get_font(48)
        assert font_small is not None
        assert font_large is not None


# ============ BaseRenderer ============

class TestBaseRenderer:
    def test_init(self):
        r = BaseRenderer(100, 100)
        assert r.width == 100
        assert r.height == 100
        assert r.image is not None

    def test_init_with_scheme(self):
        r = BaseRenderer(200, 200, ColorScheme.BUSINESS)
        assert r.colors == COLOR_SCHEMES[ColorScheme.BUSINESS]

    def test_create_gradient_vertical(self):
        r = BaseRenderer(50, 50)
        r.create_gradient_background((255, 0, 0), (0, 0, 255), "vertical")
        assert r.image.size == (50, 50)

    def test_create_gradient_horizontal(self):
        r = BaseRenderer(50, 50)
        r.create_gradient_background((255, 0, 0), (0, 0, 255), "horizontal")
        assert r.image.size == (50, 50)

    def test_create_gradient_diagonal(self):
        r = BaseRenderer(50, 50)
        r.create_gradient_background((255, 0, 0), (0, 0, 255), "diagonal")
        assert r.image.size == (50, 50)

    def test_draw_text_centered(self):
        r = BaseRenderer(200, 200)
        height = r.draw_text_centered("Hello", 50, 20, (0, 0, 0))
        assert height > 0

    def test_draw_rounded_rect(self):
        r = BaseRenderer(200, 200)
        r.draw_rounded_rect((10, 10, 100, 100), radius=10, fill=(255, 0, 0))
        # No exception

    def test_save(self, tmp_path):
        r = BaseRenderer(100, 100)
        path = str(tmp_path / "test.png")
        r.save(path)
        from pathlib import Path
        assert Path(path).exists()


# ============ CoverImageGenerator ============

class TestCoverImageGenerator:
    def test_generate_gradient(self):
        gen = CoverImageGenerator(Platform.XIAOHONGSHU)
        img = gen.generate("Test Title")
        assert img.size == (1080, 1080)

    def test_generate_solid(self):
        gen = CoverImageGenerator(Platform.XIAOHONGSHU, ColorScheme.BUSINESS)
        img = gen.generate("Title", style="solid")
        assert img.size == (1080, 1080)

    def test_generate_with_subtitle(self):
        gen = CoverImageGenerator(Platform.WEIBO)
        img = gen.generate("Title", subtitle="Subtitle text")
        assert img is not None

    def test_generate_with_tags(self):
        gen = CoverImageGenerator(Platform.ZHIHU)
        img = gen.generate("Title", tags=["tag1", "tag2", "tag3"])
        assert img is not None

    def test_generate_all_options(self):
        gen = CoverImageGenerator(Platform.DOUYIN, ColorScheme.VIBRANT)
        img = gen.generate("Title", subtitle="Sub", tags=["t1"], style="gradient")
        assert img.size == PLATFORM_CONFIGS[Platform.DOUYIN].cover_size


# ============ InfoImageGenerator ============

class TestInfoImageGenerator:
    def test_generate_comparison_table(self):
        gen = InfoImageGenerator(Platform.XIAOHONGSHU)
        img = gen.generate_comparison_table(
            title="Comparison",
            headers=["Item", "A", "B"],
            rows=[
                ["Feature 1", "Yes", "No"],
                ["Feature 2", "No", "Yes"],
            ],
        )
        assert img is not None

    def test_generate_with_highlight_col(self):
        gen = InfoImageGenerator(Platform.WEIBO)
        img = gen.generate_comparison_table(
            title="Test",
            headers=["X", "Y"],
            rows=[["1", "2"]],
            highlight_col=1,
        )
        assert img is not None

    def test_different_platform(self):
        gen = InfoImageGenerator(Platform.BILIBILI, ColorScheme.MINIMAL)
        img = gen.generate_comparison_table(
            title="Test",
            headers=["A", "B"],
            rows=[["1", "2"]],
        )
        assert img.size == PLATFORM_CONFIGS[Platform.BILIBILI].info_size


# ============ CardImageGenerator ============

class TestCardImageGenerator:
    def test_generate_highlight_cards(self):
        gen = CardImageGenerator(Platform.XIAOHONGSHU)
        img = gen.generate_highlight_cards(
            title="Highlights",
            highlights=[
                {"title": "Feature 1", "desc1": "Description 1", "desc2": "Detail 1"},
                {"title": "Feature 2", "desc1": "Description 2", "desc2": "Detail 2"},
            ],
        )
        assert img is not None

    def test_empty_highlights(self):
        gen = CardImageGenerator(Platform.WEIBO)
        img = gen.generate_highlight_cards(title="Test", highlights=[])
        assert img is not None

    def test_missing_fields(self):
        gen = CardImageGenerator(Platform.ZHIHU)
        img = gen.generate_highlight_cards(
            title="Test",
            highlights=[{"title": "Only title"}],
        )
        assert img is not None


# ============ SummaryImageGenerator ============

class TestSummaryImageGenerator:
    def test_generate_recommendations(self):
        gen = SummaryImageGenerator(Platform.XIAOHONGSHU)
        img = gen.generate_recommendations(
            title="Recommendations",
            recommendations=[
                ("Scenario A", "Model X", "Reason 1"),
                ("Scenario B", "Model Y", "Reason 2"),
            ],
        )
        assert img is not None

    def test_generate_with_slogan(self):
        gen = SummaryImageGenerator(Platform.DOUYIN, ColorScheme.VIBRANT)
        img = gen.generate_recommendations(
            title="Test",
            recommendations=[("S", "M", "R")],
            slogan="The Future is Now",
        )
        assert img is not None

    def test_empty_recommendations(self):
        gen = SummaryImageGenerator(Platform.WEIBO)
        img = gen.generate_recommendations(
            title="Test",
            recommendations=[],
        )
        assert img is not None


# ============ ImageGenerator (Unified Entry) ============

class TestImageGenerator:
    def test_init(self):
        gen = ImageGenerator("xiaohongshu", "tech")
        assert gen.platform == Platform.XIAOHONGSHU
        assert gen.color_scheme == ColorScheme.TECH

    def test_init_invalid_platform(self):
        with pytest.raises(ValueError):
            ImageGenerator("invalid_platform")

    def test_generate_cover(self):
        gen = ImageGenerator()
        img = gen.generate_cover("Test Title")
        assert img is not None

    def test_generate_comparison(self):
        gen = ImageGenerator()
        img = gen.generate_comparison(
            title="Test",
            headers=["A", "B"],
            rows=[["1", "2"]],
        )
        assert img is not None

    def test_generate_highlights(self):
        gen = ImageGenerator()
        img = gen.generate_highlights(
            title="Test",
            highlights=[{"title": "H1", "desc1": "D1", "desc2": "D2"}],
        )
        assert img is not None

    def test_generate_summary(self):
        gen = ImageGenerator()
        img = gen.generate_summary(
            title="Test",
            recommendations=[("S", "M", "R")],
        )
        assert img is not None

    def test_generate_all_for_content(self, tmp_path):
        gen = ImageGenerator("xiaohongshu", "tech")
        content = {
            "title": "Test Title",
            "subtitle": "Subtitle",
            "tags": ["tag1"],
            "comparison": {
                "title": "Compare",
                "headers": ["A", "B"],
                "rows": [["1", "2"]],
                "highlight_col": 1,
            },
            "highlights": {
                "title": "Highlights",
                "items": [{"title": "H", "desc1": "D1", "desc2": "D2"}],
            },
            "recommendations": {
                "title": "Recs",
                "items": [("S", "M", "R")],
                "slogan": "Slogan!",
            },
        }
        paths = gen.generate_all_for_content(content, str(tmp_path / "output"))
        assert len(paths) == 4
        for p in paths:
            from pathlib import Path
            assert Path(p).exists()

    def test_generate_all_cover_only(self, tmp_path):
        gen = ImageGenerator()
        content = {"title": "Only Cover"}
        paths = gen.generate_all_for_content(content, str(tmp_path / "output"))
        assert len(paths) == 1


# ============ Convenience Function ============

class TestGenerateForPlatform:
    def test_generate(self, tmp_path):
        content = {"title": "Test", "tags": ["t1"]}
        paths = generate_for_platform("xiaohongshu", content, str(tmp_path / "out"))
        assert len(paths) >= 1
