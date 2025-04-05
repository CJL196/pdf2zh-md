import os
import shutil
import tempfile
from pathlib import Path
import gradio as gr
from openai import OpenAI
import subprocess
from omegaconf import OmegaConf
import re
import fitz  # PyMuPDF库，用于PDF预览

# 加载配置
config = OmegaConf.load('config.yaml')

# 确保临时目录存在
os.makedirs(config.paths.temp_dir, exist_ok=True)

client = OpenAI(
    api_key=config.api.api_key,
    base_url=config.api.base_url
)

def split_markdown_by_headers(markdown_content):
    """将markdown内容按照大标题分段"""
    # 使用正则表达式匹配以#开头的标题
    # 确保#后面有空格，避免匹配代码中的注释
    header_pattern = r'^(#{1,6}\s+.+)$'
    sections = []
    current_section = []
    
    for line in markdown_content.split('\n'):
        if re.match(header_pattern, line):
            if current_section:
                sections.append('\n'.join(current_section))
            current_section = [line]
        else:
            current_section.append(line)
    
    if current_section:
        sections.append('\n'.join(current_section))
    
    return sections

def translate_text(text, target_lang="中文"):
    """使用大模型API翻译文本"""
    # 将文本按标题分段
    sections = split_markdown_by_headers(text)
    translated_sections = []
    
    for section in sections:
        prompt = f"请将以下Markdown格式的论文段落逐句翻译成{target_lang}。翻译时需确保语言具有学术性，准确传达原文含义，不得遗漏任何部分。你必须翻译每一句话，而不是总结内容。仅输出翻译结果，不得添加任何无关内容或注释。遇到<html>包裹的块只需原样输出，保持原有的markdown格式：\n\n{section}"
        
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model=config.api.model,
            max_tokens=8192,
        )
        translated_sections.append(chat_completion.choices[0].message.content)
    
    # 合并所有翻译后的段落
    return '\n\n'.join(translated_sections)

def convert_pdf_to_markdown(pdf_file):
    """将PDF转换为Markdown格式"""
    if pdf_file is None:
        return None, "请上传PDF文件"
    
    # 创建临时目录
    temp_dir = os.path.join(config.paths.temp_dir, os.urandom(8).hex())
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # 保存上传的PDF
        pdf_path = os.path.join(temp_dir, "input.pdf")
        shutil.copy(pdf_file.name, pdf_path)
        
        # 使用MinerU转换PDF
        try:
            subprocess.run([
                config.paths.mineru_path,
                "-p", pdf_path,
                "-o", temp_dir
            ], check=True)
            
            # 获取生成的markdown文件路径
            pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
            md_path = os.path.join(temp_dir, pdf_name, "auto", f"{pdf_name}.md")
            images_dir = os.path.join(temp_dir, pdf_name, "auto", "images")
            
            if not os.path.exists(md_path):
                return None, "PDF转换失败"
            
            # 创建输出目录
            output_dir = os.path.join(temp_dir, "output")
            os.makedirs(output_dir, exist_ok=True)
            
            # 复制markdown文件
            shutil.copy2(md_path, os.path.join(output_dir, f"{pdf_name}.md"))
            
            # 复制图片文件夹
            if os.path.exists(images_dir):
                shutil.copytree(images_dir, os.path.join(output_dir, "images"))
            
            # 创建zip文件
            zip_path = os.path.join(temp_dir, "output.zip")
            shutil.make_archive(
                os.path.join(temp_dir, "output"),
                'zip',
                output_dir
            )
            
            return zip_path, "转换完成"
            
        except Exception as e:
            return None, f"转换失败: {str(e)}"
            
    finally:
        # 根据配置决定是否清理临时文件
        if config.settings.cleanup_temp:
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"清理临时文件失败: {str(e)}")

def process_pdf(pdf_file, target_lang="中文"):
    """处理PDF文件：转换为markdown并翻译"""
    if pdf_file is None:
        return None, "请上传PDF文件"
    
    # 创建临时目录
    temp_dir = os.path.join(config.paths.temp_dir, os.urandom(8).hex())
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # 保存上传的PDF
        pdf_path = os.path.join(temp_dir, "input.pdf")
        shutil.copy(pdf_file.name, pdf_path)
        
        # 使用MinerU转换PDF
        try:
            subprocess.run([
                config.paths.mineru_path,
                "-p", pdf_path,
                "-o", temp_dir
            ], check=True)
            
            # 获取生成的markdown文件路径
            pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
            md_path = os.path.join(temp_dir, pdf_name, "auto", f"{pdf_name}.md")
            images_dir = os.path.join(temp_dir, pdf_name, "auto", "images")
            
            if not os.path.exists(md_path):
                return None, "PDF转换失败"
            
            # 读取markdown内容
            with open(md_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            # 翻译markdown内容
            translated_content = translate_text(md_content, target_lang)
            
            # 创建输出目录
            output_dir = os.path.join(temp_dir, "output")
            os.makedirs(output_dir, exist_ok=True)
            
            # 保存原文markdown
            shutil.copy2(md_path, os.path.join(output_dir, f"{pdf_name}_original.md"))
            
            # 保存翻译后的markdown
            output_md = os.path.join(output_dir, f"{pdf_name}_translated.md")
            with open(output_md, 'w', encoding='utf-8') as f:
                f.write(translated_content)
            
            # 复制图片文件夹
            if os.path.exists(images_dir):
                shutil.copytree(images_dir, os.path.join(output_dir, "images"))
            
            # 创建zip文件
            zip_path = os.path.join(temp_dir, "output.zip")
            shutil.make_archive(
                os.path.join(temp_dir, "output"),
                'zip',
                output_dir
            )
            
            return zip_path, "处理完成"
            
        except Exception as e:
            return None, f"处理失败: {str(e)}"
            
    finally:
        # 根据配置决定是否清理临时文件
        if config.settings.cleanup_temp:
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"清理临时文件失败: {str(e)}")

def preview_pdf(pdf_file):
    """预览PDF文件的前五页"""
    if pdf_file is None:
        return None, "请上传PDF文件"
    
    try:
        # 打开PDF文件
        doc = fitz.open(pdf_file.name)
        
        # 获取总页数
        total_pages = doc.page_count
        
        # 只显示前五页
        num_pages = min(5, total_pages)
        
        # 创建临时目录
        temp_dir = os.path.join(config.paths.temp_dir, os.urandom(8).hex())
        os.makedirs(temp_dir, exist_ok=True)
        
        # 保存预览图片
        preview_images = []
        for page_num in range(num_pages):
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # 1.5倍缩放以提高清晰度
            img_path = os.path.join(temp_dir, f"preview_page_{page_num+1}.png")
            pix.save(img_path)
            preview_images.append(img_path)
        
        doc.close()
        return preview_images, f"PDF预览成功，显示前{num_pages}页，共{total_pages}页"
    except Exception as e:
        return None, f"PDF预览失败: {str(e)}"

# 创建Gradio界面
with gr.Blocks() as demo:
    gr.Markdown("# PDF工具")
    gr.Markdown("上传PDF文件，选择转换方式：")
    gr.Markdown("1. 转换为Markdown（保留原文）")
    gr.Markdown("2. 转换为Markdown并翻译")
    
    with gr.Row():
        with gr.Column(scale=2):  # 增加左侧列的比例
            pdf_input = gr.File(label="上传PDF文件")
            preview_gallery = gr.Gallery(label="PDF预览", show_label=True, columns=1, rows=5, height=600)  # 增加预览窗口高度
            preview_status = gr.Textbox(label="预览状态")
        
        with gr.Column(scale=1):  # 右侧列比例较小
            target_lang = gr.Dropdown(
                choices=["中文", "English", "日本語", "한국어"],
                value="中文",
                label="选择目标语言（仅用于翻译）"
            )
            with gr.Row():
                convert_btn = gr.Button("转换为Markdown")
                translate_btn = gr.Button("转换并翻译")
            output_file = gr.File(label="下载结果")
            status = gr.Textbox(label="处理状态")
    
    # 上传文件后自动触发预览
    pdf_input.change(
        fn=preview_pdf,
        inputs=[pdf_input],
        outputs=[preview_gallery, preview_status]
    )
    
    convert_btn.click(
        fn=convert_pdf_to_markdown,
        inputs=[pdf_input],
        outputs=[output_file, status]
    )
    
    translate_btn.click(
        fn=process_pdf,
        inputs=[pdf_input, target_lang],
        outputs=[output_file, status]
    )

if __name__ == "__main__":
    demo.launch(share=True, server_name="0.0.0.0") 