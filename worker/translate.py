import os
import shutil
from openai import OpenAI
import subprocess
import re

# 加载配置
from config import config


client = OpenAI(
  api_key=os.getenv("API_KEY"),
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
    prompt = f"请将以下Markdown格式的论文段落逐句翻译成{target_lang}。"
    for p in config.prompts:
      prompt += p
    prompt += "\n\n" + section

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

def convert_pdf_to_markdown(tmp_path):
  """将PDF转换为Markdown格式"""
  if tmp_path is None:
    return None, "请上传PDF文件"
  
  # 创建临时目录
  temp_dir = os.path.join(config.paths.temp_dir, os.urandom(8).hex())
  os.makedirs(temp_dir, exist_ok=True)
  
  try:
    # 保存上传的PDF
    pdf_path = os.path.join(temp_dir, "input.pdf")
    shutil.copy(tmp_path, pdf_path)
    
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

def process_pdf(tmp_path, target_lang="中文"):
  """处理PDF文件：转换为markdown并翻译"""
  if tmp_path is None:
    return None, "请上传PDF文件"
  
  # 创建临时目录
  temp_dir = os.path.join(config.paths.temp_dir, os.urandom(8).hex())
  os.makedirs(temp_dir, exist_ok=True)
  
  try:
    # 保存上传的PDF
    pdf_path = os.path.join(temp_dir, "input.pdf")
    shutil.copy(tmp_path, pdf_path)
    
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
