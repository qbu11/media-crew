"""Image generation routes."""

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.services.image_generator import (
    ImageGenerator,
    generate_for_platform,
    PLATFORM_CONFIGS,
    COLOR_SCHEMES,
    Platform,
    ColorScheme,
)

router = APIRouter(prefix="/images", tags=["Images"])

IMAGES_DIR = Path(__file__).parent.parent.parent.parent / "generated_images"
IMAGES_DIR.mkdir(exist_ok=True)


class ImageGenerateRequest(BaseModel):
    """Full image set generation request."""

    platform: Literal["xiaohongshu", "weibo", "zhihu", "bilibili", "douyin"] = Field(
        description="目标平台"
    )
    color_scheme: Literal["tech", "business", "vibrant", "minimal"] = Field(
        default="tech", description="配色方案"
    )
    content: dict[str, Any] = Field(
        description="Content data with title, subtitle, tags, comparison, highlights, recommendations"
    )
    output_name: str | None = Field(None, description="输出文件夹名称,默认使用时间戳")


class SingleImageRequest(BaseModel):
    """Single image generation request."""

    platform: Literal["xiaohongshu", "weibo", "zhihu", "bilibili", "douyin"]
    color_scheme: Literal["tech", "business", "vibrant", "minimal"] = "tech"
    image_type: Literal["cover", "comparison", "highlights", "summary"]
    data: dict[str, Any]


@router.post("/generate")
async def generate_images(request: ImageGenerateRequest) -> dict[str, Any]:
    """Generate a full set of images for a platform."""
    try:
        if request.output_name:
            output_dir = IMAGES_DIR / request.platform / request.output_name
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = IMAGES_DIR / request.platform / timestamp

        output_dir.mkdir(parents=True, exist_ok=True)

        paths = generate_for_platform(
            platform=request.platform,
            content=request.content,
            output_dir=str(output_dir),
            color_scheme=request.color_scheme,
        )

        relative_paths = [str(Path(p).relative_to(IMAGES_DIR.parent)) for p in paths]

        return {
            "success": True,
            "data": {
                "platform": request.platform,
                "color_scheme": request.color_scheme,
                "output_dir": str(output_dir.relative_to(IMAGES_DIR.parent)),
                "images": relative_paths,
                "count": len(paths),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片生成失败: {e}")


@router.post("/generate-single")
async def generate_single_image(request: SingleImageRequest) -> dict[str, Any]:
    """Generate a single image."""
    try:
        generator = ImageGenerator(request.platform, request.color_scheme)

        if request.image_type == "cover":
            image = generator.generate_cover(
                title=request.data.get("title", ""),
                subtitle=request.data.get("subtitle"),
                tags=request.data.get("tags"),
                style=request.data.get("style", "gradient"),
            )
        elif request.image_type == "comparison":
            image = generator.generate_comparison(
                title=request.data.get("title", "对比"),
                headers=request.data.get("headers", []),
                rows=request.data.get("rows", []),
                highlight_col=request.data.get("highlight_col"),
            )
        elif request.image_type == "highlights":
            image = generator.generate_highlights(
                title=request.data.get("title", "核心亮点"),
                highlights=request.data.get("items", []),
            )
        elif request.image_type == "summary":
            image = generator.generate_summary(
                title=request.data.get("title", "我的建议"),
                recommendations=request.data.get("items", []),
                slogan=request.data.get("slogan"),
            )
        else:
            raise HTTPException(status_code=400, detail="不支持的图片类型")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = IMAGES_DIR / request.platform / "single"
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{request.image_type}_{timestamp}.png"
        filepath = output_dir / filename
        image.save(str(filepath))

        return {
            "success": True,
            "data": {
                "platform": request.platform,
                "image_type": request.image_type,
                "filepath": str(filepath.relative_to(IMAGES_DIR.parent)),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"图片生成失败: {e}")


@router.get("/platforms")
async def list_platform_configs() -> dict[str, Any]:
    """List all platform image specs."""
    configs = {}
    for platform in Platform:
        config = PLATFORM_CONFIGS[platform]
        configs[platform.value] = {
            "name": config.name,
            "cover_size": config.cover_size,
            "info_size": config.info_size,
            "card_size": config.card_size,
            "font_scale": config.font_scale,
        }
    return {"success": True, "data": configs}


@router.get("/color-schemes")
async def list_color_schemes() -> dict[str, Any]:
    """List all color schemes."""
    schemes = {}
    for scheme in ColorScheme:
        colors = COLOR_SCHEMES[scheme]
        schemes[scheme.value] = {
            "primary": f"rgb{colors['primary']}",
            "secondary": f"rgb{colors['secondary']}",
            "accent": f"rgb{colors['accent']}",
            "success": f"rgb{colors['success']}",
            "warning": f"rgb{colors['warning']}",
        }
    return {"success": True, "data": schemes}


@router.get("/history")
async def list_generated_images(
    platform: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """List previously generated images."""
    images: list[dict[str, Any]] = []

    if platform:
        search_dir = IMAGES_DIR / platform
        if not search_dir.exists():
            return {"success": True, "data": [], "total": 0}
    else:
        search_dir = IMAGES_DIR

    for img_file in search_dir.rglob("*.png"):
        if img_file.is_file():
            stat = img_file.stat()
            images.append(
                {
                    "filepath": str(img_file.relative_to(IMAGES_DIR.parent)),
                    "filename": img_file.name,
                    "platform": img_file.parent.parent.name if platform is None else platform,
                    "size": stat.st_size,
                    "created_at": stat.st_mtime,
                }
            )

    images.sort(key=lambda x: x["created_at"], reverse=True)

    return {"success": True, "data": images[:limit], "total": len(images)}
