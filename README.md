# jmdown

基于nonebot聊天机器人开发的jmcomic下载插件，输入/jm ID即可下载好漫画pdf上传到群文件

## 功能特点

* 下载jm漫画
* 打包成PDF
* 上传Q 群文件
* 

## 安装方法

### 前置要求

1. Python 3.10+ 环境
2. pipx (python包管理器)
3. NoneBot 2.0 框架

### 安装步骤

请确保安装了 python 3.10+ 环境

1. 一. 安装NoneBot 2.0 | ([快速上手 | NoneBot](https://nonebot.dev/docs/quick-start)) <- 详细请看
   
   ```
   1. 安装 pipx
   python -m pip install --user pipx
   python -m pipx ensurepath
   // 安装完毕 和 添加到系统PATH环境变量中后  重启终端
   
   2. 安装脚手架
   pipx install nb-cli
   
   3. 创建项目
   cd desktop
   mkdir NoneBot2.0
   cd NoneBot2.0
   // 在桌面创建文件夹并进入后
   
   nb create
   // 使用模板: bootstrap (初学者或用户)
   // 创建你的项目名称, 这里用 "jm_bot" 举例
   // 用鼠标选择适配器: OneBot V11
   // 选择驱动器: FastAPI
   // 立即安装依赖和虚拟环境
   // 用鼠标选择内置插件: echo
   
   cd jm_bot
   // 把下载后的压缩包 "jmdl_bot-main/" 内全部文件 解压至 "jm_bot/" 文件夹内, 系统会提示 "替换目标中的文件", 确认就好
   .\.venv\Scripts\activate
   pip install -r .\requirements.txt
   // 等待依赖安装完毕
   
   // 最后
   nb run --reload
   
   // 后续需要使用 只需要进入 "NoneBot2.0/jm_bot/" 文件夹内 输入 "nb run -reload"
   ```
2. 二. 安装 Lagrange.OneBot [下载链接]([Releases · LagrangeDev/Lagrange.Core](https://github.com/LagrangeDev/Lagrange.Core/releases))
   
   ```
   1. 下载 "Lagrange.OneBot_win-x64_net9.0_SelfContained.zip"
   //  把下载的压缩包中的 exe 解压至 "jm_bot/qq_bot" 文件夹内
   //  然后双击exe运行, 看到 文件夹内出现 "appsettings.json" 后 关闭exe
   
   2. 打开 "appsettings.json"
   // "Uin" 填qq号
   // "Protocol" 是登陆系统 可以改成 Windows
   // "ConsoleCompatibilityMode" 是扫码登陆 默认false 改成true
   // 修改后保存退出, 再启动一次exe
   
   // 启动后文件夹内会出现 ".png" 图片,  打开 用手机扫码登陆qq
   
   // 若一切正常, 只需要确保 exe 和 "nb run --reload" 都启动, 就完成了
   ```

### 配置

```
1. 打开 "jm_bot/src/plugins/onebot_plugin_jmdown/option.yml" 文件
// 修改 "base_dir" 和 "pdf_dir"   *建议在jm_bot文件夹里创建Books文件夹来储存*
```

### 结尾

若有其他问题,可加群提问: 329770237

