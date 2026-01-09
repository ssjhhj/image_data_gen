import sys
import os
import math
import random

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsLineItem,
    QFileDialog, QPushButton,
    QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QSpinBox
)
from PySide6.QtGui import (
    QPixmap, QPen, QPainter, QKeySequence
)
from PySide6.QtCore import Qt, QRectF


class GraphicsView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # 关键：关闭默认的拖拽模式
        self.setDragMode(QGraphicsView.NoDrag)

        # 用于手动实现拖拽视图
        self.is_panning = False
        self.last_pos = None

    def mousePressEvent(self, event):
        # 如果点到了 Item，就交给父类处理（选中 + 拖动）
        if self.itemAt(event.position().toPoint()):
            super().mousePressEvent(event)
        else:
            # 点到空白处，准备拖动视图
            self.is_panning = True
            self.last_pos = event.pos()
            self.setCursor(Qt.OpenHandCursor)

    def mouseMoveEvent(self, event):
        if self.is_panning:
            # 拖动视图
            delta = event.pos() - self.last_pos
            self.last_pos = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_panning:
            self.is_panning = False
            self.setCursor(Qt.ArrowCursor)
        else:
            super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        items = self.scene().selectedItems()
        if not items:
            # 未选中项时，滚轮缩放视图
            factor = 1.1 if event.angleDelta().y() > 0 else 0.9
            self.scale(factor, factor)
            return

        # 选中项时，缩放选中的线或异物
        factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        for item in items:
            if isinstance(item, QGraphicsPixmapItem):
                item.setScale(item.scale() * factor)
            elif isinstance(item, QGraphicsLineItem):
                pen = item.pen()
                pen.setWidthF(max(1.0, pen.widthF() * factor))
                item.setPen(pen)
        event.accept()


class ImageEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("图像合成 / 数据生成工具")
        self.resize(1300, 850)

        self.scene = QGraphicsScene()
        self.view = GraphicsView(self.scene)

        self.background_item = None
        self.line_item = None

        self._init_ui()
        self._load_default_background()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.addWidget(self.view, 1)

        side = QVBoxLayout()
        layout.addLayout(side)

        btn_bg = QPushButton("切换背景")
        btn_bg.clicked.connect(self.change_background)
        side.addWidget(btn_bg)

        btn_line = QPushButton("添加线")
        btn_line.clicked.connect(self.create_line)
        side.addWidget(btn_line)

        side.addWidget(QLabel("线角度（°）"))
        self.angle_slider = QSlider(Qt.Horizontal)
        self.angle_slider.setRange(-90, 90)
        self.angle_slider.setValue(0)
        self.angle_slider.valueChanged.connect(self.update_line_angle)
        side.addWidget(self.angle_slider)

        btn_defect = QPushButton("添加异物")
        btn_defect.clicked.connect(self.add_defect)
        side.addWidget(btn_defect)

        side.addSpacing(20)

        side.addWidget(QLabel("批量生成数量"))
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 1000)
        self.batch_spin.setValue(50)
        side.addWidget(self.batch_spin)

        btn_batch = QPushButton("批量生成")
        btn_batch.clicked.connect(self.batch_generate)
        side.addWidget(btn_batch)

        side.addStretch()

        save = self.addAction("Save")
        save.setShortcut(QKeySequence.Save)
        save.triggered.connect(self.save_image)

    # ---------------- 背景 ----------------
    def _load_default_background(self):
        if os.path.exists("original.png"):
            self.set_background("original.png")
        else:
            # 提示用户缺少默认背景图
            print("警告：未找到默认背景图 original.png，请手动选择背景图")

    def set_background(self, path):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            print(f"错误：无法加载图片 {path}")
            return

        self.scene.clear()
        self.background_item = QGraphicsPixmapItem(pixmap)
        self.background_item.setZValue(0)
        self.scene.addItem(self.background_item)

        self.scene.setSceneRect(QRectF(pixmap.rect()))
        self.create_line()

    def change_background(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择背景", "", "Images (*.png *.jpg *.bmp)"
        )
        if path:
            self.set_background(path)

    # ---------------- 线 ----------------
    def create_line(self):
        if not self.background_item:
            return

        rect = self.scene.sceneRect()
        cx, cy = round(rect.center().x()), round(rect.center().y())

        length = max(rect.width(), rect.height()) * 3

        self.line_item = QGraphicsLineItem(
            -length / 2, 0,
             length / 2, 0
        )

        pen = QPen(Qt.black)
        pen.setWidthF(3.0)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)

        self.line_item.setPen(pen)
        self.line_item.setPos(cx, cy)

        # ⭐ 关键：旋转中心 = 几何中心
        self.line_item.setTransformOriginPoint(
            self.line_item.boundingRect().center()
        )

        self.line_item.setFlags(
            QGraphicsLineItem.ItemIsMovable |
            QGraphicsLineItem.ItemIsSelectable
        )
        self.line_item.setZValue(10)
        self.scene.addItem(self.line_item)

    def update_line_angle(self, angle):
        if self.line_item:
            self.line_item.setRotation(angle)

    # ---------------- 异物 ----------------
    def add_defect(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择异物", "", "Images (*.png *.jpg *.bmp)"
        )
        if not path:
            return

        pix = QPixmap(path)
        if pix.isNull():
            print(f"错误：无法加载异物图片 {path}")
            return

        item = QGraphicsPixmapItem(pix)
        item.setScale(0.2)
        item.setZValue(20)

        item.setFlags(
            QGraphicsPixmapItem.ItemIsMovable |
            QGraphicsPixmapItem.ItemIsSelectable
        )

        item.setPos(self.scene.sceneRect().center())
        self.scene.addItem(item)
    
    def add_defect_by_path(self, path):
        if not os.path.exists(path):
            return  # 不存在则静默忽略

        pix = QPixmap(path)
        if pix.isNull():
            return

        item = QGraphicsPixmapItem(pix)
        item.setScale(0.2)
        item.setZValue(20)

        item.setFlags(
            QGraphicsPixmapItem.ItemIsMovable |
            QGraphicsPixmapItem.ItemIsSelectable
        )

        item.setPos(self.scene.sceneRect().center())
        self.scene.addItem(item)

    def keyPressEvent(self, event):
        key = event.key()

        # Qt.Key_1 到 Qt.Key_9 是连续的
        if Qt.Key_1 <= key <= Qt.Key_9:
            index = key - Qt.Key_0  # 得到 1~9
            yiwu_path = os.path.join(os.getcwd(), "yiwu", f"{index}.png")
            self.add_defect_by_path(yiwu_path)
            return

        super().keyPressEvent(event)
    
    # ---------------- 批量 ----------------
    def batch_generate(self):
        if not self.background_item:
            print("错误：请先设置背景图")
            return

        count = self.batch_spin.value()
        # 保存位置为当前文件夹的 data 目录
        out_dir = os.path.join(os.getcwd(), "data")
        os.makedirs(out_dir, exist_ok=True)

        yiwu_dir = os.path.join(os.getcwd(), "yiwu")
        if not os.path.exists(yiwu_dir):
            print(f"错误：未找到异物目录 {yiwu_dir}")
            return

        # 定义每个异物图片对应的缩放比例（1-5.png 分别对应自定义大小）
        yiwu_scale_map = {
            "1.png": 0.2,
            "2.png": 0.25,
            "3.png": 0.18,
            "4.png": 0.3,
            "5.png": 0.22
        }
        
        # 筛选出 1-5.png 的异物图片
        yiwu_imgs = []
        for f in os.listdir(yiwu_dir):
            if f in yiwu_scale_map.keys():  # 只保留指定的异物图片
                yiwu_imgs.append(os.path.join(yiwu_dir, f))
        
        if not yiwu_imgs:
            print(f"错误：异物目录 {yiwu_dir} 中未找到 1.png-5.png 文件")
            return

        rect = self.scene.sceneRect()
        bg_pixmap = self.background_item.pixmap()

        for i in range(count):
            temp_scene = QGraphicsScene()
            # 添加背景
            bg_item = QGraphicsPixmapItem(bg_pixmap)
            bg_item.setZValue(0)
            temp_scene.addItem(bg_item)

            cx, cy = rect.center().x(), rect.center().y()
            line_angle = random.uniform(-15, 15)  # 线的旋转角度

            # 添加线
            length = max(rect.width(), rect.height()) * 3
            line = QGraphicsLineItem(-length / 2, 0, length / 2, 0)
            pen = QPen(Qt.black)
            pen.setWidthF(random.uniform(2, 5))
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            line.setPen(pen)
            line.setPos(cx, cy)
            line.setTransformOriginPoint(line.boundingRect().center())
            line.setRotation(line_angle)
            temp_scene.addItem(line)

            # ========== 核心修改：只添加一个异物，且中心点落在线上 ==========
            # 1. 随机选一个异物
            yiwu_path = random.choice(yiwu_imgs)
            yiwu_filename = os.path.basename(yiwu_path)
            pix = QPixmap(yiwu_path)
            if pix.isNull():
                continue
            
            # 2. 创建异物Item并设置缩放
            defect_item = QGraphicsPixmapItem(pix)
            defect_item.setScale(yiwu_scale_map[yiwu_filename])
            defect_item.setRotation(random.uniform(0, 360))  # 异物随机旋转
            
            # 3. 计算线上的随机位置（确保异物中心点落在线上）
            # 线的旋转角度转弧度
            radian = math.radians(line_angle)
            # 在线的长度范围内随机选一个偏移量（-length/2 到 length/2）
            line_offset = random.uniform(-length/3, length/3)
            # 根据线的角度计算异物的坐标（中心点落在线上）
            defect_x = cx + line_offset * math.cos(radian)
            defect_y = cy + line_offset * math.sin(radian)
            
            # 设置异物位置（setPos是设置Item的左上角，需要修正为中心点对齐）
            defect_rect = defect_item.boundingRect()
            defect_center_x = defect_rect.width() / 2
            defect_center_y = defect_rect.height() / 2
            defect_item.setPos(defect_x - defect_center_x, defect_y - defect_center_y)
            defect_item.setZValue(20)
            
            temp_scene.addItem(defect_item)

            # 保存图片
            img = QPixmap(rect.size().toSize())
            img.fill(Qt.white)  # 使用白色背景替代透明背景，避免保存后背景变黑
            painter = QPainter(img)
            temp_scene.render(painter, QRectF(img.rect()), rect)
            painter.end()
            save_path = os.path.join(out_dir, f"{i:04d}.png")
            img.save(save_path)
            print(f"已保存：{save_path}")

        print(f"批量生成完成！共生成 {count} 张图片，保存至：{out_dir}")

    # ---------------- 保存 ----------------
    def save_image(self):
        import datetime  # 导入日期时间模块
        
        out_dir = os.path.join(os.getcwd(), "data")
        os.makedirs(out_dir, exist_ok=True)
        
        current_time = datetime.datetime.now()
        file_name = current_time.strftime("%Y-%m-%d_%H-%M-%S-%f") + ".png"
        save_path = os.path.join(out_dir, file_name)
        
        rect = self.scene.sceneRect()
        pix = QPixmap(rect.size().toSize())
        pix.fill(Qt.white)  # 使用白色背景
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.scene.render(painter, QRectF(pix.rect()), rect)
        painter.end()
        pix.save(save_path)
        
        print(f"图片已保存至：{save_path}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = ImageEditor()
    w.show()
    sys.exit(app.exec())