from nonebot import on_command
from .func import echo_message  # 从 func.py 导入功能

# 注册消息事件处理器
echo = on_command(cmd="echo",priority=10, block=False)

@echo.handle()
async def handle_echo(bot, event):
    await echo_message(bot, event)  # 调用 func.py 中的逻辑