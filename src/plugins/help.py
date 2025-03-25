from nonebot import on_command
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Bot, Message
from nonebot.adapters.onebot.v11 import MessageSegment


Help = on_command(cmd="help",aliases={"Help","帮助"},priority=1)

@Help.handle()
async def Help_send(bot: Bot, event: GroupMessageEvent, state: T_State):
   msg="\n输入'/jm id' 获取本子\neg: /jm 114514\n下载发送需要时间，请不要重复请求\npdf文件命名规则为：密码_漫画名"
   await Help.finish(message=Message(MessageSegment.at(event.user_id)+Message(msg)))
