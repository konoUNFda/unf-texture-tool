import sys
import os
import glob
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QFileDialog, QFrame, QSlider, QGroupBox, 
                             QMessageBox, QSpinBox, QComboBox, QListWidget, QCheckBox, 
                             QAbstractItemView, QListWidgetItem, QTextEdit, QLineEdit)
from PyQt5.QtCore import Qt, QMimeData, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QImage, QFont, QDrag
from PIL import Image

# ============================================================
# 全局样式表 (纯白背景，参考 Tool1.py 视觉)
# ============================================================
STYLE_SHEET = """
    QMainWindow, QWidget#MainCentral { background-color: #ffffff; }
    QFrame { border: none; }
    
    QLabel { color: #333333; }
    
    QPushButton { 
        background-color: #ffffff; color: #333333; 
        border: 1px solid #dcdcdc; border-radius: 4px; padding: 6px 12px; 
    }
    QPushButton:hover { background-color: #f5f5f5; }
    
    /* 主执行按钮样式 */
    QPushButton#PrimaryBtn {
        background-color: #0e639c; color: white; border: none; font-weight: bold;
    }
    QPushButton#PrimaryBtn:hover { background-color: #1177bb; }
    
    /* 批处理模式下按钮样式 */
    QPushButton#BatchBtn {
        background-color: #d86210; color: white; border: none; font-weight: bold;
    }

    QListWidget { background-color: #ffffff; border: 1px solid #dcdcdc; border-radius: 4px; }
    QListWidget::item:selected { background-color: #e6f7ff; color: #007acc; }
    
    QLineEdit, QComboBox, QSpinBox { 
        background-color: #ffffff; border: 1px solid #dcdcdc; 
        border-radius: 4px; padding: 4px; 
    }
    
    QGroupBox { 
        border: 1px solid #eeeeee; border-radius: 6px; 
        margin-top: 15px; font-weight: bold; color: #333333;
        padding-top: 15px; background-color: #ffffff;
    }
    QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
    
    QSlider::groove:horizontal { border: 1px solid #eeeeee; height: 6px; background: #f0f0f0; border-radius: 3px; }
    QSlider::handle:horizontal { background: #007acc; border: 1px solid #007acc; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }
"""

COLORS = {'R': "#A00000", 'G': "#008000", 'B': "#0000FF", 'A': "#555555"}

# ============================================================
# 通道槽位组件
# ============================================================
class ChannelSlot(QGroupBox):
    rule_changed = pyqtSignal()

    def __init__(self, channel_name):
        super().__init__(f"{channel_name} 通道")
        self.channel_name = channel_name
        self.is_batch_mode = False
        self.fixed_path = None     
        self.match_suffix = None   
        self.setAcceptDrops(True)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(15)

        self.lbl_status = QLabel("纯色")
        self.lbl_status.setFixedSize(100, 50) 
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setWordWrap(True)
        self.update_label_style(active=False)

        ctrl_layout = QVBoxLayout()
        ctrl_layout.setSpacing(8)
        row_src = QHBoxLayout()
        row_src.addWidget(QLabel("来源:"))
        self.combo_src = QComboBox()
        self.combo_src.addItems(["填充", "R", "G", "B", "A"])
        self.combo_src.currentIndexChanged.connect(self.rule_changed.emit)
        row_src.addWidget(self.combo_src)

        self.sld_val = QSlider(Qt.Horizontal)
        self.sld_val.setRange(0, 255)
        self.sld_val.setValue(255 if self.channel_name == 'A' else 0)
        self.sld_val.valueChanged.connect(self.rule_changed.emit)

        ctrl_layout.addLayout(row_src)
        ctrl_layout.addWidget(self.sld_val)
        layout.addWidget(self.lbl_status)
        layout.addLayout(ctrl_layout)

    def update_label_style(self, active=False):
        color = COLORS[self.channel_name]
        if active:
            self.lbl_status.setStyleSheet(f"background-color: #ffffff; border: 2px solid {color}; border-radius: 6px; color: {color}; font-weight: bold;")
        else:
            self.lbl_status.setStyleSheet(f"background-color: #ffffff; border: 2px dashed #dcdcdc; border-radius: 6px; color: #999999;")

    def set_batch_ui(self, enabled):
        self.is_batch_mode = enabled
        self.update_display()

    def dragEnterEvent(self, event):
        if event.mimeData().hasText(): event.accept()

    def dropEvent(self, event):
        path = event.mimeData().text()
        if self.is_batch_mode:
            fname = os.path.basename(path).split(".")[0]
            if "_" in fname:
                self.match_suffix = "_" + fname.split("_")[-1]
                self.combo_src.setCurrentIndex(1)
        else:
            self.fixed_path = path
            self.combo_src.setCurrentIndex(1)
        self.update_display()
        self.rule_changed.emit()

    def update_display(self):
        text = self.match_suffix if self.is_batch_mode else (os.path.basename(self.fixed_path) if self.fixed_path else "纯色")
        if not self.is_batch_mode and len(text) > 12: text = text[:10] + "..."
        self.lbl_status.setText(text)
        is_active = (self.match_suffix is not None) if self.is_batch_mode else (self.fixed_path is not None)
        self.update_label_style(active=is_active)

    def get_data(self, target_size, batch_file_map=None):
        mode = self.combo_src.currentIndex()
        if mode == 0: return Image.new("L", target_size, self.sld_val.value())
        img_path = batch_file_map.get(self.match_suffix) if (self.is_batch_mode and batch_file_map) else self.fixed_path
        if img_path and os.path.exists(img_path):
            try:
                with Image.open(img_path).convert("RGBA") as img:
                    resample_mode = Image.NEAREST if target_size[0] < 300 else Image.LANCZOS
                    return img.resize(target_size, resample_mode).split()[mode - 1]
            except: pass
        return Image.new("L", target_size, self.sld_val.value())

# ============================================================
# 素材列表类
# ============================================================
class FileLibraryList(QListWidget):
    files_updated = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if os.path.isdir(path):
                    for ext in ['*.png', '*.jpg', '*.tga', '*.bmp', '*.jpeg', '*.tif']:
                        self.add_paths(glob.glob(os.path.join(path, ext)))
                else: self.add_paths([path])
            self.files_updated.emit()
            event.accept()

    def add_paths(self, paths):
        for p in paths:
            if not p.lower().endswith(('.png', '.jpg', '.jpeg', '.tga', '.bmp', '.tif')): continue
            exists = False
            for i in range(self.count()):
                if self.item(i).data(Qt.UserRole) == p: exists = True; break
            if not exists:
                item = QListWidgetItem(os.path.basename(p))
                item.setData(Qt.UserRole, p); self.addItem(item)

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item: return
        drag = QDrag(self); mime = QMimeData(); mime.setText(item.data(Qt.UserRole))
        drag.setMimeData(mime); drag.exec_(Qt.CopyAction)

# ============================================================
# 主窗口 (修改中间布局对齐)
# ============================================================
class MegaPacker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UNF 纹理通道合并工具")
        self.resize(1150, 780)
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.do_render_preview)
        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        main_widget.setObjectName("MainCentral")
        self.setCentralWidget(main_widget)
        
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # 1. 素材库 (左侧)
        left_layout = QVBoxLayout()
        left_layout.setSpacing(12)
        left_layout.addWidget(QLabel("<b>导入列表</b>"))
        self.lib_list = FileLibraryList()
        self.chk_batch = QCheckBox("启用批处理模式")
        self.chk_batch.setStyleSheet("font-weight: bold; color: #d86210;")
        self.chk_batch.toggled.connect(self.on_batch_toggled)
        left_layout.addWidget(self.lib_list)
        left_layout.addWidget(self.chk_batch)
        layout.addLayout(left_layout, 25)

        # 2. 通道规则 (中间) - 修改重点：添加 AddStretch 向上对齐
        mid_layout = QVBoxLayout()
        mid_layout.setSpacing(10)
        mid_layout.addWidget(QLabel("<b>通道配置</b>"))
        self.slots = {}
        for ch in ['R', 'G', 'B', 'A']:
            s = ChannelSlot(ch)
            s.rule_changed.connect(self.request_preview)
            self.slots[ch] = s
            mid_layout.addWidget(s)
        
        # 这一行将所有上面的控件推向顶部
        mid_layout.addStretch() 
        
        layout.addLayout(mid_layout, 35)

        # 3. 预览与导出 (右侧)
        right_layout = QVBoxLayout()
        right_layout.setSpacing(15)
        right_layout.addWidget(QLabel("<b>输出预览</b>"))
        self.lbl_preview_img = QLabel("预览图")
        self.lbl_preview_img.setFixedSize(400, 400)
        self.lbl_preview_img.setStyleSheet("background-color: #f9f9f9; border: 1px solid #eeeeee; border-radius: 4px;")
        self.lbl_preview_img.setAlignment(Qt.AlignCenter)
        self.txt_batch_info = QTextEdit()
        self.txt_batch_info.setFixedSize(400, 400)
        self.txt_batch_info.hide()
        right_layout.addWidget(self.lbl_preview_img)
        right_layout.addWidget(self.txt_batch_info)

        export_group = QGroupBox("导出设置")
        export_lay = QVBoxLayout(export_group)
        path_lay = QHBoxLayout()
        self.edit_export_dir = QLineEdit()
        btn_sel_dir = QPushButton("浏览")
        btn_sel_dir.clicked.connect(self.select_dir)
        path_lay.addWidget(self.edit_export_dir); path_lay.addWidget(btn_sel_dir)
        export_lay.addLayout(path_lay)
        self.btn_exec = QPushButton("执行合并 (导出当前)")
        self.btn_exec.setObjectName("PrimaryBtn")
        self.btn_exec.setFixedHeight(45)
        self.btn_exec.clicked.connect(self.run_process)
        export_lay.addWidget(self.btn_exec)
        right_layout.addWidget(export_group)
        right_layout.addStretch()
        layout.addLayout(right_layout, 40)

    def request_preview(self): self.preview_timer.start(100)
    def select_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择目录")
        if d: self.edit_export_dir.setText(d)

    def on_batch_toggled(self, checked):
        for s in self.slots.values(): s.set_batch_ui(checked)
        self.lbl_preview_img.setVisible(not checked)
        self.txt_batch_info.setVisible(checked)
        self.btn_exec.setText("执行批量合并" if checked else "执行合并 (导出当前)")
        self.btn_exec.setObjectName("BatchBtn" if checked else "PrimaryBtn")
        self.btn_exec.style().unpolish(self.btn_exec)
        self.btn_exec.style().polish(self.btn_exec)
        self.request_preview()

    def do_render_preview(self):
        if self.chk_batch.isChecked():
            groups = self.get_groups()
            info = f"<p style='color:#d86210;'><b>识别到 {len(groups)} 组导出任务：</b></p><hr>"
            for prefix in groups.keys(): info += f"• {prefix}_Packed.png<br>"
            self.txt_batch_info.setHtml(info)
        else:
            try:
                chs = [self.slots[c].get_data((256, 256)) for c in ['R', 'G', 'B', 'A']]
                merged = Image.merge("RGBA", tuple(chs))
                qimg = QImage(merged.tobytes("raw", "RGBA"), 256, 256, QImage.Format_RGBA8888)
                self.lbl_preview_img.setPixmap(QPixmap.fromImage(qimg).scaled(400, 400, Qt.KeepAspectRatio))
            except: pass

    def get_groups(self):
        all_files = [self.lib_list.item(i).data(Qt.UserRole) for i in range(self.lib_list.count())]
        groups = {}
        active_suffixes = [s.match_suffix for s in self.slots.values() if s.match_suffix]
        for f in all_files:
            name = os.path.basename(f).rsplit(".", 1)[0]
            if "_" in name:
                parts = name.split("_")
                suffix, prefix = "_" + parts[-1], "_".join(parts[:-1])
                if suffix in active_suffixes:
                    if prefix not in groups: groups[prefix] = {}
                    groups[prefix][suffix] = f
        return groups

    def run_process(self):
        base_dir = self.edit_export_dir.text()
        if not base_dir: return
        export_dir = os.path.join(base_dir, "Export")
        if not os.path.exists(export_dir): os.makedirs(export_dir)
        if not self.chk_batch.isChecked():
            save_path = os.path.join(export_dir, "Merged.png")
            chs = [self.slots[c].get_data((2048, 2048)) for c in ['R', 'G', 'B', 'A']]
            Image.merge("RGBA", tuple(chs)).save(save_path)
            QMessageBox.information(self, "完成", f"已保存至:\n{save_path}")
        else:
            groups = self.get_groups(); success = 0
            for prefix, file_map in groups.items():
                try:
                    ref_img = Image.open(list(file_map.values())[0])
                    chs = [self.slots[c].get_data(ref_img.size, batch_file_map=file_map) for c in ['R', 'G', 'B', 'A']]
                    Image.merge("RGBA", tuple(chs)).save(os.path.join(export_dir, f"{prefix}_Packed.png"))
                    success += 1
                except: pass
            QMessageBox.information(self, "完成", f"批量处理完成！")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 9))
    app.setStyleSheet(STYLE_SHEET)
    win = MegaPacker()
    win.show()
    sys.exit(app.exec_())
