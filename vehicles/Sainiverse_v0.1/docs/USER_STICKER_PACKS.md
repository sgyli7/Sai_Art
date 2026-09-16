# 用户提供贴纸包检查

检查日期：2026-09-16。两个 ZIP 来自用户指定下载，由主任务保存。检查仅解压图像/读取文本及 ZIP 目录，未运行程序，未导入包中的游戏行为配置。

## Better Stickers Mod v2.2

归档：`references/user_stickers/3403239_4424174.zip`；mod ID 3403239，file ID 4424174。[作者作品页](https://mod.io/g/snowrunner/m/better-stickers)

包内 22 张 PNG 实际是一张总览和 21 张游戏截图，不是透明贴花源图。总览 1532×689 RGB；截图均为 1920×1200 RGBA，抽查 alpha 为全不透明。嵌套 Previews.zip 是相同预览集合。

真正的色彩贴花位于 `for_shared_textures/*__d_a.pct`，共 21 张。已从这些文件的 BC7 顶层图像数据直接解码为 PNG，保留原始分辨率与 alpha，没有截取截图、放大或重画。512² 文件图像数据偏移 144，256² 文件偏移 136；均对应头部 offset54 的整数值 +6。结果经总览及近图检查，文字与图形正常。不是通用 PCT 转换器，未处理法线和其他通道。

### 推荐本车少量使用的四张

完整目录：`/home/ethan/Projects/RobotDesign/Leviathan_001/vehicles/Leviathan_003/candidates/r030_full_texture/references/user_stickers/inspection/better_decoded/`

| 文件名 | 原始尺寸/alpha | 内容与位置建议 |
| --- | --- | --- |
| `trucks_outside_sticker_1x1_aigle__d_a.png` | 512×512，RGBA，alpha 0–255 | **GEOTECH / Subsurface Survey**：铁锈红几何波纹图形、浅色牌底、清晰副标题。最适合外部勘测设备罩或仪器舱，不放驾驶舱品牌主位 |
| `trucks_outside_sticker_1x1_rescue_units_01__d_a.png` | 256×256，RGBA，alpha 0–255 | **SPECIALIZED TRANSPORT LLC**：紧凑拱形盾牌，黑/米色，适合货运拖车侧面；地名行是原图内容，若保留需整体当承运商贴纸 |
| `trucks_outside_sticker_1x1_offroad_warden_01__d_a.png` | 256×256，RGBA，alpha 0–255 | **Kemco / MOBILE SOIL TESTING**：橙色长条字标与黑色设备用途文字，适合勘测工作舱小区域 |
| `trucks_outside_sticker_1x1_route_searcher_01__d_a.png` | 256×256，RGBA，alpha 0–255 | **ALLIED OILFIELD SERVICES**：小泵机剪影、青色主字、较密的小字。适合能源设备服务侧一处；不泛贴到机器人入口 |

该包整体是运输/林业/地方服务公司风格，并非搞笑梗图包。更卡通的 Black Badger 狼獾头像、较张扬的 Midwest Express 彩色手写体，以及 Park Ranger、Volunteer Fire Dept 等身份不匹配内容不优先用于本车。不能因为文件名叫 `aigle` 或 `rescue_units` 就据此决定用途，文件名继承了被替换的游戏贴花槽，实际图案如上。

已查看联络表：`references/user_stickers/inspection/better_decoded_decoded_sheet.jpg`；原截图联络表：`references/user_stickers/inspection/better_contact_sheet.jpg`。详细路径、尺寸、alpha 和源条目保存在 `inspection/decoded_manifest.json`。

## GG Sticker Packs

归档：`references/user_stickers/2186838_5656732.zip`；mod ID 2186838，file ID 5656732。包内 `Gg_Sticker_Packs.pak` 和 `nx64.pak` 都是标准 ZIP，可只读解析。

前者包含 105 个条目，主要是 XML 配置和网格预编译数据。后者含 17 张 `__d_a.pct`，以及共享法线/其他通道。文件名和有限预览显示齿轮外框的发动机、燃油、悬挂、轮胎图标，以及动物徽章和 Gaskellgames 标识。XML 还包含减伤倍率等游戏增益行为；本任务只需美术，不应把这些配置带入运行版本。

图像头记录色彩贴图为 500×500。此次快速 BC7/BC3 解码尝试能看见形状，但有明显颜色/像素异常，因此 **`inspection/gg_decoded/` 全部只是失败的格式检查输出，不可当正式美术源使用**；manifest 中已标为 `REJECTED_COLOR_DECODE_NOT_VERIFIED`。没有继续逆向其他可能的编码，保留原包供后续正式转换。不能把异常颜色误说成作者原配色或原有磨损。

## 实际发现的作者/再分发说明

Better Stickers 的 `readme.txt` 给出作者 [StickerGuy](https://mod.io/u/stickerguy/)、[Ko-Fi](https://ko-fi.com/thestickerguy)，感谢 nakedDave 的 Easy Sticker Generator；其余是安装说明。该 readme 没有声明跨项目再分发许可证。

GG 两层归档内未找到以 license/readme/copyright 命名的说明文件，所查 XML 没有发现再分发许可文本。Gaskellgames 名称出现在配置与标识中，但它不是许可证声明。

用户已明确提供资产并要求在本地作品中挑选使用，本次检查没有把“未找到许可”当作本地使用的额外审批障碍。以上仅记录将来公开上传资产时需要准确呈现的来源与许可状态：本次未发现明确通用再分发条款，不应把这些第三方图案声明为本项目原创或自行附上开源许可证。
