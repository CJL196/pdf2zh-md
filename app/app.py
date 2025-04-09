from task_registry import TaskRegistry
import gradio as gr
import fitz  # PyMuPDF库，用于PDF预览

# 加载配置
from config import QUEUE_SIZE

# Gradio 服务端内存中的任务ID存储（简单实现，应考虑持久化）
task_registry = TaskRegistry(maxlen=QUEUE_SIZE)

def preview_pdf(tmp_path):
  """预览PDF文件的前五页"""
  if tmp_path is None:
    return None, "请上传PDF文件"
  try:
    doc = fitz.open(tmp_path)  # 打开PDF文件
    total_pages = doc.page_count  # 获取总页数
    num_pages = min(5, total_pages)  # 只显示前五页
    # 保存预览图片
    preview_images = []
    for page_num in range(num_pages):
      page = doc[page_num]
      pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # 1.5倍缩放以提高清晰度
      preview_images.append(pix.pil_image())  # requires pymupdf>=1.25.2
    doc.close()
    return preview_images, f"PDF预览成功，显示前{num_pages}页，共{total_pages}页"
  except Exception as e:
    return None, f"PDF预览失败: {str(e)}"

def submit_convert_task(tmp_path: str, target_lang: str = None):
  """提交转换任务"""
  if tmp_path is None:
    return "请上传PDF文件"
  try:
    task_id = task_registry.register_task(tmp_path, target_lang)
    return f"提交成功, 任务ID: {task_id}"
  except Exception as e:
    return f"提交任务失败: {str(e)}"

with gr.Blocks() as web:
  gr.Markdown("# PDF翻译工具")
  
  with gr.Tabs():
    with gr.TabItem("提交任务"):
      with gr.Row():
        with gr.Column(scale=2):
          gr_file = gr.File(label="上传PDF文件")
          preview_gallery = gr.Gallery(label="PDF预览", columns=1, rows=5, height=600)
        
        with gr.Column(scale=1):
          target_lang = gr.Dropdown(
            choices=["中文", "English", "日本語", "한국어"],
            value="中文",
            label="选择目标语言"
          )
          with gr.Row():
            convert_btn = gr.Button("转换为Markdown")
            translate_btn = gr.Button("转换并翻译")
          submit_status = gr.Textbox(label="提交状态", interactive=False)
          preview_status = gr.Textbox(label="预览状态", interactive=False)
    
    with gr.TabItem("任务队列"):
      # 表头
      with gr.Row(show_progress=True, equal_height=True, variant="compact"):
        gr.HighlightedText(
          value=[("📬", "任务状态"), ("任务ID", None)],
          label="",
          container=True,
          color_map={"任务状态": "rgba(180, 180, 180, 0.6)"},
          scale=6
        )
        gr.Button(value="更新时间", variant="huggingface", scale=2, size="sm")
        gr.Button(value="总进度", variant="huggingface", size="sm")
        gr.Button(value="", variant="huggingface", interactive=False, size="sm")
        gr.Button(value="", variant="huggingface", interactive=False, size="sm")
      task_items = []
      
      for i in range(QUEUE_SIZE):
        with gr.Row(show_progress=True, equal_height=True, variant="panel") as row:  # 默认隐藏
          task_items.extend([
            gr.HighlightedText(visible=False, label="", container=True, scale=6),
            gr.Button(visible=False, scale=2, size="sm"),
            gr.Button(visible=False, size="sm"),
            gr.DownloadButton(label="下载结果", visible=False, variant="primary", size="sm"),
            gr.Button(value="删除任务", visible=False, variant="stop", size="sm"),
          ])
      
      gr.Button("手动刷新(默认每隔 5 秒刷新一次)").click(
        fn=task_registry.update_all_tasks,
        outputs=task_items,
      )
  
  # 自动刷新
  t = gr.Timer(5)
  t.tick(
    fn=task_registry.update_all_tasks,
    outputs=task_items,
  )

  for i in range(QUEUE_SIZE):
    del_btn: gr.Button = task_items[i * 5 + 4]
    del_btn.click(
      # 删除任务
      fn=lambda x=i: task_registry.remove_task(x),
    ).then(
      # 删除任务后刷新任务队列显示的组件
      fn=task_registry.update_all_tasks,
      outputs=task_items,
    )

  # 提交任务逻辑
  convert_btn.click(
    fn=lambda f: submit_convert_task(f.name),
    inputs=gr_file,
    outputs=submit_status
  )
  
  translate_btn.click(
    fn=lambda f, l: submit_convert_task(f.name, l),
    inputs=[gr_file, target_lang],
    outputs=submit_status
  )

  # 上传文件后自动触发预览
  gr_file.change(
    fn=preview_pdf,
    inputs=[gr_file],
    outputs=[preview_gallery, preview_status]
  )

if __name__ == "__main__":
  web.launch(share=True, server_name="0.0.0.0") 