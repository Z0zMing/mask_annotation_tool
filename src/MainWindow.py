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
    QPixmap,
    QPainter,
    QPen,
    QColor,
    QImage,
    QPainterPath,
    QBrush,
    QKeySequence,
    QImageReader,
)
from PyQt5.QtCore import Qt, QPoint, QSize, QRect, QTimer, QThreadPool, QRunnable
import threading
from Canvas import Canvas
import numpy as np
try:
    from np_utils import mask_has_content
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

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

    def initUI(self):
        self.setWindowTitle("图像掩码工具")
        self.setMinimumSize(1280, 720)
        self.setMaximumSize(1600, 1024)
        

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
        
        self.setSaveDirButton = QPushButton("选择保存目录")
        self.setSaveDirButton.clicked.connect(self.setSaveDirectory)

        drawModeLabel = QLabel("绘制模式:")
        self.targetButton = QPushButton("目标区域 (添加)")
        self.targetButton.setCheckable(True)
        self.targetButton.setChecked(True)
        self.targetButton.clicked.connect(lambda: self.setDrawingMode("target"))

        self.nonTargetButton = QPushButton("非目标区域 (移除)")
        self.nonTargetButton.setCheckable(True)
        self.nonTargetButton.clicked.connect(lambda: self.setDrawingMode("non-target"))

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
        
        self.customColorButton = QPushButton("自定义")
        self.customColorButton.clicked.connect(self.selectCustomColor)
        
        drawModeLayout = QHBoxLayout()
        drawModeLayout.addWidget(drawModeLabel)
        drawModeLayout.addWidget(self.targetButton)
        drawModeLayout.addWidget(self.nonTargetButton)
        drawModeLayout.addStretch()
        drawModeLayout.addWidget(colorLabel)
        drawModeLayout.addWidget(self.redColorButton)
        drawModeLayout.addWidget(self.whiteColorButton)
        drawModeLayout.addWidget(self.customColorButton)

        controlsLayout.addWidget(self.openButton)
        controlsLayout.addWidget(self.openFolderButton)
        controlsLayout.addWidget(self.setSaveDirButton)
        controlsLayout.addStretch()
        controlsLayout.addWidget(brushLabel)
        controlsLayout.addWidget(self.brushSlider)
        controlsLayout.addWidget(self.brushSizeLabel)
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
        self.statusBar.showMessage("准备就绪。打开图像或文件夹开始。")

        QShortcut(QKeySequence(Qt.Key_Left), self, self.previousImage)
        QShortcut(QKeySequence(Qt.Key_Right), self, self.nextImage)
        QShortcut(QKeySequence(Qt.Key_S | Qt.ControlModifier), self, self.saveMask)
        
        QShortcut(QKeySequence(Qt.Key_Up | Qt.ControlModifier), self, self.increaseBrushSize)
        QShortcut(QKeySequence(Qt.Key_Down | Qt.ControlModifier), self, self.decreaseBrushSize)

        QShortcut(QKeySequence(Qt.Key_Plus | Qt.ControlModifier), self, self.increaseBrushSize)
        QShortcut(QKeySequence(Qt.Key_Minus | Qt.ControlModifier), self, self.decreaseBrushSize)

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
        if mode == "target":
            self.targetButton.setChecked(True)
            self.nonTargetButton.setChecked(False)
            self.statusBar.showMessage("绘制模式: 目标区域 (添加到掩码)")
        else:
            self.targetButton.setChecked(False)
            self.nonTargetButton.setChecked(True)
            self.statusBar.showMessage("绘制模式: 非目标区域 (从掩码中移除)")

        self.canvas.setDrawingMode(mode)
        
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageMaskingTool()
    window.show()
    sys.exit(app.exec_())