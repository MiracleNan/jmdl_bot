from nonebot import on_regex
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Bot, Message
from nonebot.adapters.onebot.v11 import MessageSegment


Help = on_regex(pattern=r'^/(help|Help|帮助)\s*$|^帮助\s*$', priority=1)


@Help.handle()
async def Help_send(bot: Bot, event: GroupMessageEvent, state: T_State):
    msg = (
        "📚 JMDL Bot 命令列表：\n"
        "\n"
        "📥 /jm <ID> - 下载本子\n"
        "🔍 /jms [noai] <关键词> [页码] [排序] - 标题搜索\n"
        "🏷 /jmstag [noai] <标签> [页码] [排序] - 标签搜索\n"
        "🏆 /jmrank [all|day|week|month] - 排行\n"
        "📖 /jminfo <ID> - 详情\n"
        "☁ /xp /tags - 群友XP词云\n"
        "📊 /status - 系统状态\n"
        " 排序: mr=最新 mv=最多浏览 mp=最多图片 tf=最多喜欢"
    )
    await Help.finish(message=Message(MessageSegment.at(event.user_id) + Message(msg)))
