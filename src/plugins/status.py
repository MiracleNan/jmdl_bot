import asyncio
from concurrent.futures import ThreadPoolExecutor
from nonebot import on_command
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Bot, Message
from nonebot.adapters.onebot.v11 import MessageSegment
import psutil
from jmcomic import JmAlbumDetail, JmOption

_status_executor = ThreadPoolExecutor(max_workers=2)

def get_cpu_usage():
    return psutil.cpu_percent(interval=None)

def get_memory_usage():
    memory = psutil.virtual_memory()
    return memory.percent, memory.total / (1024 ** 3), memory.used / (1024 ** 3)

def get_disk_usage():
    disk = psutil.disk_usage('/')
    free_disk = disk.free / (1024 ** 3)
    return free_disk

def netcheck():
    try:
        client = JmOption.default().new_jm_client()
        album: JmAlbumDetail = client.get_album_detail(str(114514))
        result = {
            "name": album.name,
            "author": album.author,
            "tags": album.tags
        }
    except Exception as e:
        result = {"error": f"查询失败: {str(e)}. 可能ID不存在，或需要登录查看隐藏内容"}
    if "error" in result:
        return "异常"
    else:
        return "正常"

Status = on_command(cmd="status", aliases={"状态", "性能"}, priority=10)

@Status.handle()
async def Status_send(bot: Bot, event: GroupMessageEvent, state: T_State):
    loop = asyncio.get_event_loop()
    # 并行执行系统检查和网络检查，避免阻塞事件loop
    cpu_future = loop.run_in_executor(_status_executor, get_cpu_usage)
    net_future = loop.run_in_executor(_status_executor, netcheck)

    cpu = get_cpu_usage()
    mem_percent, mem_total, mem_used = get_memory_usage()
    free_disk = get_disk_usage()

    result = f"CPU:{cpu}% 内存:{mem_percent}%({mem_used:.1f}/{mem_total:.1f}GB) 剩余硬盘:{free_disk:.1f}GB"
    await bot.send_group_msg(group_id=event.group_id, message=Message(result))

    net_status = await net_future
    await Status.finish(message=Message(f"与jm连接{net_status}"))
