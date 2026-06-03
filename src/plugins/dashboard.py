# -*- coding: utf-8 -*-
"""
JMDL Bot 后台管理系统
提供: 系统监控 / 实时日志 / 文件管理 / 历史记录 / 命令测试台
"""
import os, shutil, json, asyncio, psutil
from datetime import datetime
from collections import deque
from nonebot import get_app, get_driver
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/admin", tags=["admin"])

import sys
from .onebot_plugin_jmdown import task_queue, pdf_dir, yml_path, executor
from .onebot_plugin_jmdown.comic import get_comic_info, search_comic, get_ranking, get_comic_detail

def _get_processing():
    """动态读取处理中的任务状态（避免 Python import 值捕获）"""
    mod = sys.modules.get("src.plugins.onebot_plugin_jmdown")
    return getattr(mod, "_processing", None) if mod else None

# ============ 工具函数 ============

def get_dir_size(path):
    total = 0
    try:
        for entry in os.scandir(path):
            if entry.is_file(): total += entry.stat().st_size
            elif entry.is_dir(): total += get_dir_size(entry.path)
    except: pass
    return total

# ============ API ============

@router.get("/api/status")
async def api_status():
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    d = psutil.disk_usage(os.path.dirname(pdf_dir) if os.path.exists(os.path.dirname(pdf_dir)) else "/")
    return {
        "running": True,
        "queue": {"size": task_queue.qsize(), "max": task_queue.maxsize},
        "processing": _get_processing(),
        "cpu": {"percent": cpu},
        "memory": {"percent": mem.percent, "used_gb": round(mem.used/(1024**3),1), "total_gb": round(mem.total/(1024**3),1)},
        "disk": {"free_gb": round(d.free/(1024**3),1), "total_gb": round(d.total/(1024**3),1)},
        "pdf_dir": pdf_dir,
        "time": datetime.now().isoformat()
    }

@router.get("/api/files")
async def api_files():
    base = os.path.dirname(pdf_dir)
    items = []
    if os.path.exists(base):
        for name in os.listdir(base):
            if name in ("pdf", "tags", "bot.log", "history.json"): continue
            path = os.path.join(base, name)
            if os.path.isdir(path):
                sz = get_dir_size(path)
                img_count = sum(1 for _ in os.scandir(path) if _.is_file())
                items.append({"name":name, "type":"dir", "size_mb":round(sz/(1024**2),2), "images":img_count, "modified":datetime.fromtimestamp(os.stat(path).st_mtime).isoformat()})
    if os.path.exists(pdf_dir):
        for f in os.listdir(pdf_dir):
            if not f.endswith('.pdf'): continue
            p = os.path.join(pdf_dir, f)
            s = os.stat(p)
            items.append({"name":f, "type":"pdf", "size_mb":round(s.st_size/(1024**2),2), "images":0, "modified":datetime.fromtimestamp(s.st_mtime).isoformat()})
    items.sort(key=lambda x:x["modified"], reverse=True)
    total_mb = round(sum(i["size_mb"] for i in items), 2)
    return {"items": items, "count": len(items), "total_mb": total_mb}

@router.post("/api/files/delete")
async def api_delete(data: dict):
    name = data.get("name", "")
    base = os.path.dirname(pdf_dir)
    for root in [pdf_dir, base]:
        p = os.path.join(root, name)
        if os.path.exists(p) and p.startswith(root) and name not in ("pdf","tags"):
            (shutil.rmtree if os.path.isdir(p) else os.remove)(p, ignore_errors=True) if os.path.isdir(p) else os.remove(p)
            return {"ok": True, "msg": f"已删除 {name}"}
    return {"ok": False, "msg": "未找到"}

@router.post("/api/files/cleanup")
async def api_cleanup():
    base = os.path.dirname(pdf_dir)
    cnt = freed = 0
    for name in list(os.listdir(base)):
        if name in ("pdf","tags","bot.log","history.json"): continue
        p = os.path.join(base, name)
        if os.path.isdir(p):
            freed += get_dir_size(p)
            shutil.rmtree(p, ignore_errors=True)
            cnt += 1
    for f in list(os.listdir(pdf_dir)):
        if f.endswith('.pdf'): os.remove(os.path.join(pdf_dir,f)); cnt += 1
    return {"ok": True, "msg": f"清理 {cnt} 项, 释放 {round(freed/(1024**2),1)} MB"}

@router.get("/api/history")
async def api_history():
    p = "/opt/jmdl_bot/books/history.json"
    if os.path.exists(p):
        with open(p) as f: return {"history": json.load(f)}
    return {"history": []}

@router.get("/api/logs")
async def api_logs():
    p = "/opt/jmdl_bot/books/bot.log"
    if not os.path.exists(p): return {"logs": [], "count": 0}
    with open(p) as f: lines = [l.strip() for l in f.readlines()[-500:] if l.strip()]
    logs = []
    for l in lines:
        level, time_str, msg = "INFO", datetime.now().strftime("%H:%M:%S"), l
        try:
            if '] [' in l:
                time_str = l[1:l.index(']')].split()[-1][:8]
                level = l.split('] [',1)[1].split(']',1)[0]
                msg = l.split('] ',2)[-1]
        except: pass
        logs.append({"time": time_str, "level": level, "msg": msg[:300]})
    return {"logs": logs[-200:], "count": len(logs)}

# ============ 命令测试台 API ============

@router.post("/api/test/jm")
async def api_test_jm(data: dict):
    """测试 /jm 下载命令（不实际发送 QQ 消息，只查询信息）"""
    mid = str(data.get("id", ""))
    if not mid or not mid.isdigit():
        return {"ok": False, "msg": "请输入有效的数字 ID"}
    try:
        info = get_comic_info(mid)
        if "error" in info: return {"ok": False, "msg": info["error"]}
        return {"ok": True, "data": {"id": mid, "name": info["name"], "author": info["author"], "tags": info["tags"], "chapters": info["episode_count"]}}
    except Exception as e:
        return {"ok": False, "msg": str(e)}

@router.post("/api/test/download")
async def api_test_download(data: dict):
    """通过 WebUI 直接触发下载（加入队列）"""
    mid = str(data.get("id", ""))
    if not mid or not mid.isdigit():
        return {"ok": False, "msg": "请输入有效的数字 ID"}
    try:
        info = get_comic_info(mid)
        if "error" in info: return {"ok": False, "msg": info["error"]}
        if task_queue.full(): return {"ok": False, "msg": f"队列已满 ({task_queue.maxsize})"}
        # 加入队列（bot=None 表示 WebUI 触发，group_id=0, user_id=0）
        await task_queue.put((None, 0, 0, mid, info["name"], info["tags"], 0))
        return {"ok": True, "msg": f"已加入队列: {info['name'][:50]}（{task_queue.qsize()}/{task_queue.maxsize}）"}
    except Exception as e:
        return {"ok": False, "msg": str(e)}

@router.post("/api/test/jms")
async def api_test_jms(data: dict):
    q = str(data.get("query", "")); page = int(data.get("page", 1)); order = str(data.get("order", "mr"))
    if not q: return {"ok": False, "msg": "请输入搜索关键词"}
    r = search_comic(q, page, order)
    if "error" in r: return {"ok": False, "msg": r["error"]}
    return {"ok": True, "data": r}

@router.post("/api/test/jmrank")
async def api_test_jmrank(data: dict):
    time_type = str(data.get("time", "week")); page = int(data.get("page", 1))
    tm = {"all":"a","day":"t","日":"t","week":"w","周":"w","month":"m","月":"m"}
    r = get_ranking(tm.get(time_type,"w"), page)
    if "error" in r: return {"ok": False, "msg": r["error"]}
    return {"ok": True, "data": r}

@router.post("/api/test/jminfo")
async def api_test_jminfo(data: dict):
    mid = str(data.get("id", ""))
    if not mid.isdigit(): return {"ok": False, "msg": "请输入有效的数字 ID"}
    r = get_comic_detail(mid)
    if "error" in r: return {"ok": False, "msg": r["error"]}
    return {"ok": True, "data": r}

# ============ WebSocket ============

@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await asyncio.sleep(2)
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            await ws.send_json({
                "queue": {"size": task_queue.qsize(), "max": task_queue.maxsize},
                "processing": _get_processing(),
                "cpu": cpu, "mem": mem.percent
            })
    except WebSocketDisconnect: pass

# ============ WebUI ============

TAB_CSS = """:root{--bg:#0f172a;--card:#1e293b;--border:#334155;--text:#e2e8f0;--muted:#94a3b8;--accent:#3b82f6;--green:#22c55e;--red:#ef4444;--yellow:#eab308}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',-apple-system,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.topbar{display:flex;align-items:center;padding:0 24px;height:56px;border-bottom:1px solid var(--border);background:var(--card)}
.topbar h1{font-size:16px;font-weight:600}.topbar h1 span{color:var(--accent)}
.topbar .status{margin-left:auto;display:flex;align-items:center;gap:6px;font-size:12px;color:var(--muted)}
.topbar .dot{width:6px;height:6px;border-radius:50%;background:var(--green)}
.tabs{display:flex;gap:2px;padding:12px 24px 0;background:var(--card);border-bottom:1px solid var(--border)}
.tab{padding:10px 18px;font-size:13px;cursor:pointer;border-radius:8px 8px 0 0;color:var(--muted);border:1px solid transparent;border-bottom:none;transition:.15s}
.tab:hover{color:var(--text);background:rgba(255,255,255,.03)}
.tab.active{color:var(--text);background:var(--bg);border-color:var(--border)}
.content{padding:24px;max-width:1400px;margin:0 auto}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px}
.card-title{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:14px;display:flex;align-items:center;gap:8px}
.stat{background:var(--bg);border-radius:8px;padding:16px;text-align:center}
.stat-v{font-size:26px;font-weight:700}.stat-l{font-size:11px;color:var(--muted);margin-top:4px}
.stat-v.g{color:var(--green)}.stat-v.b{color:var(--accent)}.stat-v.y{color:var(--yellow)}.stat-v.r{color:var(--red)}
.bar{height:4px;background:var(--bg);border-radius:2px;margin-top:8px;overflow:hidden}
.bar-f{height:100%;border-radius:2px;transition:width .5s}
.bar-f.b{background:var(--accent)}.bar-f.y{background:var(--yellow)}
.btn{padding:7px 14px;border:none;border-radius:6px;cursor:pointer;font-size:12px;font-weight:500;transition:.15s;display:inline-flex;align-items:center;gap:6px}
.btn-p{background:var(--accent);color:#fff}.btn-p:hover{background:#2563eb}
.btn-d{background:var(--red);color:#fff}.btn-d:hover{background:#dc2626}
.btn-o{background:transparent;color:var(--muted);border:1px solid var(--border)}.btn-o:hover{background:var(--border);color:var(--text)}
.btn-sm{padding:4px 10px;font-size:11px}
.actions{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap}
input,select{background:var(--bg);border:1px solid var(--border);color:var(--text);padding:8px 12px;border-radius:6px;font-size:13px;outline:none}
input:focus,select:focus{border-color:var(--accent)}
input{flex:1;min-width:150px}
select{min-width:100px}
.scroll{max-height:420px;overflow-y:auto}
.row{display:flex;align-items:center;padding:10px 0;border-bottom:1px solid var(--border);gap:12px;font-size:13px}
.row:hover{background:rgba(255,255,255,.01)}
.row .n{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.row .m{color:var(--muted);font-size:11px;white-space:nowrap}
.badge{padding:2px 8px;border-radius:10px;font-size:11px;font-weight:500}
.badge.s{background:var(--green);color:#fff}.badge.e{background:var(--red);color:#fff}.badge.w{background:var(--yellow);color:#000}
.badge.d{background:var(--accent);color:#fff}.badge.p{background:var(--muted);color:#fff}
.result-box{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:14px;margin-top:12px;font-size:13px;line-height:1.6;white-space:pre-wrap;max-height:400px;overflow-y:auto}
.log-line{display:flex;padding:2px 0;font-size:12px;font-family:'JetBrains Mono',monospace;line-height:1.7;border-bottom:1px solid rgba(255,255,255,.03)}
.log-time{color:var(--muted);margin-right:10px;flex-shrink:0;width:65px}
.log-level{padding:1px 5px;border-radius:3px;font-size:10px;margin-right:8px;flex-shrink:0;min-width:55px;text-align:center}
.log-level.I{background:var(--accent);color:#fff}.log-level.E{background:var(--red);color:#fff}
.log-level.S{background:var(--green);color:#fff}.log-level.W{background:var(--yellow);color:#000}
.log-msg{overflow:hidden;text-overflow:ellipsis}"""

HTML = '''<!DOCTYPE html>
<html lang="zh"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>JMDL Bot Admin</title><style>''' + TAB_CSS + '''</style></head><body>
<div class="topbar"><h1><span>📚</span> JMDL Bot 管理后台</h1>
<div class="status" id="status-bar"><span class="dot" id="dot"></span><span id="status-text">连接中</span></div></div>
<div class="tabs" id="tabs">
<div class="tab active" data-tab="overview">📊 总览</div>
<div class="tab" data-tab="test">🧪 命令测试</div>
<div class="tab" data-tab="logs">📋 日志</div>
<div class="tab" data-tab="files">📁 文件</div>
<div class="tab" data-tab="history">📜 历史</div>
</div>
<div class="content" id="content"></div>
<script>
const $=s=>document.querySelector(s);
const $$=s=>document.querySelectorAll(s);
const API='/admin/api',WS_URL=`${location.protocol==='https:'?'wss:':'ws:'}//${location.host}/admin/ws`;
let ws,logs=[],fileCache=[];

// ====== Tabs ======
$$('.tab').forEach(t=>t.onclick=()=>{$$('.tab').forEach(x=>x.classList.remove('active'));t.classList.add('active');render(t.dataset.tab)});

// ====== WebSocket ======
function connectWS(){ws=new WebSocket(WS_URL);ws.onmessage=e=>{const d=JSON.parse(e.data);updateLiveStats(d)};ws.onclose=()=>setTimeout(connectWS,3000)}
function updateLiveStats(d){document.getElementById('queue-stat')&&(document.getElementById('queue-stat').textContent=d.queue.size+'/'+d.queue.max);document.getElementById('cpu-stat')&&(document.getElementById('cpu-stat').textContent=d.cpu+'%');document.getElementById('mem-stat')&&(document.getElementById('mem-stat').textContent=d.mem+'%');}

// ====== API helpers ======
async function get(p){return fetch(API+p).then(r=>r.json())}
async function post(p,d){return fetch(API+p,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)}).then(r=>r.json())}

// ====== Overview ======
async function renderOverview(){
  let d;try{d=await get('/status')}catch(e){$('#content').innerHTML='<div class=card><div class=card-title>无法连接服务</div></div>';return}
  document.getElementById('status-text').textContent='运行中';
  document.getElementById('dot').style.background='var(--green)';
  $('#content').innerHTML=`
<div class="grid4" style="margin-bottom:20px">
<div class="card"><div class="stat"><div class="stat-v g" id="queue-stat">${d.queue.size}/${d.queue.max}</div><div class="stat-l">队列任务</div><div class="bar"><div class="bar-f b" style="width:${d.queue.max?d.queue.size/d.queue.max*100:0}%"></div></div></div></div>
<div class="card"><div class="stat"><div class="stat-v b" id="cpu-stat">${d.cpu.percent}%</div><div class="stat-l">CPU</div><div class="bar"><div class="bar-f b" style="width:${d.cpu.percent}%"></div></div></div></div>
<div class="card"><div class="stat"><div class="stat-v y" id="mem-stat">${d.memory.percent}%</div><div class="stat-l">内存 ${d.memory.used_gb}/${d.memory.total_gb} GB</div><div class="bar"><div class="bar-f y" style="width:${d.memory.percent}%"></div></div></div></div>
<div class="card"><div class="stat"><div class="stat-v">${d.disk.free_gb} GB</div><div class="stat-l">磁盘剩余</div></div></div>
</div>
<div class="grid2">
<div class="card"><div class="card-title">🖥 服务信息</div>
<div style="font-size:13px;line-height:2">
<div>PDF 目录: <span style="color:var(--muted)">${d.pdf_dir}</span></div>
<div>队列容量: <span style="color:var(--muted)">${d.queue.max}</span></div>
<div>启动时间: <span style="color:var(--muted)">${new Date(d.time).toLocaleString()}</span></div>
</div></div>
<div class="card"><div class="card-title">📥 快速下载</div>
<div style="display:flex;gap:8px;align-items:center">
<input type="text" id="quick-jm" placeholder="输入 JM ID 下载" style="flex:1">
<button class="btn btn-p" onclick="quickDownload()">下载</button>
</div>
<div id="quick-result" style="margin-top:10px;font-size:13px"></div>
</div></div>`;
  updateLiveStats(d);
}

async function quickDownload(){
  const id=$('#quick-jm').value.trim();
  if(!id)return;
  const r=await post('/test/download',{id});
  $('#quick-result').innerHTML=`<div style="color:${r.ok?'var(--green)':'var(--red)'}">${r.ok?'✅':'❌'} ${r.msg}</div>`;
}

// ====== Command Test ======
async function renderTest(){
$('#content').innerHTML=`
<div class="grid2">
<div class="card"><div class="card-title">🔍 搜索 /jms</div>
<div style="display:flex;gap:8px;margin-bottom:10px">
<input id="t-jms-q" placeholder="关键词" value="汉化"><input id="t-jms-p" placeholder="页码" value="1" style="width:60px"><select id="t-jms-o"><option value="mr">最新</option><option value="mv">最多浏览</option><option value="mp">最多图片</option><option value="tf">最多喜欢</option></select>
<button class="btn btn-p" onclick="testCmd('jms')">搜索</button></div>
<div id="r-jms" class="result-box" style="display:none"></div></div>

<div class="card"><div class="card-title">🏆 排行榜 /jmrank</div>
<div style="display:flex;gap:8px;margin-bottom:10px">
<select id="t-rank-t"><option value="week">周榜</option><option value="month">月榜</option><option value="all">总榜</option><option value="day">日榜</option></select>
<input id="t-rank-p" placeholder="页码" value="1" style="width:60px">
<button class="btn btn-p" onclick="testCmd('jmrank')">查询</button></div>
<div id="r-jmrank" class="result-box" style="display:none"></div></div>

<div class="card"><div class="card-title">📖 详情 /jminfo</div>
<div style="display:flex;gap:8px;margin-bottom:10px">
<input id="t-info-id" placeholder="JM ID" value="114514"><button class="btn btn-p" onclick="testCmd('jminfo')">查询</button></div>
<div id="r-jminfo" class="result-box" style="display:none"></div></div>

<div class="card"><div class="card-title">📥 查询 ID /jm</div>
<div style="display:flex;gap:8px;margin-bottom:10px">
<input id="t-jm-id" placeholder="JM ID"><button class="btn btn-p" onclick="testCmd('jm')">查询</button>
<button class="btn btn-d" onclick="testCmd('download')">直接下载</button></div>
<div id="r-jm" class="result-box" style="display:none"></div></div>
</div>`;
}

async function testCmd(cmd){
  let d,r,boxId='r-'+cmd;
  $(`#${boxId}`).style.display='block';
  $(`#${boxId}`).innerHTML='<span style="color:var(--muted)">执行中...</span>';

  switch(cmd){
    case 'jms':d={query:$('#t-jms-q').value,page:parseInt($('#t-jms-p').value)||1,order:$('#t-jms-o').value};r=await post('/test/jms',d);
      if(r.ok){let t=`<b>搜索: ${d.query}</b> | 共${r.data.total}结果 | 第${r.data.page}页/${r.data.page_count}页<hr style="border-color:var(--border);margin:8px 0">`;
        r.data.results.forEach((x,i)=>t+=`\n<b>${i+1}.</b> [<span style="color:var(--accent)">${x.id}</span>] ${x.name}<br><span style="color:var(--muted)">🏷 ${(x.tags||[]).join(', ')}</span>`);
        $(`#${boxId}`).innerHTML=t;}
      break;
    case 'jmrank':d={time:$('#t-rank-t').value,page:parseInt($('#t-rank-p').value)||1};r=await post('/test/jmrank',d);
      if(r.ok){let t=`<b>JM 排行</b> | 共${r.data.total}结果<hr style="border-color:var(--border);margin:8px 0">`;
        r.data.results.forEach((x,i)=>{const m={1:'🥇',2:'🥈',3:'🥉'};t+=`\n${m[i]||i+'.'} [<span style="color:var(--accent)">${x.id}</span>] ${x.name}`});
        $(`#${boxId}`).innerHTML=t;}
      break;
    case 'jminfo':d={id:$('#t-info-id').value};r=await post('/test/jminfo',d);
      if(r.ok){let e=r.data;$(boxId).innerHTML=`<b>📖 ${e.name}</b><br>作者: ${e.author} | 页数: ${e.pages} | 章节: ${e.chapters}<br>❤ ${e.likes} | 👁 ${e.views}<br>Tags: ${(e.tags||[]).join(', ')}`;}
      break;
    case 'jm':d={id:$('#t-jm-id').value};r=await post('/test/jm',d);
      if(r.ok){let e=r.data;$(boxId).innerHTML=`<b>${e.name}</b><br>作者: ${e.author} | 章节: ${e.chapters}<br>Tags: ${(e.tags||[]).join(', ')}<br><span style="color:var(--green);margin-top:8px;display:inline-block">📥 可使用 /jm ${e.id} 下载</span>`;}
      break;
    case 'download':d={id:$('#t-jm-id').value};r=await post('/test/download',d);
      if(r.ok){$('#r-jm').innerHTML='<span style="color:var(--green)">📥 '+r.msg+'</span>';}
      break;
  }
  if(!r.ok){$(`#${boxId}`).innerHTML='<span style="color:var(--red)">❌ '+r.msg+'</span>';}
}

// ====== Logs ======
async function renderLogs(){
$('#content').innerHTML=`<div class="card"><div class="card-title">📋 实时日志 <span style="margin-left:auto;font-weight:400;color:var(--muted)" id="log-count"></span></div>
<div style="display:flex;gap:6px;margin-bottom:12px"><button class="btn btn-sm btn-o active filter-btn" data-lvl="ALL">全部</button><button class="btn btn-sm btn-o filter-btn" data-lvl="I">INFO</button><button class="btn btn-sm btn-o filter-btn" data-lvl="S">SUCCESS</button><button class="btn btn-sm btn-o filter-btn" data-lvl="W">WARN</button><button class="btn btn-sm btn-o filter-btn" data-lvl="E">ERROR</button>
<button class="btn btn-sm btn-p" onclick="refreshLogs()" style="margin-left:auto">🔄 刷新</button></div>
<div class="scroll" id="log-view" style="font-family:monospace;font-size:12px"></div></div>`;
  document.querySelectorAll('.filter-btn').forEach(b=>b.onclick=function(){document.querySelectorAll('.filter-btn').forEach(x=>x.classList.remove('active'));this.classList.add('active');renderLogLines(this.dataset.lvl)});
  await refreshLogs();
}

async function refreshLogs(){logs=(await get('/logs')).logs;document.getElementById('log-count').textContent=logs.length+' 条';renderLogLines('ALL')}
function renderLogLines(filter){const v=document.getElementById('log-view');if(!v)return;let filtered=filter==='ALL'?logs:logs.filter(l=>l.level[0]===filter);if(!filtered.length){v.innerHTML='<div style="color:var(--muted);text-align:center;padding:40px">暂无日志</div>';return}v.innerHTML=filtered.map(l=>`<div class="log-line"><span class="log-time">${l.time}</span><span class="log-level ${l.level[0]}">${l.level}</span><span class="log-msg">${l.msg}</span></div>`).join('');v.scrollTop=v.scrollHeight}

// ====== Files ======
async function renderFiles(){
$('#content').innerHTML=`<div class="card"><div class="card-title">📁 文件管理 <span style="margin-left:auto;font-weight:400;color:var(--muted)" id="file-count"></span></div>
<div class="actions"><button class="btn btn-p" onclick="refreshFiles()">🔄 刷新</button><button class="btn btn-d" onclick="cleanupFiles()">🗑️ 清理全部</button></div>
<div class="scroll" id="file-list"><div style="color:var(--muted);text-align:center;padding:40px">加载中...</div></div></div>`;
  await refreshFiles();
}

async function refreshFiles(){let d=await get('/files');fileCache=d.items;document.getElementById('file-count').textContent=d.count+' 项 · '+d.total_mb+' MB';
 const v=document.getElementById('file-list');if(!d.items.length){v.innerHTML='<div style="color:var(--muted);text-align:center;padding:40px">暂无文件</div>';return}
 v.innerHTML=d.items.map(f=>`<div class="row"><span class="n">${f.type==='dir'?'📁':'📄'} ${f.name}</span><span class="m">${f.images?f.images+' 张图 · ':''}${f.size_mb} MB</span><button class="btn btn-sm btn-o" onclick="delFile('${f.name}')">删除</button></div>`).join('')}

async function delFile(name){if(!confirm('删除 '+name+'？'))return;await post('/files/delete',{name});refreshFiles()}
async function cleanupFiles(){if(!confirm('清理所有下载文件？'))return;await post('/files/cleanup',{});refreshFiles()}

// ====== History ======
async function renderHistory(){
$('#content').innerHTML=`<div class="card"><div class="card-title">📜 下载历史</div><div class="scroll" id="history-list"><div style="color:var(--muted);text-align:center;padding:40px">加载中...</div></div></div>`;
 let d=await get('/history');const v=document.getElementById('history-list');
 if(!d.history.length){v.innerHTML='<div style="color:var(--muted);text-align:center;padding:40px">暂无记录</div>';return}
 v.innerHTML=d.history.map(h=>`<div class="row"><span style="width:140px;color:var(--muted);flex-shrink:0">${h.time}</span><span class="n">${h.name}</span><span class="m">${h.size_mb}MB</span><span class="badge ${h.status==='success'?'s':'e'}">${h.status==='success'?'成功':'失败'}</span></div>`).join('')}

// ====== Init ======
function render(tab){const f={overview:renderOverview,test:renderTest,logs:renderLogs,files:renderFiles,history:renderHistory};f[tab]&&f[tab]()}
connectWS();render('overview');setInterval(()=>{refreshLogs()},10000);
</script></body></html>'''

@router.get("", response_class=HTMLResponse)
async def admin_page():
    return HTML


# ============ 注册路由 ============

driver = get_driver()

@driver.on_startup
async def _register():
    app = get_app()
    app.include_router(router)
