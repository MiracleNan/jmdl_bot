# -*- coding: utf-8 -*-
"""
Author: MiracleNan
Email: 2127610576@qq.com
GitHub: https://github.com/MiracleNan/jmdl_bot
Created: 2025-03-27
Description: A NoneBot plugin for handling /jm commands to download comics and upload them to group files.
Copyright: © 2025 <Your Name>. All rights reserved.
"""
import re
import os
import time
import uuid
import shutil
import asyncio
import json
import datetime
import psutil
import jmcomic
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from nonebot import on_regex
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Bot, Message, MessageSegment
from jmcomic import JmAlbumDetail
from pikepdf import Pdf, Encryption
from .func import clear, read_option_yml
from .pdf_func import encrypt_pdf
from .comic import *

# 日志文件路径
LOG_FILE = "/opt/jmdl_bot/books/bot.log"

# 频率限制: 防重复请求
_last_request = {}  # {key: timestamp}
RATE_LIMITS = {
    "jm": 10,    # /jm 下载: 10秒冷却  (防止队列堆积)
    "jms": 3,    # /jms 搜索: 3秒冷却
    "jmrank": 3, # /jmrank 排行: 3秒冷却
    "jminfo": 2, # /jminfo 详情: 2秒冷却
}

def check_rate_limit(user_id: int, cmd: str) -> tuple[bool, int]:
    """检查频率限制, 返回 (是否放行, 剩余冷却秒数)"""
    key = f"{user_id}:{cmd}"
    now = time.time()
    limit = RATE_LIMITS.get(cmd, 3)
    if key in _last_request:
        elapsed = now - _last_request[key]
        if elapsed < limit:
            return False, int(limit - elapsed)
    _last_request[key] = now
    # 清理过期记录
    if len(_last_request) > 500:
        _last_request.clear()
    return True, 0

def add_log(level, msg):
    """写入日志文件"""
    time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{time_str}] [{level}] {msg}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except:
        pass
    print(f"[{level}] {msg}")

def add_history(name, manga_id, status, size_mb=0):
    """写入历史记录文件"""
    import json
    history_file = "/opt/jmdl_bot/books/history.json"
    try:
        history = []
        if os.path.exists(history_file):
            with open(history_file, "r") as f:
                history = json.load(f)
        history.insert(0, {
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "name": name,
            "manga_id": manga_id,
            "status": status,
            "size_mb": round(size_mb, 2)
        })
        history = history[:100]  # 只保留100条
        with open(history_file, "w") as f:
            json.dump(history, f, ensure_ascii=False)
    except:
        pass

Jm = on_regex(pattern=r'^/jm\s+(\d+)$', priority=1)

file_locks = {}

yml_path = os.path.join(os.path.dirname(__file__), "option.yml")
_config = read_option_yml(yml_path)
if _config is None:
    raise RuntimeError(f"无法读取配置文件: {yml_path}，请检查 option.yml 格式")
_, pdf_dir = _config

# 设置最大响应数为 MAX_QUEUE_SIZE
MAX_QUEUE_SIZE = 5
task_queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
_queue_started = False
_processing = None  # 当前处理中的任务信息
last_clear_time = 0
CLEAR_INTERVAL = 300  # 清理间隔（秒）

# 设置最大下载任务数为 max_workers
executor = ThreadPoolExecutor(max_workers=2)  

def download_album_sync(manga_id, option):
    jmcomic.download_album(manga_id, option)

async def check_and_clear(threshold=30):

    global last_clear_time
    current_time = asyncio.get_event_loop().time()
    
    if current_time - last_clear_time >= CLEAR_INTERVAL:
        disk = psutil.disk_usage(pdf_dir)
        free_disk = disk.free / (1024 ** 3)  # GB
        print(f"Disk free space: {free_disk:.2f} GB")
        
        if free_disk < threshold:
            result = clear(threshold)
            if result == 0:
                print("Disk cleanup successful")
            else:
                print("Disk cleanup failed")
        last_clear_time = current_time

async def check_is_admin(bot, group_id, self_id):
    """检查 bot 是否是群管理员"""
    try:
        info = await bot.call_api("get_group_member_info", group_id=group_id, user_id=self_id)
        return info.get("role") in ("owner", "admin")
    except:
        return False


async def safe_delete(bot, msg_ids):
    """安全撤回消息（忽略错误）"""
    for mid in msg_ids:
        try:
            if mid:
                await bot.call_api("delete_msg", message_id=mid)
        except:
            pass


async def process_queue():
    while True:
        try:
            global _processing
            bot, group_id, user_id, manga_id, name, tags, queue_msg_id = await task_queue.get()
            _processing = {"name": name, "manga_id": manga_id, "started": datetime.datetime.now().isoformat()}
            add_log("INFO", f"开始处理: {name} (ID:{manga_id})")

            file_name = f"{name}.pdf"
            temp_file_name = f"{manga_id}_{user_id}_{uuid.uuid4().hex[:8]}.pdf"
            full_path = os.path.join(pdf_dir, temp_file_name)
            default_path = os.path.join(pdf_dir, file_name)
            print(default_path)
            output_pdf_path = None
            interim_msg_ids = [queue_msg_id] if queue_msg_id else []

            # WebUI 触发或 bot 不可用时的保护
            if bot is None:
                add_log("WARN", f"WebUI 触发下载，跳过群文件上传: {name}")
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(executor, download_album_sync, manga_id, jmcomic.create_option_by_file(yml_path))
                await asyncio.sleep(1)
                if os.path.exists(default_path):
                    shutil.move(default_path, full_path)
                    password, output_pdf_path = encrypt_pdf(full_path)
                    file_size = os.path.getsize(output_pdf_path) / (1024 * 1024)
                    add_log("SUCCESS", f"WebUI下载完成: {name} ({file_size:.1f}MB) 密码: {password}")
                    add_history(name, manga_id, "success", file_size)
                _processing = None
                task_queue.task_done()
                continue

            try:
                groupfiles = await bot.call_api("get_group_root_files", group_id=group_id)
                # 去重：用上传时的实际文件名 (password_mangaId.pdf) 来比对
                group_file_names_set = set()
                for f in groupfiles['files']:
                    # 新的格式: password_mangaId.pdf, 旧的格式: password_name.pdf
                    # 统一提取 mangaId 进行比对
                    fname = f['file_name']
                    if '_' in fname:
                        rest = fname.rsplit('.', 1)[0]  # 去掉 .pdf
                        if '_' in rest:
                            parts = rest.split('_')
                            if parts[-1].isdigit():
                                group_file_names_set.add(parts[-1])  # manga_id

                if manga_id in group_file_names_set:
                    add_log("WARN", f"文件已存在: {name}")
                    await bot.send_group_msg(group_id=group_id, message=Message([MessageSegment.at(user_id), MessageSegment.text(f" 你查询的漫画：{name} 已存在于群文件")]))
                    continue

                await check_and_clear(30)

                option = jmcomic.create_option_by_file(yml_path)
                loop = asyncio.get_event_loop()

                with get_file_lock(group_id, file_locks):
                    await loop.run_in_executor(executor, count_tag, tags, f"{group_id}.txt")

                add_log("INFO", f"正在下载: {name}")
                await loop.run_in_executor(executor, download_album_sync, manga_id, option)
                await asyncio.sleep(1)

                if not os.path.exists(default_path):
                    add_log("ERROR", f"下载失败: {name}")
                    add_history(name, manga_id, "failed")
                    await bot.send_group_msg(group_id=group_id, message=Message([MessageSegment.at(user_id), MessageSegment.text(f" 下载 {name} 失败，文件未生成")]))
                    continue

                shutil.move(default_path, full_path)

                password, output_pdf_path = encrypt_pdf(full_path)
                file_size = os.path.getsize(output_pdf_path) / (1024 * 1024)
                add_log("SUCCESS", f"打包完成: {name} ({file_size:.1f}MB)")

                pack_msg = await bot.send_group_msg(group_id=group_id, message=Message([MessageSegment.text(f" 📦 {name[:30]}... 打包完成，上传中...")]))
                if pack_msg and isinstance(pack_msg, dict) and 'message_id' in pack_msg:
                    interim_msg_ids.append(pack_msg['message_id'])

                upload_name = f"{password}_{manga_id}.pdf"
                add_log("INFO", f"正在上传: {name}")
                await bot.call_api(
                    "upload_group_file",
                    group_id=group_id,
                    file=output_pdf_path,
                    name=upload_name
                )
                add_log("SUCCESS", f"上传完成: {name}")
                add_history(name, manga_id, "success", file_size)

                asyncio.create_task(safe_delete(bot, interim_msg_ids))

                await bot.send_group_msg(group_id=group_id, message=Message([MessageSegment.at(user_id), MessageSegment.text(f" {name} ({file_size:.1f}MB) 已上传群文件，密码: {password}")]))

            except Exception as e:
                print(f"Error processing {name}: {str(e)}")
                add_log("ERROR", f"处理失败: {name} - {str(e)}")
                add_history(name, manga_id, "failed")
                if "timeout" in str(e).lower():
                    await bot.send_group_msg(group_id=group_id, message=Message([MessageSegment.at(user_id), MessageSegment.text(f" {name} 文件过大，若稍后未发送请换jm号重试")]))
                else:
                    await bot.send_group_msg(group_id=group_id, message=Message([MessageSegment.at(user_id), MessageSegment.text(f" {name} 文件上传失败：{str(e)}")]))

            finally:
                if os.path.exists(full_path):
                    os.remove(full_path)
                if output_pdf_path and os.path.exists(output_pdf_path):
                    os.remove(output_pdf_path)
                _processing = None
                task_queue.task_done()

        except Exception as e:
            print(f"Queue processor error: {e}")
            await asyncio.sleep(1)

async def start_queue_processor():
    global _queue_started
    if not _queue_started:
        _queue_started = True
        asyncio.create_task(process_queue())

@Jm.handle()
async def Jm_send(bot: Bot, event: GroupMessageEvent, state: T_State):
    await start_queue_processor()

    group_id = event.group_id
    user_id = event.user_id

    match = re.match(r'^/jm\s+(\d+)$', str(event.get_message()).strip())

    if match:
        # 频率限制检查
        allowed, cooldown = check_rate_limit(user_id, "jm")
        if not allowed:
            await Jm.finish(Message([MessageSegment.at(user_id), MessageSegment.text(f" 请勿频繁请求，{cooldown}秒后再试")]))
            return

        manga_id = match.group(1)
        loop = asyncio.get_event_loop()
        jminfo = await loop.run_in_executor(executor, get_comic_info, manga_id)

        if "error" in jminfo:
            await Jm.finish(Message([MessageSegment.at(user_id), MessageSegment.text(" Jm号不存在或输入错误")]))
            return

        name = jminfo['name']
        tags = jminfo['tags']
        if task_queue.full():
            await Jm.finish(Message([MessageSegment.at(user_id), MessageSegment.text(f" 队列已满（最大 {MAX_QUEUE_SIZE} 个任务），请稍后再试")]))
            return

        # 发送加入队列的消息并捕获 message_id
        queue_msg = await bot.send_group_msg(group_id=group_id, message=Message([MessageSegment.at(user_id), MessageSegment.text(f" 已加入队列：{name}（当前队列：{task_queue.qsize() + 1}/{MAX_QUEUE_SIZE}），排队中...")]))
        queue_msg_id = queue_msg.get('message_id', 0) if isinstance(queue_msg, dict) else 0

        await task_queue.put((bot, group_id, user_id, manga_id, name, tags, queue_msg_id))
        add_log("INFO", f"加入队列: {name} (ID:{manga_id}) 队列:{task_queue.qsize()}/{MAX_QUEUE_SIZE}")
        await Jm.finish()


# ============ 新增命令 ============

JmSearch = on_regex(pattern=r'^/jms\s+(.+)$', priority=5)
JmTag = on_regex(pattern=r'^/jmstag\s+(.+)$', priority=5)
JmRank = on_regex(pattern=r'^/jmrank(\s+.*)?$', priority=5)
JmInfo = on_regex(pattern=r'^/jminfo\s+(\S+)$', priority=5)


@JmTag.handle()
async def JmTag_send(bot: Bot, event: GroupMessageEvent, state: T_State):
    match = re.match(r'^/jmstag\s+(.+)$', str(event.get_message()).strip())
    if not match:
        return
    user_id = event.user_id
    allowed, cooldown = check_rate_limit(user_id, "jms")
    if not allowed:
        await JmTag.finish(Message([MessageSegment.at(user_id), MessageSegment.text(f" 搜索太频繁，{cooldown}秒后再试")]))
        return

    args = match.group(1).split()
    noai = False
    if args[0].lower() == 'noai':
        noai = True
        args = args[1:]

    if not args:
        await JmTag.finish("用法: /jmstag [noai] <标签> [页码] [排序:mr/mv/mp/tf]")
        return

    valid_orders = {"mr", "mv", "mp", "tf"}
    order = "mr"
    page = 1
    tail_count = 0
    if args[-1] in valid_orders:
        order = args[-1]; tail_count += 1
    idx = len(args) - 1 - tail_count
    if idx >= 0 and args[idx].isdigit():
        page = int(args[idx]); tail_count += 1
    tag = " ".join(args[:len(args) - tail_count]) if tail_count > 0 else " ".join(args)

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, search_comic_by_tag, tag, page, order, noai)

    if "error" in result:
        await JmTag.finish(result["error"])
        return
    if not result["results"]:
        await JmTag.finish(f"未找到标签 '{tag}' 的结果")
        return

    order_map = {"mr": "最新", "mv": "最多浏览", "mp": "最多图片", "tf": "最多喜欢"}
    order_name = order_map.get(order, order)
    text = f"🏷 标签: {tag}{' · 无AI' if noai else ''} | {order_name} | 第{page}页/{result['page_count']}页\n"
    for i, r in enumerate(result["results"], 1):
        name_display = r['name'] if len(r['name']) <= 45 else r['name'][:42] + "..."
        text += f"\n{i}. [{r['id']}] {name_display}"

    text += f"\n\n📥 /jm <ID> 即可下载 | /jminfo <ID> 查看详情"
    await JmTag.finish(Message(text))


@JmSearch.handle()
async def JmSearch_send(bot: Bot, event: GroupMessageEvent, state: T_State):
    match = re.match(r'^/jms\s+(.+)$', str(event.get_message()).strip())
    if not match:
        return
    user_id = event.user_id
    args = match.group(1).split()
    noai = False

    # 检查 noai 前缀
    if args[0].lower() == 'noai':
        noai = True
        args = args[1:]

    if not args:
        await JmSearch.finish("用法: /jms [noai] <关键词> [页码] [排序:mr/mv/mp/tf]")
        return

    # 频率限制
    allowed, cooldown = check_rate_limit(user_id, "jms")
    if not allowed:
        await JmSearch.finish(Message([MessageSegment.at(user_id), MessageSegment.text(f" 搜索太频繁，{cooldown}秒后再试")]))
        return

    # 解析: 最后参数可能是排序/页码，其余是关键词
    order = "mr"
    page = 1
    tail_count = 0  # 末尾被识别为参数的数量

    valid_orders = {"mr", "mv", "mp", "tf"}

    # 看最后一个是不是排序
    if args[-1] in valid_orders:
        order = args[-1]
        tail_count += 1

    # 看倒数第N个是不是页码
    idx = len(args) - 1 - tail_count
    if idx >= 0 and args[idx].isdigit():
        page = int(args[idx])
        tail_count += 1

    # 其余的作为关键词
    query = " ".join(args[:len(args) - tail_count]) if tail_count > 0 else " ".join(args)

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, search_comic_smart, query, page, order, noai)

    if "error" in result:
        await JmSearch.finish(result["error"])
        return

    if not result["results"]:
        suffix = " (已过滤AI)" if noai else ""
        await JmSearch.finish(f"未找到与 '{query}' 相关的结果{suffix}")
        return

    order_map = {"mr": "最新", "mv": "最多浏览", "mp": "最多图片", "tf": "最多喜欢"}
    order_name = order_map.get(order, order)
    noai_label = " · 无AI" if noai else ""
    text = f"🔍 搜索: {query}{noai_label} | {order_name} | 第{page}页/{result['page_count']}页\n"
    for i, r in enumerate(result["results"], 1):
        name_display = r['name'] if len(r['name']) <= 45 else r['name'][:42] + "..."
        text += f"\n{i}. [{r['id']}] {name_display}"

    text += f"\n\n📥 /jm <ID> 即可下载"
    await JmSearch.finish(Message(text))


@JmRank.handle()
async def JmRank_send(bot: Bot, event: GroupMessageEvent, state: T_State):
    match = re.match(r'^/jmrank(\s+(.*))?$', str(event.get_message()).strip())
    if not match:
        return
    args = (match.group(2) or "").split()
    time_type = args[0] if args else "week"
    page = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1

    time_map = {"all": "a", "day": "t", "日": "t", "week": "w", "周": "w", "month": "m", "月": "m"}
    time_code = time_map.get(time_type, "w")
    time_name = {"a": "总榜", "t": "日榜", "w": "周榜", "m": "月榜"}.get(time_code, time_type)

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, get_ranking, time_code, page)

    if "error" in result:
        await JmRank.finish(result["error"])
        return

    if not result["results"]:
        await JmRank.finish(f"🏆 JM {time_name} 暂无数据")
        return

    text = f"🏆 JM {time_name} TOP10 | 第{page}页\n"
    for i, r in enumerate(result["results"], 1):
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        medal = medals.get(i, f"{i}.")
        text += f"\n{medal} [{r['id']}] {r['name'][:35]}"

    text += f"\n\n📥 /jm <ID> 即可下载"
    await JmRank.finish(Message(text))


@JmInfo.handle()
async def JmInfo_send(bot: Bot, event: GroupMessageEvent, state: T_State):
    match = re.match(r'^/jminfo\s+(\S+)', str(event.get_message()).strip())
    if not match:
        return

    manga_id = match.group(1)
    if not manga_id.isdigit():
        await JmInfo.finish("用法: /jminfo <ID> (纯数字)")
        return

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, get_comic_detail, manga_id)

    if "error" in result:
        await JmInfo.finish(result["error"])
        return

    text = f"📖 {result['name']}\n"
    text += f"作者: {result['author']}\n"
    text += f"页数: {result['pages']} | 章节: {result['chapters']}\n"
    text += f"❤ {result['likes']} | 👁 {result['views']}\n"
    if result.get('pub_date'):
        text += f"日期: {result['pub_date']}\n"
    tags_str = ', '.join(result['tags'][:8]) if result['tags'] else '无'
    text += f"Tags: {tags_str}\n"

    text += f"\n📥 /jm {manga_id} 即可下载"
    await JmInfo.finish(Message(text))