# 素材版权说明（NOTICE）

本仓库的 **代码** 以 MIT 协议发布（见 [LICENSE](LICENSE)）。
**下面这些内容不在 MIT 范围内**，版权归《夏末白夜》原作方所有，收录它们只是为了让仓库能直接构建出可运行的包。

## 不在 MIT 范围内的内容

| 路径 | 内容 | 来源 |
|---|---|---|
| `src/common/story/*.txt` | 全部剧本文字（13,162 句台词 / 33.4 万字） | PC 版 `_story/*.rpyc` 解包后编译 |
| `src/common/img/b/` | 背景图 30 张 | PC 版 `images/`、`bgm/` 等 `.rpa` 解包 |
| `src/common/img/s/` | 立绘与表情差分（4 名角色 213 张 + 店长 4 姿） | 同上 |
| `src/common/img/w/`、`img/t/` | CG 原图与缩略图 13 组 | 同上 |
| `src/common/img/ui/` | 首页背景、标题 logo、应用图标 | PC 版 `gui/`（`main_menu`、`pc/logo`、`window_icon`） |
| `preview/*.png` | 用上述素材合成的界面预览图 | —— |

## 可以自由使用的部分（MIT）

- `src/pages/**/*.ux`：7 个页面
- `src/common/reader.js`、`vm.js`、`assets.js`（`assets.js` 是生成文件，但生成逻辑在 `tools/` 里）
- `src/app.ux`、`src/manifest.json`
- `tools/**`：解包、编译、出图、校验、构建脚本
- `sim/**`：浏览器模拟器
- 全部文档（`README.md`、`NOTICE.md`、`LICENSE`）

## 使用建议

- 拿这套代码去做**自己的** VN 移植完全没问题：把 `src/common/img/` 和 `src/common/story/` 换成你自己的
  素材与剧本，改一下 `manifest.json` 的包名和 `assets.js` 的索引即可。
- **不要**把这批素材用于任何商业用途，也不要单独再分发素材。
- 如果版权方有异议，删除上表列出的目录即可，代码本身不依赖具体内容。
