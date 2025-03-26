from jmcomic import JmAlbumDetail,JmOption
import jmcomic,os,yaml,argparse

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
