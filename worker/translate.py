from datetime import datetime
import os
import shutil
import subprocess
import re

from celery.contrib.abortable import AbortableTask

# 加载配置
from config import CLEAN_UP_TEMP, MINERU_PATH, MODEL, PROMPTS, TEMP_DIR, client, r


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

def translate_text(text, target_lang, tracker):
  """将文本按标题分段
  Returns:
    None|str :返回  None 表示被取消
  """
  """使用大模型API翻译文本"""
  sections = split_markdown_by_headers(text)
  translated_sections = []
  tracker.split_progress(len(sections))
  
  for section in sections:
    prompt = f"请将以下Markdown格式的论文段落逐句翻译成{target_lang}。"
    prompt += PROMPTS
    prompt += "\n\n" + section

    chat_completion = client.chat.completions.create(
      messages=[
        {
          "role": "user",
          "content": prompt,
        }
      ],
      model=MODEL,
      max_tokens=8192,
    )
    translated_sections.append(chat_completion.choices[0].message.content)
    if tracker.step():
      return None  # 翻译过程被取消
  
  # 合并所有翻译后的段落
  return '\n\n'.join(translated_sections)

class ProgressTracker:
  """用于追踪 LLM 翻译过程的进度情况"""
  def __init__(self, task, executor, progress_start, progress_end):
    self.task = task
    self.executor = executor
    self.progress = progress_start
    self.progress_end = progress_end

  def split_progress(self, step_count):
    """根据总段落数量设置进度步长"""
    self.progress_step = int((self.progress_end - self.progress) / step_count)

  def step(self) -> bool:
    """每完成一个段落翻译都检查一次取消状态并更新进度"""
    self.progress += self.progress_step
    return self.executor.progress(self.task, self.progress)

class Executor:
  def __init__(self, filename, target_lang):
    self.target_lang=target_lang
    self.filename = filename
  
  def progress(self, task, progress) -> bool:
    """检查取消状态并更新进度
    Args:
      task: celery task
      progress: 进度, 范围 [1, 100]
    Returns:
      bool: True 表示被取消
    """
    if task.is_aborted():  # 检查取消状态
      self.clean_up()
      return True
    else:
      task.update_state(
        state='PROGRESS', 
        meta={
          'progress': progress,
          'status': f'处理中... {progress}%',
          'timestamp': datetime.now().isoformat()
        }
      )
      return False

  def step1(self):
    """创建本任务使用的临时目录"""
    try:
      self.temp_dir = os.path.join(TEMP_DIR, os.urandom(8).hex())
      os.makedirs(self.temp_dir, exist_ok=True)
    except Exception as e:
      raise Exception("创建临时目录失败") from e

  def step2(self):
    """保存上传到 Redis 的 PDF"""
    try:
      self.input_pdf_path = os.path.join(self.temp_dir, self.filename)
      file_data = r.get(f"file:{self.filename}")
      with open(self.input_pdf_path, 'wb') as f:
        f.write(file_data)
    except Exception as e:
      raise Exception("保存上传到 Redis 的 PDF 失败") from e

  def step3(self):
    """使用 MinerU magic-pdf 转换 PDF 生成 markdown 和图片"""
    try:
      subprocess.run([
        MINERU_PATH,
        "-p", self.input_pdf_path,
        "-o", self.temp_dir
      ], check=True)
    except Exception as e:
      raise Exception("MinerU 转换 PDF 失败") from e

  def step4(self):
    """获取 magic-pdf 生成的 markdown 和图片路径"""
    try:
      self.pdf_name = os.path.splitext(os.path.basename(self.input_pdf_path))[0]
      self.md_path = os.path.join(self.temp_dir, self.pdf_name, "auto", f"{self.pdf_name}.md")
      self.images_dir = os.path.join(self.temp_dir, self.pdf_name, "auto", "images")
      assert os.path.exists(self.md_path), "PDF 生成的 Markdown 文件不存在"
    except Exception as e:
      raise Exception("PDF 转换失败")

  def step5(self):
    """创建用于打包的输出目录"""
    try:
      # 创建 output 目录
      self.output_dir = os.path.join(self.temp_dir, "output")
      os.makedirs(self.output_dir, exist_ok=True)
      # 复制原文 markdown
      shutil.copy2(self.md_path, os.path.join(self.output_dir, f"{self.pdf_name}_original.md"))
      # 复制图片
      if os.path.exists(self.images_dir):
        shutil.copytree(self.images_dir, os.path.join(self.output_dir, "images"))
    except Exception as e:
      raise Exception("创建 output 目录失败") from e

  def step6(self, tracker):
    """翻译 markdown"""
    try:
      # 读取 markdown 内容
      with open(self.md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
      # 翻译 markdown 内容
      translated_content = translate_text(md_content, self.target_lang, tracker)
      if translated_content is None:
        return
      # 保存翻译后的 markdown
      output_md = os.path.join(self.output_dir, f"{self.pdf_name}_translated.md")
      with open(output_md, 'w', encoding='utf-8') as f:
        f.write(translated_content)
    except Exception as e:
      raise Exception("翻译失败") from e

  def step7(self):
    """打包 zip"""
    try:
      self.zip_path = os.path.join(self.temp_dir, f"{self.pdf_name}.zip")
      shutil.make_archive(
        os.path.join(self.temp_dir, self.pdf_name),
        'zip',
        self.output_dir
      )
    except Exception as e:
      raise Exception("打包 zip 失败") from e

  def step8(self):
    """通过 redis 传输 zip 文件"""
    try:
      with open(self.zip_path, "rb") as f:
        file_data = f.read()
      r.set(f"file:{self.pdf_name}.zip", file_data)
    except Exception as e:
      raise Exception("上传 zip 文件到 Redis 失败") from e

  def clean_up(self):
    """根据配置决定是否清理临时文件"""
    if CLEAN_UP_TEMP:
      try:
        shutil.rmtree(self.temp_dir)
      except Exception as e:
        print(f"清理临时文件失败: {str(e)}")
        # 不抛出异常
