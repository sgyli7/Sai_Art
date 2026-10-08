"""Compose original appearance artwork into a review PDF without raster editing."""
from pathlib import Path
import argparse
import json
import sys


parser = argparse.ArgumentParser()
parser.add_argument("--document-tools", type=Path)
args = parser.parse_args()
if args.document_tools:
    sys.path.insert(0, str(args.document_tools))

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas


root = Path(__file__).resolve().parent.parent
pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
width, height = landscape(A3)
target = root / "gorilla_v0_1_review_rev_f.pdf"
book = canvas.Canvas(str(target), pagesize=(width, height), pageCompression=1)
book.setTitle("Gorilla V0.1 - Appearance Review - Rev F")
book.setAuthor("Sai_Art")


def draw_image(path, x, y, box_width, box_height):
    original = ImageReader(str(path))
    iw, ih = original.getSize()
    ratio = min(box_width / iw, box_height / ih)
    dw, dh = iw * ratio, ih * ratio
    book.drawImage(original, x + (box_width - dw) / 2,
                   y + (box_height - dh) / 2, dw, dh)


pages = [
    ("主设计与 Z 腿侧面", "images/z_leg_variant_rev_f.png"),
    ("正／侧／背视图", "images/turnaround_rev_f.png"),
]
for number, (subtitle, asset) in enumerate(pages, start=1):
    book.setFillColor(HexColor("#fcfbf8"))
    book.rect(0, 0, width, height, stroke=0, fill=1)
    book.setFillColor(HexColor("#176b99"))
    book.setFont("Helvetica-Bold", 25)
    book.drawString(36, height - 43, "GORILLA V0.1")
    book.setFillColor(HexColor("#45515b"))
    book.setFont("STSong-Light", 13)
    book.drawString(36, height - 66, f"外观审阅稿 / Rev F / {subtitle}")
    book.setStrokeColor(HexColor("#e8b448"))
    book.setLineWidth(2)
    book.line(36, height - 78, width - 36, height - 78)
    draw_image(root / asset, 24, 60, width - 48, height - 152)
    book.setFillColor(HexColor("#5a6670"))
    book.setFont("STSong-Light", 9)
    book.drawString(36, 38, "模型包络绘制基准：高 2.650 m / 最大宽 2.587 m / 最大深 1.072 m（宽度含手臂外沿）")
    book.drawString(36, 23, "Sai_Art / 外观设计审阅版 / 尺寸与制作记录见 dimension_lock.json / generation_manifest.json")
    book.setFont("Helvetica", 9)
    book.drawRightString(width - 36, 23, f"{number:02d} / {len(pages):02d}")
    book.showPage()
book.save()

html = """<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gorilla V0.1 · 外观审阅稿</title>
<style>body{margin:0;background:#f4f6f7;color:#33444e;font:16px/1.65 system-ui,sans-serif}main{max-width:1400px;margin:auto;padding:30px}h1{color:#176b99;margin-bottom:8px}p{max-width:1000px}figure{margin:28px 0;background:#fff;padding:18px;border-radius:12px}img{width:100%;height:auto;display:block}a{color:#176b99}figcaption{padding:12px 0 0}.links{display:flex;gap:24px;flex-wrap:wrap}</style>
<main><h1>Gorilla V0.1 · Rev F</h1><p>外观审阅稿。连续宽厚的头身核心，三段式 Z 腿与独立踝足；保留 URI 的洁净表面和精密装配细节。</p>
<p>模型包络绘制基准：高 2.650 m、最大宽 2.587 m、最大深 1.072 m。粗模用于尺寸定位，外观由设计图决定。</p>
<p class="links"><a href="gorilla_v0_1_review_rev_f.pdf">打开两页 PDF</a><a href="review_notes.md">设计说明</a><a href="generation_manifest.json">精确提示与生成记录</a></p>
<figure><a href="images/z_leg_variant_rev_f.png"><img src="images/z_leg_variant_rev_f.png" alt="Gorilla 主设计与三段 Z 腿侧面"></a><figcaption>01 · 主设计与三段 Z 腿侧面（点击查看原图）</figcaption></figure>
<figure><a href="images/turnaround_rev_f.png"><img src="images/turnaround_rev_f.png" alt="Gorilla 正侧背三视图"></a><figcaption>02 · 正／侧／背视图（点击查看原图）</figcaption></figure>
<p>当前等待外形审核，尚未向 SaiRobot 项目交付。A–E 图保留为过程记录，本版以 Rev F 为准。</p></main></html>"""
(root / "review.html").write_text(html)
print(json.dumps({"pdf": str(target), "pages": len(pages),
                  "html": str(root / "review.html")}, ensure_ascii=False))
