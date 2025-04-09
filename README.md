# PDF翻译工具

这是一个基于Gradio的Web应用，可以将PDF文件转换为Markdown格式并进行翻译。该工具使用MinerU进行PDF转换，使用DeepSeek API进行翻译。

## 示例

左侧为输入的pdf，右侧为翻译后的markdown文件

![demo2](assets/demo2.png)
![demo1](assets/demo.png)

## 在线体验

在中大校园网内访问 [http://172.18.198.204:7861/](http://172.18.198.204:7861/)

## 功能特点

- 支持PDF文件上传
- 支持多种目标语言选择（中文、英文、日文、韩文）
- 自动提取PDF中的图片
- 保持Markdown格式
- 打包下载翻译结果和图片
- 使用配置文件管理设置

## 部署安装

### Worker

`worker` 目录下

#### 安装依赖

跟随[MinerU官方教程](https://github.com/opendatalab/MinerU?tab=readme-ov-file#quick-start)安装 magic-pdf。安装过程是需要[下载模型参数](https://github.com/papayalove/Magic-PDF/blob/master/docs/how_to_download_models_zh_cn.md)的，这些模型参数通过 huggingface_hub 下载，默认会存储在系统盘的 ``~YourUser/.cache/` 目录下，请确保相关磁盘空间（或者或许能改存储路径）。

注意，若需要 GPU 加速，需要按照其指定要求的 CUDA 等的版本：
- [Windows](https://github.com/papayalove/Magic-PDF/blob/master/docs/README_Windows_CUDA_Acceleration_zh_CN.md)
- [Ubuntu](https://github.com/papayalove/Magic-PDF/blob/master/docs/README_Ubuntu_CUDA_Acceleration_zh_CN.md)

由于 magic-pdf 对环境要求比较严格，为了避免和其他依赖打架，最好给它单独创建一个环境安装，然后配置中填写其 `.../magic-pdf` 绝对路径。

> 目前 app 部分的 PyMuPDF 已经和 magic-pdf 的要求 冲突了

其他依赖安装：

```bash
pip install -r requirements.txt
```

#### 配置说明

在 `config.yaml` 文件中可以配置以下选项：

- `settings`: 应用设置
  - `cleanup_temp`: 是否在处理完成后删除临时文件

- `redis`: Redis 相关配置

- `api`: API相关配置
  - `base_url`: DeepSeek API的基础URL
  - `api_key`: DeepSeek API密钥
  - `model`: 使用的模型名称

- `paths`: 路径配置
  - `temp_dir`: 临时文件目录
  - `mineru_path`: MinerU可执行文件路径

- `prompts`: 翻译要求的 prompts


此外，安装好 magic-pdf 后，其配置文件在：`~YourUser/magic-pdf.json`。


#### 启动应用

确保 Redis 可以访问，可以参考 `worker/docker-compose.yaml` 部署。

```shell
# 指定为 4 线程启动
celery -A celery_app.app worker --loglevel=info  --concurrency=4

# celery 在 Windows 尚不支持多线程，需要指定为单线程启动
celery -A celery_app.app worker --loglevel=info --pool=solo
```

#### 注意事项

- 确保MinerU环境已正确配置
- 确保DeepSeek API密钥有效
- 处理大文件时可能需要较长时间
- 临时文件默认保存在项目根目录的 `tmp` 文件夹中 

### Web App

`app` 目录下

#### 安装依赖

```bash
pip install -r requirements.txt
```

#### 配置说明

在 `config.yaml` 文件中可以配置以下选项：

- `settings`: 应用设置settings:
  - `queue_size`: 队列大小
  - `result_dir`: 临时存放任务结果文件的目录 

- `redis`: Redis 相关配置

#### 启动应用

确保 Redis 可以访问。Web App 将通过 Redis 和 Worker 通信。

```shell
python app.py
```
