# A股风格轮动盯盘仪表盘 — GitHub Pages 部署指南

## 一键部署步骤

### 1. 创建 GitHub 仓库

在 [GitHub](https://github.com/new) 新建一个 **Public** 仓库，名称随意（如 `a-share-dashboard`）。

### 2. 推送代码

```bash
# 在项目目录下初始化 git（如果还没有）
git init
git add .
git commit -m "Initial commit: A股风格轮动盯盘仪表盘"

# 关联你的 GitHub 仓库（替换 YOUR_USERNAME/YOUR_REPO）
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

### 3. 启用 GitHub Pages

1. 打开仓库 → **Settings** → **Pages**
2. **Source**: `Deploy from a branch`
3. **Branch**: `main`，目录选 `/ (root)`
4. 点击 **Save**

等待 1-2 分钟，你的仪表盘就在 `https://YOUR_USERNAME.github.io/YOUR_REPO/` 上线了。

### 4. 验证自动刷新

GitHub Actions 会在每个交易日 **北京时间 16:30** 自动运行：
- 抓取最新指数数据
- 重新生成仪表盘
- 自动提交并部署

你也可以在仓库的 **Actions** 标签页手动点击 `Run workflow` 立即触发。

## 文件说明

| 文件 | 作用 |
|------|------|
| `fetch_data.py` | 用 akshare 抓取 13 个指数历史数据 → `data/style_indices_v2.csv` |
| `gen_data.py` | 读 CSV，计算均线/动量/信号 → `dashboard_data.json` |
| `build_html.py` | 读 JSON，生成 HTML 仪表盘 + JS 数据文件 |
| `dashboard.html` | 盯盘仪表盘（Chart.js 图表 + 信号面板） |
| `dashboard_data.js` | `const DATA = {...}` 数据文件 |
| `index.html` | GitHub Pages 入口（= dashboard.html 的副本） |
| `.github/workflows/daily_update.yml` | 自动刷新工作流 |

## 本地运行

```bash
pip install akshare pandas numpy
python fetch_data.py      # 抓取数据
python gen_data.py        # 生成 JSON
python build_html.py      # 生成 HTML
# 浏览器打开 dashboard.html
```

## 自定义

- 修改 `.github/workflows/daily_update.yml` 中的 `cron` 可调整刷新时间
- 修改 `gen_data.py` 中的评分逻辑可自定义信号规则
