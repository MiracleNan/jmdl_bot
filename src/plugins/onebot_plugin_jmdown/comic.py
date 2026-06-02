from jmcomic import JmAlbumDetail, JmOption
import jmcomic
import os
import yaml
import json
from threading import Lock

def get_file_lock(group_id, file_locks):
    return file_locks.setdefault(group_id, Lock())

def get_comic_info(comic_id):
    try:
        client = JmOption.default().new_jm_client()
        album: JmAlbumDetail = client.get_album_detail(str(comic_id))

        result = {
            "name": album.name,
            "author": album.author,
            "tags": album.tags,
            "episode_count": len(album.episode_list)
        }
        return result

    except Exception as e:
        return {"error": f"查询失败: {str(e)}. 可能ID不存在"}

def count_tag(tags=None, filename="tags.txt"):
    if tags is None:
        tags = {}
    current_dir = os.path.dirname(os.path.abspath(__file__))
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
        if tag not in ('全彩','中文'):
            dic[tag] = dic.get(tag, 0) + 1

    try:
        with open(file_path, "w", encoding='utf-8') as f:
            json.dump(dic, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"写入 {file_path} 时发生错误: {e}")

    return dic


# ============ 新增功能 ============

def search_comic(query, page=1, order_by='mr'):
    """搜索本子, 每页返回5条"""
    try:
        client = JmOption.default().new_jm_client()
        page_result = client.search_site(
            search_query=str(query),
            page=page,
            order_by=order_by
        )
        results = []
        for item in page_result.content[:5]:
            aid, info = item
            results.append({
                "id": aid,
                "name": info.get("name", ""),
                "author": info.get("author", ""),
                "tags": info.get("tag_list", []),
            })
        return {
            "results": results,
            "total": page_result.total,
            "page": page,
            "page_count": page_result.page_count
        }
    except Exception as e:
        return {"error": f"搜索失败: {str(e)}"}


def get_ranking(time='w', page=1, category='0'):
    """获取排行榜 - 通过 jmcomic API 客户端
    time: 'a'=全部, 't'=今日, 'w'=本周(默认), 'm'=本月
    注意: 今日榜('t')可能为空
    """
    try:
        client = JmOption.default().new_jm_client()
        page_result = client.categories_filter(
            page=page,
            time=time,
            category=category,
            order_by='mv'
        )
        results = []
        for item in page_result.content[:10]:
            aid, info = item
            results.append({
                "id": aid,
                "name": info.get("name", ""),
                "author": info.get("author", ""),
                "tags": info.get("tag_list", []),
                "views": info.get("total_views", ""),
            })
        return {
            "results": results,
            "total": page_result.total,
            "page": page
        }
    except Exception as e:
        return {"error": f"获取排行失败: {str(e)}"}


def get_comic_detail(comic_id):
    """获取本子详细信息"""
    try:
        client = JmOption.default().new_jm_client()
        album: JmAlbumDetail = client.get_album_detail(str(comic_id))
        return {
            "id": album.album_id,
            "name": album.name,
            "author": album.author,
            "tags": album.tags,
            "pages": album.page_count,
            "chapters": len(album.episode_list),
            "likes": album.likes,
            "views": album.views,
            "description": album.description or "",
            "pub_date": album.pub_date or "",
            "authors": album.authors or [],
            "actors": album.actors or [],
        }
    except Exception as e:
        return {"error": f"查询详情失败: {str(e)}"}