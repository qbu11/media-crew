"""
统一图片生成器 - 支持多平台配图自动生成
支持: 小红书、微博、知乎、B站、抖音
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ============ 平台配置 ============

class Platform(Enum):
    XIAOHONGSHU = "xiaohongshu"
    WEIBO = "weibo"
    ZHIHU = "zhihu"
    BILIBILI = "bilibili"
    DOUYIN = "douyin"

@dataclass
class PlatformConfig:
    """平台配置"""
    name: str
    width: int
    height: int
    cover_size: tuple[int, int]
    info_size: tuple[int, int]
    card_size: tuple[int, int]
    font_scale: float  # 字体缩放系数

PLATFORM_CONFIGS = {
    Platform.XIAOHONGSHU: PlatformConfig(
        name="小红书",
        width=1080, height=1080,
        cover_size=(1080, 1080),
        info_size=(1080, 1080),
        card_size=(1080, 1080),
        font_scale=1.0
    ),
    Platform.WEIBO: PlatformConfig(
        name="微博",
        width=1080, height=1080,
        cover_size=(1080, 1080),
        info_size=(1080, 1080),
        card_size=(1080, 1080),
        font_scale=0.9
    ),
    Platform.ZHIHU: PlatformConfig(
        name="知乎",
        width=1120, height=630,
        cover_size=(1120, 630),
        info_size=(1080, 800),
        card_size=(1080, 720),
        font_scale=0.8
    ),
    Platform.BILIBILI: PlatformConfig(
        name="B站",
        width=1080, height=1440,
        cover_size=(1920, 1080),  # 视频封面
        info_size=(1080, 1440),   # 动态配图
        card_size=(1080, 1440),
        font_scale=0.9
    ),
    Platform.DOUYIN: PlatformConfig(
        name="抖音",
        width=1080, height=1920,
        cover_size=(1080, 1920),
        info_size=(1080, 1920),
        card_size=(1080, 1920),
        font_scale=1.2
    ),
}

# ============ 配色方案 ============

class ColorScheme(Enum):
    TECH = "tech"
    BUSINESS = "business"
    VIBRANT = "vibrant"
    MINIMAL = "minimal"

COLOR_SCHEMES = {
    ColorScheme.TECH: {
        "primary": (30, 58, 138),      # 深蓝
        "secondary": (124, 58, 237),   # 紫色
        "accent": (59, 130, 246),      # 亮蓝
        "success": (16, 185, 129),     # 绿色
        "warning": (245, 158, 11),     # 橙色
        "text_dark": (17, 24, 39),
        "text_light": (255, 255, 255),
        "bg_light": (243, 244, 246),
    },
    ColorScheme.BUSINESS: {
        "primary": (37, 99, 235),
        "secondary": (99, 102, 241),
        "accent": (14, 165, 233),
        "success": (34, 197, 94),
        "warning": (234, 179, 8),
        "text_dark": (15, 23, 42),
        "text_light": (255, 255, 255),
        "bg_light": (248, 250, 252),
    },
    ColorScheme.VIBRANT: {
        "primary": (249, 115, 22),
        "secondary": (234, 179, 8),
        "accent": (239, 68, 68),
        "success": (34, 197, 94),
        "warning": (168, 85, 247),
        "text_dark": (28, 25, 23),
        "text_light": (255, 255, 255),
        "bg_light": (254, 252, 232),
    },
    ColorScheme.MINIMAL: {
        "primary": (55, 65, 81),
        "secondary": (107, 114, 128),
        "accent": (75, 85, 99),
        "success": (34, 197, 94),
        "warning": (234, 179, 8),
        "text_dark": (17, 24, 39),
        "text_light": (255, 255, 255),
        "bg_light": (249, 250, 251),
    },
}

# ============ 字体管理 ============

class FontManager:
    """字体管理器"""

    FONT_PATHS_CN = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    ]

    FONT_PATHS_EN = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]

    _cache: dict[int, ImageFont.FreeTypeFont] = {}

    @classmethod
    def get_font(cls, size: int, prefer_cn: bool = True) -> ImageFont.FreeTypeFont:
        """获取字体"""
        if size in cls._cache:
            return cls._cache[size]

        paths = cls.FONT_PATHS_CN if prefer_cn else cls.FONT_PATHS_EN

        for path in paths:
            try:
                font = ImageFont.truetype(path, size)
                cls._cache[size] = font
                return font
            except Exception:
                continue

        return ImageFont.load_default()

# ============ 基础渲染器 ============

class BaseRenderer:
    """基础图片渲染器"""

    def __init__(
        self,
        width: int,
        height: int,
        color_scheme: ColorScheme = ColorScheme.TECH
    ):
        self.width = width
        self.height = height
        self.colors = COLOR_SCHEMES[color_scheme]
        self.image = Image.new('RGB', (width, height), self.colors["bg_light"])
        self.draw = ImageDraw.Draw(self.image)

    def create_gradient_background(
        self,
        color1: tuple[int, int, int],
        color2: tuple[int, int, int],
        direction: str = "vertical"
    ) -> None:
        """创建渐变背景"""
        base = Image.new('RGB', (self.width, self.height), color1)
        top = Image.new('RGB', (self.width, self.height), color2)
        mask = Image.new('L', (self.width, self.height))

        mask_data = []
        for y in range(self.height):
            for x in range(self.width):
                if direction == "vertical":
                    mask_data.append(int(255 * (y / self.height)))
                elif direction == "horizontal":
                    mask_data.append(int(255 * (x / self.width)))
                else:  # diagonal
                    mask_data.append(int(255 * ((x + y) / (self.width + self.height))))

        mask.putdata(mask_data)
        base.paste(top, (0, 0), mask)
        self.image = base
        self.draw = ImageDraw.Draw(self.image)

    def draw_text_centered(
        self,
        text: str,
        y: int,
        font_size: int,
        color: tuple[int, int, int],
        bold: bool = False
    ) -> int:
        """居中绘制文字,返回文字高度"""
        font = FontManager.get_font(font_size)
        bbox = self.draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (self.width - text_width) // 2
        self.draw.text((x, y), text, fill=color, font=font)
        return text_height

    def draw_rounded_rect(
        self,
        coords: tuple[int, int, int, int],
        radius: int = 20,
        fill: tuple[int, int, int] | None = None,
        outline: tuple[int, int, int] | None = None,
        width: int = 1
    ) -> None:
        """绘制圆角矩形"""
        self.draw.rounded_rectangle(
            coords,
            radius=radius,
            fill=fill,
            outline=outline,
            width=width
        )

    def save(self, filepath: str, quality: int = 95) -> None:
        """保存图片"""
        self.image.save(filepath, quality=quality)

# ============ 封面图生成器 ============

class CoverImageGenerator:
    """封面图生成器"""

    def __init__(self, platform: Platform, color_scheme: ColorScheme = ColorScheme.TECH):
        self.platform = platform
        self.config = PLATFORM_CONFIGS[platform]
        self.color_scheme = color_scheme
        self.colors = COLOR_SCHEMES[color_scheme]

    def generate(
        self,
        title: str,
        subtitle: str | None = None,
        tags: list[str] | None = None,
        style: str = "gradient"
    ) -> Image.Image:
        """生成封面图"""
        width, height = self.config.cover_size
        renderer = BaseRenderer(width, height, self.color_scheme)

        # 背景
        if style == "gradient":
            renderer.create_gradient_background(
                self.colors["primary"],
                self.colors["secondary"]
            )
        elif style == "solid":
            renderer.image = Image.new('RGB', (width, height), self.colors["primary"])
            renderer.draw = ImageDraw.Draw(renderer.image)

        # 主标题
        font_scale = self.config.font_scale
        title_y = height // 2 - int(60 * font_scale)
        renderer.draw_text_centered(
            title,
            title_y,
            int(80 * font_scale),
            self.colors["text_light"]
        )

        # 副标题
        if subtitle:
            subtitle_y = height // 2 + int(50 * font_scale)
            renderer.draw_text_centered(
                subtitle,
                subtitle_y,
                int(40 * font_scale),
                self.colors["text_light"]
            )

        # 标签
        if tags:
            tag_y = height - int(120 * font_scale)
            tag_text = " | ".join(tags)
            renderer.draw_text_centered(
                tag_text,
                tag_y,
                int(28 * font_scale),
                self.colors["text_light"]
            )

        return renderer.image

# ============ 信息图生成器 ============

class InfoImageGenerator:
    """信息图生成器 - 表格/对比图"""

    def __init__(self, platform: Platform, color_scheme: ColorScheme = ColorScheme.TECH):
        self.platform = platform
        self.config = PLATFORM_CONFIGS[platform]
        self.color_scheme = color_scheme
        self.colors = COLOR_SCHEMES[color_scheme]

    def generate_comparison_table(
        self,
        title: str,
        headers: list[str],
        rows: list[list[str]],
        highlight_col: int | None = None
    ) -> Image.Image:
        """生成对比表格"""
        width, height = self.config.info_size
        renderer = BaseRenderer(width, height, self.color_scheme)

        font_scale = self.config.font_scale

        # 标题
        title_font = int(60 * font_scale)
        bbox = renderer.draw.textbbox((0, 0), title, font=FontManager.get_font(title_font))
        title_width = bbox[2] - bbox[0]
        renderer.draw.text(
            ((width - title_width) // 2, int(80 * font_scale)),
            title,
            fill=self.colors["text_dark"],
            font=FontManager.get_font(title_font)
        )

        # 表格布局
        table_x = int(80 * font_scale)
        table_y = int(200 * font_scale)
        col_width = int((width - 2 * table_x) / len(headers))
        row_height = int(100 * font_scale)

        cell_font = int(28 * font_scale)

        # 表头
        for i, header in enumerate(headers):
            x = table_x + i * col_width
            y = table_y
            renderer.draw_rounded_rect(
                [x, y, x + col_width - 10, y + row_height - 10],
                radius=10,
                fill=self.colors["primary"]
            )

            bbox = renderer.draw.textbbox((0, 0), header, font=FontManager.get_font(cell_font))
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            renderer.draw.text(
                (x + (col_width - text_w) // 2 - 5, y + (row_height - text_h) // 2 - 5),
                header,
                fill=self.colors["text_light"],
                font=FontManager.get_font(cell_font)
            )

        # 数据行
        for row_idx, row in enumerate(rows):
            for col_idx, cell in enumerate(row):
                x = table_x + col_idx * col_width
                y = table_y + (row_idx + 1) * row_height

                bg_color = self.colors["bg_light"] if row_idx % 2 == 0 else (255, 255, 255)

                # 高亮列
                if highlight_col is not None and col_idx == highlight_col:
                    bg_color = (220, 252, 231)  # 浅绿色

                renderer.draw_rounded_rect(
                    [x, y, x + col_width - 10, y + row_height - 10],
                    radius=5,
                    fill=bg_color,
                    outline=self.colors["text_dark"],
                    width=1
                )

                bbox = renderer.draw.textbbox((0, 0), cell, font=FontManager.get_font(cell_font))
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]

                text_color = self.colors["success"] if highlight_col == col_idx else self.colors["text_dark"]
                renderer.draw.text(
                    (x + (col_width - text_w) // 2 - 5, y + (row_height - text_h) // 2 - 5),
                    cell,
                    fill=text_color,
                    font=FontManager.get_font(cell_font)
                )

        return renderer.image

# ============ 卡片图生成器 ============

class CardImageGenerator:
    """卡片图生成器 - 要点列表/功能介绍"""

    def __init__(self, platform: Platform, color_scheme: ColorScheme = ColorScheme.TECH):
        self.platform = platform
        self.config = PLATFORM_CONFIGS[platform]
        self.color_scheme = color_scheme
        self.colors = COLOR_SCHEMES[color_scheme]

    def generate_highlight_cards(
        self,
        title: str,
        highlights: list[dict[str, str]]
    ) -> Image.Image:
        """生成亮点卡片列表"""
        width, height = self.config.card_size
        renderer = BaseRenderer(width, height, self.color_scheme)

        font_scale = self.config.font_scale

        # 标题
        title_font = int(60 * font_scale)
        bbox = renderer.draw.textbbox((0, 0), title, font=FontManager.get_font(title_font))
        title_width = bbox[2] - bbox[0]
        renderer.draw.text(
            ((width - title_width) // 2, int(60 * font_scale)),
            title,
            fill=self.colors["text_dark"],
            font=FontManager.get_font(title_font)
        )

        # 卡片参数
        card_width = int(width * 0.85)
        card_height = int(180 * font_scale)
        card_x = (width - card_width) // 2
        start_y = int(180 * font_scale)
        spacing = int(30 * font_scale)

        title_font_card = int(36 * font_scale)
        desc_font = int(28 * font_scale)
        num_font = int(40 * font_scale)

        for i, highlight in enumerate(highlights):
            y = start_y + i * (card_height + spacing)

            # 卡片背景
            renderer.draw_rounded_rect(
                [card_x, y, card_x + card_width, y + card_height],
                radius=15,
                fill=(255, 255, 255),
                outline=self.colors["primary"],
                width=3
            )

            # 序号圆圈
            circle_x = card_x + int(50 * font_scale)
            circle_y = y + int(50 * font_scale)
            circle_r = int(25 * font_scale)
            renderer.draw.ellipse(
                [circle_x - circle_r, circle_y - circle_r,
                 circle_x + circle_r, circle_y + circle_r],
                fill=self.colors["primary"]
            )

            # 序号
            bbox = renderer.draw.textbbox((0, 0), str(i + 1), font=FontManager.get_font(num_font))
            num_w = bbox[2] - bbox[0]
            num_h = bbox[3] - bbox[1]
            renderer.draw.text(
                (circle_x - num_w // 2, circle_y - num_h // 2 - 5),
                str(i + 1),
                fill=self.colors["text_light"],
                font=FontManager.get_font(num_font)
            )

            # 标题
            renderer.draw.text(
                (card_x + int(100 * font_scale), y + int(25 * font_scale)),
                highlight.get("title", ""),
                fill=self.colors["text_dark"],
                font=FontManager.get_font(title_font_card)
            )

            # 描述1
            renderer.draw.text(
                (card_x + int(100 * font_scale), y + int(75 * font_scale)),
                highlight.get("desc1", ""),
                fill=self.colors["text_dark"],
                font=FontManager.get_font(desc_font)
            )

            # 描述2
            renderer.draw.text(
                (card_x + int(100 * font_scale), y + int(115 * font_scale)),
                highlight.get("desc2", ""),
                fill=self.colors["text_dark"],
                font=FontManager.get_font(desc_font)
            )

        return renderer.image

# ============ 总结图生成器 ============

class SummaryImageGenerator:
    """总结图生成器 - 场景建议/行动指南"""

    def __init__(self, platform: Platform, color_scheme: ColorScheme = ColorScheme.TECH):
        self.platform = platform
        self.config = PLATFORM_CONFIGS[platform]
        self.color_scheme = color_scheme
        self.colors = COLOR_SCHEMES[color_scheme]

    def generate_recommendations(
        self,
        title: str,
        recommendations: list[tuple[str, str, str]],  # (场景, 推荐, 原因)
        slogan: str | None = None
    ) -> Image.Image:
        """生成推荐建议图"""
        width, height = self.config.card_size
        renderer = BaseRenderer(width, height, self.color_scheme)

        font_scale = self.config.font_scale

        # 标题
        title_font = int(60 * font_scale)
        bbox = renderer.draw.textbbox((0, 0), title, font=FontManager.get_font(title_font))
        title_width = bbox[2] - bbox[0]
        renderer.draw.text(
            ((width - title_width) // 2, int(80 * font_scale)),
            title,
            fill=self.colors["text_dark"],
            font=FontManager.get_font(title_font)
        )

        # 建议列表
        scenario_font = int(36 * font_scale)
        model_font = int(32 * font_scale)
        reason_font = int(24 * font_scale)

        start_y = int(220 * font_scale)
        spacing = int(120 * font_scale)
        left_margin = int(120 * font_scale)

        for i, (scenario, model, reason) in enumerate(recommendations):
            y = start_y + i * spacing

            # 场景
            renderer.draw.text(
                (left_margin, y),
                scenario,
                fill=self.colors["text_dark"],
                font=FontManager.get_font(scenario_font)
            )

            # 箭头
            arrow_text = "->"
            bbox = renderer.draw.textbbox((0, 0), arrow_text, font=FontManager.get_font(scenario_font))
            bbox[2] - bbox[0]
            renderer.draw.text(
                (left_margin + int(180 * font_scale), y),
                arrow_text,
                fill=self.colors["primary"],
                font=FontManager.get_font(scenario_font)
            )

            # 模型名称
            renderer.draw.text(
                (left_margin + int(250 * font_scale), y),
                model,
                fill=self.colors["primary"],
                font=FontManager.get_font(model_font)
            )

            # 原因
            renderer.draw.text(
                (left_margin + int(250 * font_scale), y + int(45 * font_scale)),
                reason,
                fill=self.colors["text_dark"],
                font=FontManager.get_font(reason_font)
            )

        # 底部标语
        if slogan:
            slogan_font = int(44 * font_scale)
            bbox = renderer.draw.textbbox((0, 0), slogan, font=FontManager.get_font(slogan_font))
            slogan_width = bbox[2] - bbox[0]
            renderer.draw.text(
                ((width - slogan_width) // 2, height - int(100 * font_scale)),
                slogan,
                fill=self.colors["secondary"],
                font=FontManager.get_font(slogan_font)
            )

        return renderer.image

# ============ 统一入口 ============

class ImageGenerator:
    """统一图片生成器入口"""

    def __init__(
        self,
        platform: str = "xiaohongshu",
        color_scheme: str = "tech"
    ):
        self.platform = Platform(platform)
        self.color_scheme = ColorScheme(color_scheme)

    def generate_cover(
        self,
        title: str,
        subtitle: str | None = None,
        tags: list[str] | None = None,
        style: str = "gradient"
    ) -> Image.Image:
        """生成封面图"""
        generator = CoverImageGenerator(self.platform, self.color_scheme)
        return generator.generate(title, subtitle, tags, style)

    def generate_comparison(
        self,
        title: str,
        headers: list[str],
        rows: list[list[str]],
        highlight_col: int | None = None
    ) -> Image.Image:
        """生成对比表格"""
        generator = InfoImageGenerator(self.platform, self.color_scheme)
        return generator.generate_comparison_table(title, headers, rows, highlight_col)

    def generate_highlights(
        self,
        title: str,
        highlights: list[dict[str, str]]
    ) -> Image.Image:
        """生成亮点卡片"""
        generator = CardImageGenerator(self.platform, self.color_scheme)
        return generator.generate_highlight_cards(title, highlights)

    def generate_summary(
        self,
        title: str,
        recommendations: list[tuple[str, str, str]],
        slogan: str | None = None
    ) -> Image.Image:
        """生成总结建议图"""
        generator = SummaryImageGenerator(self.platform, self.color_scheme)
        return generator.generate_recommendations(title, recommendations, slogan)

    def generate_all_for_content(
        self,
        content: dict,
        output_dir: str
    ) -> list[str]:
        """根据内容自动生成全套图片"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        paths = []

        # 封面图
        cover = self.generate_cover(
            title=content.get("title", ""),
            subtitle=content.get("subtitle"),
            tags=content.get("tags"),
            style="gradient"
        )
        cover_path = str(output_path / "1_cover.png")
        cover.save(cover_path)
        paths.append(cover_path)

        # 对比表
        if content.get("comparison"):
            comp = content.get("comparison")
            table = self.generate_comparison(
                title=comp.get("title", "对比"),
                headers=comp.get("headers", []),
                rows=comp.get("rows", []),
                highlight_col=comp.get("highlight_col")
            )
            table_path = str(output_path / "2_comparison.png")
            table.save(table_path)
            paths.append(table_path)

        # 亮点
        if content.get("highlights"):
            hl = content.get("highlights")
            cards = self.generate_highlights(
                title=hl.get("title", "核心亮点"),
                highlights=hl.get("items", [])
            )
            cards_path = str(output_path / "3_highlights.png")
            cards.save(cards_path)
            paths.append(cards_path)

        # 建议
        if content.get("recommendations"):
            rec = content.get("recommendations")
            summary = self.generate_summary(
                title=rec.get("title", "我的建议"),
                recommendations=rec.get("items", []),
                slogan=rec.get("slogan")
            )
            summary_path = str(output_path / "4_recommendations.png")
            summary.save(summary_path)
            paths.append(summary_path)

        return paths


# ============ 便捷函数 ============

def generate_for_platform(
    platform: str,
    content: dict,
    output_dir: str,
    color_scheme: str = "tech"
) -> list[str]:
    """便捷函数: 为指定平台生成图片"""
    generator = ImageGenerator(platform, color_scheme)
    return generator.generate_all_for_content(content, output_dir)


# ============ 测试 ============

if __name__ == "__main__":
    # 测试内容
    test_content = {
        "title": "AI三巨头激战2026!",
        "subtitle": "Claude Opus 4.6 登顶排行榜",
        "tags": ["AI", "科技", "Claude"],
        "comparison": {
            "title": "三巨头性能对比",
            "headers": ["指标", "Claude", "GPT-5.2", "Gemini"],
            "rows": [
                ["上下文", "100万", "20万", "200万"],
                ["SWE-bench", "80.8%", "73.2%", "75.6%"],
                ["编程能力", "5星", "4星", "4星"],
            ],
            "highlight_col": 1
        },
        "highlights": {
            "title": "Claude Opus 4.6 三大亮点",
            "items": [
                {"title": "100万token上下文窗口", "desc1": "相当于3本《三体》", "desc2": "是GPT-5.2的5倍"},
                {"title": "Agent Teams多智能体", "desc1": "多个AI协同工作", "desc2": "就像组了个超强战队"},
                {"title": "编程能力爆表", "desc1": "SWE-bench 80.8%", "desc2": "完爆竞争对手"},
            ]
        },
        "recommendations": {
            "title": "我的选择建议",
            "items": [
                ("写代码", "Claude Opus 4.6", "编程能力最强"),
                ("日常聊天", "GPT-5.2", "响应快，生态好"),
                ("多模态任务", "Gemini 3.1 Pro", "原生多模态"),
                ("中文场景", "Kimi K2 / GLM-5", "中文优化"),
            ],
            "slogan": "2026年AI大爆发"
        }
    }

    # 为各平台生成图片
    platforms = ["xiaohongshu", "weibo", "zhihu", "bilibili", "douyin"]

    for platform in platforms:
        print(f"[INFO] 正在为 {platform} 生成图片...")
        output_dir = f"output_images/{platform}"
        paths = generate_for_platform(platform, test_content, output_dir)
        print(f"[OK] {platform}: 生成了 {len(paths)} 张图片")
        for p in paths:
            print(f"  - {p}")

    print("\n[DONE] 所有平台图片生成完成!")
