import re
from nonebot import on_regex,on_command
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Bot, Message
from nonebot.adapters.onebot.v11 import MessageSegment
import os


Test = on_command(cmd="test",priority=1)

@Test.handle()
async def Test_send(bot: Bot, event: GroupMessageEvent, state: T_State):
   await Test.finish(message=Message(f"Bot online,group_id{event.group_id}"))
