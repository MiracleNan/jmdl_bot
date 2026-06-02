# JMDL Bot

基于 [NoneBot2](https://nonebot.dev/) + [jmcomic](https://github.com/hect0x7/JMComic-Crawler-Python) 的 QQ 群聊漫画下载机器人。

## 功能

| 命令 | 说明 | 示例 |
|------|------|------|
| `/jm <ID>` | 下载漫画 → 打包PDF → 加密上传群文件 | `/jm 114514` |
| `/jms <关键词> [页码] [排序]` | 搜索漫画 | `/jms 汉化 1 mv` |
| `/jmrank [all\|day\|week\|month]` | 排行榜 TOP10 | `/jmrank week` |
| `/jminfo <ID>` | 查看漫画详情 | `/jminfo 114514` |
| `/xp` / `/tags` | 群友XP标签词云 | `/xp` |
| `/status` | 系统状态（CPU/内存/磁盘） | `/status` |
| `/help` | 帮助信息 | `/help` |

### 后台管理

```
http://<服务器IP>:8080/admin
```

功能：系统监控、实时日志、命令测试台、文件管理、下载历史

## 部署

### Docker 部署（推荐）

```bash
git clone https://github.com/MiracleNan/jmdl_bot.git
cd jmdl_bot

# 1. 配置 option.yml
vim src/plugins/onebot_plugin_jmdown/option.yml

# 2. 配置 NapCat (QQ 协议端)
# https://github.com/NapNeko/NapCatQQ

# 3. 启动
docker compose -f docker-compose.yml up -d --build
```

### 手动部署

```bash
pip install "nonebot2[fastapi]" nonebot-adapter-onebot jmcomic img2pdf wordcloud pikepdf psutil pyyaml
nb run
```

## 架构

```
QQ 群 ←→ NapCatQQ (OneBot V11) ←→ NoneBot2 ←→ jmcomic (爬虫)
                                    ↓
                              FastAPI :8080 (后台管理)
```

## License

MIT
