import sys
import os
import glob
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QFileDialog, QFrame, QSlider, QGroupBox, 
                             QMessageBox, QSpinBox, QComboBox, QListWidget, QCheckBox, 
                             QAbstractItemView, QListWidgetItem, QTextEdit, QLineEdit,
                             QStackedWidget)
from PyQt5.QtCore import Qt, QMimeData, pyqtSignal, QTimer
from PyQt5.QtGui import QPixmap, QImage, QFont, QDrag
from PIL import Image, ImageEnhance

# ============================================================
# 白色现代主题配置
# ============================================================
STYLE_SHEET = """
QMainWindow { background-color: #FFFFFF; }
QWidget { background-color: #FFFFFF; color: #333333; font-family: "Segoe UI", "Microsoft YaHei"; }

/* 导航栏 */
QFrame#NavFrame { background-color: #F8F9FA; border-bottom: 1px solid #E0E0E0; }

/* 容器面板 */
QGroupBox { 
    border: 1px solid #E0E0E0; border-radius: 8px; 
    margin-top: 1.5em; padding-top: 10px; font-weight: bold;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }

/* 输入组件 */
QLineEdit, QTextEdit, QListWidget { 
    background-color: #FFFFFF; border: 1px solid #D1D1D1; border-radius: 4px; padding: 5px; color: #333333;
}
QListWidget::item:selected { background-color: #E3F2FD; color: #1976D2; }
QComboBox { 
    background-color: #FFFFFF; border: 1px solid #D1D1D1; border-radius: 4px; padding: 3px 10px; 
}

/* 按钮样式 */
QPushButton { 
    background-color: #F0F0F0; border: 1px solid #D1D1D1; border-radius: 4px; padding: 8px 15px; color: #333333;
}
QPushButton:hover { background-color: #E5E5E5; }
QPushButton#PrimaryBtn { background-color: #0078D4; color: white; border: none; }
QPushButton#PrimaryBtn:hover { background-color: #006CBD; }
QPushButton#AccentBtn { background-color: #F57C00; color: white; border: none; }

/* 滑块 */
QSlider::groove:horizontal { border: 1px solid #D1D1D1; height: 6px; background: #F0F0F0; border-radius: 3px; }
QSlider::handle:horizontal { 
    background: #0078D4; border: 1px solid #0078D4; width: 16px; height: 16px; 
    margin: -6px 0; border-radius: 8px; 
}

/* 预览图区域 */
QLabel#PreviewArea { background-color: #FDFDFD; border: 1px solid #E0E0E0; border-radius: 4px; }
"""

# 通道颜色定义
COLORS = {
    'R': {"main": "#D32F2F", "bg": "#FFEBEE"}, 
    'G': {"main": "#388E3C", "bg": "#E8F5E9"}, 
    'B': {"main": "#1976D2", "bg": "#E3F2FD"}, 
    'A': {"main": "#616161", "bg": "#F5F5F5"}
}

# ============================================================
# 辅助组件
# ============================================================

class FileLibraryList(QListWidget):
    files_updated = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True); self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
    def dragEnterEvent(self, e): e.accept() if e.mimeData().hasUrls() else e.ignore()
    def dragMoveEvent(self, e): e.accept() if e.mimeData().hasUrls() else e.ignore()
    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            for url in e.mimeData().urls():
                path = url.toLocalFile()
                if os.path.isdir(path):
                    for ext in ['*.png', '*.jpg', '*.tga', '*.bmp', '*.jpeg', '*.tif']:
                        self.add_paths(glob.glob(os.path.join(path, ext)))
                else: self.add_paths([path])
            self.files_updated.emit(); e.accept()
    def add_paths(self, paths):
        for p in paths:
            if not p.lower().endswith(('.png', '.jpg', '.jpeg', '.tga', '.bmp', '.tif')): continue
            if not any(self.item(i).data(Qt.UserRole) == p for i in range(self.count())):
                item = QListWidgetItem(os.path.basename(p)); item.setData(Qt.UserRole, p); self.addItem(item)
    def startDrag(self, actions):
        item = self.currentItem()
        if item:
            drag = QDrag(self); mime = QMimeData(); mime.setText(item.data(Qt.UserRole))
            drag.setMimeData(mime); drag.exec_(Qt.CopyAction)

class PackerSlot(QGroupBox):
    rule_changed = pyqtSignal()
    def __init__(self, ch_name):
        super().__init__(f"{ch_name} 通道")
        self.ch_name = ch_name; self.is_batch = False
        self.fixed_path = None; self.match_suffix = None
        self.setAcceptDrops(True)
        # 为不同通道设置标题颜色
        self.setStyleSheet(f"QGroupBox::title {{ color: {COLORS[self.ch_name]['main']}; }}")
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        self.lbl_status = QLabel("纯色填充"); self.lbl_status.setFixedSize(160, 55); self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet(f"border: 2px dashed #D1D1D1; border-radius:6px; color:#999; background:#FAFAFA;")
        
        self.combo_src = QComboBox(); self.combo_src.addItems(["填充", "R", "G", "B", "A"])
        self.combo_src.currentIndexChanged.connect(self.rule_changed.emit)
        
        self.sld_val = QSlider(Qt.Horizontal); self.sld_val.setRange(0, 255)
        self.sld_val.setValue(255 if self.ch_name == 'A' else 0)
        self.sld_val.setStyleSheet(f"QSlider::handle:horizontal {{ background: {COLORS[self.ch_name]['main']}; border: 1px solid {COLORS[self.ch_name]['main']}; }}")
        self.sld_val.valueChanged.connect(self.rule_changed.emit)
        
        layout.addWidget(self.lbl_status, 0, Qt.AlignCenter); layout.addWidget(self.combo_src); layout.addWidget(self.sld_val)

    def set_batch_mode(self, enabled): self.is_batch = enabled; self.update_display()
    def dragEnterEvent(self, e): e.accept() if e.mimeData().hasText() else e.ignore()
    def dropEvent(self, e):
        path = e.mimeData().text()
        if self.is_batch:
            fname = os.path.basename(path).split(".")[0]
            if "_" in fname: self.match_suffix = "_" + fname.split("_")[-1]; self.combo_src.setCurrentIndex(1)
        else: self.fixed_path = path; self.combo_src.setCurrentIndex(1)
        self.update_display(); self.rule_changed.emit(); e.accept()

    def update_display(self):
        text = self.match_suffix if self.is_batch else (os.path.basename(self.fixed_path) if self.fixed_path else "纯色填充")
        c = COLORS[self.ch_name]
        self.lbl_status.setText(text)
        if self.fixed_path or self.match_suffix:
            self.lbl_status.setStyleSheet(f"border: 2px solid {c['main']}; border-radius:6px; background:{c['bg']}; color:{c['main']}; font-weight:bold;")
        else:
            self.lbl_status.setStyleSheet(f"border: 2px dashed #D1D1D1; border-radius:6px; color:#999; background:#FAFAFA;")

    def get_data(self, size, fmap=None):
        m = self.combo_src.currentIndex()
        if m == 0: return Image.new("L", size, self.sld_val.value())
        p = fmap.get(self.match_suffix) if (self.is_batch and fmap) else self.fixed_path
        if p and os.path.exists(p):
            with Image.open(p).convert("RGBA") as img:
                return img.resize(size, Image.LANCZOS).split()[m - 1]
        return Image.new("L", size, self.sld_val.value())

class DraggableBtn(QLabel):
    def __init__(self, text, ch_type):
        super().__init__(text)
        self.ch_type = ch_type; self.setAlignment(Qt.AlignCenter); self.setFixedSize(110, 38)
        self.setStyleSheet(f"background:#FFFFFF; color:{COLORS[ch_type]['main']}; border:1px solid {COLORS[ch_type]['main']}; border-radius:4px; font-weight:bold;")
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            drag = QDrag(self); mime = QMimeData(); mime.setText(self.ch_type)
            drag.setMimeData(mime); drag.exec_(Qt.CopyAction)

class AdjusterSlot(QLabel):
    clicked = pyqtSignal(str); data_changed = pyqtSignal()
    def __init__(self, ch_name):
        super().__init__()
        self.ch_name = ch_name; self.source_ch = ch_name; self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter); self.setFixedSize(95, 95); self.update_style(); self.update_display()
    def update_style(self, sel=False):
        c = COLORS[self.ch_name]
        border = f"2px solid {c['main']}" if sel else "1px solid #E0E0E0"
        bg = c['bg'] if sel else "#FFFFFF"
        self.setStyleSheet(f"background:{bg}; border:{border}; border-radius:8px;")
    def dragEnterEvent(self, e): e.accept() if e.mimeData().hasText() else e.ignore()
    def dropEvent(self, e):
        self.source_ch = e.mimeData().text(); self.data_changed.emit(); e.accept()
    def mousePressEvent(self, e): self.clicked.emit(self.ch_name)
    def update_display(self):
        self.setText(f"<small>{self.ch_name} 目标</small><br><b style='color:{COLORS[self.source_ch]['main']}; font-size:16px;'>{self.source_ch}</b>")

# ============================================================
# 面板与主逻辑（保持原有功能）
# ============================================================

class AdjusterPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True); self.src_img = None; self.src_chs = {}; self.outputs = []
        self.curr_idx = -1; self.curr_ch = 'R'; self.normal_state = 0
        self.init_ui(); self.add_out()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25); layout.setSpacing(25)
        left = QVBoxLayout(); left.setSpacing(15)
        self.lbl_src = QLabel("拖入原图"); self.lbl_src.setObjectName("PreviewArea")
        self.lbl_src.setFixedSize(280, 280); self.lbl_src.setAlignment(Qt.AlignCenter)
        left.addWidget(self.lbl_src)
        for c in ['R','G','B','A']: left.addWidget(DraggableBtn(f"源 {c} 通道", c))
        left.addStretch(); layout.addLayout(left)
        mid = QVBoxLayout(); mid.setSpacing(15)
        self.lbl_pre = QLabel("合并预览"); self.lbl_pre.setObjectName("PreviewArea")
        self.lbl_pre.setFixedSize(400, 400); self.lbl_pre.setAlignment(Qt.AlignCenter)
        mid.addWidget(self.lbl_pre)
        btn_h = QHBoxLayout(); btn_h.setSpacing(5)
        b_add = QPushButton("＋新建"); b_del = QPushButton("－删除")
        b_nor = QPushButton("Normal模式"); b_rgba = QPushButton("一键 RGBA 分离")
        for b in [b_add, b_del, b_nor, b_rgba]: b.setFixedHeight(32)
        btn_h.addWidget(b_add); btn_h.addWidget(b_del); btn_h.addWidget(b_nor); btn_h.addWidget(b_rgba)
        b_add.clicked.connect(self.add_out); b_del.clicked.connect(self.del_out)
        b_nor.clicked.connect(self.toggle_nor); b_rgba.clicked.connect(self.one_key_rgba)
        mid.addLayout(btn_h)
        self.list_w = QListWidget(); self.list_w.setFixedHeight(120)
        self.list_w.currentRowChanged.connect(self.switch_out)
        self.edit_name = QLineEdit(); self.edit_name.setPlaceholderText("方案名称...")
        self.edit_name.editingFinished.connect(self.rename_out)
        mid.addWidget(self.list_w); mid.addWidget(self.edit_name)
        slot_h = QHBoxLayout(); slot_h.setSpacing(10); self.slot_ws = {}
        for c in ['R','G','B','A']:
            sw = AdjusterSlot(c); sw.clicked.connect(self.select_slot); sw.data_changed.connect(self.on_drop)
            self.slot_ws[c] = sw; slot_h.addWidget(sw)
        mid.addLayout(slot_h); layout.addLayout(mid)
        right = QVBoxLayout(); right.setSpacing(15)
        self.lbl_ch_v = QLabel("通道预览"); self.lbl_ch_v.setObjectName("PreviewArea")
        self.lbl_ch_v.setFixedSize(400, 400); self.lbl_ch_v.setAlignment(Qt.AlignCenter)
        right.addWidget(self.lbl_ch_v)
        param_box = QGroupBox("选中通道参数")
        p_layout = QVBoxLayout(param_box); p_layout.setSpacing(8)
        self.chk_solid = QCheckBox("填充纯色模式"); self.chk_solid.clicked.connect(self.sync)
        self.sld_s = QSlider(Qt.Horizontal); self.sld_s.setRange(0, 255); self.sld_s.valueChanged.connect(self.sync)
        self.sld_b = QSlider(Qt.Horizontal); self.sld_b.setRange(0, 200); self.sld_b.setValue(100); self.sld_b.valueChanged.connect(self.sync)
        self.sld_c = QSlider(Qt.Horizontal); self.sld_c.setRange(0, 200); self.sld_c.setValue(100); self.sld_c.valueChanged.connect(self.sync)
        p_layout.addWidget(self.chk_solid); p_layout.addWidget(QLabel("灰度值:")); p_layout.addWidget(self.sld_s)
        p_layout.addWidget(QLabel("亮度:")); p_layout.addWidget(self.sld_b); p_layout.addWidget(QLabel("对比度:")); p_layout.addWidget(self.sld_c)
        right.addWidget(param_box)
        self.chk_smart = QCheckBox("智能命名 / Export 文件夹"); self.chk_smart.setChecked(True)
        btn_e = QPushButton("执行当前导出"); btn_e.setObjectName("PrimaryBtn"); btn_e.setFixedHeight(45)
        btn_e.clicked.connect(self.export_curr)
        btn_f = QPushButton("批量处理文件夹"); btn_f.setFixedHeight(45)
        btn_f.clicked.connect(self.export_folder)
        right.addStretch(); right.addWidget(self.chk_smart); right.addWidget(btn_e); right.addWidget(btn_f)
        layout.addLayout(right)

    def get_unique_name(self, base_name):
        existing_names = [out["name"] for out in self.outputs]
        if base_name not in existing_names: return base_name
        counter = 1
        while True:
            new_name = f"{base_name}.{counter:03d}"
            if new_name not in existing_names: return new_name
            counter += 1
    def add_out(self, name=None):
        if not name: name = f"Out"
        unique_name = self.get_unique_name(name)
        slots = {c: {"src": c, "b": 100, "c": 100, "is_s": True, "s_v": 255 if c=='A' else 128} for c in ['R','G','B','A']}
        self.outputs.append({"name": unique_name, "slots": slots})
        self.list_w.addItem(unique_name); self.list_w.setCurrentRow(len(self.outputs)-1)
    def del_out(self):
        idx = self.list_w.currentRow()
        if idx >= 0 and len(self.outputs) > 1:
            self.list_w.setCurrentRow(-1); self.outputs.pop(idx); self.list_w.takeItem(idx)
            self.list_w.setCurrentRow(min(idx, len(self.outputs)-1))
        elif len(self.outputs) <= 1: QMessageBox.warning(self, "警告", "必须保留至少一个方案。")
    def one_key_rgba(self):
        for c in ['R','G','B','A']:
            t_name = f"{c}"; u_name = self.get_unique_name(t_name)
            self.add_out(u_name); t = self.outputs[-1]["slots"]
            for o in ['R','G','B']: t[o].update({"src": c, "is_s": False})
            t['A'].update({"is_s": True, "s_v": 255})
        self.refresh()
    def toggle_nor(self):
        if self.curr_idx < 0: return
        self.normal_state = (self.normal_state + 1) % 3; v = [128, 255, 0][self.normal_state]
        self.outputs[self.curr_idx]["slots"]['B'].update({"is_s": True, "s_v": v}); self.select_slot('B')
    def switch_out(self, idx):
        if idx < 0 or idx >= len(self.outputs): self.curr_idx = -1; return
        self.curr_idx = idx; d = self.outputs[idx]; self.edit_name.setText(d["name"])
        for c in ['R','G','B','A']: 
            self.slot_ws[c].source_ch = d["slots"][c]["src"]; self.slot_ws[c].update_display()
        self.select_slot(self.curr_ch)
    def select_slot(self, ch):
        if self.curr_idx < 0: return
        self.curr_ch = ch; conf = self.outputs[self.curr_idx]["slots"][ch]
        for n, w in self.slot_ws.items(): w.update_style(n == ch)
        self.chk_solid.setChecked(conf["is_s"]); self.sld_s.setValue(conf["s_v"])
        self.sld_b.setValue(conf["b"]); self.sld_c.setValue(conf["c"]); self.refresh()
    def on_drop(self):
        if self.curr_idx < 0: return
        self.chk_solid.setChecked(False)
        self.outputs[self.curr_idx]["slots"][self.curr_ch]["src"] = self.slot_ws[self.curr_ch].source_ch
        self.sync()
    def sync(self):
        if self.curr_idx < 0: return
        conf = self.outputs[self.curr_idx]["slots"][self.curr_ch]
        conf.update({"is_s": self.chk_solid.isChecked(), "s_v": self.sld_s.value(), "b": self.sld_b.value(), "c": self.sld_c.value()})
        self.refresh()
    def refresh(self):
        if not self.src_img or self.curr_idx < 0: return
        res = []
        for c in ['R','G','B','A']:
            conf = self.outputs[self.curr_idx]["slots"][c]
            if conf["is_s"]: ch = Image.new("L", self.src_img.size, conf["s_v"])
            else:
                ch = self.src_chs[conf["src"]].copy()
                if conf["b"] != 100: ch = ImageEnhance.Brightness(ch).enhance(conf["b"]/100.0)
                if conf["c"] != 100: ch = ImageEnhance.Contrast(ch).enhance(conf["c"]/100.0)
            res.append(ch)
        self.up_lbl(self.lbl_pre, Image.merge("RGBA", tuple(res)))
        self.up_lbl(self.lbl_ch_v, res[['R','G','B','A'].index(self.curr_ch)])
    def up_lbl(self, lbl, pil):
        t = pil.copy(); t.thumbnail((lbl.width(), lbl.height()))
        q = QImage(t.convert("RGBA").tobytes("raw", "RGBA"), t.size[0], t.size[1], QImage.Format_RGBA8888)
        lbl.setPixmap(QPixmap.fromImage(q))
    def rename_out(self): 
        if self.curr_idx >= 0:
            new_name = self.edit_name.text()
            self.outputs[self.curr_idx]["name"] = new_name
            self.list_w.currentItem().setText(new_name)
    def export_curr(self): 
        if hasattr(self, 'last_p') and self.src_img: self.do_save(self.last_p)
    def export_folder(self):
        f = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if f:
            fs = []
            for e in ['*.png', '*.jpg', '*.tga', '*.bmp']: fs.extend(glob.glob(os.path.join(f, e)))
            for x in fs: self.do_save(x)
            QMessageBox.information(self, "完成", "批量任务结束")
    def do_save(self, p):
        img = Image.open(p).convert("RGBA"); base = os.path.splitext(os.path.basename(p))[0]
        chs = img.split(); d = {'R':chs[0], 'G':chs[1], 'B':chs[2], 'A':chs[3]}
        out_d = os.path.dirname(p)
        if self.chk_smart.isChecked():
            out_d = os.path.join(out_d, "Export")
            if not os.path.exists(out_d): os.makedirs(out_d)
        for i, out in enumerate(self.outputs):
            final = []
            for c in ['R','G','B','A']:
                conf = out["slots"][c]
                if conf["is_s"]: ch = Image.new("L", img.size, conf["s_v"])
                else:
                    ch = d[conf["src"]].copy()
                    if conf["b"] != 100: ch = ImageEnhance.Brightness(ch).enhance(conf["b"]/100.0)
                    if conf["c"] != 100: ch = ImageEnhance.Contrast(ch).enhance(conf["c"]/100.0)
                final.append(ch)
            name = f"{base}_{i+1}_{out['name']}.png" if self.chk_smart.isChecked() else f"{base}_{out['name']}.png"
            Image.merge("RGBA", tuple(final)).save(os.path.join(out_d, name))
    def dragEnterEvent(self, e): e.accept() if e.mimeData().hasUrls() else e.ignore()
    def dropEvent(self, e):
        p = e.mimeData().urls()[0].toLocalFile()
        if p.lower().endswith(('.png', '.jpg', '.tga', '.bmp')):
            self.last_p = p; self.src_img = Image.open(p).convert("RGBA")
            cs = self.src_img.split(); self.src_chs = {'R':cs[0],'G':cs[1],'B':cs[2],'A':cs[3]}
            self.up_lbl(self.lbl_src, self.src_img); self.refresh()

class PackerPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.timer = QTimer(); self.timer.setSingleShot(True); self.timer.timeout.connect(self.render)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25); layout.setSpacing(25)
        left = QVBoxLayout(); left.setSpacing(12)
        left.addWidget(QLabel("<b>导入列表</b>"))
        self.lib = FileLibraryList(); self.lib.files_updated.connect(self.auto_p)
        left.addWidget(self.lib)
        self.chk_batch = QCheckBox("启用批处理模式"); self.chk_batch.toggled.connect(self.toggle)
        left.addWidget(self.chk_batch); layout.addLayout(left, 1)
        mid = QVBoxLayout(); mid.setSpacing(12); self.slots = {}
        for c in ['R','G','B','A']:
            s = PackerSlot(c); s.rule_changed.connect(self.timer.start); self.slots[c] = s; mid.addWidget(s)
        layout.addLayout(mid, 1)
        right = QVBoxLayout(); right.setSpacing(12)
        self.lbl_pre = QLabel("预览"); self.lbl_pre.setObjectName("PreviewArea")
        self.lbl_pre.setFixedSize(450, 450); self.lbl_pre.setAlignment(Qt.AlignCenter)
        self.txt = QTextEdit(); self.txt.setReadOnly(True); self.txt.hide()
        self.edit = QLineEdit(); self.edit.setPlaceholderText("输出路径...")
        btn = QPushButton("导出合并贴图"); btn.setObjectName("PrimaryBtn"); btn.setFixedHeight(50)
        btn.clicked.connect(self.run)
        right.addWidget(self.lbl_pre); right.addWidget(self.txt); right.addWidget(self.edit); right.addWidget(btn)
        layout.addLayout(right, 2)

    def toggle(self, c):
        for s in self.slots.values(): s.set_batch_mode(c)
        self.lbl_pre.setVisible(not c); self.txt.setVisible(c); self.timer.start(50)
    def auto_p(self):
        if self.lib.count() > 0 and not self.edit.text(): self.edit.setText(os.path.dirname(self.lib.item(0).data(Qt.UserRole)))
        self.timer.start(50)
    def render(self):
        if self.chk_batch.isChecked():
            gps = self.get_groups(); self.txt.setHtml(f"任务数: {len(gps)}<br><br>" + "<br>".join([f"• {k}" for k in gps.keys()]))
        else:
            try:
                chs = [self.slots[c].get_data((256, 256)) for c in ['R','G','B','A']]
                img = Image.merge("RGBA", tuple(chs))
                self.lbl_pre.setPixmap(QPixmap.fromImage(QImage(img.tobytes("raw", "RGBA"), 256, 256, QImage.Format_RGBA8888)).scaled(450,450, Qt.KeepAspectRatio))
            except: pass
    def get_groups(self):
        gps = {}; active = [s.match_suffix for s in self.slots.values() if s.match_suffix]
        for i in range(self.lib.count()):
            f = self.lib.item(i).data(Qt.UserRole); n = os.path.basename(f).rsplit(".", 1)[0]
            if "_" in n:
                sfx = "_" + n.split("_")[-1]; pfx = "_".join(n.split("_")[:-1])
                if sfx in active:
                    if pfx not in gps: gps[pfx] = {}
                    gps[pfx][sfx] = f
        return gps
    def run(self):
        base = self.edit.text(); out = os.path.join(base, "Export") if base else "Export"
        if not os.path.exists(out): os.makedirs(out)
        if not self.chk_batch.isChecked():
            chs = [self.slots[c].get_data((2048, 2048)) for c in ['R','G','B','A']]
            Image.merge("RGBA", tuple(chs)).save(os.path.join(out, "Merged.png"))
        else:
            gps = self.get_groups()
            for pfx, fmap in gps.items():
                ref = Image.open(list(fmap.values())[0])
                chs = [self.slots[c].get_data(ref.size, fmap=fmap) for c in ['R','G','B','A']]
                Image.merge("RGBA", tuple(chs)).save(os.path.join(out, f"{pfx}_Packed.png"))
        QMessageBox.information(self, "完成", "处理结束")

class UNFToolMain(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UNF的贴图综合工具")
        self.resize(1350, 920)
        self.setStyleSheet(STYLE_SHEET)
        nav = QFrame(); nav.setObjectName("NavFrame"); nav.setFixedHeight(65)
        l = QHBoxLayout(nav); l.setContentsMargins(25, 0, 25, 0)
        title = QLabel("UNF TEXTURE TOOL")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #0078D4;")
        l.addWidget(title)
        self.btn_sw = QPushButton("➔ 切换至: 通道调节模式"); self.btn_sw.setFixedSize(220, 38)
        self.btn_sw.setObjectName("PrimaryBtn"); self.btn_sw.clicked.connect(self.sw)
        l.addStretch(); l.addWidget(self.btn_sw); self.setMenuWidget(nav)
        self.stk = QStackedWidget(); self.p1 = PackerPanel(); self.p2 = AdjusterPanel()
        self.stk.addWidget(self.p1); self.stk.addWidget(self.p2); self.setCentralWidget(self.stk)

    def sw(self):
        idx = 1 - self.stk.currentIndex(); self.stk.setCurrentIndex(idx)
        if idx == 1:
            self.btn_sw.setText("➔ 切换至: 通道合并模式")
            self.btn_sw.setObjectName("AccentBtn")
        else:
            self.btn_sw.setText("➔ 切换至: 通道调节模式")
            self.btn_sw.setObjectName("PrimaryBtn")
        self.btn_sw.style().unpolish(self.btn_sw)
        self.btn_sw.style().polish(self.btn_sw)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = UNFToolMain(); win.show(); sys.exit(app.exec_())
