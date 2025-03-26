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
import random
from PyPDF2 import PdfReader, PdfWriter

def clear():
    directory = "/home/mira/Books"
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
    try:
        
        page = client.search_site(search_query=str(comic_id))
        album: JmAlbumDetail = page.single_album
        
        result = {
            "name": album.name,
            "author": album.author,
            "tags": album.tags
        }
        return result
    
    except Exception as e:
        return {"error": f"查询失败: {str(e)}. 可能ID不存在，或需要登录查看隐藏内容"}

def modify_file(file_path,password):
    try:
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(password)
    except Exception as e:
        print(f"无法修改文件 {file_path}: {e}")

def encrypt_pdf(input_pdf_path):

    password = str(random.randint(10000, 99999))

    dir_name, original_file_name = os.path.split(input_pdf_path)
    
    output_file_name = f"{password}_{original_file_name}"
    output_pdf_path = os.path.join(dir_name, output_file_name)
    
    reader = PdfReader(input_pdf_path)
    writer = PdfWriter()

    for page_num in range(len(reader.pages)):
        writer.add_page(reader.pages[page_num])

    writer.encrypt(password)

    with open(output_pdf_path, "wb") as output_file:
        writer.write(output_file)
    modify_file(output_pdf_path,password)
    return password, output_pdf_path

Jm = on_regex(pattern=r'^/jm\s+(\d+)$',priority=1)

path = os.path.join(os.path.dirname(__file__), '/home/mira/jmcomic/option.yml')
client = jmcomic.create_option(path).new_jm_client()
base_path = "/home/mira/Books/pdf"

clear()

@Jm.handle()
async def Jm_send(bot: Bot, event: GroupMessageEvent, state: T_State):
    groupid=event.group_id
    usrid=event.user_id
    user_msg = str(event.get_message()).strip()
    match = re.match(r'^/jm\s+(\d+)$', user_msg)
    
    if match:
        manga_id = match.group(1)
        jminfo = get_comic_info(manga_id)
        
        if "error" in jminfo:
            msg = "id不存在或输入错误"
            await Jm.finish(message=MessageSegment.at(usrid)+Message(msg))
        else:

            name=jminfo['name']
            
            groupfiles = await bot.call_api("get_group_root_files", group_id=groupid)

            group_file_names_set = set(file['file_name'].split('_', 1)[-1] for file in groupfiles['files'])

            print(group_file_names_set)
            if (name+".pdf") in group_file_names_set:
                await Jm.finish(message=Message(MessageSegment.at(usrid)+' 漫画已存在于群文件'))
            
            option = jmcomic.create_option_by_file('/home/mira/jmcomic/option.yml')
            jmcomic.download_album(manga_id,option)
            await bot.send_group_msg(group_id=groupid,message=Message(MessageSegment.at(usrid)+" 下载完成，发送中\n请勿重复请求"))
            file_name = f"{name}.pdf"
            full_path = os.path.join(base_path, file_name)
            _,output_pdf_path=encrypt_pdf(full_path)
            try:

                await bot.call_api(
                    "upload_group_file",
                    group_id=event.group_id,
                    file=output_pdf_path
        )

                await Jm.finish(Message(MessageSegment.at(usrid)+f" 请求的 {file_name} 已发送"))
            except Exception as e:
                if str(e)=="FinishedException()":
                    return
                if str(e)=='''NetWorkError(message='WebSocket call api upload_group_file timeout')''':
                    await Jm.finish(Message(MessageSegment.at(usrid)+f" 文件过大"))
                else:    
                    await Jm.finish(Message(MessageSegment.at(usrid)+f" 文件上传失败：{str(e)}")) 
   

