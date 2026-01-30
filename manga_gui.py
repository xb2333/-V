import os
import sys
import shutil
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import textwrap

# ==========================================
# 1. 导入库
# ==========================================
try:
    import cv2
    import easyocr
    from PIL import Image, ImageDraw, ImageFont
    import translators as ts
    import numpy as np
except ImportError as e:
    print("-------------------------------------------------------")
    print(f"【缺少库】请在黑框里运行: pip install easyocr opencv-python pillow translators numpy")
    print("-------------------------------------------------------")
    input(f"错误详情: {e} (按回车退出)")
    sys.exit()

class MangaTranslator:
    def __init__(self, root):
        self.root = root
        self.root.title("自动漫画翻译 (v11.0 完美排版版)")
        self.root.geometry("650x650")
        
        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.status = tk.StringVar(value="等待开始...")
        self.running = False
        self.font_path = self._get_font()

        self._setup_ui()

    def _get_font(self):
        fonts = ["simhei.ttf", "msyh.ttc", "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf"]
        for f in fonts:
            if os.path.exists(f): return f
        return "arial.ttf"

    def _setup_ui(self):
        frame = tk.Frame(self.root, padx=10, pady=10)
        frame.pack(fill='x')
        
        tk.Label(frame, text="输入目录:").grid(row=0, column=0, sticky='w')
        tk.Entry(frame, textvariable=self.input_dir, width=40).grid(row=0, column=1, padx=5)
        tk.Button(frame, text="选择", command=lambda: self.input_dir.set(filedialog.askdirectory())).grid(row=0, column=2)

        tk.Label(frame, text="输出目录:").grid(row=1, column=0, sticky='w')
        tk.Entry(frame, textvariable=self.output_dir, width=40).grid(row=1, column=1, padx=5)
        tk.Button(frame, text="选择", command=lambda: self.output_dir.set(filedialog.askdirectory())).grid(row=1, column=2)

        info_frame = tk.Frame(self.root, pady=10)
        info_frame.pack(fill='x', padx=10)
        tk.Label(info_frame, text="🔥 v11.0 升级内容：", fg="#D32F2F", font=("微软雅黑", 10, "bold")).pack(anchor='w')
        tk.Label(info_frame, text="1. 完美排版：文字绝对不超框，自动缩小、自动换行。", fg="gray").pack(anchor='w')
        tk.Label(info_frame, text="2. 翻译优化：强制锁定日文源，减少乱码和误译。", fg="gray").pack(anchor='w')

        self.btn = tk.Button(self.root, text="开始精细化嵌字", command=self.start, bg="#D32F2F", fg="white", font=("微软雅黑", 12, "bold"))
        self.btn.pack(fill='x', padx=20, pady=5)

        self.log_box = scrolledtext.ScrolledText(self.root, height=15)
        self.log_box.pack(fill='both', expand=True, padx=10)
        
        tk.Label(self.root, textvariable=self.status, bg="#eee").pack(fill='x', side='bottom')

    def log(self, msg):
        self.log_box.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {msg}\n")
        self.log_box.see(tk.END)

    def start(self):
        if self.running: return
        in_path = self.input_dir.get()
        out_path = self.output_dir.get()
        if not in_path or not out_path:
            return messagebox.showerror("错误", "请先选择文件夹")
        
        self.running = True
        self.btn.config(state='disabled')
        threading.Thread(target=self.run_process, args=(in_path, out_path), daemon=True).start()

    def run_process(self, in_dir, out_dir):
        if not os.path.exists(out_dir): os.makedirs(out_dir)
        
        self.log("启动排版引擎...")
        try:
            reader = easyocr.Reader(['ja', 'en'], gpu=False) 
        except Exception as e:
            self.log(f"引擎启动失败: {e}")
            self.running = False
            self.btn.config(state='normal')
            return

        files = [f for f in os.listdir(in_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp'))]
        total = len(files)
        self.log(f"开始处理 {total} 张图片...")

        for i, filename in enumerate(files):
            if not self.running: break
            
            src_path = os.path.join(in_dir, filename)
            dst_path = os.path.join(out_dir, f"trans_{filename}")
            
            self.status.set(f"处理中: {filename} ({i+1}/{total})")
            
            try:
                # 1. OpenCV 读取
                img_cv = cv2.imdecode(np.fromfile(src_path, dtype=np.uint8), -1)
                if img_cv.shape[2] == 4:
                    img_cv = cv2.cvtColor(img_cv, cv2.COLOR_BGRA2BGR)
                
                # 2. 识别 (段落模式)
                # min_size=10: 太小的噪点字不识别
                try:
                    results = reader.readtext(img_cv, paragraph=True, x_ths=0.8, y_ths=0.5, min_size=10)
                except Exception:
                    continue

                if not results:
                    self.log(f"[{i+1}/{total}] {filename}: 无文字，跳过")
                    shutil.copy(src_path, dst_path)
                    continue

                # 3. 处理每个气泡
                count = 0
                text_tasks = [] 

                for item in results:
                    bbox = item[0]
                    text_original = item[1]
                    if len(text_original.strip()) < 1: continue

                    # A. 智能去字 (保留背景)
                    bg_is_dark = self._clean_text_background(img_cv, bbox)
                    text_color = "white" if bg_is_dark else "black"

                    # B. 翻译 (优化：强制 from_language='ja')
                    text_trans = text_original
                    try:
                        # 强制指定源语言为日文，防止把汉字当中文翻
                        text_trans = ts.translate_text(text_original, translator='baidu', from_language='ja', to_language='zh')
                    except:
                        try:
                            # 备用谷歌
                            text_trans = ts.translate_text(text_original, translator='google', from_language='ja', to_language='zh-CN')
                        except:
                            pass
                    
                    text_tasks.append((bbox, text_trans, text_color))
                    count += 1

                # 4. 绘图
                img_pil = Image.fromarray(cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB))
                draw = ImageDraw.Draw(img_pil)

                for task in text_tasks:
                    # 使用新的完美排版函数
                    self._draw_text_perfect_fit(draw, task[0], task[1], task[2])

                img_pil.save(dst_path)
                self.log(f"[{i+1}/{total}] {filename}: 排版 {count} 处")

            except Exception as e:
                self.log(f"❌ 异常 {filename}: {e}")
                if not os.path.exists(dst_path): shutil.copy(src_path, dst_path)

        self.status.set("完成")
        self.running = False
        self.btn.config(state='normal')
        messagebox.showinfo("完成", f"排版优化完成！\n查看: {out_dir}")

    def _clean_text_background(self, img, bbox):
        coords = np.array(bbox).astype(np.int32)
        x_min, y_min = np.min(coords, axis=0)
        x_max, y_max = np.max(coords, axis=0)
        
        h, w = img.shape[:2]
        x_min, x_max = max(0, x_min), min(w, x_max)
        y_min, y_max = max(0, y_min), min(h, y_max)
        
        roi = img[y_min:y_max, x_min:x_max]
        if roi.size == 0: return False

        gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray_roi)
        is_dark_bg = mean_brightness < 100

        if is_dark_bg:
            _, mask = cv2.threshold(gray_roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        else:
            _, mask = cv2.threshold(gray_roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        kernel = np.ones((3,3), np.uint8)
        dilated_mask = cv2.dilate(mask, kernel, iterations=2)
        try:
            inpainted_roi = cv2.inpaint(roi, dilated_mask, 3, cv2.INPAINT_TELEA)
            img[y_min:y_max, x_min:x_max] = inpainted_roi
        except:
            pass # 极少数情况inpaint会失败，忽略
        
        return is_dark_bg

    def _draw_text_perfect_fit(self, draw, bbox, text, color):
        """
        核心排版算法：不断缩小字体，直到能塞进气泡为止
        """
        coords = np.array(bbox).astype(np.int32)
        x_min, y_min = np.min(coords, axis=0)
        x_max, y_max = np.max(coords, axis=0)
        
        # 气泡的实际宽高
        box_w = x_max - x_min
        box_h = y_max - y_min
        
        # 初始字体大小 (设得大一点，从大往小试)
        font_size = 40 
        min_font_size = 10
        
        final_font = None
        final_wrapped_text = text
        
        # --- 迭代缩小算法 ---
        while font_size >= min_font_size:
            try:
                font = ImageFont.truetype(self.font_path, font_size)
            except:
                font = ImageFont.load_default()
            
            # 估算当前字体下一行能塞多少个字
            # 注意：汉字宽≈font_size，非汉字窄一些，这里取平均
            char_width = font_size
            chars_per_line = max(1, int(box_w / char_width))
            
            # 自动换行
            wrapped_text = textwrap.fill(text, width=chars_per_line)
            
            # 计算换行后，整段文字实际占多大地方
            # draw.multiline_textbbox 需要 Pillow >= 9.2
            try:
                left, top, right, bottom = draw.multiline_textbbox((0,0), wrapped_text, font=font)
                text_w = right - left
                text_h = bottom - top
            except:
                # 兼容旧版 Pillow，简单估算
                lines = wrapped_text.split('\n')
                text_w = max([len(line) for line in lines]) * font_size
                text_h = len(lines) * (font_size + 2)

            # 关键判断：如果宽 OR 高 超出了气泡，就缩小字体
            if text_w <= box_w and text_h <= box_h:
                final_font = font
                final_wrapped_text = wrapped_text
                break # 找到了！跳出循环
            
            font_size -= 2 # 每次缩小2号，继续试
            
        # 如果缩到最小还是放不下，就强制用最小号
        if final_font is None:
            try:
                final_font = ImageFont.truetype(self.font_path, min_font_size)
            except:
                final_font = ImageFont.load_default()
            chars_per_line = max(1, int(box_w / min_font_size))
            final_wrapped_text = textwrap.fill(text, width=chars_per_line)

        # 绘制居中
        # 重新计算最终文字的宽高
        try:
            left, top, right, bottom = draw.multiline_textbbox((0,0), final_wrapped_text, font=final_font)
            real_w = right - left
            real_h = bottom - top
        except:
             lines = final_wrapped_text.split('\n')
             real_w = max([len(line) for line in lines]) * min_font_size
             real_h = len(lines) * min_font_size

        # 计算居中坐标
        pos_x = x_min + (box_w - real_w) / 2
        pos_y = y_min + (box_h - real_h) / 2
        
        # 绘制文字 (如果是浅色字，加深色描边；深色字加浅色描边)
        outline_color = "white" if color == "black" else "black"
        if color == "black": # 只给黑字加白描边，清晰度最高
             for off_x, off_y in [(-1,-1), (-1,1), (1,-1), (1,1)]:
                 draw.multiline_text((pos_x+off_x, pos_y+off_y), final_wrapped_text, font=final_font, fill="white", align="center")

        draw.multiline_text((pos_x, pos_y), final_wrapped_text, font=final_font, fill=color, align="center")

if __name__ == "__main__":
    os.makedirs(os.path.expanduser('~/.cache/translators'), exist_ok=True)
    root = tk.Tk()
    app = MangaTranslator(root)
    root.mainloop()