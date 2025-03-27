from jmcomic import JmAlbumDetail,JmOption
import jmcomic
import os
import yaml
import json
from nonebot import on_regex
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Bot, Message,MessageSegment

def get_comic_info(comic_id):
    try:
        page = JmOption.default().new_jm_client().search_site(search_query=str(comic_id))
        album: JmAlbumDetail = page.single_album
        
        result = {
            "name": album.name,
            "author": album.author,
            "tags": album.tags
        }
        return result
    
    except Exception as e:
        return {"error": f"查询失败: {str(e)}. 可能ID不存在"}

def count_tag(tags, filename="tags.txt"):
    current_dir = os.getcwd()
    tags_dir = os.path.join(current_dir, "tags")

    if not os.path.exists(tags_dir):
        try:
            os.makedirs(tags_dir, exist_ok=True)
            print(f"创建文件夹: {tags_dir}")
        except Exception as e:
            print(f"创建文件夹 {tags_dir} 失败: {e}")
            return {}

    file_path = os.path.join(tags_dir, filename)

    dic = {}

    if os.path.isfile(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            dic = json.load(file)

    for tag in tags:
        dic[tag] = dic.get(tag, 0) + 1

    try:
        with open(file_path, "w", encoding='utf-8') as f:
            json.dump(dic, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"写入 {file_path} 时发生错误: {e}")

    return dic