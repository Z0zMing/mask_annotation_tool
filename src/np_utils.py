import numpy as np
from PyQt5.QtGui import QImage

def qimage_to_numpy(image):
    if image.isNull():
        return None
        
    width = image.width()
    height = image.height()
    
    if image.format() == QImage.Format_ARGB32 or image.format() == QImage.Format_ARGB32_Premultiplied:
        ptr = image.constBits()
        if ptr is None:
            return None
            
        ptr.setsize(image.byteCount())
        arr = np.array(ptr).reshape(height, width, 4)
        return arr
    
    elif image.format() == QImage.Format_RGB32:
        ptr = image.constBits()
        if ptr is None:
            return None
            
        ptr.setsize(image.byteCount())
        arr = np.array(ptr).reshape(height, width, 4)
        return arr
    
    elif image.format() == QImage.Format_RGB888:
        ptr = image.constBits()
        if ptr is None:
            return None
            
        ptr.setsize(image.byteCount())
        arr = np.array(ptr).reshape(height, width, 3)
        return arr
    
    return None

def numpy_to_qimage(array, format=QImage.Format_ARGB32):
    if array is None:
        return QImage()
        
    height, width = array.shape[:2]
    
    if len(array.shape) == 3:
        if array.shape[2] == 4:
            bytes_per_line = 4 * width
            img = QImage(array.data, width, height, bytes_per_line, format)
            return img
        elif array.shape[2] == 3:
            bytes_per_line = 3 * width
            img = QImage(array.data, width, height, bytes_per_line, QImage.Format_RGB888)
            return img
    
    elif len(array.shape) == 2:
        bytes_per_line = width
        img = QImage(array.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
        return img
    
    return QImage()

def mask_has_content(mask_image):
    try:
        array = qimage_to_numpy(mask_image)
        if array is None:
            return False
            
        if array.shape[2] >= 4:
            return np.any(array[:, :, 3] > 0)
        return False
    except Exception as e:
        print("NumPy处理错误:", e)
        return False
