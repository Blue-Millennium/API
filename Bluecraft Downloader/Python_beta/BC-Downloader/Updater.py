import os
import re
import threading
import tkinter as tk
import zipfile
from tkinter import ttk
from urllib.parse import urlparse

import requests
from tqdm import tqdm


def download_file(url, local_filename=None, chunk_size=8192):
    global cancel_update, local_zip_path
    """
    下载文件到本地并显示进度条。
    """
    if local_filename is None:
        # 清理URL以获得合法的文件名
        local_filename = url.split('/')[-1].split('?')[0]  # 移除查询字符串
        # 进一步清理，移除可能存在的非法文件名字符
        local_filename = ''.join(c for c in local_filename if c.isalnum() or c in ('.', '-', '_'))
        local_zip_path = local_filename

    # 确保文件名不为空且合法
    if not local_filename:
        raise ValueError("无法从URL中获取有效的文件名")

    response = requests.get(url, stream=True)
    response.raise_for_status()

    total_size = int(response.headers.get('content-length', 0))
    progress_bar = tqdm(total=total_size, unit='iB', unit_scale=True, desc=f"Downloading {local_filename}")

    with open(local_filename, 'wb') as file:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if cancel_update:  # 新增：检查是否需要取消
                print("下载已取消")
                break
            if chunk:  # filter out keep-alive new chunks
                progress_bar.update(len(chunk))
                file.write(chunk)
    progress_bar.close()

    if total_size != 0 and progress_bar.n != total_size:
        print("ERROR, something went wrong")

    return local_filename


def extract_zip(zip_file_path, extract_to='.'):
    """
    解压zip文件到指定目录。
    """
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        zip_ref.extractall(path=extract_to)


def fetch_and_process_url(url):
    """
    从给定URL中提取版本和下载链接，下载zip文件并解压到当前脚本所在的目录。
    解压完成后删除ZIP文件。
    """
    response = requests.get(url)
    content = response.text
    match = re.search(r'(\d+(?:\.\d+)+)\|([^\|\s]+)', content)
    if match:
        version, download_url = match.groups()
        print(f"找到版本: {version}, 开始下载...")

        # 构建本地文件名，保持与远程一致
        parsed_url = urlparse(download_url)
        filename = os.path.basename(parsed_url.path)
        local_zip_path = download_file(download_url)

        # 解压到当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        extract_zip(local_zip_path, current_dir)

        print(f"版本 {version} 下载并解压完成至当前目录: {current_dir}")

        # 清理：删除已解压的ZIP文件
        try:
            os.remove(local_zip_path)
            print(f"已删除临时ZIP文件: {local_zip_path}")
        except OSError as e:
            print(f"删除文件时发生错误: {e.strerror}")

    else:
        print("未找到符合格式的信息。")


def update_progress_bar(value, max_value, bar, label):
    """更新进度条和标签文本"""
    percent = min(int((value / max_value) * 100), 100)
    bar['value'] = percent
    label.config(text=f"{percent}% Complete")
    root.update_idletasks()  # 更新GUI


def gui_fetch_and_process_url(url):
    """
    在GUI环境中执行fetch_and_process_url操作，并更新界面。
    """
    global progress_bar, status_label

    status_label.config(text="正在检查更新...")
    root.update_idletasks()

    fetch_and_process_url(url)

    # 模拟下载进度更新（实际应用中需调整以反映真实进度）
    total_size = 100  # 示例总大小
    for i in range(total_size + 1):
        update_progress_bar(i, total_size, progress_bar, status_label)
        root.after(100)  # 每100毫秒更新一次


cancel_update = False


def cancel_update_callback():
    """标记取消更新，关闭窗口，并尝试删除临时下载文件"""
    global cancel_update, local_zip_path

    cancel_update = True

    # 检查local_zip_path是否已定义且指向一个存在的文件
    if local_zip_path is not None:  # 添加检查local_zip_path是否已定义
        if os.path.exists(local_zip_path):
            try:
                os.remove(local_zip_path)
                print(f"下载已取消，临时文件 {local_zip_path} 已删除。")
            except OSError as e:
                print(f"尝试删除临时文件时出错: {e.strerror}")
        else:
            print(f"local_zip_path定义但文件不存在: {local_zip_path}")
    else:
        print("local_zip_path未定义，无需执行删除操作。")

    root.destroy()


def auto_fetch_and_process_url(url):
    """
    自动在GUI环境中执行fetch_and_process_url操作，并更新界面。
    """
    global progress_bar, status_label, cancel_button

    status_label.config(text="正在检查更新...")
    root.update_idletasks()

    # 启用取消按钮
    cancel_button.config(state=tk.NORMAL)

    fetch_and_process_url(url)

    # 模拟下载进度更新（实际应用中需调整以反映真实进度）
    total_size = 100  # 示例总大小
    for i in range(total_size + 1):
        if not cancel_update:
            update_progress_bar(i, total_size, progress_bar, status_label)
            root.after(100)  # 每100毫秒更新一次
        else:
            break

    # 下载完成后或取消后，禁用取消按钮
    cancel_button.config(state=tk.DISABLED)

    if cancel_update:
        status_label.config(text="更新已取消")
    else:
        status_label.config(text="更新完成")


def threaded_fetch_and_process_url(url):
    """
    在独立线程中执行fetch_and_process_url操作。
    """
    auto_fetch_and_process_url(url)


def create_gui():
    global progress_bar, status_label, root, cancel_button

    root = tk.Tk()
    root.title("软件更新器")
    root.geometry("400x200")  # 调整窗口大小以适应没有开始更新按钮的布局

    main_frame = tk.Frame(root)
    main_frame.pack(pady=20)

    status_label = tk.Label(main_frame, text="正在初始化...", font=("Helvetica", 12))
    status_label.pack(pady=10)

    progress_bar = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, length=300, mode='determinate')
    progress_bar.pack(pady=10)

    # 取消更新按钮
    cancel_button = tk.Button(main_frame, text="取消更新", command=cancel_update_callback,
                              font=("Helvetica", 10), state=tk.DISABLED)
    cancel_button.pack(pady=10)

    # 绑定窗口关闭事件
    root.protocol("WM_DELETE_WINDOW", cancel_update_callback)

    # 启动一个新的线程来执行更新操作
    update_thread = threading.Thread(target=threaded_fetch_and_process_url, args=(url,))
    update_thread.start()

    root.mainloop()


if __name__ == "__main__":
    url = "https://Bluecraft-Server.github.io/API/Python_Downloader_API/Version_Check"  # 请替换为实际网页地址
    create_gui()
