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

def clear():
    directory = r"D:\books"
    keep_folders = {"longimg", "pdf"}
    try:
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isdir(item_path):
                if item.lower() not in keep_folders:
                    shutil.rmtree(item_path, ignore_errors=True) 
                    print(f"Deleted folder: {item_path}")
                else:
                    print(f"Kept folder: {item_path}")

    except FileNotFoundError:
        print(f"Directory {directory} not found.")
    except PermissionError:
        print("Permission denied. Please run the script with appropriate permissions.")
    except Exception as e:
        print(f"An error occurred: {e}")
    return 0

def get_comic_info(comic_id):
    """
    根据漫画ID查询信息
    :param comic_id: 禁漫天堂的漫画ID（纯数字）
    :return: 包含漫画信息的字典或错误信息
    """
    try:
        # 查询漫画信息
        page = client.search_site(search_query=str(comic_id))
        album: JmAlbumDetail = page.single_album
        
        # 提取所需信息
        result = {
            "name": album.name,
            "author": album.author,
            "tags": album.tags
        }
        return result
    
    except Exception as e:
        return {"error": f"查询失败: {str(e)}. 可能ID不存在，或需要登录查看隐藏内容"}

def get_sorted_sequence_numbers(base_directory, folder_name):
    """
    获取指定文件夹内png图片的升序序号列表（五位数格式）
    :param base_directory: 基础目录路径
    :param folder_name: 文件夹名称（漫画名称）
    :return: 升序排列的五位数格式序号列表
    """
    target_folder = os.path.join(base_directory, folder_name)
    if not os.path.isdir(target_folder):
        return []
    
    files = os.listdir(target_folder)
    sequence_numbers = []
    pattern = re.compile(r'(\d{5})\.png$', re.IGNORECASE)  # 提取5位数字
    
    for filename in files:
        match = pattern.match(filename)
        if match:
            sequence_number = int(match.group(1))
            sequence_numbers.append(sequence_number)
    
    # 升序排序并格式化为五位数字符串
    sequence_numbers.sort()
    formatted_numbers = [f"{num:05d}" for num in sequence_numbers]
    return formatted_numbers

def split_image_if_too_long(input_path, max_length=14000):
    """
    读取图片，若高度超过 max_length，则切割成多个不超过 max_length 的图片，
    并储存在原路径下
    :param input_path: 输入图片路径
    :param max_length: 最大允许高度（默认 15000 像素）
    :return: 返回生成的图片路径列表
    """
    # 打开图片
    img = Image.open(input_path)
    width, height = img.size

    # 如果高度不超过 max_length，直接返回原路径
    if height <= max_length:
        return [input_path]

    # 计算需要切割成几部分
    num_parts = (height + max_length - 1) // max_length  # 向上取整
    output_paths = []

    # 获取文件目录、基本名和扩展名
    dir_name = os.path.dirname(input_path)  # 原路径的目录
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    ext = os.path.splitext(input_path)[1]

    # 切割图片并保存到原路径
    for i in range(num_parts):
        # 计算当前部分的起始和结束位置
        top = i * max_length
        bottom = min((i + 1) * max_length, height)

        # 裁剪图片
        cropped_img = img.crop((0, top, width, bottom))

        # 生成输出文件名，保存在原路径下
        output_path = os.path.join(dir_name, f"{base_name}_{i+1}{ext}")
        cropped_img.save(output_path, quality=95)  # 保存到原目录
        output_paths.append(output_path)

    return output_paths

Jm = on_regex(pattern=r'^/jm\s+(\d+)$',priority=1)

path = os.path.join(os.path.dirname(__file__), 'D:/code/jmcomic/option.yml')
client = jmcomic.create_option(path).new_jm_client()
base_path = r"D:\Books\pdf"

clear()

@Jm.handle()
async def Jm_send(bot: Bot, event: GroupMessageEvent, state: T_State):
    groupid=event.group_id
    usrid=event.user_id
    user_msg = str(event.get_message()).strip()
    match = re.match(r'^/jm\s+(\d+)$', user_msg)
    
    if match:
        # 提取 ID 并将其返回为对象
        manga_id = match.group(1)
        jminfo = get_comic_info(manga_id)
        if "error" in jminfo:
            msg = "id不存在或输入错误"
            await Jm.finish(message=MessageSegment.at(usrid)+Message(msg))
        else:
            # msg = f"漫画名称: {result['name']}-作者: {result['author']}"
            name=jminfo['name']
            
            groupfiles = await bot.call_api("get_group_root_files", group_id=groupid)
            group_file_names_set = set(file['file_name'] for file in groupfiles['files'])
            print(group_file_names_set)
            if (name+".pdf") in group_file_names_set:
                await Jm.finish(message=Message(MessageSegment.at(usrid)+'漫画已存在于群文件'))
            
            option = jmcomic.create_option_by_file('D:/code/jmcomic/option.yml')
            jmcomic.download_album(manga_id,option)
            await bot.send_group_msg(group_id=groupid,message=Message(MessageSegment.at(usrid)+"下载完成，发送中请勿重复请求"))
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
                await Jm.finish(Message(MessageSegment.at(usrid)+f" 请求的 {file_name} 已发送"))
            except Exception as e:
        # 上传失败时返回错误信息
                if str(e)=="FinishedException()":
                    return
                if str(e)=='''NetWorkError(message='WebSocket call api upload_group_file timeout')''':
                    await Jm.finish(Message(MessageSegment.at(usrid)+f" 文件过大"))
                else:    
                    await Jm.finish(Message(MessageSegment.at(usrid)+f" 文件上传失败：{str(e)}")) 
   

