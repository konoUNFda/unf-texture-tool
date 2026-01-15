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

# 颜色配置
COLORS = {'R': "#A00000", 'G': "#008000", 'B': "#0000FF", 'A': "#555555"}

# ============================================================
# 左侧素材库列表
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
                else:
                    self.add_paths([path])
            self.files_updated.emit()
            event.accept()
        else:
            super().dropEvent(event)

    def add_paths(self, paths):
        for p in paths:
            if not p.lower().endswith(('.png', '.jpg', '.jpeg', '.tga', '.bmp', '.tif')):
                continue
            exists = False
            for i in range(self.count()):
                if self.item(i).data(Qt.UserRole) == p:
                    exists = True; break
            if not exists:
                item = QListWidgetItem(os.path.basename(p))
                item.setData(Qt.UserRole, p)
                self.addItem(item)

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item: return
        drag = QDrag(self); mime = QMimeData()
        mime.setText(item.data(Qt.UserRole))
        drag.setMimeData(mime); drag.exec_(Qt.CopyAction)

# ============================================================
# 中间通道槽位
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
        layout = QVBoxLayout(self)
        self.lbl_status = QLabel("纯色")
        self.lbl_status.setFixedSize(130, 50); self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet(f"border: 1px dashed {COLORS[self.channel_name]};")

        self.combo_src = QComboBox()
        self.combo_src.addItems(["填充", "R", "G", "B", "A"])
        self.combo_src.currentIndexChanged.connect(self.rule_changed.emit)

        self.sld_val = QSlider(Qt.Horizontal)
        self.sld_val.setRange(0, 255)
        self.sld_val.setValue(255 if self.channel_name == 'A' else 0)
        self.sld_val.valueChanged.connect(self.rule_changed.emit)

        layout.addWidget(self.lbl_status, 0, Qt.AlignCenter)
        layout.addWidget(self.combo_src); layout.addWidget(self.sld_val)

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
                QMessageBox.warning(self, "错误", "需要带下划线的后缀文件")
        else:
            self.fixed_path = path
            self.combo_src.setCurrentIndex(1)
        self.update_display()
        self.rule_changed.emit()

    def update_display(self):
        text = self.match_suffix if self.is_batch_mode else (os.path.basename(self.fixed_path) if self.fixed_path else "空")
        self.lbl_status.setText(text)

    def get_data(self, target_size, batch_file_map=None):
        mode = self.combo_src.currentIndex()
        if mode == 0: return Image.new("L", target_size, self.sld_val.value())
        
        img_path = batch_file_map.get(self.match_suffix) if (self.is_batch_mode and batch_file_map) else self.fixed_path
        if img_path and os.path.exists(img_path):
            try:
                with Image.open(img_path).convert("RGBA") as img:
                    # 只有真正执行导出时才用 LANCZOS，预览可以用 NEAREST 加速
                    resample_mode = Image.NEAREST if target_size[0] < 300 else Image.LANCZOS
                    return img.resize(target_size, resample_mode).split()[mode - 1]
            except: pass
        return Image.new("L", target_size, self.sld_val.value())

# ============================================================
# 主窗口
# ============================================================
class MegaPacker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UNF的合并工具")
        self.resize(1200, 800)
        self.export_path = ""
        
        # 优化：防抖动计时器
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.do_render_preview)
        
        self.init_ui()

    def init_ui(self):
        main_widget = QWidget(); self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # 1. 素材库
        left_layout = QVBoxLayout()
        self.lib_list = FileLibraryList()
        self.lib_list.files_updated.connect(self.auto_update_export_dir)
        left_layout.addWidget(QLabel("导入列表"))
        left_layout.addWidget(self.lib_list)
        self.chk_batch = QCheckBox("启用批处理模式")
        self.chk_batch.toggled.connect(self.on_batch_toggled)
        left_layout.addWidget(self.chk_batch)
        layout.addLayout(left_layout, 1)

        # 2. 通道规则
        mid_layout = QVBoxLayout()
        self.slots = {}
        for ch in ['R', 'G', 'B', 'A']:
            s = ChannelSlot(ch); s.rule_changed.connect(self.request_preview)
            self.slots[ch] = s; mid_layout.addWidget(s)
        layout.addLayout(mid_layout, 1)

        # 3. 预览导出
        right_layout = QVBoxLayout()
        self.edit_export_dir = QLineEdit()
        btn_sel_dir = QPushButton("浏览"); btn_sel_dir.clicked.connect(self.select_dir)
        path_lay = QHBoxLayout(); path_lay.addWidget(self.edit_export_dir); path_lay.addWidget(btn_sel_dir)
        right_layout.addLayout(path_lay)

        self.lbl_preview_img = QLabel("预览图"); self.lbl_preview_img.setFixedSize(400, 400)
        self.lbl_preview_img.setStyleSheet("background:#111;"); self.lbl_preview_img.setAlignment(Qt.AlignCenter)
        self.txt_batch_info = QTextEdit(); self.txt_batch_info.setReadOnly(True); self.txt_batch_info.hide()
        
        right_layout.addWidget(self.lbl_preview_img); right_layout.addWidget(self.txt_batch_info)
        
        btn_exec = QPushButton("开始合并流程"); btn_exec.setFixedHeight(50)
        btn_exec.clicked.connect(self.run_process)
        right_layout.addWidget(btn_exec)
        layout.addLayout(right_layout, 2)

    def request_preview(self):
        # 不直接渲染，而是启动计时器，等待100ms
        self.preview_timer.start(100)

    def do_render_preview(self):
        if self.chk_batch.isChecked():
            self.update_batch_list_text()
        else:
            try:
                # 预览使用 256 尺寸，极大提升速度
                size = (256, 256)
                chs = [self.slots[c].get_data(size) for c in ['R', 'G', 'B', 'A']]
                merged = Image.merge("RGBA", tuple(chs))
                qimg = QImage(merged.tobytes("raw", "RGBA"), 256, 256, QImage.Format_RGBA8888)
                self.lbl_preview_img.setPixmap(QPixmap.fromImage(qimg).scaled(400, 400, Qt.KeepAspectRatio))
            except: pass

    def update_batch_list_text(self):
        groups = self.get_groups()
        info = f"<b>识别到 {len(groups)} 组导出任务：</b><br><hr>"
        for prefix in groups.keys():
            info += f"• {prefix}_Packed.png<br>"
        self.txt_batch_info.setHtml(info)

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

    def auto_update_export_dir(self):
        if self.lib_list.count() > 0 and not self.edit_export_dir.text():
            self.export_path = os.path.dirname(self.lib_list.item(0).data(Qt.UserRole))
            self.edit_export_dir.setText(self.export_path)
        self.request_preview()

    def select_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择目录"); 
        if d: self.export_path = d; self.edit_export_dir.setText(d)

    def on_batch_toggled(self, checked):
        for s in self.slots.values(): s.set_batch_ui(checked)
        self.lbl_preview_img.setVisible(not checked); self.txt_batch_info.setVisible(checked)
        self.request_preview()

    def run_process(self):
        base_dir = self.edit_export_dir.text()
        if not base_dir: return
        
        # 核心逻辑：自动创建 export 文件夹
        export_dir = os.path.join(base_dir, "Export")
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

        if not self.chk_batch.isChecked():
            # 单图模式
            save_path = os.path.join(export_dir, "Merged.png")
            chs = [self.slots[c].get_data((2048, 2048)) for c in ['R', 'G', 'B', 'A']]
            Image.merge("RGBA", tuple(chs)).save(save_path)
            QMessageBox.information(self, "完成", f"已保存至:\n{save_path}")
        else:
            # 批处理模式
            groups = self.get_groups(); success = 0
            for prefix, file_map in groups.items():
                try:
                    ref_img = Image.open(list(file_map.values())[0])
                    chs = [self.slots[c].get_data(ref_img.size, batch_file_map=file_map) for c in ['R', 'G', 'B', 'A']]
                    Image.merge("RGBA", tuple(chs)).save(os.path.join(export_dir, f"{prefix}_Packed.png"))
                    success += 1
                except: pass
            QMessageBox.information(self, "完成", f"批量处理完成！\n已输出 {success} 个文件到 Export 文件夹。")

if __name__ == "__main__":
    app = QApplication(sys.argv); app.setFont(QFont("微软雅黑", 9))
    win = MegaPacker(); win.show(); sys.exit(app.exec_())
