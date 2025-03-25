# import re
# from nonebot import on_regex,on_command
# from nonebot.typing import T_State
# from nonebot.adapters.onebot.v11 import GroupMessageEvent, Bot, Message
# from nonebot.adapters.onebot.v11 import MessageSegment
# import os


# Test = on_command(cmd="test",priority=1)

# @Test.handle()
# async def Test_send(bot: Bot, event: GroupMessageEvent, state: T_State):
#    result = await bot.call_api("get_group_root_files", group_id=event.group_id)
#    print(result)
#    await Test.finish(message=Message())
