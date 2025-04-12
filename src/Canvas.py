import sys
import os
from PyQt5.QtWidgets import (
    QWidget,
    QSizePolicy,
    QMessageBox,
)
from PyQt5.QtGui import (
    QPainter,
    QPen,
    QColor,
    QImage,
    QBrush,
    QImageReader,
    QPixmap,
)
from PyQt5.QtCore import Qt, QPoint, QRect, QRectF
import numpy as np


class Canvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setMouseTracking(True)
        
        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )

        self.baseImage = QImage()
        self.maskLayer = None
        self.drawing = False
        self.lastPoint = QPoint()
        self.brushSize = 10
        self.originalImageSize = None
        self.drawingMode = "target"
        self.drawingColor = QColor(255, 0, 0, 50)
        self.scaleFactor = 1.0
        self.zoomFactor = 1.0
        self.minZoom = 0.1
        self.maxZoom = 10.0
        self.imageRect = QRect()
        
        self.cacheEnabled = True
        self.cachedPixmap = QPixmap()  
        self.cachedDirty = True 
        self.updateRect = QRect()
        
        self.panMode = False
        self.panning = False
        self.panStart = QPoint()
        self.imageOffset = QPoint(0, 0)
        
        # Add undo/redo stacks
        self.undoStack = []
        self.redoStack = []
        self.maxStackSize = 20  # Limit stack size to prevent memory issues

        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(self.backgroundRole(), QColor(220, 220, 220))
        self.setPalette(p)

    def loadImage(self, filePath):
        reader = QImageReader(filePath)
        reader.setAutoTransform(True)
        
        self.baseImage = reader.read()
        self.originalImageSize = self.baseImage.size()
        self.zoomFactor = 1.0
        
        self.calculateImageRect()
        
        self.createMaskLayer()
        
        self.invalidateCache()
        self.update()
        
    def setImage(self, image):
        if image and not image.isNull():
            self.baseImage = image
            self.originalImageSize = self.baseImage.size()
            self.zoomFactor = 1.0
            
            self.calculateImageRect()
            
            self.createMaskLayer()
            
            self.invalidateCache()
            self.update()
    
    def invalidateCache(self):
        self.cachedDirty = True
        self.updateRect = self.rect()
            
    def createMaskLayer(self):
        if self.baseImage.isNull():
            return
            
        self.maskLayer = QImage(self.baseImage.size(), QImage.Format_ARGB32)
        self.maskLayer.fill(Qt.transparent)
        # Clear history when creating a new mask
        self.undoStack.clear()
        self.redoStack.clear()

    def calculateImageRect(self):
        if self.baseImage.isNull():
            return
            
        canvasWidth = self.width()
        canvasHeight = self.height()
        
        imageWidth = max(1, self.baseImage.width())
        imageHeight = max(1, self.baseImage.height())
        
        canvasWidth -= 20
        canvasHeight -= 20
        
        widthRatio = canvasWidth / imageWidth
        heightRatio = canvasHeight / imageHeight
        
        self.scaleFactor = min(widthRatio, heightRatio, 1.0) * self.zoomFactor
        
        newWidth = int(imageWidth * self.scaleFactor)
        newHeight = int(imageHeight * self.scaleFactor)
        
        if newWidth < 10 or newHeight < 10:
            self.scaleFactor = min(canvasWidth / imageWidth, canvasHeight / imageHeight)
            newWidth = int(imageWidth * self.scaleFactor)
            newHeight = int(imageHeight * self.scaleFactor)
        
        x = (self.width() - newWidth) // 2 + self.imageOffset.x()
        y = (self.height() - newHeight) // 2 + self.imageOffset.y()
        
        self.imageRect = QRect(x, y, newWidth, newHeight)

    def resetPan(self):
        self.zoomFactor = 1.0
        self.imageOffset = QPoint(0, 0)
        self.calculateImageRect()
        self.invalidateCache()
        self.update()
        
        if self.parent and hasattr(self.parent, 'statusBar'):
            self.parent.statusBar.showMessage("视图已重置：缩放和平移已恢复到初始状态")

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier and not self.baseImage.isNull():
            delta = event.angleDelta().y()
            
            if delta > 0:
                factor = 1.1
            else:
                factor = 0.9
                
            newZoom = self.zoomFactor * factor
            
            if self.minZoom <= newZoom <= self.maxZoom:
                self.zoomFactor = newZoom
                
                oldRect = QRect(self.imageRect)
                
                self.calculateImageRect()
                self.update()
                
                if self.parent and hasattr(self.parent, 'statusBar'):
                    self.parent.statusBar.showMessage(f"缩放: {int(self.zoomFactor * 100)}%")
            
            event.accept()
        else:
            super().wheelEvent(event)
        
    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self.baseImage.isNull():
            self.calculateImageRect()
            self.update()

    def setBrushSize(self, size):
        self.brushSize = size
        
    def setDrawingColor(self, color):
        self.drawingColor = color

    def setDrawingMode(self, mode):
        self.drawingMode = mode

    def clearMask(self):
        if self.maskLayer:
            # Save current state before clearing
            if self.hasMaskContent():
                self.saveMaskState()
                
            self.maskLayer.fill(Qt.transparent)
            self.invalidateCache()
            self.update()

    def hasMaskContent(self):
        if self.maskLayer is None:
            return False
        
        try:
            width = self.maskLayer.width()
            height = self.maskLayer.height()
            
            ptr = self.maskLayer.constBits()
            if ptr is None:
                return self._checkMaskContentTraditional()
                
            ptr.setsize(self.maskLayer.byteCount())
            arr = np.array(ptr).reshape(height, width, 4)
            
            return np.any(arr[:, :, 3] > 0)
            
        except Exception:
            return self._checkMaskContentTraditional()
    
    def _checkMaskContentTraditional(self):
        for y in range(self.maskLayer.height()):
            for x in range(self.maskLayer.width()):
                pixel = self.maskLayer.pixel(x, y)
                alpha = (pixel >> 24) & 0xFF
                
                if alpha > 0:
                    return True
                    
        return False

    def saveMask(self, filePath):
        if not self.hasMaskContent():
            QMessageBox.information(self, "保存掩膜", "没有检测到掩膜内容，未保存文件。")
            return False
            
        if os.path.exists(filePath):
            overwrite = QMessageBox.question(
                self,
                "覆盖",
                f"文件 {filePath} 已存在，是否覆盖？",
                QMessageBox.Yes | QMessageBox.No,
            )
            if overwrite == QMessageBox.No:
                return False
                
        if self.maskLayer:
            binaryMask = QImage(self.maskLayer.size(), QImage.Format_RGB32)
            binaryMask.fill(Qt.black)

            hasMarks = False

            for y in range(self.maskLayer.height()):
                for x in range(self.maskLayer.width()):
                    pixel = self.maskLayer.pixel(x, y)
                    alpha = (pixel >> 24) & 0xFF

                    if alpha > 0:
                        binaryMask.setPixel(x, y, 0xFFFFFF)
                        hasMarks = True

            if not hasMarks:
                return False

            if self.originalImageSize and self.originalImageSize != binaryMask.size():
                binaryMask = binaryMask.scaled(
                    self.originalImageSize,
                    Qt.IgnoreAspectRatio,
                    Qt.SmoothTransformation,
                )

            return binaryMask.save(filePath)
        return False

    def updateCachedPixmap(self, updateRect=None):
        if self.baseImage.isNull() or not self.cacheEnabled:
            return
            
        if updateRect is None:
            updateRect = self.rect()
        
        if self.cachedDirty or self.cachedPixmap.isNull() or self.cachedPixmap.size() != self.size():
            self.cachedPixmap = QPixmap(self.size())
            self.cachedPixmap.fill(Qt.transparent)
            self.cachedDirty = False
            
            painter = QPainter(self.cachedPixmap)
            
            painter.fillRect(self.rect(), QColor(220, 220, 220))
            
            if not self.imageRect.isEmpty():
                painter.drawImage(self.imageRect, self.baseImage)
                
                if self.maskLayer:
                    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                    painter.drawImage(self.imageRect, self.maskLayer)
                    
                    if self.drawingMode != "target":
                        painter.setPen(QPen(QColor(255, 100, 100), 2, Qt.DashLine))
                        painter.drawRect(self.imageRect)
            
            painter.end()
        else:
            painter = QPainter(self.cachedPixmap)
            
            painter.fillRect(updateRect, QColor(220, 220, 220))
            
            imgUpdateRect = self.imageRect.intersected(updateRect)
            if not imgUpdateRect.isEmpty():
                imgX = (imgUpdateRect.x() - self.imageRect.x()) / self.scaleFactor
                imgY = (imgUpdateRect.y() - self.imageRect.y()) / self.scaleFactor
                imgWidth = imgUpdateRect.width() / self.scaleFactor
                imgHeight = imgUpdateRect.height() / self.scaleFactor
                
                srcRect = QRectF(imgX, imgY, imgWidth, imgHeight)
                destRect = QRectF(imgUpdateRect)
                
                painter.drawImage(destRect, self.baseImage, srcRect)
                
                if self.maskLayer:
                    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                    painter.drawImage(destRect, self.maskLayer, srcRect)
            
            if self.drawingMode != "target" and updateRect.intersects(self.imageRect):
                painter.setPen(QPen(QColor(255, 100, 100), 2, Qt.DashLine))
                painter.drawRect(self.imageRect)
            
            painter.end()
    
    def paintEvent(self, event):
        if self.baseImage.isNull():
            return

        updateRect = event.rect()
        
        if self.cacheEnabled:
            self.updateCachedPixmap(updateRect)
            
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.SmoothPixmapTransform,  self.zoomFactor < 1.0)
            painter.drawPixmap(updateRect, self.cachedPixmap, updateRect)
            painter.end()
        else:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.SmoothPixmapTransform,  self.zoomFactor < 1.0)
            
            painter.setPen(Qt.black)
            painter.fillRect(updateRect, QColor(220, 220, 220))
            
            if not self.imageRect.isEmpty() and updateRect.intersects(self.imageRect):
                painter.drawImage(self.imageRect, self.baseImage)
                
                if self.maskLayer:
                    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
                    painter.drawImage(self.imageRect, self.maskLayer)
                    
                    if self.drawingMode != "target":
                        painter.setPen(QPen(QColor(255, 100, 100), 2, Qt.DashLine))
                        painter.drawRect(self.imageRect)
            
            painter.end()

    def mapToImage(self, point):
        if self.imageRect.isEmpty() or self.baseImage.isNull():
            return QPoint()
            
        if not self.imageRect.contains(point):
            return QPoint()
            
        x = int((point.x() - self.imageRect.x()) / self.scaleFactor)
        y = int((point.y() - self.imageRect.y()) / self.scaleFactor)
        
        return QPoint(x, y)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.baseImage.isNull():
            if self.panMode:
                self.panning = True
                self.panStart = event.pos()
                self.setCursor(Qt.ClosedHandCursor)
                return
            
            # Save state before starting a new drawing operation
            if not self.drawing and self.maskLayer:
                self.saveMaskState()
                
            imagePoint = self.mapToImage(event.pos())
            
            if imagePoint.x() >= 0 and imagePoint.y() >= 0 and imagePoint.x() < self.baseImage.width() and imagePoint.y() < self.baseImage.height():
                self.drawing = True
                self.lastPoint = imagePoint

                radius = self.brushSize // 2 + 2
                affectedArea = QRect(
                    self.imageRect.x() + int(imagePoint.x() * self.scaleFactor) - radius,
                    self.imageRect.y() + int(imagePoint.y() * self.scaleFactor) - radius,
                    radius * 2,
                    radius * 2
                )

                painter = QPainter(self.maskLayer)
                painter.setCompositionMode(QPainter.CompositionMode_Source)

                if self.drawingMode == "target":
                    painter.setPen(
                        QPen(
                            self.drawingColor,
                            self.brushSize,
                            Qt.SolidLine,
                            Qt.RoundCap,
                            Qt.RoundJoin,
                        )
                    )
                    painter.setBrush(QBrush(self.drawingColor))
                else:
                    painter.setPen(
                        QPen(
                            Qt.black,
                            self.brushSize,
                            Qt.SolidLine,
                            Qt.RoundCap,
                            Qt.RoundJoin,
                        )
                    )
                    painter.setBrush(QBrush(Qt.black))
                    painter.setCompositionMode(QPainter.CompositionMode_Clear)

                painter.drawPoint(self.lastPoint)
                painter.end()
                
                self.cachedDirty = True
                self.update(affectedArea)

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.LeftButton) and self.panning:
            delta = event.pos() - self.panStart
            self.imageOffset += delta
            self.panStart = event.pos()
            self.calculateImageRect()
            self.invalidateCache()
            self.update()
            return
            
        if (event.buttons() & Qt.LeftButton) and self.drawing:
            imagePoint = self.mapToImage(event.pos())
            
            if imagePoint.x() >= 0 and imagePoint.y() >= 0 and imagePoint.x() < self.baseImage.width() and imagePoint.y() < self.baseImage.height():
                minX = min(self.lastPoint.x(), imagePoint.x()) - self.brushSize
                minY = min(self.lastPoint.y(), imagePoint.y()) - self.brushSize
                maxX = max(self.lastPoint.x(), imagePoint.x()) + self.brushSize
                maxY = max(self.lastPoint.y(), imagePoint.y()) + self.brushSize
                
                imgRect = QRect(minX, minY, maxX - minX, maxY - minY)
                screenMinX = self.imageRect.x() + int(minX * self.scaleFactor)
                screenMinY = self.imageRect.y() + int(minY * self.scaleFactor)
                screenMaxX = self.imageRect.x() + int(maxX * self.scaleFactor)
                screenMaxY = self.imageRect.y() + int(maxY * self.scaleFactor)
                
                affectedArea = QRect(
                    screenMinX,
                    screenMinY,
                    screenMaxX - screenMinX,
                    screenMaxY - screenMinY
                )

                painter = QPainter(self.maskLayer)
                painter.setCompositionMode(QPainter.CompositionMode_Source)

                if self.drawingMode == "target":
                    painter.setPen(
                        QPen(
                            self.drawingColor,
                            self.brushSize,
                            Qt.SolidLine,
                            Qt.RoundCap,
                            Qt.RoundJoin,
                        )
                    )
                else:
                    painter.setPen(
                        QPen(
                            Qt.black,
                            self.brushSize,
                            Qt.SolidLine,
                            Qt.RoundCap,
                            Qt.RoundJoin,
                        )
                    )
                    painter.setCompositionMode(QPainter.CompositionMode_Clear)

                painter.drawLine(self.lastPoint, imagePoint)
                painter.end()

                self.lastPoint = imagePoint
                
                self.cachedDirty = True
                self.update(affectedArea)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.panning:
                self.panning = False
                self.setCursor(Qt.OpenHandCursor)
            self.drawing = False

    def setPanMode(self, enabled):
        self.panMode = enabled
        self.setCursor(Qt.OpenHandCursor if enabled else Qt.ArrowCursor)
        self.invalidateCache()
        self.update()
    
    def saveMaskState(self):
        if self.maskLayer:
            self.redoStack.clear()
            self.undoStack.append(self.maskLayer.copy())
            if len(self.undoStack) > self.maxStackSize:
                self.undoStack.pop(0)
    
    def canUndo(self):
        return len(self.undoStack) > 0
    
    def canRedo(self):
        return len(self.redoStack) > 0
    
    def undo(self):
        if not self.canUndo():
            return False
            
        if self.maskLayer:
            self.redoStack.append(self.maskLayer.copy())
            self.maskLayer = self.undoStack.pop()
            self.invalidateCache()
            self.update()
            return True
        return False
    
    def redo(self):
        if not self.canRedo():
            return False
            
        if self.maskLayer:
            self.undoStack.append(self.maskLayer.copy())
            self.maskLayer = self.redoStack.pop()
            self.invalidateCache()
            self.update()
            return True
        return False