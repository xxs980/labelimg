# Adapted LabelImg for Enhanced User Experience

This repository is a fork of [HumanSignal/labelImg](https://github.com/HumanSignal/labelImg), maintained at [xxs980/labelimg](https://github.com/xxs980/labelimg). The original repository is archived and no longer being maintained. This fork is based on the latest version (1.8.6) and includes fixes and personal-use modifications.

[Original README](./original_README.rst)

## Installation

### Install from source / 从源码安装

This fork is not published on PyPI, so `pip install` by package name is not supported. Use the source checkout below.

以下命令直接使用系统中已有的 `python` / `python3` 和 `pip`。源码安装后会生成 `mlabelImg` 命令；修改源码时推荐使用 editable 安装，只安装当前代码时使用普通源码安装。两种安装方式二选一，不要同时执行。

#### Windows (PowerShell)

```powershell
git clone https://github.com/xxs980/labelimg
cd labelimg
python -m pip install --upgrade pip
python -m pip install pyqt5 lxml
pyrcc5 -o libs/resources.py resources.qrc
```

然后从下面两种安装方式中选择一种：

```powershell
# 方式一：editable 安装，修改源码后立即生效
python -m pip install -e .
```

```powershell
# 方式二：普通源码安装，安装当前仓库的代码副本
python -m pip install .
```

安装完成后启动：

```powershell
mlabelImg
```

#### Linux / macOS

```bash
git clone https://github.com/xxs980/labelimg
cd labelimg
python3 -m pip install --upgrade pip
python3 -m pip install pyqt5 lxml
pyrcc5 -o libs/resources.py resources.qrc
```

然后从下面两种安装方式中选择一种：

```bash
# 方式一：editable 安装，修改源码后立即生效
python3 -m pip install -e .
```

```bash
# 方式二：普通源码安装，安装当前仓库的代码副本
python3 -m pip install .
```

安装完成后启动：

```bash
mlabelImg
```

如果找不到 `mlabelImg` 命令，Windows 可改用 `python -m mlabelImg` 启动，Linux/macOS 可改用 `python3 -m mlabelImg`。

## Local startup / 本地启动

以下步骤只用于直接运行当前仓库中的源码，不会安装 `mlabelImg` 命令。如果希望安装后通过 `mlabelImg` 启动，请使用上面的 “Install from source”。建议使用 Python 3.8 或更高版本。

### Windows (PowerShell)

在仓库根目录（例如 `D:\labelimg`）执行：

```powershell
python -m pip install --upgrade pip
python -m pip install pyqt5 lxml
pyrcc5 -o libs/resources.py resources.qrc
python mlabelImg.py
```

### Linux / macOS

```bash
python3 -m pip install --upgrade pip
python3 -m pip install pyqt5 lxml
pyrcc5 -o libs/resources.py resources.qrc
python3 mlabelImg.py
```

`libs/resources.py` 是由 `resources.qrc` 生成的资源文件，并且已被 Git 忽略。只有在文件缺失或修改了 `resources.qrc` 后，才需要重新执行 `pyrcc5`。如果找不到 `pyrcc5` 命令，可以改用：

```powershell
python -m PyQt5.pyrcc_main -o libs/resources.py resources.qrc
```

### Launch options

```text
# Run directly from the source checkout
python mlabelImg.py [IMAGE_DIR] [CLASS_FILE] [SAVE_DIR]

# Run after either source installation method
mlabelImg [IMAGE_DIR] [CLASS_FILE] [SAVE_DIR]
```

三个参数都是可选的：

- 不带参数启动：`python mlabelImg.py` 或 `mlabelImg`，然后在界面中选择 `File -> Open Dir`。
- 按完整 YOLO 工作区启动（源码安装后）：

```powershell
mlabelImg .\data\images .\data\classes.txt .\data\labels
```

直接运行源码时，把上面的 `mlabelImg` 换成 `python mlabelImg.py`。其中 `IMAGE_DIR` 是图片目录，`CLASS_FILE` 是预定义类别文件，`SAVE_DIR` 是标注保存目录。启动后在左侧工具栏选择 `YOLO` 格式即可。

## Usage

### Setup directory

Create a folder structure same as below

```
├── data
    ├── images
    └── labels
```

Put all of your image in `images` directory. And create a `classes.txt` contain all class you want to label. Example of `classes.txt` as below

``` txt
dog
cat
pig
```

Put `classes.txt` in the `labels` directory, the directory of the annotations. It is
also looked for next to the images and one level above both, so the file may stay
wherever your dataset already keeps it. Without that file the boxes are still shown,
but their classes are named `class0`, `class1`, ... after the index in the `.txt`.

Full structure of workspace as below

```
├── data
    ├── images
    │   ├── img1.jpg
    │   ├── img2.jpg
    │   └── ...
    ├── labels
    │   └── classes.txt
    └── classes.txt
```

### Run mlabelImg

After installing from source, start it with:

```powershell
mlabelImg .\data\images .\data\classes.txt .\data\labels
```

When running directly from a source checkout, use:

```powershell
python mlabelImg.py .\data\images .\data\classes.txt .\data\labels
```

On GUI of labelImg: 

- `File -> Change Save Dir -> (save label directory)`
- Choose `YOLO` format on the left tray

Next and previous image with `D -> A`

Label with `W`

Delete the current image and its annotation with `T` (asks before deleting)

Delete `.\data\classes.txt` after labeling

### Label format

With `YOLO` format, label will be saved with format `label_index x_center y_center w h` and normalize to scale `[0, 1]`

``` txt
1 0.415842 0.863095 0.102970 0.101190
1 0.228713 0.315476 0.077228 0.053571
1 0.756436 0.328869 0.114851 0.050595
```

## Reference

- Author: TzuTa Lin
- Author Email: tzu.ta.lin@gmail.com
- [tzutalin/labelImg](https://github.com/tzutalin/labelImg)
