import sys
import os
import glob
import copy
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QListWidget, QListWidgetItem, QFileDialog, 
                             QSplitter, QFrame, QLineEdit, QCheckBox, QSlider, QGroupBox, 
                             QMessageBox, QSpinBox, QAbstractItemView)
from PyQt5.QtCore import Qt, QMimeData, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QDrag, QFont, QIcon
from PIL import Image, ImageEnhance, ImageOps 

def resource_path(relative_path):
    """ 获取资源的绝对路径，兼容 PyInstaller 打包后的路径 """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

CHANNEL_COLORS = {
    'R': "#A00000", # 深红
    'G': "#008000", # 深绿
    'B': "#0000FF", # 深蓝
    'A': "#555555"  # 深灰
}

# ===========================
# 自定义支持拖入文件夹的按钮
# ===========================
class DropButton(QPushButton):
    folder_dropped = pyqtSignal(str)

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0].toLocalFile()
            if os.path.isdir(url):
                event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if os.path.isdir(path):
                self.folder_dropped.emit(path)
                event.acceptProposedAction()

# ===========================
# 左侧源通道按钮
# ===========================
class DraggableChannel(QLabel):
    def __init__(self, text, channel_type, parent=None):
        super().__init__(text, parent)
        self.channel_type = channel_type
        self.setAlignment(Qt.AlignCenter)
        color = CHANNEL_COLORS.get(channel_type, "#333333")
        self.setStyleSheet(f"""
            QLabel {{
                background-color: #ffffff; 
                color: {color}; 
                border: 1px solid #dcdcdc; 
                border-radius: 6px;
                font-weight: bold;
            }}
            QLabel:hover {{
                background-color: #f0f0f0;
                border-color: #007acc;
            }}
        """)
        self.setFixedSize(100, 45) 

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.channel_type)
            drag.setMimeData(mime_data)
            drag.setPixmap(self.grab())
            drag.exec_(Qt.CopyAction)

# ===========================
# 通道槽位
# ===========================
class DropChannelSlot(QLabel):
    clicked = pyqtSignal(str) 
    data_changed = pyqtSignal()

    def __init__(self, channel_name, parent=None):
        super().__init__(parent)
        self.channel_name = channel_name
        self.source_channel = channel_name
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedSize(90, 90)
        self.update_style(False)
        self.update_display()

    def update_style(self, selected=False):
        native_color = CHANNEL_COLORS.get(self.channel_name, "#dcdcdc")
        if selected:
            self.setStyleSheet(f"background-color: #f0f9ff; border: 2px solid {native_color}; border-radius: 8px;")
        else:
            self.setStyleSheet(f"background-color: #ffffff; border: 2px dashed #dcdcdc; border-radius: 8px;")

    def dragEnterEvent(self, event):
        if event.mimeData().hasText(): event.accept()
        else: event.ignore()

    def dropEvent(self, event):
        source_ch = event.mimeData().text()
        self.source_channel = source_ch
        self.update_display()
        self.data_changed.emit()
        event.accept()

    def mousePressEvent(self, event):
        self.clicked.emit(self.channel_name)

    def update_display(self):
        native_color = CHANNEL_COLORS.get(self.channel_name, "#333333")
        source_color = CHANNEL_COLORS.get(self.source_channel, "#333333")
        self.setText(f"""
            <div style='line-height: 140%;'>
                <span style='color:{native_color}; font-weight:bold;'>{self.channel_name} 通道</span><br>
                <span style='color:{source_color};'>来自: {self.source_channel}</span>
            </div>
        """)

# ===========================
# 主窗口
# ===========================
class TexturePacker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UNF的贴图拆分工具v1.2")
        icon_path = resource_path("tmr.ico")
        self.setWindowIcon(QIcon(icon_path))
        self.resize(1400, 850)
        
        # 开启窗口层级的拖拽支持
        self.setAcceptDrops(True)
        
        self.src_image_path = None
        self.src_image = None
        self.src_channels = {}
        self.outputs = [] 
        self.current_output_index = -1
        self.current_selected_slot = 'R'
        self.output_dir = "" 
        
        self.history_stack = []
        self.redo_stack = []
        self.max_history = 20

        self.create_default_output_data()
        self.init_ui()
        
        if len(self.outputs) > 0:
            self.list_outputs.setCurrentRow(0)
            self.change_current_output(0)

    # --- 拖拽图片导入逻辑 ---
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ['.png', '.jpg', '.jpeg', '.tga', '.bmp']:
                self.load_image_by_path(file_path)
                event.acceptProposedAction()

    def save_state(self):
        state = copy.deepcopy(self.outputs)
        self.history_stack.append(state)
        if len(self.history_stack) > self.max_history: self.history_stack.pop(0)
        self.redo_stack.clear()

    def init_ui(self):
        font = QFont("Microsoft YaHei", 9)
        QApplication.setFont(font)

        self.setStyleSheet("""
            QMainWindow, QWidget#central { background-color: #ffffff; }
            QFrame { border: none; }
            QPushButton { 
                background-color: #ffffff; color: #333333; 
                border: 1px solid #dcdcdc; border-radius: 4px; padding: 6px 12px; 
            }
            QPushButton:hover { background-color: #f5f5f5; }
            QListWidget { background-color: #ffffff; border: 1px solid #dcdcdc; border-radius: 4px; }
            QListWidget::item:selected { background-color: #e6f7ff; color: #007acc; }
            QLineEdit, QSpinBox { 
                background-color: #ffffff; border: 1px solid #dcdcdc; 
                border-radius: 4px; padding: 4px; 
            }
            QGroupBox { 
                border: 1px solid #eeeeee; border-radius: 6px; 
                margin-top: 20px; font-weight: bold; color: #333333;
                padding-top: 20px; 
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QSlider::groove:horizontal { border: 1px solid #eeeeee; height: 6px; background: #f0f0f0; border-radius: 3px; }
            QSlider::handle:horizontal { background: #007acc; border: 1px solid #007acc; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }
        """)

        central_widget = QWidget()
        central_widget.setObjectName("central")
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- 左侧 ---
        left_panel = QFrame()
        left_vbox = QVBoxLayout(left_panel)
        left_vbox.setSpacing(12) 
        
        self.lbl_src_preview = QLabel("拖入图片或点击导入")
        self.lbl_src_preview.setFixedSize(260, 260)
        self.lbl_src_preview.setStyleSheet("background-color: #f9f9f9; border: 2px dashed #cccccc; border-radius: 4px;")
        self.lbl_src_preview.setAlignment(Qt.AlignCenter)
        
        btn_import = QPushButton("导入源图")
        btn_import.setFixedHeight(35)
        btn_import.clicked.connect(self.load_image_dialog)
        
        left_vbox.addWidget(QLabel("<b>源文件预览</b>"))
        left_vbox.addWidget(self.lbl_src_preview)
        left_vbox.addWidget(btn_import)
        left_vbox.addSpacing(15)
        
        for ch in ['R', 'G', 'B', 'A']:
            btn_box = QHBoxLayout()
            btn_box.addWidget(DraggableChannel(f"源 {ch}", ch))
            btn_box.addStretch()
            left_vbox.addLayout(btn_box)
        left_vbox.addStretch()

        # --- 中间 ---
        mid_panel = QFrame()
        mid_vbox = QVBoxLayout(mid_panel)
        self.lbl_out_preview = QLabel("合并预览")
        self.lbl_out_preview.setFixedSize(400, 400)
        self.lbl_out_preview.setStyleSheet("background-color: #f9f9f9; border: 1px solid #eeeeee; border-radius: 4px;")
        self.lbl_out_preview.setAlignment(Qt.AlignCenter)
        
        list_btn_layout = QVBoxLayout()
        row_btns = QHBoxLayout()
        btn_add_out = QPushButton("＋ 新建输出项")
        btn_add_out.clicked.connect(self.add_output_ui)
        btn_del_out = QPushButton("－ 删除输出项")
        btn_del_out.clicked.connect(self.remove_output_ui)
        row_btns.addWidget(btn_add_out); row_btns.addWidget(btn_del_out)
        
        row_modes = QHBoxLayout()
        btn_normal = QPushButton("Normal 模式")
        btn_normal.clicked.connect(self.toggle_normal_mode)
        btn_split = QPushButton("一键分离 RGBA")
        btn_split.clicked.connect(self.split_channels_mode)
        row_modes.addWidget(btn_normal); row_modes.addWidget(btn_split)
        
        list_btn_layout.addLayout(row_btns); list_btn_layout.addLayout(row_modes)

        self.list_outputs = QListWidget()
        self.list_outputs.setDragEnabled(True)
        self.list_outputs.setAcceptDrops(True)
        self.list_outputs.setDropIndicatorShown(True)
        self.list_outputs.setDragDropMode(QAbstractItemView.InternalMove)
        self.list_outputs.setDefaultDropAction(Qt.MoveAction)
        
        self.list_outputs.model().rowsMoved.connect(self.handle_list_reorder)
        self.list_outputs.currentRowChanged.connect(self.change_current_output)

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("重命名当前输出...")
        self.edit_name.editingFinished.connect(self.rename_output_final)
        
        self.slots_layout = QHBoxLayout()
        self.slot_widgets = {}
        for ch in ['R', 'G', 'B', 'A']:
            sw = DropChannelSlot(ch)
            sw.clicked.connect(self.select_slot_for_editing)
            sw.data_changed.connect(self.handle_slot_drop)
            self.slot_widgets[ch] = sw
            self.slots_layout.addWidget(sw)

        mid_vbox.addWidget(QLabel("<b>输出预览</b>"))
        mid_vbox.addWidget(self.lbl_out_preview)
        mid_vbox.addWidget(QLabel("<b>输出列表 (拖拽可排序)</b>"))
        mid_vbox.addLayout(list_btn_layout)
        mid_vbox.addWidget(self.list_outputs)
        mid_vbox.addWidget(self.edit_name)
        mid_vbox.addSpacing(15)
        mid_vbox.addWidget(QLabel("<b>通道配置</b>"))
        mid_vbox.addLayout(self.slots_layout)

        # --- 右侧 ---
        right_panel = QFrame()
        right_panel.setMinimumWidth(360) 
        right_vbox = QVBoxLayout(right_panel)
        
        self.lbl_chan_preview = QLabel("单通道视图")
        self.lbl_chan_preview.setFixedSize(220, 220)
        self.lbl_chan_preview.setStyleSheet("background-color: #f9f9f9; border: 1px solid #eeeeee; border-radius: 4px;")
        self.lbl_chan_preview.setAlignment(Qt.AlignCenter)
        
        self.group_mod = QGroupBox("通道调节")
        mod_lay = QVBoxLayout()
        mod_lay.setSpacing(18) 
        mod_lay.setContentsMargins(15, 25, 15, 15)

        self.chk_solid = QCheckBox("填充纯色模式")
        self.chk_solid.clicked.connect(self.handle_chk_click)
        mod_lay.addWidget(self.chk_solid)

        self.chk_invert = QCheckBox("反转通道颜色")
        self.chk_invert.clicked.connect(self.handle_chk_click)
        mod_lay.addWidget(self.chk_invert)

        def create_val_row(label_text, min_v, max_v, default_v):
            row = QHBoxLayout()
            lbl = QLabel(label_text); lbl.setFixedWidth(80)
            sld = QSlider(Qt.Horizontal); sld.setRange(min_v, max_v); sld.setValue(default_v)
            spn = QSpinBox(); spn.setRange(min_v, max_v); spn.setValue(default_v); spn.setFixedWidth(85) 
            sld.valueChanged.connect(spn.setValue); spn.valueChanged.connect(sld.setValue)
            sld.valueChanged.connect(self.update_data_from_ui_no_history)
            sld.sliderReleased.connect(self.handle_slider_released)
            row.addWidget(lbl); row.addWidget(sld); row.addWidget(spn)
            return row, sld, spn

        row_solid, self.sld_solid, self.spn_solid = create_val_row("纯色灰度:", 0, 255, 128)
        row_bright, self.sld_bright, self.spn_bright = create_val_row("亮度调节:", 0, 200, 100)
        row_contrast, self.sld_contrast, self.spn_contrast = create_val_row("对比度:", 0, 200, 100)

        mod_lay.addLayout(row_solid); mod_lay.addLayout(row_bright); mod_lay.addLayout(row_contrast)
        self.group_mod.setLayout(mod_lay)
        
        self.lbl_path_display = QLabel("输出目录: 默认源图路径")
        self.lbl_path_display.setStyleSheet("color: #007acc; font-size: 11px;")
        self.lbl_path_display.setWordWrap(True)
        
        btn_select_dir = QPushButton("更改输出目录")
        btn_select_dir.clicked.connect(self.select_output_directory)
        
        self.chk_smart_export = QCheckBox("增加序号前缀 / Export文件夹")
        self.chk_smart_export.setChecked(True)
        
        btn_run = QPushButton("执行合并 (导出当前)")
        btn_run.setStyleSheet("background-color: #0e639c; color: white; height: 45px; font-weight: bold;")
        btn_run.clicked.connect(self.process_single)
        
        self.btn_batch = DropButton("批量处理文件夹 (可拖入)")
        self.btn_batch.setStyleSheet("background-color: #d86210; color: white; height: 45px; font-weight: bold;")
        self.btn_batch.clicked.connect(self.batch_select_and_run)
        self.btn_batch.folder_dropped.connect(self.execute_batch_process)

        right_vbox.addWidget(QLabel("<b>当前通道预览</b>"))
        right_vbox.addWidget(self.lbl_chan_preview, 0, Qt.AlignCenter)
        right_vbox.addWidget(self.group_mod)
        right_vbox.addStretch()
        right_vbox.addWidget(self.lbl_path_display); right_vbox.addWidget(btn_select_dir)
        right_vbox.addWidget(self.chk_smart_export) 
        right_vbox.addWidget(btn_run); right_vbox.addWidget(self.btn_batch)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel); splitter.addWidget(mid_panel); splitter.addWidget(right_panel)
        splitter.setStretchFactor(1, 2)
        main_layout.addWidget(splitter)
        self.refresh_list_widget()

    # ================= 业务逻辑 =================

    def handle_list_reorder(self, parent, start, end, destination, row):
        if start == row: return
        self.save_state()
        moving_data = self.outputs.pop(start)
        new_pos = row if row < start else row - 1
        if new_pos < 0: new_pos = 0
        self.outputs.insert(new_pos, moving_data)
        self.current_output_index = self.list_outputs.currentRow()

    def create_default_output_data(self, name=None):
        if name is None:
            existing_names = [out["name"] for out in self.outputs]
            counter = 1
            while f"Out{counter}" in existing_names: counter += 1
            name = f"Out{counter}"
        new_slots = {ch: {"source": ch, "brightness": 100, "contrast": 100, "is_solid": True, "solid_value": 255 if ch == 'A' else 128, "is_inverted": False} for ch in ['R', 'G', 'B', 'A']}
        self.outputs.append({"name": name, "slots": new_slots})
        self.current_output_index = len(self.outputs) - 1

    def change_current_output(self, index):
        if index < 0 or index >= len(self.outputs): return
        self.current_output_index = index
        data = self.outputs[index]
        self.edit_name.blockSignals(True); self.edit_name.setText(data["name"]); self.edit_name.blockSignals(False)
        for ch in ['R', 'G', 'B', 'A']:
            self.slot_widgets[ch].source_channel = data["slots"][ch]["source"]
            self.slot_widgets[ch].update_display()
        self.select_slot_for_editing(self.current_selected_slot)

    def select_slot_for_editing(self, slot_name):
        self.current_selected_slot = slot_name
        for name, sw in self.slot_widgets.items(): sw.update_style(name == slot_name)
        if not (0 <= self.current_output_index < len(self.outputs)): return
        conf = self.outputs[self.current_output_index]["slots"][slot_name]
        self.chk_solid.blockSignals(True); self.chk_solid.setChecked(conf["is_solid"]); self.chk_solid.blockSignals(False)
        self.chk_invert.blockSignals(True); self.chk_invert.setChecked(conf.get("is_inverted", False)); self.chk_invert.blockSignals(False)
        self.sld_solid.setValue(conf["solid_value"]); self.sld_bright.setValue(conf["brightness"]); self.sld_contrast.setValue(conf["contrast"]); self.refresh_previews()

    def handle_slot_drop(self):
        if self.current_output_index < 0: return
        target_slot = self.sender()
        if not target_slot: return
        target_name = target_slot.channel_name 
        self.save_state()
        for ch in ['R', 'G', 'B', 'A']: self.outputs[self.current_output_index]["slots"][ch]["source"] = self.slot_widgets[ch].source_channel
        self.outputs[self.current_output_index]["slots"][target_name]["is_solid"] = False
        self.select_slot_for_editing(target_name)

    def refresh_list_widget(self):
        self.list_outputs.blockSignals(True); self.list_outputs.clear()
        for out in self.outputs: self.list_outputs.addItem(out["name"])
        if 0 <= self.current_output_index < len(self.outputs): self.list_outputs.setCurrentRow(self.current_output_index)
        self.list_outputs.blockSignals(False)

    def update_data_from_ui_no_history(self):
        if not (0 <= self.current_output_index < len(self.outputs)): return
        conf = self.outputs[self.current_output_index]["slots"][self.current_selected_slot]
        conf["is_solid"] = self.chk_solid.isChecked(); conf["is_inverted"] = self.chk_invert.isChecked() 
        conf["solid_value"] = self.sld_solid.value(); conf["brightness"] = self.sld_bright.value(); conf["contrast"] = self.sld_contrast.value()
        self.refresh_previews()

    def get_processed_ch(self, slot_conf, size, source_dict=None):
        active_dict = source_dict if source_dict is not None else self.src_channels
        if slot_conf["is_solid"]: ch_img = Image.new("L", size, int(slot_conf["solid_value"]))
        else: ch_img = active_dict.get(slot_conf["source"], Image.new("L", size, 0)).copy()
        if slot_conf["brightness"] != 100: ch_img = ImageEnhance.Brightness(ch_img).enhance(slot_conf["brightness"]/100.0)
        if slot_conf["contrast"] != 100: ch_img = ImageEnhance.Contrast(ch_img).enhance(slot_conf["contrast"]/100.0)
        if slot_conf.get("is_inverted", False): ch_img = ImageOps.invert(ch_img)
        return ch_img

    def refresh_previews(self):
        if not self.src_image or not (0 <= self.current_output_index < len(self.outputs)): return
        size = self.src_image.size; curr_out = self.outputs[self.current_output_index]
        res_chs = [self.get_processed_ch(curr_out["slots"][c], size) for c in ['R', 'G', 'B', 'A']]
        self.update_img_label(self.lbl_out_preview, Image.merge("RGBA", tuple(res_chs)))
        self.update_img_label(self.lbl_chan_preview, res_chs[['R','G','B','A'].index(self.current_selected_slot)])

    def update_img_label(self, label, pil_img):
        tmp = pil_img.copy(); tmp.thumbnail((label.width(), label.height())); qimg = QImage(tmp.convert("RGBA").tobytes("raw", "RGBA"), tmp.size[0], tmp.size[1], QImage.Format_RGBA8888); label.setPixmap(QPixmap.fromImage(qimg))

    def load_image_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.tga *.bmp)")
        if path: self.load_image_by_path(path)

    def load_image_by_path(self, path):
        try:
            self.src_image_path = path; self.src_image = Image.open(path).convert("RGBA")
            chs = self.src_image.split(); self.src_channels = {'R': chs[0], 'G': chs[1], 'B': chs[2], 'A': chs[3]}
            self.update_img_label(self.lbl_src_preview, self.src_image); self.refresh_previews()
            if not self.output_dir: self.output_dir = os.path.dirname(path); self.lbl_path_display.setText(f"输出目录: {self.output_dir}")
        except: pass

    def select_output_directory(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if d: self.output_dir = d; self.lbl_path_display.setText(f"输出目录: {d}")

    def batch_select_and_run(self):
        folder = QFileDialog.getExistingDirectory(self, "选择源文件夹")
        if folder: self.execute_batch_process(folder)

    def execute_batch_process(self, folder):
        files = []
        for ext in ['*.png', '*.jpg', '*.jpeg', '*.tga', '*.bmp']:
            files.extend(glob.glob(os.path.join(folder, ext)) + glob.glob(os.path.join(folder, ext.upper())))
        if not files: return
        last_dir = None
        for f in files: last_dir = self.export_image(f)
        QMessageBox.information(self, "批量完成", f"已处理 {len(files)} 个文件。")
        if last_dir: self.open_folder(last_dir) 

    def export_image(self, file_path):
        try:
            temp_img = Image.open(file_path).convert("RGBA"); base_name = os.path.splitext(os.path.basename(file_path))[0]
            size = temp_img.size; chs = temp_img.split(); temp_dict = {'R': chs[0], 'G': chs[1], 'B': chs[2], 'A': chs[3]}
            target_dir = self.output_dir if self.output_dir else os.path.dirname(file_path)
            if self.chk_smart_export.isChecked():
                target_dir = os.path.join(target_dir, "Export")
                if not os.path.exists(target_dir): os.makedirs(target_dir)
            for idx, out in enumerate(self.outputs):
                final_chs = [self.get_processed_ch(out["slots"][c], size, temp_dict) for c in ['R', 'G', 'B', 'A']]
                save_name = f"{base_name}_{idx+1}_{out['name']}.png" if self.chk_smart_export.isChecked() else f"{base_name}_{out['name']}.png"
                Image.merge("RGBA", tuple(final_chs)).save(os.path.join(target_dir, save_name))
            return target_dir 
        except: return None

    def open_folder(self, path):
        try:
            if sys.platform == 'win32': os.startfile(path)
            elif sys.platform == 'darwin': subprocess.Popen(['open', path])
            else: subprocess.Popen(['xdg-open', path])
        except: pass

    def handle_chk_click(self): self.save_state(); self.update_data_from_ui_no_history()
    def handle_slider_released(self): self.save_state()
    def add_output_ui(self): self.save_state(); self.create_default_output_data(); self.refresh_list_widget(); self.list_outputs.setCurrentRow(len(self.outputs) - 1)
    def remove_output_ui(self):
        if len(self.outputs) > 1:
            self.save_state(); row = self.list_outputs.currentRow(); del self.outputs[row]
            self.current_output_index = max(0, row-1); self.refresh_list_widget(); self.change_current_output(self.current_output_index)
    def rename_output_final(self):
        if 0 <= self.current_output_index < len(self.outputs):
            new_name = self.edit_name.text()
            if self.outputs[self.current_output_index]["name"] != new_name:
                self.save_state(); self.outputs[self.current_output_index]["name"] = new_name; self.refresh_list_widget()

    # --- 法线模式逻辑修复 ---
    def toggle_normal_mode(self):
        if self.current_output_index < 0: return
        self.save_state()
        current_out = self.outputs[self.current_output_index]
        slots = current_out["slots"]

        if current_out["name"] != "N":
            # 逻辑1：如果名字不是N，改成N，B换纯白
            current_out["name"] = "N"
            slots['B']["is_solid"] = True
            slots['B']["solid_value"] = 255
        else:
            # 逻辑2：如果名字已经是N，B保持纯白，切换G的反转
            slots['B']["is_solid"] = True
            slots['B']["solid_value"] = 255
            slots['G']["is_inverted"] = not slots['G'].get("is_inverted", False)

        # 同步 UI 列表名和数据
        self.refresh_list_widget()
        self.change_current_output(self.current_output_index)

    def split_channels_mode(self):
        self.save_state(); self.outputs = []
        for target in ['R', 'G', 'B', 'A']:
            new_out = {"name": f"{target}", "slots": {}}
            for slot in ['R', 'G', 'B']: new_out["slots"][slot] = {"source": target, "brightness": 100, "contrast": 100, "is_solid": False, "solid_value": 0, "is_inverted": False}
            new_out["slots"]['A'] = {"source": 'A', "brightness": 100, "contrast": 100, "is_solid": True, "solid_value": 255, "is_inverted": False}
            self.outputs.append(new_out)
        self.current_output_index = 0; self.refresh_list_widget(); self.change_current_output(0)

    def process_single(self):
        if not self.src_image_path: return
        target_dir = self.export_image(self.src_image_path)
        QMessageBox.information(self, "成功", "导出完成！")
        if target_dir: self.open_folder(target_dir) 

if __name__ == "__main__":
    app = QApplication(sys.argv); window = TexturePacker(); window.show(); sys.exit(app.exec_())
