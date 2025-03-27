import os
import yaml
import psutil
import shutil

def read_option_yml(file_path: str = None) -> tuple[str, str] | None:
    if file_path is None:
        file_path = os.path.join(os.path.dirname(__file__), "option.yml")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            base_dir = config.get("dir_rule", {}).get("base_dir")
            pdf_dir = config.get("plugins", {}).get("after_album", [{}])[0].get("kwargs", {}).get("pdf_dir")
            if base_dir and pdf_dir: 
                return base_dir, pdf_dir
            else:
                print(f"base_dir 或 pdf_dir 未找到: base_dir={base_dir}, pdf_dir={pdf_dir}")
                return None
    except FileNotFoundError:
        print(f"文件 {file_path} 不存在")
        return None
    except yaml.YAMLError as e:
        print(f"解析 YAML 文件失败: {e}")
        return None
    except Exception as e:
        print(f"读取文件时发生错误: {e}")
        return None

def clear(threshold=float('inf')) -> int:
    config = read_option_yml()
    if config is None:
        print("无法读取 base_dir 和 pdf_dir，清理操作中止")
        return 1
    
    base_dir, _ = config  # 只使用 base_dir，忽略 pdf_dir
    keep_folders = {"longimg", "pdf"}
    
    if not os.path.exists(base_dir):
        print(f"base_dir {base_dir} 不存在")
        return 1
    disk = psutil.disk_usage('/')
    free_disk = disk.free / (1024 ** 3) 
    
    if free_disk<threshold:
        try:
            for item in os.listdir(base_dir):
                item_path = os.path.join(base_dir, item)
                if os.path.isdir(item_path):
                    if item.lower() not in keep_folders:
                        shutil.rmtree(item_path, ignore_errors=True)
                        print(f"Deleted folder: {item_path}")
                    else:
                        print(f"Kept folder: {item_path}")
        except PermissionError:
            print("权限不足，请以适当权限运行脚本")
            return 1
        except Exception as e:
            print(f"发生错误: {e}")
            return 1
        return 0
    else:
        return 0