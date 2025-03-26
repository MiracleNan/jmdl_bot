import re,os,jmcomic,random,shutil
from nonebot import on_regex
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Bot, Message,MessageSegment
from jmcomic import JmAlbumDetail
from pikepdf import Pdf, Encryption
from .func import clear,read_option_yml
from .pdf_func import encrypt_pdf
from .comic import *

Jm = on_regex(pattern=r'^/jm\s+(\d+)$',priority=1)

yml_path = os.path.join(os.path.dirname(__file__), "option.yml")
path = yml_path
_,pdf_dir = read_option_yml(yml_path)

@Jm.handle()
async def Jm_send(bot: Bot, event: GroupMessageEvent, state: T_State):
    
    clear(30)
    
    groupid=event.group_id
    usrid=event.user_id
    match = re.match(r'^/jm\s+(\d+)$', str(event.get_message()).strip())
    
    if match:
        manga_id = match.group(1)
        jminfo = get_comic_info(manga_id)
        
        if "error" in jminfo:
            msg = " Jm号不存在或输入错误"
            await Jm.finish(message=MessageSegment.at(usrid)+Message(msg))
        else:

            name=jminfo['name']
            
            groupfiles = await bot.call_api("get_group_root_files", group_id=groupid)

            group_file_names_set = set(file['file_name'].split('_', 1)[-1] for file in groupfiles['files'])

            print(group_file_names_set)
            if (name+".pdf") in group_file_names_set:
                await Jm.finish(message=Message(MessageSegment.at(usrid)+f' 你查询的漫画：{name}已存在于群文件'))
            await bot.send_group_msg(group_id=groupid, message=MessageSegment.at(usrid) + " 开始下载漫画，请稍等...")
            
            option = jmcomic.create_option_by_file(yml_path)
            jmcomic.download_album(manga_id,option)
            
            file_name = f"{name}.pdf"
            full_path = os.path.join(pdf_dir, file_name)
            _,output_pdf_path=encrypt_pdf(full_path)
            await bot.send_group_msg(group_id=groupid,message=Message(MessageSegment.at(usrid)+" 打包完成，发送中\n请勿重复请求"))
            try:

                await bot.call_api(
                    "upload_group_file",
                    group_id=event.group_id,
                    file=output_pdf_path,
        )

                await Jm.finish(Message(MessageSegment.at(usrid)+f" 请求的 {file_name} 已发送"))
            except Exception as e:
                if str(e)=="FinishedException()":
                    return
                if "timeout" in str(e).lower():
                    await Jm.finish(Message(MessageSegment.at(usrid)+f" 文件过大,若稍后未发送请换jm号重试"))
                else:    
                    await Jm.finish(Message(MessageSegment.at(usrid)+f" 文件上传失败：{str(e)}")) 
   

