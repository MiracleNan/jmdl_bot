import re
from nonebot import on_regex
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Bot, Message
from nonebot.adapters.onebot.v11 import MessageSegment
import os
import jmcomic
from jmcomic import JmAlbumDetail
from PIL import Image
from time import sleep
import shutil
from picfunc import *

Jm = on_regex(pattern=r'^/jm\s+(\d+)$',priority=1)

path = os.path.join(os.path.dirname(__file__), 'D:/code/jmcomic/option.yml')
client = jmcomic.create_option(path).new_jm_client()
base_path = r"D:\Books\pdf"

clear()

@Jm.handle()
async def Jm_send(bot: Bot, event: GroupMessageEvent, state: T_State):
   
    user_msg = str(event.get_message()).strip()
    match = re.match(r'^/jm\s+(\d+)$', user_msg)
   
    if match:
        # 提取 ID 并将其返回为对象
        manga_id = match.group(1)
        result = get_comic_info(manga_id)
       
        if "error" in result:
            msg = "id不存在或输入错误"
            await Jm.finish(message=Message(msg))
        else:
            # msg = f"漫画名称: {result['name']}-作者: {result['author']}"
            name=result['name']
            option = jmcomic.create_option_by_file('D:/code/jmcomic/option.yml')
            jmcomic.download_album(manga_id,option)

            file_name = f"{name}.pdf"
            full_path = os.path.join(base_path, file_name)
            try:
                # 调用 upload_group_file API 上传文件
                await bot.call_api(
                    "upload_group_file",
                    group_id=event.group_id,
                    file=full_path,
                    name=file_name
        )
        # 上传成功后发送消息通知
                await Jm.finish(f"你需要的 {file_name} 已发送")
            except Exception as e:
        # 上传失败时返回错误信息
                if str(e)=="FinishedException()":
                    return
                await Jm.finish(f"文件上传失败：{str(e)}") 
            # paths=split_image_if_too_long(full_path, max_length=10000)
            # messages=[]
            # finalmsg=Message(name)
            # for path in paths:
            #     finalmsg+=Message(MessageSegment.image(path))
            
            # await Test.finish(message=Message(finalmsg))      

