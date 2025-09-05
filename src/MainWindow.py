import sys
import os
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
    QLabel,
    QSlider,
    QStatusBar,
    QShortcut,
    QFrame,
    QColorDialog,
)
from PyQt5.QtGui import (
    QColor,
    QImage,
    QKeySequence,
    QImageReader,
    QPainter,
)
from PyQt5.QtCore import Qt, QTimer, QThreadPool, QRunnable, pyqtSignal, QObject, QRect
from .Canvas import Canvas
try:
    from .utils import mask_has_content
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# try:
from .inference import Inference
INFERENCE_AVAILABLE = True
# except ImportError:
#     INFERENCE_AVAILABLE = False

class ImageLoaderWorker(QRunnable):
    def __init__(self, file_path, callback):
        super().__init__()
        self.file_path = file_path
        self.callback = callback
        
    def run(self):
        reader = QImageReader(self.file_path)
        reader.setAutoTransform(True)
        image = reader.read()
        
        self.callback(self.file_path, image)

class ImageMaskingTool(QMainWindow):
    def __init__(self):
        super().__init__()
        
        if INFERENCE_AVAILABLE:
            try:
                self.inference_engine = Inference()
                self.inference_available = True
            except Exception as e:
                print(f"推理引擎初始化失败: {e}")
                self.inference_available = False
        else:
            self.inference_available = False
        
        self.initUI()
        
        self.imageCache = {}
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(3)
        
        self.saveTimer = QTimer()
        self.saveTimer.setSingleShot(True)
        self.saveTimer.timeout.connect(self.performDelayedSave)
        self.pendingSavePath = None
        self.saveDelay = 1000

        self.canvas.cacheEnabled = True
        
        self.panMode = True
        self.canvas.setPanMode(True)

class ImageMaskingTool(QMainWindow):
    def __init__(self):
        super().__init__()
        
        if INFERENCE_AVAILABLE:
            try:
                self.inference_engine = Inference()
                self.inference_available = True
            except Exception as e:
                print(f"推理引擎初始化失败: {e}")
                self.inference_available = False
        else:
            self.inference_available = False
        
        self.initUI()
        
        self.imageCache = {}
        self.threadpool = QThreadPool()
        self.threadpool.setMaxThreadCount(3)
        
        self.saveTimer = QTimer()
        self.saveTimer.setSingleShot(True)
        self.saveTimer.timeout.connect(self.performDelayedSave)
        self.pendingSavePath = None
        self.saveDelay = 1000

        self.canvas.cacheEnabled = True
        
        self.panMode = True
        self.canvas.setPanMode(True)

    def initUI(self):
        self.setWindowTitle("图像掩码工具")
        self.setMinimumSize(1280, 720)
        # self.setMaximumSize(1600, 1024)
        

        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        mainLayout = QVBoxLayout(centralWidget)

        controlsLayout = QHBoxLayout()

        self.openButton = QPushButton("打开图像")
        self.openButton.clicked.connect(self.openImage)
        self.openFolderButton = QPushButton("打开文件夹")
        self.openFolderButton.clicked.connect(self.openFolder)
        self.clearButton = QPushButton("清除掩码")
        self.clearButton.clicked.connect(self.clearMask)
        self.saveButton = QPushButton("保存掩码")
        self.saveButton.clicked.connect(self.saveMask)
        self.saveButton.setEnabled(False)
        
        self.rectPromptButton = QPushButton("框选金属")
        self.rectPromptButton.setCheckable(True)
        self.rectPromptButton.setChecked(False)
        self.rectPromptButton.clicked.connect(self.toggleRectPromptMode)
        
        self.setSaveDirButton = QPushButton("选择保存目录")
        self.setSaveDirButton.clicked.connect(self.setSaveDirectory)

        drawModeLabel = QLabel("绘制模式:")
        self.targetButton = QPushButton("目标区域 (添加)")
        self.targetButton.setCheckable(True)
        self.targetButton.setChecked(False)
        self.targetButton.clicked.connect(lambda: self.setDrawingMode("target") if self.targetButton.isChecked() else None)

        self.nonTargetButton = QPushButton("非目标区域 (移除)")
        self.nonTargetButton.setCheckable(True)
        self.nonTargetButton.setChecked(False)
        self.nonTargetButton.clicked.connect(lambda: self.setDrawingMode("non-target") if self.nonTargetButton.isChecked() else None)
        
        self.lassoButton = QPushButton("套索模式")
        self.lassoButton.setCheckable(True)
        self.lassoButton.setChecked(False)
        self.lassoButton.clicked.connect(lambda: self.setDrawingMode("lasso") if self.lassoButton.isChecked() else None)
        
        self.panButton = QPushButton("平移模式")
        self.panButton.setCheckable(True)
        self.panButton.setChecked(True)
        self.panButton.clicked.connect(self.togglePanMode)
        
        self.resetViewButton = QPushButton("重置视图")
        self.resetViewButton.clicked.connect(self.resetView)

        brushLabel = QLabel("画笔大小:")
        self.brushSlider = QSlider(Qt.Horizontal)
        self.brushSlider.setMinimum(1)
        self.brushSlider.setMaximum(50)
        self.brushSlider.setValue(10)
        self.brushSlider.setTickPosition(QSlider.TicksBelow)
        self.brushSlider.setTickInterval(5)
        self.brushSlider.valueChanged.connect(self.updateBrushSize)
        self.brushSizeLabel = QLabel("10 px")
        self.brushSizeLabel.setMinimumWidth(40)

        colorLabel = QLabel("颜色选择:")
        
        self.redColorButton = QPushButton("")
        self.redColorButton.setStyleSheet("background-color: red; min-width: 24px; min-height: 24px;")
        self.redColorButton.clicked.connect(lambda: self.setDrawingColor(QColor(255, 0, 0, 50)))
        
        self.whiteColorButton = QPushButton("")
        self.whiteColorButton.setStyleSheet("background-color: white; min-width: 24px; min-height: 24px;")
        self.whiteColorButton.clicked.connect(lambda: self.setDrawingColor(QColor(255, 255, 255, 50)))

        self.greenColorButton = QPushButton("")
        self.greenColorButton.setStyleSheet("background-color: green; min-width: 24px; min-height: 24px;")
        self.greenColorButton.clicked.connect(lambda: self.setDrawingColor(QColor(0, 255, 0, 50)))

        self.blueColorButton = QPushButton("")
        self.blueColorButton.setStyleSheet("background-color: blue; min-width: 24px; min-height: 24px;")
        self.blueColorButton.clicked.connect(lambda: self.setDrawingColor(QColor(0, 0, 255, 50)))

        self.yellowColorButton = QPushButton("")
        self.yellowColorButton.setStyleSheet("background-color: yellow; min-width: 24px; min-height: 24px;")
        self.yellowColorButton.clicked.connect(lambda: self.setDrawingColor(QColor(255, 255, 0, 50)))
        
        self.customColorButton = QPushButton("自定义")
        self.customColorButton.clicked.connect(self.selectCustomColor)
        
        drawModeLayout = QHBoxLayout()
        drawModeLayout.addWidget(drawModeLabel)
        drawModeLayout.addWidget(self.targetButton)
        drawModeLayout.addWidget(self.nonTargetButton)
        drawModeLayout.addWidget(self.lassoButton)  
        drawModeLayout.addWidget(self.panButton)
        drawModeLayout.addWidget(self.resetViewButton)
        drawModeLayout.addStretch()
        drawModeLayout.addWidget(colorLabel)
        drawModeLayout.addWidget(self.redColorButton)
        drawModeLayout.addWidget(self.whiteColorButton)
        drawModeLayout.addWidget(self.greenColorButton)
        drawModeLayout.addWidget(self.blueColorButton)
        drawModeLayout.addWidget(self.yellowColorButton)
        drawModeLayout.addWidget(self.customColorButton)

        controlsLayout.addWidget(self.openButton)
        controlsLayout.addWidget(self.openFolderButton)
        controlsLayout.addWidget(self.setSaveDirButton)
        controlsLayout.addStretch()
        controlsLayout.addWidget(brushLabel)
        controlsLayout.addWidget(self.brushSlider)
        controlsLayout.addWidget(self.brushSizeLabel)
        controlsLayout.addWidget(self.rectPromptButton)
        controlsLayout.addWidget(self.clearButton)
        controlsLayout.addWidget(self.saveButton)

        allControlsLayout = QVBoxLayout()
        allControlsLayout.addLayout(controlsLayout)
        allControlsLayout.addLayout(drawModeLayout)

        mainLayout.addLayout(allControlsLayout)

        self.canvas = Canvas(self)
        self.canvas.setMinimumSize(600, 400)
        mainLayout.addWidget(self.canvas, 1)

        navLayout = QHBoxLayout()

        self.prevButton = QPushButton("← 上一张")
        self.prevButton.clicked.connect(self.previousImage)
        self.prevButton.setEnabled(False)

        self.imageCountLabel = QLabel("未加载图像")
        self.imageCountLabel.setAlignment(Qt.AlignCenter)
        self.imageCountLabel.setMinimumWidth(200)

        self.nextButton = QPushButton("下一张 →")
        self.nextButton.clicked.connect(self.nextImage)
        self.nextButton.setEnabled(False)

        self.saveAllButton = QPushButton("保存所有掩码")
        self.saveAllButton.clicked.connect(self.saveAllMasks)
        self.saveAllButton.setEnabled(False)

        navLayout.addWidget(self.prevButton)
        navLayout.addWidget(self.imageCountLabel)
        navLayout.addWidget(self.nextButton)
        navLayout.addStretch()
        navLayout.addWidget(self.saveAllButton)

        mainLayout.addLayout(navLayout)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        mainLayout.addWidget(line)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("平移模式: 可以用鼠标左键拖动图像")

        QShortcut(QKeySequence(Qt.Key_Left), self, self.previousImage)
        QShortcut(QKeySequence(Qt.Key_Right), self, self.nextImage)
        QShortcut(QKeySequence(Qt.Key_S | Qt.ControlModifier), self, self.saveMask)
        
        QShortcut(QKeySequence(Qt.Key_Up | Qt.ControlModifier), self, self.increaseBrushSize)
        QShortcut(QKeySequence(Qt.Key_Down | Qt.ControlModifier), self, self.decreaseBrushSize)

        QShortcut(QKeySequence(Qt.Key_Plus | Qt.ControlModifier), self, self.increaseBrushSize)
        QShortcut(QKeySequence(Qt.Key_Minus | Qt.ControlModifier), self, self.decreaseBrushSize)
        
        QShortcut(QKeySequence(Qt.Key_Space), self, self.togglePanMode)
        QShortcut(QKeySequence(Qt.Key_R), self, self.resetView)
        
        QShortcut(QKeySequence(Qt.Key_Z | Qt.ControlModifier), self, self.undoAction)
        QShortcut(QKeySequence(Qt.Key_Y | Qt.ControlModifier), self, self.redoAction)
        
        QShortcut(QKeySequence(Qt.Key_L), self, self.toggleLassoMode)
        QShortcut(QKeySequence(Qt.Key_B), self, self.toggleRectPromptMode)
        QShortcut(QKeySequence(Qt.Key_A), self, self.toggleRectAddMode)
        QShortcut(QKeySequence(Qt.Key_E), self, self.toggleRectEraseMode)

        self.imagePath = None
        self.brushSize = 10
        self.imageFiles = []
        self.currentImageIndex = -1
        self.folderPath = None
        self.masks = {}
        self.drawingMode = "target"
        self.drawingColor = QColor(255, 0, 0, 50)
        self.canvas.setDrawingColor(self.drawingColor)
        self.saveDirectory = None

    def openImage(self):
        options = QFileDialog.Options()
        filePath, _ = QFileDialog.getOpenFileName(
            self,
            "打开图像",
            "",
            "图像文件 (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)",
            options=options,
        )

        if filePath:
            self.imageFiles = [filePath]
            self.currentImageIndex = 0
            self.folderPath = None

            self.imagePath = filePath
            self.loadImageToCanvas(filePath)
            self.saveButton.setEnabled(True)
            self.saveAllButton.setEnabled(False)

            self.updateNavigationControls()
            self.statusBar.showMessage(f"已加载图像: {os.path.basename(filePath)}")

    def openFolder(self):
        options = QFileDialog.Options()
        folderPath = QFileDialog.getExistingDirectory(
            self, "打开文件夹", "", options=options
        )

        if folderPath:
            self.folderPath = folderPath

            self.imageFiles = []
            for filename in os.listdir(folderPath):
                if filename.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")
                ):
                    self.imageFiles.append(os.path.join(folderPath, filename))

            self.imageFiles.sort()

            if self.imageFiles:
                self.currentImageIndex = 0
                self.imagePath = self.imageFiles[0]
                self.loadImageToCanvas(self.imagePath)
                self.preloadImages()

                self.saveButton.setEnabled(True)
                self.saveAllButton.setEnabled(True)
                self.updateNavigationControls()
                self.statusBar.showMessage(
                    f"已加载文件夹，包含 {len(self.imageFiles)} 张图像"
                )
            else:
                self.statusBar.showMessage("所选文件夹中未找到图像文件")

    def preloadImages(self):
        if not self.imageFiles:
            return
            
        keys_to_remove = []
        for key in self.imageCache:
            if key not in self.imageFiles or abs(self.imageFiles.index(key) - self.currentImageIndex) > 5:
                keys_to_remove.append(key)
                
        for key in keys_to_remove:
            del self.imageCache[key]
            
        preload_indices = []
        
        for i in range(max(0, self.currentImageIndex - 2), min(len(self.imageFiles), self.currentImageIndex + 3)):
            if i != self.currentImageIndex and i >= 0 and i < len(self.imageFiles):
                preload_indices.append(i)
                
        for idx in preload_indices:
            path = self.imageFiles[idx]
            
            if path in self.imageCache:
                continue
                
            worker = ImageLoaderWorker(path, self.cacheImage)
            self.threadpool.start(worker)
            
    def cacheImage(self, path, image):
        if image and not image.isNull():
            self.imageCache[path] = image
            
    def loadImageToCanvas(self, image_path):
        if image_path in self.imageCache:
            self.canvas.setImage(self.imageCache[image_path])
            self.statusBar.showMessage(f"从缓存加载图像: {os.path.basename(image_path)}")
        else:
            self.canvas.loadImage(image_path)
            worker = ImageLoaderWorker(image_path, self.cacheImage)
            self.threadpool.start(worker)

    def previousImage(self):
        if self.imageFiles and self.currentImageIndex > 0:
            self.scheduleSaveCurrentMask()
            
            self.currentImageIndex -= 1
            self.imagePath = self.imageFiles[self.currentImageIndex]

            self.loadImageToCanvas(self.imagePath)

            if self.imagePath in self.masks:
                self.canvas.maskLayer = self.masks[self.imagePath]
                self.canvas.update()

            self.updateNavigationControls()
            self.preloadImages()
            self.statusBar.showMessage(
                f"已加载图像: {os.path.basename(self.imagePath)}"
            )

    def nextImage(self):
        if self.imageFiles and self.currentImageIndex < len(self.imageFiles) - 1:
            self.scheduleSaveCurrentMask()
            
            self.currentImageIndex += 1
            self.imagePath = self.imageFiles[self.currentImageIndex]

            self.loadImageToCanvas(self.imagePath)

            if self.imagePath in self.masks:
                self.canvas.maskLayer = self.masks[self.imagePath]
                self.canvas.update()

            self.updateNavigationControls()
            self.preloadImages()
            self.statusBar.showMessage(
                f"已加载图像: {os.path.basename(self.imagePath)}"
            )
            
    def scheduleSaveCurrentMask(self):
        if self.saveTimer.isActive():
            self.saveTimer.stop()
        
        if (hasattr(self.canvas, "maskLayer") and 
            not self.canvas.maskLayer.isNull() and 
            self.canvas.hasMaskContent()):
            
            self.masks[self.imagePath] = self.canvas.maskLayer.copy()
            
            if self.saveDirectory:
                baseName = os.path.splitext(os.path.basename(self.imagePath))[0]
                savePath = os.path.join(self.saveDirectory, f"{baseName}_mask.png")
            else:
                baseDir = os.path.dirname(self.imagePath)
                baseName = os.path.splitext(os.path.basename(self.imagePath))[0]
                savePath = os.path.join(baseDir, f"{baseName}_mask.png")
            
            self.pendingSavePath = savePath
            self.saveTimer.start(self.saveDelay)
    
    def performDelayedSave(self):
        if self.pendingSavePath and self.imagePath in self.masks:
            tempCanvas = Canvas(self)
            tempCanvas.baseImage = self.canvas.baseImage.copy() if hasattr(self.canvas, "baseImage") else QImage()
            tempCanvas.maskLayer = self.masks[self.imagePath]
            tempCanvas.originalImageSize = self.canvas.originalImageSize

            success = tempCanvas.saveMask(self.pendingSavePath)
            if success:
                self.statusBar.showMessage(f"已保存掩码: {os.path.basename(self.pendingSavePath)}")
                
            self.pendingSavePath = None

    def updateNavigationControls(self):
        self.prevButton.setEnabled(self.currentImageIndex > 0)
        self.nextButton.setEnabled(self.currentImageIndex < len(self.imageFiles) - 1)

        if self.imageFiles:
            self.imageCountLabel.setText(
                f"图像 {self.currentImageIndex + 1} / {len(self.imageFiles)}"
            )
        else:
            self.imageCountLabel.setText("未加载图像")

    def clearMask(self):
        if hasattr(self.canvas, "maskLayer"):
            self.canvas.clearMask()

            if self.imagePath in self.masks:
                del self.masks[self.imagePath]

            self.statusBar.showMessage("掩码已清除")

    def setSaveDirectory(self):
        options = QFileDialog.Options()
        directory = QFileDialog.getExistingDirectory(
            self, "选择保存目录", "", options=options
        )
        
        if directory:
            self.saveDirectory = directory
            self.statusBar.showMessage(f"已设置保存目录: {directory}")

    def saveMask(self):
        if self.saveTimer.isActive():
            self.saveTimer.stop()
            self.pendingSavePath = None
            
        if self.imagePath:
            hasMask = False
            if NUMPY_AVAILABLE and hasattr(self.canvas, "maskLayer") and not self.canvas.maskLayer.isNull():
                hasMask = mask_has_content(self.canvas.maskLayer)
            else:
                hasMask = (hasattr(self.canvas, "maskLayer") and 
                           not self.canvas.maskLayer.isNull() and 
                           self.canvas.hasMaskContent())
                
            if not hasMask:
                self.statusBar.showMessage("没有检测到掩膜内容，未保存文件。")
                return

            self.masks[self.imagePath] = self.canvas.maskLayer.copy()

            baseDir = os.path.dirname(self.imagePath)
            baseName = os.path.splitext(os.path.basename(self.imagePath))[0]
            
            if self.saveDirectory:
                savePath = os.path.join(self.saveDirectory, f"{baseName}_mask.png")
                success = self.canvas.saveMask(savePath)
                if success:
                    self.statusBar.showMessage(f"掩码已保存为: {savePath}")
                else:
                    self.statusBar.showMessage("保存掩码时出错")
            else:
                savePath = os.path.join(baseDir, f"{baseName}_mask.png")
                options = QFileDialog.Options()
                filePath, _ = QFileDialog.getSaveFileName(
                    self, "保存掩码", savePath, "PNG文件 (*.png)", options=options
                )

                if filePath:
                    success = self.canvas.saveMask(filePath)
                    if success:
                        self.statusBar.showMessage(
                            f"掩码已保存为: {os.path.basename(filePath)}"
                        )
                    else:
                        self.statusBar.showMessage("保存掩码时出错")

    def saveAllMasks(self):
        if self.saveTimer.isActive():
            self.saveTimer.stop()
            self.pendingSavePath = None
            
        if not self.imageFiles:
            return

        if hasattr(self.canvas, "maskLayer") and not self.canvas.maskLayer.isNull() and self.canvas.hasMaskContent():
            self.masks[self.imagePath] = self.canvas.maskLayer.copy()

        masksToSave = {}
        for imagePath, maskLayer in self.masks.items():
            tempCanvas = Canvas(self)
            tempCanvas.maskLayer = maskLayer
            if tempCanvas.hasMaskContent():
                masksToSave[imagePath] = maskLayer

        if not masksToSave:
            self.statusBar.showMessage("没有可保存的掩膜内容")
            return

        outputDir = self.saveDirectory
        if not outputDir:
            options = QFileDialog.Options()
            outputDir = QFileDialog.getExistingDirectory(
                self, "选择输出目录", self.folderPath or "", options=options
            )

        if not outputDir:
            return

        savedCount = 0
        for imagePath, maskLayer in masksToSave.items():
            baseName = os.path.splitext(os.path.basename(imagePath))[0]
            savePath = os.path.join(outputDir, f"{baseName}_mask.png")

            tempCanvas = Canvas(self)
            tempCanvas.baseImage = QImage(imagePath)
            tempCanvas.maskLayer = maskLayer
            tempCanvas.originalImageSize = self.canvas.originalImageSize

            if tempCanvas.saveMask(savePath):
                savedCount += 1

        self.statusBar.showMessage(f"已保存 {savedCount} 个掩码到 {outputDir}")

    def updateBrushSize(self):
        size = self.brushSlider.value()
        self.brushSize = size
        self.brushSizeLabel.setText(f"{size} px")
        self.canvas.setBrushSize(size)
        
    def increaseBrushSize(self):
        newSize = min(self.brushSlider.value() + 1, self.brushSlider.maximum())
        self.brushSlider.setValue(newSize)
        
    def decreaseBrushSize(self):
        newSize = max(self.brushSlider.value() - 1, self.brushSlider.minimum())
        self.brushSlider.setValue(newSize)

    def setDrawingMode(self, mode):
        self.drawingMode = mode
        self.targetButton.setChecked(False)
        self.nonTargetButton.setChecked(False)
        self.lassoButton.setChecked(False)
        self.rectPromptButton.setChecked(False)
        self.panButton.setChecked(False)
        
        self.panMode = False
        self.canvas.setPanMode(False)
        
        if mode == "target":
            self.targetButton.setChecked(True)
            self.statusBar.showMessage("绘制模式: 目标区域 (添加到掩码)，可使用Ctrl+Z撤销，Ctrl+Y重做")
        elif mode == "non-target":
            self.nonTargetButton.setChecked(True)
            self.statusBar.showMessage("绘制模式: 非目标区域 (从掩码中移除)，可使用Ctrl+Z撤销，Ctrl+Y重做")
        elif mode == "lasso":
            self.lassoButton.setChecked(True)
            self.statusBar.showMessage("套索模式: 按住鼠标绘制闭合曲线，松开后自动填充区域，可使用Ctrl+Z撤销，Ctrl+Y重做")
        elif mode == "rect_prompt":
            self.rectPromptButton.setChecked(True)
            self.statusBar.showMessage("框选金属模式: 在图像上拖拽矩形框以执行金属区域提示推理")
        elif mode == "rect_add":
            self.statusBar.showMessage("拉框添加模式: 拖拽矩形为遮盖上色")
        elif mode == "rect_erase":
            self.statusBar.showMessage("拉框擦除模式: 拖拽矩形擦除已遮盖区域")
        
        self.canvas.setDrawingMode(mode)
    
    def togglePanMode(self):
        self.panMode = not self.panMode
        self.panButton.setChecked(self.panMode)
        self.targetButton.setChecked(False)
        self.nonTargetButton.setChecked(False)
        self.lassoButton.setChecked(False)
        self.canvas.setPanMode(self.panMode)
        
        if self.panMode:
            self.statusBar.showMessage("平移模式: 可以用鼠标左键拖动图像")
        else:
            self.setDrawingMode(self.drawingMode)
    
    def toggleLassoMode(self):
        if self.drawingMode == "lasso":
            self.setDrawingMode("target")
        else:
            self.setDrawingMode("lasso")

    def toggleRectPromptMode(self):
        if self.drawingMode == "rect_prompt":
            self.setDrawingMode("target")
        else:
            self.setDrawingMode("rect_prompt")

    def toggleRectAddMode(self):
        if self.drawingMode == "rect_add":
            self.setDrawingMode("target")
        else:
            self.setDrawingMode("rect_add")

    def toggleRectEraseMode(self):
        if self.drawingMode == "rect_erase":
            self.setDrawingMode("target")
        else:
            self.setDrawingMode("rect_erase")

    def onRectAddSelected(self, box):
        if not self.inference_available or not self.imagePath:
            return
        try:
            mask_arr, _ = self.inference_engine.run_prompt_inference(
                image=self.imagePath,
                box=box,
                multimask_output=False,
                hq_token_only=False,
            )
        except Exception as e:
            print(f"rect add 推理失败: {e}")
            return
        self._applyMaskAdd(mask_arr)

    def onRectEraseSelected(self, box):
        if not self.inference_available or not self.imagePath:
            return
        try:
            mask_arr, _ = self.inference_engine.run_prompt_inference(
                image=self.imagePath,
                box=box,
                multimask_output=False,
                hq_token_only=False,
            )
        except Exception as e:
            print(f"rect erase 推理失败: {e}")
            return
        self._applyMaskErase(mask_arr)

    def _resizeMaskToCanvas(self, mask_arr):
        import numpy as np
        from PIL import Image as _PIL
        if hasattr(self.canvas, 'baseImage') and not self.canvas.baseImage.isNull():
            w = self.canvas.baseImage.width()
            h = self.canvas.baseImage.height()
            if mask_arr.shape[:2] != (h, w):
                mask_arr = np.array(_PIL.fromarray(mask_arr.astype(np.uint8), 'L').resize((w, h), _PIL.NEAREST))
            return mask_arr, w, h
        return mask_arr, None, None

    def _applyMaskAdd(self, mask_arr):
        import numpy as np
        mask_arr = (mask_arr * 255).astype(np.uint8) if mask_arr.max() <= 1 else mask_arr.astype(np.uint8)
        mask_arr, w, h = self._resizeMaskToCanvas(mask_arr)
        if w is None:
            return
        if not hasattr(self.canvas, 'maskLayer') or self.canvas.maskLayer is None:
            self.canvas.createMaskLayer()
        mask_bool = mask_arr > 128
        if not mask_bool.any():
            return
        # 先清除将要叠加的区域，避免重复叠加加深
        clear_rgba = np.zeros((h, w, 4), dtype=np.uint8)
        clear_rgba[mask_bool, 3] = 255
        qimg_clear = QImage(clear_rgba.data, w, h, w * 4, QImage.Format_RGBA8888).copy()
        painter = QPainter(self.canvas.maskLayer)
        try:
            painter.setCompositionMode(QPainter.CompositionMode_DestinationOut)
            painter.drawImage(0, 0, qimg_clear)
            # 再按固定透明度覆盖
            green_rgba = np.zeros((h, w, 4), dtype=np.uint8)
            green_rgba[mask_bool] = [0, 255, 0, 128]
            qimg_green = QImage(green_rgba.data, w, h, w * 4, QImage.Format_RGBA8888).copy()
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.drawImage(0, 0, qimg_green)
        finally:
            painter.end()
        self.masks[self.imagePath] = self.canvas.maskLayer.copy()
        self.canvas.invalidateCache()
        self.canvas.update()

    def _applyMaskErase(self, mask_arr):
        import numpy as np
        mask_arr = (mask_arr * 255).astype(np.uint8) if mask_arr.max() <= 1 else mask_arr.astype(np.uint8)
        mask_arr, w, h = self._resizeMaskToCanvas(mask_arr)
        if w is None:
            return
        if not hasattr(self.canvas, 'maskLayer') or self.canvas.maskLayer is None:
            return
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[mask_arr > 128, 3] = 255
        qimg = QImage(rgba.data, w, h, w * 4, QImage.Format_RGBA8888).copy()
        p = QPainter(self.canvas.maskLayer)
        try:
            p.setCompositionMode(QPainter.CompositionMode_DestinationOut)
            p.drawImage(0, 0, qimg)
        finally:
            p.end()
        self.masks[self.imagePath] = self.canvas.maskLayer.copy()
        self.canvas.invalidateCache()
        self.canvas.update()

    def onBoxPromptSelected(self, box):
        if not self.inference_available or not self.imagePath:
            print(f"图像的路径是: {self.imagePath}")
            self.statusBar.showMessage("推理不可用或未加载图像")
            return
        import time
        t0 = time.time()
        try:
            mask_result, _ = self.inference_engine.run_prompt_inference(
                image=self.imagePath,
                box=box,
                multimask_output=False,
                hq_token_only=False,
            )
        except Exception as e:
            # self.statusBar.showMessage(f"框选推理失败: {e}")
            print(f"框选推理失败: {e}") 
            return
        try:
            import numpy as np
            if isinstance(mask_result, np.ndarray):
                if mask_result.max() <= 1:
                    mask_result = (mask_result * 255).astype(np.uint8)
                else:
                    mask_result = mask_result.astype(np.uint8)
                if hasattr(self.canvas, 'baseImage') and not self.canvas.baseImage.isNull():
                    w = self.canvas.baseImage.width()
                    h = self.canvas.baseImage.height()
                    if mask_result.shape[:2] != (h, w):
                        from PIL import Image as _PIL
                        _m = _PIL.fromarray(mask_result, mode='L').resize((w, h), _PIL.NEAREST)
                        mask_result = np.array(_m)
                    import numpy as _np
                    mask_bool = mask_result > 128
                    painted = int(mask_bool.sum())
                    if not hasattr(self.canvas, 'maskLayer') or self.canvas.maskLayer is None:
                        self.canvas.createMaskLayer()
                    painter = QPainter(self.canvas.maskLayer)
                    try:
                        if painted > 0:
                            # 先把该掩膜区域清空，避免重复叠加加深
                            clear_rgba = _np.zeros((h, w, 4), dtype=_np.uint8)
                            clear_rgba[mask_bool, 3] = 255
                            qimg_clear = QImage(clear_rgba.data, w, h, w * 4, QImage.Format_RGBA8888).copy()
                            painter.setCompositionMode(QPainter.CompositionMode_DestinationOut)
                            painter.drawImage(0, 0, qimg_clear)

                            # 再以固定透明度覆盖绿色
                            green_rgba = _np.zeros((h, w, 4), dtype=_np.uint8)
                            green_rgba[mask_bool] = [0, 255, 0, 128]
                            qimg_green = QImage(green_rgba.data, w, h, w * 4, QImage.Format_RGBA8888).copy()
                            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                            painter.drawImage(0, 0, qimg_green)
                    finally:
                        painter.end()
                    self.masks[self.imagePath] = self.canvas.maskLayer.copy()
                    self.canvas.invalidateCache()
                    self.canvas.update()
                    dt = (time.time() - t0) * 1000.0
                    self.statusBar.showMessage(f"框选金属推理完成: 用时{dt:.1f}ms, 上色像素{painted}")
                else:
                    self.statusBar.showMessage("无法获取基础图像信息")
            else:
                self.statusBar.showMessage("推理结果格式错误")
        except Exception as e:
            self.statusBar.showMessage(f"应用推理结果时出错: {e}")
    
    def resetView(self):
        self.canvas.resetPan()
        self.statusBar.showMessage("视图已重置")
        
    def setDrawingColor(self, color):
        self.drawingColor = color
        self.canvas.setDrawingColor(color)
        
        colorName = ""
        if color.red() == 255 and color.green() == 0 and color.blue() == 0:
            colorName = "红色"
        elif color.red() == 255 and color.green() == 255 and color.blue() == 255:
            colorName = "白色"
        else:
            colorName = f"RGB({color.red()}, {color.green()}, {color.blue()})"
            
        self.statusBar.showMessage(f"当前绘制颜色: {colorName}")
    
    def selectCustomColor(self):
        color = QColorDialog.getColor(self.drawingColor, self)
        if color.isValid():
            color.setAlpha(50)
            self.setDrawingColor(color)

    def undoAction(self):
        if hasattr(self.canvas, 'undo'):
            if self.panMode:
                self.statusBar.showMessage("绘制模式下才能执行撤销操作")
                return
            
            if self.canvas.undo():
                if self.imagePath in self.masks:
                    self.masks[self.imagePath] = self.canvas.maskLayer.copy()
                self.statusBar.showMessage("已撤销上一步绘制操作")
            else:
                self.statusBar.showMessage("没有可撤销的操作")

    def redoAction(self):
        if hasattr(self.canvas, 'redo'):
            if self.panMode:
                self.statusBar.showMessage("绘制模式下才能执行重做操作")
                return
                
            if self.canvas.redo():
                if self.imagePath in self.masks:
                    self.masks[self.imagePath] = self.canvas.maskLayer.copy()
                self.statusBar.showMessage("已重做上一步绘制操作")
            else:
                self.statusBar.showMessage("没有可重做的操作")

    def runInference(self):
        """运行AI推理"""
        if not self.inference_available or not self.imagePath:
            self.statusBar.showMessage("推理功能不可用或未加载图像")
            return
            
        if not os.path.exists(self.imagePath):
            self.statusBar.showMessage("图像文件不存在")
            return
            
        self.inferenceButton.setEnabled(False)
        self.inferenceButton.setText("推理中...")
        self.statusBar.showMessage("正在运行AI推理，请稍候...")
        
        worker = InferenceWorker(self.inference_engine, self.imagePath, self.onInferenceComplete)
        self.threadpool.start(worker)
    
    def onInferenceComplete(self, mask_result, error):
        """推理完成的回调函数"""
        self.inferenceButton.setEnabled(self.inference_available)
        self.inferenceButton.setText("AI推理掩码")
        
        if error:
            if "Input type" in error and "bias type" in error:
                self.statusBar.showMessage("推理失败: 数据类型不匹配，正在重新初始化...")
                try:
                    self.inference_engine = Inference()
                    self.statusBar.showMessage("推理引擎已重新初始化，请重试")
                except Exception:
                    self.statusBar.showMessage("重新初始化失败")
            elif "CUDA" in error:
                self.statusBar.showMessage("推理失败: CUDA错误，建议切换到CPU模式")
            elif "memory" in error.lower():
                self.statusBar.showMessage("推理失败: 内存不足")
            else:
                self.statusBar.showMessage(f"推理失败: {error}")
            return
            
        if mask_result is None:
            self.statusBar.showMessage("推理失败：未获得有效结果")
            return
            
        try:
            # 保存当前掩码状态（用于撤销）
            if hasattr(self.canvas, "maskLayer") and not self.canvas.maskLayer.isNull():
                if hasattr(self.canvas, "saveMaskState"):
                    self.canvas.saveMaskState()
            
            # 转换numpy数组为QImage掩膜
            import numpy as np
            
            if isinstance(mask_result, np.ndarray):
                # 确保数据范围正确
                if mask_result.max() <= 1.0:
                    mask_result = (mask_result * 255).astype(np.uint8)
                else:
                    mask_result = mask_result.astype(np.uint8)
                
                # 创建与原图相同大小的掩膜
                if hasattr(self.canvas, 'baseImage') and not self.canvas.baseImage.isNull():
                    target_width = self.canvas.baseImage.width()
                    target_height = self.canvas.baseImage.height()
                    
                    # 如果推理结果尺寸与原图不同，需要调整
                    if mask_result.shape[0] != target_height or mask_result.shape[1] != target_width:
                        from PIL import Image
                        mask_pil = Image.fromarray(mask_result, mode='L')
                        mask_pil = mask_pil.resize((target_width, target_height), Image.NEAREST)
                        mask_result = np.array(mask_pil)
                    
                    # 创建ARGB32格式的掩膜图像
                    mask_qimg = QImage(target_width, target_height, QImage.Format_ARGB32)
                    mask_qimg.fill(Qt.transparent)
                    
                    # 设置掩膜颜色
                    color = QColor(self.drawingColor)
                    color.setAlpha(128)  # 半透明
                    
                    # 逐像素设置掩膜
                    pixels_set = 0
                    for y in range(target_height):
                        for x in range(target_width):
                            if mask_result[y, x] > 128:  # 阈值判断
                                mask_qimg.setPixelColor(x, y, color)
                                pixels_set += 1
                    
                    if pixels_set > 0:
                        # 确保Canvas有maskLayer
                        if not hasattr(self.canvas, 'maskLayer') or self.canvas.maskLayer is None:
                            self.canvas.createMaskLayer()
                        
                        # 将推理结果应用到画布
                        self.canvas.maskLayer = mask_qimg
                        
                        # 保存到掩码字典
                        self.masks[self.imagePath] = mask_qimg.copy()
                        
                        # 刷新画布
                        self.canvas.invalidateCache()
                        self.canvas.update()
                        
                        self.statusBar.showMessage("AI推理完成，已生成掩码")
                    else:
                        self.statusBar.showMessage("推理完成，但未检测到有效区域")
                else:
                    self.statusBar.showMessage("无法获取基础图像信息")
            else:
                self.statusBar.showMessage("推理结果格式错误")
                
        except Exception as e:
            self.statusBar.showMessage(f"处理推理结果时出错: {str(e)}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageMaskingTool()
    window.show()
    sys.exit(app.exec_())