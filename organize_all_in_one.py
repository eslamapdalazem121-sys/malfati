import argparse
import csv
from datetime import datetime
import hashlib
from pathlib import Path
import shutil
import sys

# ==============================================================================
# الإعدادات الافتراضية (عدّل المسارات حسب جهازك)
# ==============================================================================
DEFAULT_DOWNLOADS_DIR = Path(r"C:\Path\To\Phone_Download")
DEFAULT_BASE_DIR = Path(r"C:\Path\To\Organized_Root")
DEFAULT_LOG_DIR_NAME = Path("01_Quick_Inbox") / "Logs"

# True = إذا شغّلت الملف مباشرة بدون خيارات أوامر تظهر لك قائمة اختيار (معاينة / تنفيذ / خروج)
INTERACTIVE_MENU_WHEN_NO_ARGS = True

# True = نقل الملف المكرر إلى مجلد Duplicates_Check للمراجعة (عند التنفيذ الفعلي)
# False = تخطي الملف المكرر وتركه في مكانه الحالي
MOVE_DUPLICATES_TO_FOLDER = True

# أسماء ملفات محددة بالكامل يتم تجاهلها وعدم تحريكها
IGNORED_EXACT_NAMES: set[str] = {
    "keep_me.txt",
    "desktop.ini",
    "thumbs.db",
}

# كلمات مفتاحية في اسم الملف إذا ظهرت يتم تجاهل الملف وعدم تحريكه
IGNORED_KEYWORDS: tuple[str, ...] = (
    "keep",
    "do_not_move",
    "لا_تنقل",
)

# امتدادات تحميل غير مكتملة أو مؤقتة يتم تجاهلها مؤقتاً
INCOMPLETE_EXTENSIONS = {".crdownload", ".part", ".tmp", ".download"}

EXTENSION_TO_CATEGORY = {
    # 03_Documents
    ".pdf": "Documents",
    ".doc": "Documents",
    ".docx": "Documents",
    ".xls": "Documents",
    ".xlsx": "Documents",
    ".ppt": "Documents",
    ".pptx": "Documents",
    ".txt": "Documents",
    ".csv": "Documents",
    # 04_Media (الصور)
    ".jpg": "Photos",
    ".jpeg": "Photos",
    ".png": "Photos",
    ".webp": "Photos",
    ".gif": "Photos",
    ".heic": "Photos",
    # 04_Media (الفيديو والصوت)
    ".mp4": "Media_Other",
    ".mkv": "Media_Other",
    ".mov": "Media_Other",
    ".avi": "Media_Other",
    ".3gp": "Media_Other",
    ".mp3": "Media_Other",
    ".wav": "Media_Other",
    ".m4a": "Media_Other",
    ".ogg": "Media_Other",
    ".aac": "Media_Other",
    # 05_Installers_Backups
    ".apk": "Installers",
    ".zip": "Backups",
    ".rar": "Backups",
    ".7z": "Backups",
    ".tar": "Backups",
    ".gz": "Backups",
}

SCREENSHOT_KEYWORDS = ("screenshot", "screen_", "لقطة", "شاشة")


# ==============================================================================
# الدوال المساعدة
# ==============================================================================
def now_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_year_month(file_path: Path) -> str:
    timestamp = file_path.stat().st_mtime
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m")


def match_ignored_rule(file_path: Path) -> str | None:
    """يرجع سبب الاستثناء إذا كان الملف مستثنى، وإلا يرجع None."""
    name_lower = file_path.name.lower()

    if name_lower in {n.lower() for n in IGNORED_EXACT_NAMES}:
        return f"اسم مستثنى مطابق ({file_path.name})"

    for kw in IGNORED_KEYWORDS:
        if kw.lower() in name_lower:
            return f"يحتوي على كلمة مستثناة ({kw})"

    return None


def compute_sha256(file_path: Path, chunk_size: int = 1024 * 1024) -> str:
    """يحسب بصمة SHA-256 للملف على أجزاء لتوفير الذاكرة مع الملفات الكبيرة."""
    hasher = hashlib.sha256()
    with file_path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def build_existing_hashes(base_dir: Path) -> dict[str, Path]:
    """يجمع بصمات الملفات الموجودة بالفعل داخل الهيكل المنظم لتسريع المقارنة."""
    hashes: dict[str, Path] = {}
    if not base_dir.exists():
        return hashes

    for existing_file in base_dir.rglob("*"):
        if existing_file.is_file():
            try:
                file_hash = compute_sha256(existing_file)
                hashes.setdefault(file_hash, existing_file)
            except OSError:
                continue
    return hashes


def resolve_download_destination(file_path: Path, base_dir: Path) -> Path:
    ext = file_path.suffix.lower()
    category = EXTENSION_TO_CATEGORY.get(ext, "Inbox")
    name_lower = file_path.name.lower()

    if category == "Photos":
        if any(k in name_lower for k in SCREENSHOT_KEYWORDS):
            return base_dir / "04_Media" / "Screenshots_Temp"
        return base_dir / "04_Media" / "Photos_By_Month" / get_year_month(file_path)

    if category == "Media_Other":
        return base_dir / "04_Media" / "Media_Assets" / get_year_month(file_path)

    if category == "Documents":
        return base_dir / "03_Documents" / get_year_month(file_path)

    if category == "Installers":
        return base_dir / "05_Installers_Backups" / "APK_And_Tools"

    if category == "Backups":
        return base_dir / "05_Installers_Backups" / "Backups"

    return base_dir / "01_Quick_Inbox"


def get_unique_destination(
    dest_folder: Path, file_path: Path, reserved_paths: set[Path] | None = None
) -> Path:
    reserved = reserved_paths or set()
    dest_file = dest_folder / file_path.name
    counter = 1
    while dest_file.exists() or dest_file in reserved:
        dest_file = dest_folder / f"{file_path.stem}_{counter}{file_path.suffix}"
        counter += 1
    return dest_file


def write_csv_log(rows: list[dict[str, str]], log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    run_stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = log_dir / f"organize_log_{run_stamp}.csv"

    fieldnames = ["timestamp", "mode", "status", "file_name", "source_path", "destination", "details"]
    with log_file.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return log_file


# ==============================================================================
# المحرك الرئيسي لفرز وتنظيم الملفات
# ==============================================================================
def organize_downloads(
    downloads_dir: Path,
    base_dir: Path,
    dry_run: bool = True,
    save_log: bool = True,
    log_dir: Path | None = None,
) -> None:
    if not downloads_dir.exists():
        print(f"مجلد التحميلات غير موجود: {downloads_dir}")
        return

    resolved_log_dir = log_dir or (base_dir / DEFAULT_LOG_DIR_NAME)
    mode_label = "DRY_RUN" if dry_run else "LIVE"
    header_text = (
        "وضع المعاينة (DRY RUN - لن يتم تعديل أي ملف)" if dry_run else "وضع التنفيذ الفعلي"
    )
    print(f"=== {header_text} ===")

    if not dry_run:
        base_dir.mkdir(parents=True, exist_ok=True)

    existing_hashes = build_existing_hashes(base_dir)
    reserved_destinations: set[Path] = set()
    log_rows: list[dict[str, str]] = []

    would_move_count = 0
    duplicate_count = 0
    skipped_count = 0
    ignored_count = 0

    for item in downloads_dir.iterdir():
        if not item.is_file():
            continue

        ignore_reason = match_ignored_rule(item)
        if ignore_reason:
            print(f"[مستثنى]: {item.name} ({ignore_reason})")
            ignored_count += 1
            log_rows.append({
                "timestamp": now_timestamp(),
                "mode": mode_label,
                "status": "IGNORED",
                "file_name": item.name,
                "source_path": str(item),
                "destination": "",
                "details": ignore_reason,
            })
            continue

        ext = item.suffix.lower()
        if ext in INCOMPLETE_EXTENSIONS:
            print(f"[تخطي - ملف مؤقت]: {item.name}")
            skipped_count += 1
            log_rows.append({
                "timestamp": now_timestamp(),
                "mode": mode_label,
                "status": "SKIPPED_TEMP",
                "file_name": item.name,
                "source_path": str(item),
                "destination": "",
                "details": f"امتداد تحميل مؤقت ({ext})",
            })
            continue

        item_hash = compute_sha256(item)

        if item_hash in existing_hashes:
            duplicate_count += 1
            original_match = existing_hashes[item_hash]
            dup_folder = base_dir / "01_Quick_Inbox" / "Duplicates_Check"
            dup_dest = get_unique_destination(dup_folder, item, reserved_destinations)

            if MOVE_DUPLICATES_TO_FOLDER:
                reserved_destinations.add(dup_dest)
                action_msg = (
                    f"سيُنقل للمراجعة -> {dup_dest.relative_to(base_dir)}"
                    if dry_run
                    else f"نُقل للمراجعة -> {dup_dest.relative_to(base_dir)}"
                )
                print(
                    f"[مكرر]: {item.name} (مطابق لـ {original_match.relative_to(base_dir)}) | {action_msg}"
                )
                if not dry_run:
                    dup_folder.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(item), str(dup_dest))

                log_rows.append({
                    "timestamp": now_timestamp(),
                    "mode": mode_label,
                    "status": "DUPLICATE_MOVED",
                    "file_name": item.name,
                    "source_path": str(item),
                    "destination": str(dup_dest.relative_to(base_dir)),
                    "details": f"مطابق للمحتوى في {original_match.relative_to(base_dir)}",
                })
            else:
                print(
                    f"[مكرر]: {item.name} (مطابق لـ {original_match.relative_to(base_dir)}) | سيُترك في مكانه"
                )
                log_rows.append({
                    "timestamp": now_timestamp(),
                    "mode": mode_label,
                    "status": "DUPLICATE_SKIPPED",
                    "file_name": item.name,
                    "source_path": str(item),
                    "destination": "",
                    "details": f"مطابق للمحتوى في {original_match.relative_to(base_dir)} (تم تركه)",
                })
            continue

        dest_folder = resolve_download_destination(item, base_dir)
        dest_file = get_unique_destination(dest_folder, item, reserved_destinations)
        reserved_destinations.add(dest_file)
        rel_dest = str(dest_file.relative_to(base_dir))

        would_move_count += 1
        prefix = "سيُنقل" if dry_run else "نُقل"
        print(f"[{prefix}]: {item.name} -> {rel_dest}")

        if not dry_run:
            dest_folder.mkdir(parents=True, exist_ok=True)
            shutil.move(str(item), str(dest_file))
            existing_hashes[item_hash] = dest_file

        log_rows.append({
            "timestamp": now_timestamp(),
            "mode": mode_label,
            "status": "WOULD_MOVE" if dry_run else "MOVED",
            "file_name": item.name,
            "source_path": str(item),
            "destination": rel_dest,
            "details": "تم الفرز بنجاح",
        })

    print("-" * 65)
    summary_verb = "سيُنفّذ" if dry_run else "اكتمل"
    print(
        f"{summary_verb} | للنقل: {would_move_count} | مستثنى: {ignored_count} | مكرر: {duplicate_count} | مؤقت متخطّى: {skipped_count}"
    )

    if save_log:
        log_path = write_csv_log(log_rows, resolved_log_dir)
        print(f"تم حفظ السجل في: {log_path}")


# ==============================================================================
# سطر الأوامر والقائمة التفاعلية
# ==============================================================================
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="فرز وتنظيم ملفات مجلد التحميلات مع كشف التكرار والملفات المؤقتة وحفظ السجل."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_DOWNLOADS_DIR,
        help="مسار مجلد التحميلات المصدر",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=DEFAULT_BASE_DIR,
        help="المسار الجذري للهيكل المنظم",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="تشغيل في وضع المعاينة فقط دون نقل أي ملف",
    )
    mode_group.add_argument(
        "--apply",
        action="store_true",
        help="تنفيذ النقل الفعلي للملفات والمجلدات",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="عدم حفظ ملف سجل CSV لهذه العملية",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=None,
        help="مسار مخصص لحفظ ملفات السجل CSV",
    )
    return parser.parse_args()


def run_interactive_menu(source: Path, target: Path, save_log: bool, log_dir: Path | None) -> None:
    print("=" * 52)
    print("        أداة تنظيم ملفات التحميلات (الكل في كود واحد)")
    print("=" * 52)
    print("1. معاينة فقط (Dry Run - آمن ولا يحرك أي ملف)")
    print("2. تنفيذ فعلي (Apply - نقل الملفات وتحديث الهيكل)")
    print("3. خروج")
    choice = input("\nاختر رقماً (1-3): ").strip()

    if choice == "1":
        organize_downloads(source, target, dry_run=True, save_log=save_log, log_dir=log_dir)
    elif choice == "2":
        organize_downloads(source, target, dry_run=False, save_log=save_log, log_dir=log_dir)
    else:
        print("تم الإلغاء.")


if __name__ == "__main__":
    no_cli_args = len(sys.argv) == 1
    args = parse_args()

    if no_cli_args and INTERACTIVE_MENU_WHEN_NO_ARGS:
        run_interactive_menu(
            source=args.source,
            target=args.target,
            save_log=not args.no_log,
            log_dir=args.log_dir,
        )
    else:
        is_dry_run = not args.apply
        organize_downloads(
            downloads_dir=args.source,
            base_dir=args.target,
            dry_run=is_dry_run,
            save_log=not args.no_log,
            log_dir=args.log_dir,
        )
