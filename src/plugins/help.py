from nonebot import on_regex
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Bot, Message
from nonebot.adapters.onebot.v11 import MessageSegment


Help = on_regex(pattern=r'^/help$|^/Help$|^帮助$', priority=1)


@Help.handle()
async def Help_send(bot: Bot, event: GroupMessageEvent, state: T_State):
    msg = (
        "📚 JMDL Bot 命令列表：\n"
        "\n"
        "📥 /jm <ID> - 下载本子\n"
        "  例: /jm 114514\n"
        "🔍 /jms <关键词> [页码] [排序] - 搜索\n"
        "  例: /jms 汉化  排序: mr/mv/mp/tf\n"
        "🏆 /jmrank [all|day|week|month] - 排行\n"
        "  例: /jmrank week\n"
        "📖 /jminfo <ID> - 详情\n"
        "  例: /jminfo 114514\n"
        "🏷 /xp 或 /tags - 群友XP词云\n"
        "📊 /status - 系统状态\n"
        "🖥 /admin - 后台管理: http://192.168.1.195:8080/admin"
    )
    await Help.finish(message=Message(MessageSegment.at(event.user_id) + Message(msg)))
