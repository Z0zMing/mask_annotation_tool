# 图像掩码标注工具详细用户指南

## 目录
1. [简介](#1-简介)
2. [安装说明](#2-安装说明)
3. [启动程序](#3-启动程序)
4. [用户界面](#4-用户界面)
5. [基本操作](#5-基本操作)
   - [5.1 打开图像](#51-打开图像)
   - [5.2 打开文件夹](#52-打开文件夹)
   - [5.3 浏览图像](#53-浏览图像)
6. [标注掩码](#6-标注掩码)
   - [6.1 绘制模式](#61-绘制模式)
   - [6.2 平移模式](#62-平移模式)
   - [6.3 画笔设置](#63-画笔设置)
   - [6.4 套索工具](#64-套索工具)
7. [图像导航和缩放](#7-图像导航和缩放)
8. [保存与导出](#8-保存与导出)
   - [8.1 保存单个掩码](#81-保存单个掩码)
   - [8.2 批量保存掩码](#82-批量保存掩码)
9. [撤销与重做](#9-撤销与重做)
10. [快捷键参考](#10-快捷键参考)
11. [高级技巧](#11-高级技巧)
12. [故障排除](#12-故障排除)
13. [联系与支持](#13-联系与支持)

## 1. 简介

图像掩码标注工具是一款专为图像分割任务设计的交互式应用程序。它允许用户通过简单的绘制操作创建精确的掩码，用于机器学习、计算机视觉等领域的图像分割训练。本工具支持多种绘制模式，包括自由绘制和套索选择，同时提供直观的用户界面和高效的键盘快捷键。

### 主要特性
- 支持多种图像格式（PNG, JPG, BMP, TIFF等）
- 多种绘制工具（画笔、套索）
- 撤销/重做功能
- 图像缩放和平移
- 批量处理图像
- 自动保存和恢复标注进度
- 丰富的键盘快捷键

## 2. 安装说明

### 系统要求
- Python 3.6 或更高版本
- 支持的操作系统：Windows, macOS, Linux

### 安装步骤

1. 克隆或下载仓库到本地：
   ```
   git clone https://github.com/Z0zMing/mask_annotation_tool.git
   ```

2. 进入项目目录：
   ```
   cd mask_annotation_tool
   ```

3. 安装依赖库：
   ```
   pip install -r requirements.txt
   ```

   主要依赖包括：
   - PyQt5：用户界面库
   - NumPy：数值计算库
   - OpenCV：图像处理库
   - Pillow：Python图像库

## 3. 启动程序

安装完成后，通过以下命令启动程序：

```
python src/MainWindow.py
```

在Windows系统中，您也可以双击`start.bat`文件（如果存在）快速启动程序。

## 4. 用户界面

启动程序后，您将看到主窗口，包含以下几个主要部分：

![用户界面示意图](interface_diagram.png)

1. **菜单栏**：顶部包含文件、编辑等菜单选项
2. **工具栏**：包含常用操作按钮
   - 打开图像/文件夹按钮
   - 保存掩码按钮
   - 清除掩码按钮
   - 绘制模式选择按钮
   - 平移模式按钮
   - 颜色选择按钮
3. **画笔设置区**：调整画笔大小的滑块
4. **主画布**：显示当前图像和绘制的掩码
5. **导航控制**：包含上一张/下一张图像按钮和图像计数信息
6. **状态栏**：底部显示当前状态和提示信息

## 5. 基本操作

### 5.1 打开图像

有两种方式可以打开单个图像：

1. 点击"打开图像"按钮
2. 在菜单中选择"文件 > 打开图像"

在弹出的文件对话框中选择要打开的图像文件。支持的格式包括PNG, JPG, JPEG, BMP, TIF, TIFF等。

成功加载图像后，图像将显示在主画布区域，同时状态栏会显示确认信息。

### 5.2 打开文件夹

处理多个图像时，可以选择打开整个文件夹：

1. 点击"打开文件夹"按钮
2. 在弹出的对话框中选择包含图像的文件夹

程序将自动加载并显示第一张图像，同时启用导航控制，让您可以浏览文件夹中的所有图像。

### 5.3 浏览图像

当您打开了包含多个图像的文件夹时，可以使用以下方式在图像间切换：

- 点击"← 上一张"和"下一张 →"按钮
- 使用键盘快捷键：左箭头键(←)和右箭头键(→)
- 状态栏和导航区域将显示当前图像的序号和总图像数

**注意**：当您在图像间切换时，当前图像的掩码会自动保存。

## 6. 标注掩码

### 6.1 绘制模式

工具提供三种主要的绘制模式：

1. **目标区域（添加）**：用于标注感兴趣的区域。
   - 点击"目标区域 (添加)"按钮选择此模式
   - 使用鼠标在图像上绘制，标记为掩码的一部分
   - 标注的区域在最终的掩码中将显示为白色

2. **非目标区域（移除）**：用于从已标注区域中删除部分。
   - 点击"非目标区域 (移除)"按钮选择此模式
   - 在已标注的区域上绘制，清除这些部分的标注
   - 这些区域在最终的掩码中将显示为黑色

3. **套索模式**：通过绘制闭合曲线快速标注整个区域。
   - 点击"套索工具"按钮或按`L`键选择此模式
   - 按住鼠标左键绘制一个闭合的轮廓
   - 释放鼠标后，轮廓内的区域将自动填充为掩码

在绘制模式之间切换时，状态栏会更新以显示当前模式。

### 6.2 平移模式

当需要处理大图像或放大后的图像时，您可能需要移动可视区域：

1. 点击"平移模式"按钮或按空格键进入平移模式
2. 鼠标光标将变为手形图标
3. 按住鼠标左键并拖动来移动图像
4. 再次点击"平移模式"按钮或按空格键返回到之前的绘制模式

### 6.3 画笔设置

调整画笔大小和颜色来适应不同的标注需求：

1. **调整画笔大小**：
   - 使用界面上的滑块调整画笔大小
   - 使用快捷键`Ctrl+↑`增加画笔大小
   - 使用快捷键`Ctrl+↓`减小画笔大小
   - 当前画笔大小显示在滑块旁边的标签中（如"10 px"）

2. **选择画笔颜色**：
   - 点击界面上的颜色按钮选择预设颜色（红色、白色、绿色、蓝色、黄色）
   - 点击"自定义"按钮打开颜色选择器，选择任意颜色
   - 注意：颜色只影响标注过程中的显示，最终导出的掩码都是二值的（黑白）

### 6.4 套索工具

套索工具适用于需要标注轮廓清晰的对象：

1. 点击"套索工具"按钮或按`L`键启用套索模式
2. 在图像上按住鼠标左键并绘制一个环绕目标对象的闭合轮廓
3. 绘制过程中，轮廓会以黄色线条显示
4. 松开鼠标后，轮廓将自动闭合，内部区域将根据当前模式（添加或移除）进行填充
5. 如果需要取消正在绘制的套索，按`ESC`键

**提示**：套索模式非常适合标注形状不规则但边界明确的对象。

## 7. 图像导航和缩放

有效的图像导航对于精确标注至关重要，特别是处理高分辨率图像时：

1. **缩放图像**：
   - 按住`Ctrl`键滚动鼠标滚轮放大或缩小图像
   - 缩放级别显示在状态栏中（如"缩放: 150%"）
   - 缩放范围从10%到1000%

2. **重置视图**：
   - 点击"重置视图"按钮或按`R`键将图像恢复到原始大小和位置

3. **平移视图**：如第6.2节所述，使用平移模式移动放大后的图像

## 8. 保存与导出

### 8.1 保存单个掩码

完成当前图像的标注后，可以通过以下方式保存掩码：

1. 点击"保存掩码"按钮
2. 使用快捷键`Ctrl+S`

如果您设置了保存目录，掩码将直接保存到该目录；否则，将弹出文件选择对话框让您选择保存位置和文件名。

保存的掩码是二值图像，白色表示标注的区域（前景），黑色表示未标注的区域（背景）。

### 8.2 批量保存掩码

处理多个图像时，可以一次性保存所有已标注的掩码：

1. 点击"保存所有掩码"按钮
2. 如果未设置保存目录，程序会提示您选择一个保存位置
3. 所有标注过的掩码都会被保存到指定目录

您可以通过点击"选择保存目录"按钮预先设置保存路径，这样所有掩码都会自动保存到该目录。

**文件命名规则**：保存的掩码文件名格式为"[原图文件名]_mask.png"。例如，原图为"dog.jpg"，对应的掩码将保存为"dog_mask.png"。

## 9. 撤销与重做

绘制过程中难免出错，程序提供了撤销和重做功能：

1. **撤销上一步操作**：
   - 按`Ctrl+Z`撤销上一个绘制操作
   - 可以多次撤销，回到之前的状态
   - 注意：只能在绘制模式下使用撤销功能，平移模式下无效

2. **重做已撤销的操作**：
   - 按`Ctrl+Y`重做之前撤销的操作
   - 可以重做多个撤销操作
   - 注意：当执行新的绘制操作后，之前撤销的操作将无法重做

## 10. 快捷键参考

熟练使用快捷键可以显著提高标注效率：

| 快捷键 | 功能 |
|--------|------|
| **导航** | |
| `←` (左箭头) | 上一张图像 |
| `→` (右箭头) | 下一张图像 |
| **编辑** | |
| `Ctrl + Z` | 撤销上一步操作 |
| `Ctrl + Y` | 重做已撤销的操作 |
| `Ctrl + S` | 保存当前掩码 |
| **视图** | |
| `Space` (空格键) | 切换平移模式 |
| `R` | 重置视图（恢复原始缩放和位置） |
| `Ctrl + 鼠标滚轮` | 缩放图像 |
| **绘制工具** | |
| `L` | 切换套索模式 |
| `Ctrl + ↑` (上箭头) | 增加画笔大小 |
| `Ctrl + ↓` (下箭头) | 减小画笔大小 |
| `Ctrl + +` | 增加画笔大小 |
| `Ctrl + -` | 减小画笔大小 |
| `Esc` | 在套索模式下取消当前绘制 |

## 11. 高级技巧

以下是一些提高标注效率的高级技巧：

1. **使用多种颜色区分不同区域**：尽管最终导出的掩码是二值的，但在绘制过程中使用不同的颜色可以帮助您区分不同类别或实例，尤其是在复杂场景中。

2. **结合使用多种工具**：复杂形状往往需要结合多种工具。例如，先用套索工具标注大致轮廓，再用画笔细化细节。

3. **批量处理策略**：处理大量图像时，先粗略标注所有图像，然后再回头细化。这样可以避免在一张图像上花费过多时间。

4. **定期保存**：尽管程序有自动保存功能，但在进行大量修改后手动保存是个好习惯，可以通过`Ctrl+S`快速保存。

5. **适当的缩放级别**：不同的标注任务适合不同的缩放级别。粗略标注可以在较小的缩放级别进行，细节处理则需要放大。

## 12. 故障排除

遇到问题时，可以尝试以下解决方案：

1. **程序无法启动**
   - 确认已安装所有依赖库：`pip install -r requirements.txt`
   - 检查Python版本是否兼容（建议使用Python 3.6+）

2. **图像无法加载**
   - 确认图像格式是否受支持（PNG, JPG, JPEG, BMP, TIF, TIFF）
   - 检查文件是否损坏或有权限限制

3. **掩码无法保存**
   - 确保目标目录存在并有写入权限
   - 检查磁盘空间是否足够
   - 确认掩码内容不为空（程序不会保存空白掩码）

4. **程序运行缓慢**
   - 处理过大的图像时可能出现性能问题，尝试降低分辨率
   - 关闭其他占用内存的应用程序
   - 使用缩放功能集中于需要标注的区域

5. **绘制问题**
   - 如果绘制行为异常，尝试切换绘制模式或重新选择工具
   - 使用撤销功能(`Ctrl+Z`)回退有问题的操作
   - 在极端情况下，可以使用"清除掩码"按钮重新开始



**版本信息**：本用户指南适用于图像掩码标注工具 v1.0.0 及以上版本。
最后更新日期：2023年11月