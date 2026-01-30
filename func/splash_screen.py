import tkinter as tk
from PIL import Image, ImageTk
import base64
from io import BytesIO

# 从resources模块导入base64编码的资源
from func.resources import STARTUP_PNG

def show_system_splash():
    """创建tkinter系统级轻量闪屏（无QApp依赖，立即显示）"""
    # 1. 创建主窗口（隐藏）
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口
    
    # 2. 创建闪屏窗口
    splash = tk.Toplevel(root)
    
    # 3. 设置窗口属性
    splash.overrideredirect(True)  # 无边框
    splash.attributes('-topmost', True)  # 置顶
    
    # 4. 设置窗口透明
    splash.attributes('-transparentcolor', 'white')  # 将白色设置为透明色
    
    # 5. 从base64编码加载图片
    try:
        # 解码base64字符串
        image_data = base64.b64decode(STARTUP_PNG)
        # 创建BytesIO对象
        image_stream = BytesIO(image_data)
        # 加载图片
        image = Image.open(image_stream)
        # 获取图片尺寸
        width, height = image.size
        
        # 6. 获取屏幕中心位置
        screen_width = splash.winfo_screenwidth()
        screen_height = splash.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        # 7. 设置窗口位置和大小
        splash.geometry(f"{width}x{height}+{x}+{y}")
        
        # 8. 转换图片为tkinter可用格式
        photo = ImageTk.PhotoImage(image)
        
        # 9. 创建标签显示图片，背景设为白色以匹配透明色
        label = tk.Label(splash, image=photo, bg='white')
        label.pack(fill=tk.BOTH, expand=tk.YES)
        
        # 10. 保存图片引用，防止被垃圾回收
        splash.photo = photo
        
    except Exception as e:
        print(f"Error loading splash image: {e}")
        # 降级方案：使用白色背景
        width, height = 400, 300
        screen_width = splash.winfo_screenwidth()
        screen_height = splash.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        splash.geometry(f"{width}x{height}+{x}+{y}")
        splash.config(bg="white")
    
    # 11. 显示窗口
    splash.update_idletasks()  # 确保窗口创建完成
    splash.deiconify()  # 显示窗口
    splash.update()  # 立即刷新显示
    return splash

def close_system_splash(splash):
    """关闭系统级闪屏"""
    if splash:
        # 获取主窗口并一起关闭
        root = splash.master
        splash.destroy()
        if root:
            root.destroy()
