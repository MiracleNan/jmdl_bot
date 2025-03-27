# -*- coding: utf-8 -*-
"""
Author: MiracleNan
Email: 2127610576@qq.com
GitHub: https://github.com/MiracleNan/jmdl_bot
Created: 2025-03-27
Description: A NoneBot plugin for handling /jm commands to download comics and upload them to group files.
Copyright: © 2025 <Your Name>. All rights reserved.
"""
import re
import os
import jmcomic
import random
import shutil
import asyncio
import psutil
from nonebot import on_regex
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Bot, Message, MessageSegment
from jmcomic import JmAlbumDetail
from pikepdf import Pdf, Encryption
from .func import clear, read_option_yml
from .pdf_func import encrypt_pdf
from .comic import *
from concurrent.futures import ThreadPoolExecutor

Jm = on_regex(pattern=r'^/jm\s+(\d+)$', priority=1)

yml_path = os.path.join(os.path.dirname(__file__), "option.yml")
_, pdf_dir = read_option_yml(yml_path)

# 设置最大响应数为 MAX_QUEUE_SIZE
MAX_QUEUE_SIZE = 5
task_queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
bot_instance = None  
last_clear_time = 0  
CLEAR_INTERVAL = 300  # 清理间隔（秒）

# 设置最大下载任务数为 max_workers 
executor = ThreadPoolExecutor(max_workers=2)  

def download_album_sync(manga_id, option):
    jmcomic.download_album(manga_id, option)

async def check_and_clear(threshold=30):
    """定期检查并清理磁盘空间"""
    global last_clear_time
    current_time = asyncio.get_event_loop().time()
    
    if current_time - last_clear_time >= CLEAR_INTERVAL:
        disk = psutil.disk_usage(pdf_dir)  # 检查 pdf_dir 所在分区
        free_disk = disk.free / (1024 ** 3)  # GB
        print(f"Disk free space: {free_disk:.2f} GB")
        
        if free_disk < threshold:
            result = clear(threshold)
            if result == 0:
                print("Disk cleanup successful")
            else:
                print("Disk cleanup failed")
        last_clear_time = current_time

async def process_queue():
    while True:
        bot, group_id, user_id, manga_id, name = await task_queue.get()
        file_name = f"{name}.pdf"  
        temp_file_name = f"{name}_{user_id}_{random.randint(1000, 9999)}.pdf"
        full_path = os.path.join(pdf_dir, temp_file_name)
        default_path = os.path.join(pdf_dir, file_name) 
        
        try:
            # 检查群文件
            groupfiles = await bot.call_api("get_group_root_files", group_id=group_id)
            group_file_names_set = set(file['file_name'].split('_', 1)[-1] for file in groupfiles['files'])

            if file_name in group_file_names_set:
                await bot.send_group_msg(group_id=group_id, message=Message([MessageSegment.at(user_id), MessageSegment.text(f" 你查询的漫画：{name} 已存在于群文件")]))
                task_queue.task_done()
                continue
            

            await check_and_clear(30)
            

            option = jmcomic.create_option_by_file(yml_path)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(executor, download_album_sync, manga_id, option)

            if not os.path.exists(default_path):
                await bot.send_group_msg(group_id=group_id, message=Message([MessageSegment.at(user_id), MessageSegment.text(f" 下载 {name} 失败，文件未生成")]))
                task_queue.task_done()
                continue
            shutil.move(default_path, full_path)
            
            password, output_pdf_path = encrypt_pdf(full_path)
    
            await bot.send_group_msg(group_id=group_id, message=Message([MessageSegment.text(f" {file_name} 打包完成，密码：{password}，发送中请勿重复请求")]))
            
            # 上传文件
            encrypted_file_name = f"{password}_{file_name}" 
            print(f"Uploading file: {output_pdf_path}, size: {os.path.getsize(output_pdf_path)} bytes")
            await bot.call_api(
                "upload_group_file",
                group_id=group_id,
                file=output_pdf_path,
                name=encrypted_file_name
            )
            await bot.send_group_msg(group_id=group_id, message=Message([MessageSegment.at(user_id), MessageSegment.text(f" 请求的 {file_name} 已发送")]))
        
        except Exception as e:
            print(f"Error processing {name}: {str(e)}")
            if "timeout" in str(e).lower():
                await bot.send_group_msg(group_id=group_id, message=Message([MessageSegment.at(user_id), MessageSegment.text(f" {name} 文件过大，若稍后未发送请换jm号重试")]))
            else:
                await bot.send_group_msg(group_id=group_id, message=Message([MessageSegment.at(user_id), MessageSegment.text(f" {name} 文件上传失败：{str(e)}")]))
        
        finally:

            if os.path.exists(full_path):
                os.remove(full_path)
            if os.path.exists(output_pdf_path):
                os.remove(output_pdf_path)
            task_queue.task_done()

async def start_queue_processor():
    global bot_instance
    if bot_instance is not None:
        asyncio.create_task(process_queue())

@Jm.handle()
async def Jm_send(bot: Bot, event: GroupMessageEvent, state: T_State):
    global bot_instance
    if bot_instance is None:
        bot_instance = bot
        await start_queue_processor() 
    
    group_id = event.group_id
    user_id = event.user_id
    
    match = re.match(r'^/jm\s+(\d+)$', str(event.get_message()).strip())
    
    if match:
        manga_id = match.group(1)
        jminfo = get_comic_info(manga_id)
        
        if "error" in jminfo:
            await Jm.finish(Message([MessageSegment.at(user_id), MessageSegment.text(" Jm号不存在或输入错误")]))
            return
        
        name = jminfo['name']
        
        if task_queue.full():
            await Jm.finish(Message([MessageSegment.at(user_id), MessageSegment.text(f" 下载队列已满（最大 {MAX_QUEUE_SIZE} 个任务），请稍后再试")]))
            return
        
        await task_queue.put((bot, group_id, user_id, manga_id, name))
        await Jm.finish(Message([MessageSegment.at(user_id), MessageSegment.text(f" 已加入下载队列：{name}（当前队列：{task_queue.qsize()}/{MAX_QUEUE_SIZE}），请耐心等待")]))