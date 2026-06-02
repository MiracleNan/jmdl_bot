import os
import json
from nonebot import on_regex
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Bot, Message
from nonebot.adapters.onebot.v11 import MessageSegment

Xp = on_regex(pattern=r'^/xp$|^/tags$|^/Xp$', priority=5)


def _find_cjk_font():
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Light.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


@Xp.handle()
async def Xp_send(bot: Bot, event: GroupMessageEvent, state: T_State):
    tags_dic = {}
    temp_path = None
    current_dir = os.path.dirname(os.path.abspath(__file__))
    tags_dir = os.path.join(current_dir, "onebot_plugin_jmdown/tags")
    file_path = os.path.join(tags_dir, f'{event.group_id}.txt')

    if not os.path.isfile(file_path):
        await Xp.finish(message=Message(MessageSegment.at(event.user_id) + Message(" 本群还没有人请求过本子")))
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tags_dic = json.load(f)

        if not tags_dic:
            await Xp.finish(message=Message(MessageSegment.at(event.user_id) + Message(" 暂无标签数据")))
            return

        font_path = _find_cjk_font()

        from wordcloud import WordCloud
        wc = WordCloud(
            prefer_horizontal=0.8,
            width=800,
            height=500,
            background_color='white',
            max_words=80,
            font_path=font_path,
        )
        wc.generate_from_frequencies(tags_dic)

        # 保存到共享目录，NapCat 容器才能访问
        temp_path = f"/opt/jmdl_bot/books/xp_{event.group_id}.png"
        wc.to_file(temp_path)

        await bot.send_group_msg(group_id=event.group_id, message=Message(MessageSegment.image(temp_path)))

    except Exception as e:
        # 如果图片生成失败，回退为文字列表
        sorted_tags = sorted(tags_dic.items(), key=lambda x: x[1], reverse=True)
        top_tags = sorted_tags[:15]
        text = "🏷 群友XP统计 TOP15:\n"
        for tag, count in top_tags:
            text += f"{tag}: {count}次\n"
        text += f"\n共 {len(sorted_tags)} 个标签"
        await Xp.finish(message=Message(text))

    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
