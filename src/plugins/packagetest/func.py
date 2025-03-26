from nonebot.adapters.onebot.v11 import Bot, Event

async def echo_message(bot: Bot, event: Event):
    message = event.get_plaintext()
    if message:  # 确保消息不为空
        await bot.send(event, message)