import sys
import os
import shutil
import mimetypes
from pathlib import Path
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QCheckBox,
    QFileDialog, QTextEdit, QListWidget, QListWidgetItem,
    QInputDialog, QMessageBox, QLabel, QDialog, QDialogButtonBox
)

# ========== CATEGORIES (edit to add more) ==========
# Folder names can use "/" to create a clean hierarchy under the selected folder.
CATEGORIES = {
    "Code/Python": [".py", ".pyw", ".pyi", ".ipynb"],
    "Code/Web": [".html", ".htm", ".css", ".js", ".json", ".ts", ".tsx"],
    "Code/Shell": [".sh", ".zsh", ".bash", ".ps1", ".bat", ".cmd"],
    "Code/Config": [".ini", ".cfg", ".conf", ".yaml", ".yml", ".env", ".toml"],

    "Media/Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".ico", ".heic"],
    "Media/Videos": [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v"],
    "Media/Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],

    "Documents/PDF": [".pdf"],
    "Documents/Office": [".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".odt", ".ods", ".odp"],
    "Documents/Text": [".txt", ".rtf", ".md", ".log", ".csv"],

    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tgz"],

    "Disk Images": [".iso", ".img", ".dmg"],
    "Software/Packages": [".deb", ".rpm", ".apk", ".msi"],
    "Software/Executables": [".exe"],

    "Databases": [".sql", ".db", ".sqlite", ".sqlite3"],
    "Fonts": [".ttf", ".otf", ".woff", ".woff2"],
    "Torrents": [".torrent"],
}

COMPOUND_EXTENSIONS = {
    ".tar.gz": "Archives",
    ".tar.bz2": "Archives",
    ".tar.xz": "Archives",
}


def _build_extension_map(categories: dict) -> dict:
    ext_map = {}
    for category, extensions in categories.items():
        for ext in extensions:
            ext_map[ext.lower()] = category
    return ext_map


EXT_TO_CATEGORY = _build_extension_map(CATEGORIES)


def _guess_category(filename: str) -> str | None:
    lower_name = filename.lower()
    for compound_ext, category in COMPOUND_EXTENSIONS.items():
        if lower_name.endswith(compound_ext):
            return category

    ext = Path(lower_name).suffix
    if ext in EXT_TO_CATEGORY:
        return EXT_TO_CATEGORY[ext]

    mime, _ = mimetypes.guess_type(lower_name)
    if not mime:
        return None

    if mime.startswith("image/"):
        return "Media/Images"
    if mime.startswith("video/"):
        return "Media/Videos"
    if mime.startswith("audio/"):
        return "Media/Audio"
    if mime == "application/pdf":
        return "Documents/PDF"
    if mime in {"application/zip", "application/x-tar", "application/gzip"}:
        return "Archives"
    if mime.startswith("text/"):
        return "Documents/Text"

    return None


def _unique_destination_path(dst: Path) -> Path:
    if not dst.exists():
        return dst

    stem = dst.stem
    suffix = dst.suffix
    parent = dst.parent
    n = 1
    while True:
        candidate = parent / f"{stem} ({n}){suffix}"
        if not candidate.exists():
            return candidate
        n += 1

# ========== MAIN WINDOW ==========
class FileOrganizer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Professional File Organizer")
        self.setGeometry(300, 200, 700, 500)

        self.folder_path = ""
        self.unknown_files = []   # list of filenames
        self.last_moves = []  # list of (src, dst) for Undo
        self.unknown_dialog = None

        # UI elements
        self.log = QTextEdit()
        self.log.setReadOnly(True)

        self.select_btn = QPushButton("📁 Select Folder")
        self.select_btn.clicked.connect(self.select_folder)

        self.preview_btn = QPushButton("👁 Preview")
        self.preview_btn.clicked.connect(self.preview_changes)

        self.organize_btn = QPushButton("🚀 Organize Files")
        self.organize_btn.clicked.connect(self.organize_files)

        self.undo_btn = QPushButton("↩ Undo Last Run")
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self.undo_last_run)

        self.recursive_cb = QCheckBox("Include subfolders (recursive)")
        self.confirm_cb = QCheckBox("Confirm before moving")
        self.confirm_cb.setChecked(True)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<h2>Smart File Organizer</h2>"))
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.select_btn)
        btn_row.addWidget(self.preview_btn)
        btn_row.addWidget(self.organize_btn)
        btn_row.addWidget(self.undo_btn)
        layout.addLayout(btn_row)

        opt_row = QHBoxLayout()
        opt_row.addWidget(self.recursive_cb)
        opt_row.addWidget(self.confirm_cb)
        layout.addLayout(opt_row)

        layout.addWidget(QLabel("<b>Activity Log:</b>"))
        layout.addWidget(self.log)

        self.setLayout(layout)

        self.setStyleSheet("""
            QWidget {
                background: #0f172a;
                color: #e5e7eb;
                font-family: "Noto Sans", "DejaVu Sans", Arial;
                font-size: 13px;
            }
            QLabel {
                color: #e5e7eb;
            }
            QPushButton {
                background-color: #1d4ed8;
                border: 1px solid #2563eb;
                border-radius: 8px;
                padding: 10px 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1e40af;
                border-color: #1d4ed8;
            }
            QPushButton:disabled {
                background-color: #334155;
                border-color: #334155;
                color: #94a3b8;
            }
            QTextEdit, QListWidget {
                background-color: #0b1220;
                border: 1px solid #1f2937;
                border-radius: 10px;
                padding: 10px;
                color: #e5e7eb;
            }
            QCheckBox {
                spacing: 8px;
            }
        """)

    # ---------- Step 1: Select Folder ----------
    def select_folder(self):
        self.folder_path = QFileDialog.getExistingDirectory(self, "Select Folder to Organize")
        if self.folder_path:
            self.log.append(f"✅ Selected folder: {self.folder_path}")

    def _category_root_names(self) -> set[str]:
        # Root folders created by our category hierarchy, e.g. "Media" from "Media/Images".
        roots = {cat.split("/", 1)[0] for cat in CATEGORIES.keys()}
        # Backward-compatible skips for older simple folders users may already have.
        roots |= {"Images", "Videos", "Audio", "Python", "Web", "Documents", "Executables", "Archives"}
        return roots

    def _build_move_plan(self):
        if not self.folder_path:
            raise RuntimeError("No folder selected")

        base = Path(self.folder_path)
        recursive = self.recursive_cb.isChecked()

        moves = []  # list of (src_path, dst_path, category)
        unknown = []

        if not recursive:
            for entry in os.scandir(base):
                if entry.is_dir(follow_symlinks=False):
                    continue
                if not entry.is_file(follow_symlinks=False):
                    continue
                category = _guess_category(entry.name)
                if category:
                    dst_dir = base / category
                    dst = _unique_destination_path(dst_dir / entry.name)
                    moves.append((Path(entry.path), dst, category))
                else:
                    unknown.append(entry.name)
            return moves, unknown

        skip_roots = self._category_root_names()
        for root, dirnames, filenames in os.walk(base):
            # Prevent recursion into already-organized roots (or pre-existing similarly named folders).
            if Path(root) == base:
                dirnames[:] = [d for d in dirnames if d not in skip_roots]

            for fname in filenames:
                src = Path(root) / fname
                if not src.is_file():
                    continue
                category = _guess_category(fname)
                if category:
                    dst_dir = base / category
                    dst = _unique_destination_path(dst_dir / fname)
                    # Skip no-op moves when file already lives there.
                    if src.resolve().parent == dst_dir.resolve():
                        continue
                    moves.append((src, dst, category))
                else:
                    unknown.append(str(src.relative_to(base)))

        return moves, unknown

    def preview_changes(self):
        if not self.folder_path:
            QMessageBox.warning(self, "No Folder", "Please select a folder first.")
            return

        self.log.clear()
        self.log.append(f"📂 Preview: {self.folder_path}\n")

        try:
            moves, unknown = self._build_move_plan()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        by_category = {}
        for _, _, category in moves:
            by_category[category] = by_category.get(category, 0) + 1

        total = len(moves)
        self.log.append(f"Planned moves: {total}")
        for category in sorted(by_category.keys()):
            self.log.append(f"  - {category}: {by_category[category]}")

        if unknown:
            self.log.append(f"\nUnknown files: {len(unknown)}")
            # Show a short sample to keep the UI responsive.
            for item in unknown[:30]:
                self.log.append(f"  - {item}")
            if len(unknown) > 30:
                self.log.append(f"  ... (+{len(unknown) - 30} more)")

    # ---------- Step 2: Auto-Organize ----------
    def organize_files(self):
        if not self.folder_path:
            QMessageBox.warning(self, "No Folder", "Please select a folder first.")
            return

        self.log.clear()
        self.log.append(f"📂 Scanning: {self.folder_path}\n")

        try:
            moves, unknown_files = self._build_move_plan()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        if not moves and not unknown_files:
            self.log.append("🎉 Nothing to organize.")
            return

        if self.confirm_cb.isChecked() and moves:
            msg = f"Move {len(moves)} file(s) into organized folders?"
            if QMessageBox.question(self, "Confirm", msg, QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
                self.log.append("ℹ️ Canceled. No files were moved.")
                return

        self.last_moves = []

        for src, dst, category in moves:
            try:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dst))
                self.last_moves.append((dst, src))  # store for undo (dst -> original src)
                rel_src = src.name if src.parent == Path(self.folder_path) else str(src.relative_to(self.folder_path))
                self.log.append(f"✔️ Moved: {rel_src} → {category}/")
            except Exception as e:
                self.log.append(f"❌ Error moving {src}: {e}")

        self.undo_btn.setEnabled(bool(self.last_moves))

        # ---------- Step 3: Handle unknown files ----------
        if unknown_files:
            self.unknown_files = unknown_files
            self.log.append(f"\n⚠️ Found {len(unknown_files)} unknown file(s).")
            self.show_unknown_dialog()
        else:
            self.log.append("\n🎉 All files organized! No leftovers.")

    def undo_last_run(self):
        if not self.last_moves:
            return

        if QMessageBox.question(
            self,
            "Undo",
            f"Undo last run ({len(self.last_moves)} move(s))?",
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return

        undone = 0
        for moved_dst, original_src in reversed(self.last_moves):
            try:
                original_src.parent.mkdir(parents=True, exist_ok=True)
                if moved_dst.exists():
                    shutil.move(str(moved_dst), str(original_src))
                    undone += 1
            except Exception as e:
                self.log.append(f"❌ Undo failed for {moved_dst}: {e}")

        self.log.append(f"\n↩ Undone moves: {undone}")
        self.last_moves = []
        self.undo_btn.setEnabled(False)

    # ---------- Step 4: Interactive unknown file handler ----------
    def show_unknown_dialog(self):
        """Opens a dialog where user can assign unknown files to custom folders."""
        dialog = QDialog(self)
        self.unknown_dialog = dialog
        dialog.setWindowTitle("Organize Unknown Files")
        dialog.setMinimumWidth(500)
        dialog.setMinimumHeight(400)

        layout = QVBoxLayout()

        # Instructions
        info = QLabel(
            "<b>These files were not recognized.</b><br>"
            "For each file (or group of files), enter a folder name.<br>"
            "Files will be moved into that folder (created automatically)."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # List of unknown files with checkboxes
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)

        for fname in self.unknown_files:
            item = QListWidgetItem(fname)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.list_widget.addItem(item)

        layout.addWidget(self.list_widget)

        # Buttons
        btn_layout = QHBoxLayout()
        assign_btn = QPushButton("📂 Move Selected to New Folder...")
        assign_btn.clicked.connect(self.move_selected_unknowns)
        skip_btn = QPushButton("❌ Skip (leave files untouched)")
        skip_btn.clicked.connect(dialog.reject)

        btn_layout.addWidget(assign_btn)
        btn_layout.addWidget(skip_btn)

        layout.addLayout(btn_layout)
        dialog.setLayout(layout)

        if dialog.exec_() == QDialog.Rejected:
            self.log.append("\nℹ️ Unknown files were left untouched.")
        self.unknown_dialog = None

    def move_selected_unknowns(self):
        """Gathers selected files, asks for a folder name, and moves them."""
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.text())

        if not selected:
            QMessageBox.information(self, "No Selection", "Please select at least one file.")
            return

        # Ask for folder name
        folder_name, ok = QInputDialog.getText(
            self, "Create Folder",
            f"Enter folder name for {len(selected)} file(s):"
        )

        if not ok or not folder_name.strip():
            return

        folder_name = folder_name.strip()
        target_dir = os.path.join(self.folder_path, folder_name)
        os.makedirs(target_dir, exist_ok=True)

        moved_count = 0
        for fname in selected:
            src = os.path.join(self.folder_path, fname)
            dst = os.path.join(target_dir, fname)
            try:
                shutil.move(src, dst)
                self.log.append(f"📦 Moved: {fname} → {folder_name}/")
                moved_count += 1
                # Remove from unknown list and from list widget
                self.unknown_files.remove(fname)
                # Remove from UI list
                for i in range(self.list_widget.count()):
                    if self.list_widget.item(i).text() == fname:
                        self.list_widget.takeItem(i)
                        break
            except Exception as e:
                self.log.append(f"❌ Error moving {fname}: {e}")

        QMessageBox.information(self, "Done", f"Moved {moved_count} file(s) into '{folder_name}'.")

        # If no unknown files remain, close the dialog
        if not self.unknown_files:
            self.log.append("\n✅ All files have been organized!")
            if getattr(self, "unknown_dialog", None) is not None:
                self.unknown_dialog.accept()
                self.unknown_dialog = None
            QMessageBox.information(self, "Complete", "All files are now organized.")


# ========== RUN ==========
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileOrganizer()
    window.show()
    sys.exit(app.exec_())
