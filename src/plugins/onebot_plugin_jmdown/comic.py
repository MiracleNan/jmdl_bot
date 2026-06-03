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

def search_comic_smart(query, page=1, order_by='mr', noai=False, count=5):
    """智能搜索: 同时搜标题+标签, 去重合并, 双命中排前面"""
    try:
        client = JmOption.default().new_jm_client()
        # 并行搜索标题和标签
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as pool:
            f_title = pool.submit(client.search_site, str(query), page, order_by, 'a', '0', None)
            f_tag = pool.submit(client.search_tag, str(query), page, order_by)
            try:
                page_title = f_title.result(timeout=20)
            except:
                page_title = None
            try:
                page_tag = f_tag.result(timeout=20)
            except:
                page_tag = None

        results = []
        seen_ids = set()

        # 先收集双命中(同时在标题和标签中出现)
        if page_title and page_tag:
            tag_ids = {item[0] for item in page_tag.content}
            for item in page_title.content:
                aid, info = item
                if aid in tag_ids and aid not in seen_ids:
                    name = info.get("name", "")
                    if noai and ("AI Generated" in name or "AI生成" in name or "AI 生成" in name):
                        continue
                    results.append({"id": aid, "name": name, "author": info.get("author", ""), "match": "双命中"})
                    seen_ids.add(aid)
                    if len(results) >= count:
                        break

        # 再补标题结果
        if page_title:
            for item in page_title.content:
                aid, info = item
                if aid in seen_ids:
                    continue
                name = info.get("name", "")
                if noai and ("AI Generated" in name or "AI生成" in name or "AI 生成" in name):
                    continue
                results.append({"id": aid, "name": name, "author": info.get("author", ""), "match": "标题"})
                seen_ids.add(aid)
                if len(results) >= count:
                    break

        # 再补标签结果
        if page_tag:
            for item in page_tag.content:
                aid, info = item
                if aid in seen_ids:
                    continue
                name = info.get("name", "")
                if noai and ("AI Generated" in name or "AI生成" in name or "AI 生成" in name):
                    continue
                results.append({"id": aid, "name": name, "author": info.get("author", ""), "match": "标签"})
                seen_ids.add(aid)
                if len(results) >= count:
                    break

        total = max(
            page_title.total if page_title else 0,
            page_tag.total if page_tag else 0,
            0
        )
        total_pages = max(
            page_title.page_count if page_title else 0,
            page_tag.page_count if page_tag else 0,
            1
        )
        return {"results": results[:count], "total": total, "page": page, "page_count": total_pages}
    except Exception as e:
        return {"error": f"搜索失败: {str(e)}"}


def search_comic_by_tag(tag, page=1, order_by='mr', noai=False):
    """按 tag 搜索本子, 每页返回5条"""
    try:
        client = JmOption.default().new_jm_client()
        page_result = client.search_tag(
            search_query=str(tag),
            page=page,
            order_by=order_by
        )
        results = []
        for item in page_result.content:
            aid, info = item
            name = info.get("name", "")
            if noai and ("AI Generated" in name or "AI生成" in name or "AI 生成" in name):
                continue
            results.append({
                "id": aid,
                "name": name,
                "author": info.get("author", ""),
                "tags": info.get("tag_list", info.get("tags", [])),
            })
            if len(results) >= 5:
                break
        return {
            "results": results,
            "total": page_result.total,
            "page": page,
            "page_count": page_result.page_count
        }
    except Exception as e:
        return {"error": f"标签搜索失败: {str(e)}"}


def search_comic(query, page=1, order_by='mr', noai=False):
    """搜索本子, 每页返回5条, noai=True时过滤AI Generated"""
    try:
        client = JmOption.default().new_jm_client()
        page_result = client.search_site(
            search_query=str(query),
            page=page,
            order_by=order_by
        )
        results = []
        for item in page_result.content:
            aid, info = item
            name = info.get("name", "")
            # 过滤 AI Generated / AI生成
            if noai and ("AI Generated" in name or "AI生成" in name or "AI 生成" in name):
                continue
            results.append({
                "id": aid,
                "name": name,
                "author": info.get("author", ""),
                "tags": info.get("tag_list", []),
            })
            if len(results) >= 5:
                break
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