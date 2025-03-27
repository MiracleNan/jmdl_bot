import os
import json
import tempfile
from nonebot import on_command
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Bot, Message
from nonebot.adapters.onebot.v11 import MessageSegment
from wordcloud import WordCloud

Xp = on_command(cmd="xp",aliases={"tags","Xp"},priority=5)

@Xp.handle()
async def Xp_send(bot: Bot, event: GroupMessageEvent, state: T_State):
    
    tags_dic={}
    current_dir = os.path.dirname(os.path.abspath(__file__))
    tags_dir = os.path.join(current_dir, "onebot_plugin_jmdown/tags")
    file_path = os.path.join(tags_dir, f'{event.group_id}.txt')
    if os.path.isfile(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                tags_dic = json.load(file)
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            wordcloud = WordCloud(
            prefer_horizontal=0.8,
            width=1000, 
            height=600, 
            background_color='white', 
            font_path='/usr/share/fonts/opentype/noto/NotoSansCJK-Light.ttc',#ubuntu22自带字体，若不存在请更改为合适路径
            max_words=100,
            ).generate_from_frequencies(tags_dic)
            
            wordcloud.to_file(temp_path)
            await bot.send_group_msg(group_id=event.group_id,message=Message(MessageSegment.image(temp_path)))
        finally:
        # 使用后手动清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        return
    else:
        await Xp.finish(message=Message(MessageSegment.at(event.user_id)+Message("本群还没有人请求过本子")))
    
