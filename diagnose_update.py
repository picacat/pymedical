# -*- coding: UTF-8 -*-
"""
pymedical 更新問題診斷工具  diagnose_update.py

用法：
    把本檔案放到 pymedical 程式目錄，關閉醫療系統後執行
    （雙擊 diagnose_update.bat，或在命令列輸入 python diagnose_update.py）

    執行完會產生 diagnose_result.txt，請回傳給系統開發人員。

本工具只讀取資訊，不會修改任何檔案。
"""

import ctypes
import datetime
import os
import os.path
import platform
import socket
import subprocess
import sys

IS_WINDOWS = platform.system() == "Windows"
CREATE_NO_WINDOW = 0x08000000 if IS_WINDOWS else 0

BINARY_EXTENSIONS = {".dll", ".pyd", ".ocx"}

DRIVE_TYPES = {
    0: "未知",
    1: "無效的磁碟機",
    2: "卸除式磁碟機",
    3: "本機磁碟機",
    4: "網路磁碟機  <== 多台電腦可能共用同一份程式",
    5: "光碟機",
    6: "RAM 磁碟",
}


class Diagnoser:
    def __init__(self, base_path):
        self.base_path = base_path
        self.git_exe = self._locate_git()
        self.lines = []
        self.summary = []

    # ------------------------------------------------------------------
    def out(self, text=""):
        self.lines.append(text)

    def section(self, title):
        self.out()
        self.out("-" * 62)
        self.out(f" {title}")
        self.out("-" * 62)

    # ------------------------------------------------------------------
    def _locate_git(self):
        for rel in [
            r"PortableGit\bin\git.exe",
            r"PortableGit\cmd\git.exe",
            r"PortableGit\mingw32\bin\git.exe",
            r"PortableGit\mingw64\bin\git.exe",
        ]:
            path = os.path.join(self.base_path, rel.replace("\\", os.sep))
            if os.path.exists(path):
                return path
        return None

    def git(self, args, timeout=180):
        """執行 git 指令，回傳 (成功?, 輸出)"""
        if not self.git_exe:
            return False, "找不到 git.exe"

        try:
            env = os.environ.copy()
            env["GIT_TERMINAL_PROMPT"] = "0"
            env["GIT_ASKPASS"] = "echo"
            env["LC_ALL"] = "C"

            kwargs = {
                "stderr": subprocess.STDOUT,
                "universal_newlines": True,
                "cwd": self.base_path,
                "env": env,
                "timeout": timeout,
            }
            if IS_WINDOWS:
                kwargs["creationflags"] = CREATE_NO_WINDOW

            result = subprocess.check_output([self.git_exe] + args, **kwargs)
            return True, result.strip()
        except subprocess.TimeoutExpired:
            return False, f"逾時 ({timeout} 秒)"
        except subprocess.CalledProcessError as e:
            return False, (e.output or "").strip()
        except Exception as e:
            return False, str(e)

    def git_lines(self, args):
        ok, output = self.git(args)
        if not ok:
            return []
        return [line for line in output.splitlines() if line.strip()]

    # ------------------------------------------------------------------
    # 各項檢查
    # ------------------------------------------------------------------
    def check_environment(self):
        self.section("[0] 基本環境")
        self.out(f"產生時間 : {datetime.datetime.now():%Y-%m-%d %H:%M:%S}")
        self.out(f"電腦名稱 : {socket.gethostname()}")
        self.out(f"使用者   : {os.environ.get('USERNAME') or os.environ.get('USER')}")
        self.out(f"作業系統 : {platform.system()} {platform.release()} ({platform.version()})")
        self.out(f"Python   : {sys.version.split()[0]}  ({sys.executable})")
        self.out(f"程式目錄 : {self.base_path}")

        # 磁碟機類型：判斷是否為多台電腦共用的網路磁碟機
        if IS_WINDOWS:
            if self.base_path.startswith("\\\\"):
                self.out("磁碟機   : UNC 網路路徑  <== 多台電腦可能共用同一份程式")
                self.summary.append("程式放在網路共用路徑上")
            else:
                try:
                    drive = os.path.splitdrive(self.base_path)[0] + "\\"
                    kind = ctypes.windll.kernel32.GetDriveTypeW(drive)
                    self.out(f"磁碟機   : {drive} {DRIVE_TYPES.get(kind, kind)}")
                    if kind == 4:
                        self.summary.append("程式放在網路磁碟機上")
                except Exception as e:
                    self.out(f"磁碟機   : 無法判斷 ({e})")

    def check_git(self):
        self.section("[1] Git 環境")

        if not self.git_exe:
            self.out("找不到 PortableGit，此電腦尚未建立 Git 更新環境。")
            self.summary.append("此電腦沒有 PortableGit")
            return False

        self.out(f"git.exe  : {self.git_exe}")
        ok, version = self.git(["--version"])
        self.out(f"版本     : {version if ok else '無法取得'}")

        if not os.path.exists(os.path.join(self.base_path, ".git")):
            self.out()
            self.out("找不到 .git 目錄，此電腦從未成功建立版本庫。")
            self.out("下次更新將是「全量寫入」，所有檔案都會被覆寫，")
            self.out("包含正在被程式載入的 DLL —— 這正是鎖檔錯誤的常見成因。")
            self.summary.append("沒有 .git 目錄，下次更新會是全量寫入")
            return False

        return True

    def check_versions(self):
        self.section("[2] 版本資訊")

        self.out("正在向 GitHub 取得最新版本...")
        ok, output = self.git(["fetch", "--depth", "1", "origin", "main"])
        if not ok:
            self.out(f"fetch 失敗：{output}")
            self.summary.append("無法連線 GitHub")
            return False
        self.out("fetch 完成")
        self.out()

        ok, head = self.git(["rev-parse", "HEAD"])
        self.out(f"本機版本 : {head if ok else '無 (HEAD 不存在)'}")
        ok, msg = self.git(["log", "-1", "--pretty=%s"])
        self.out(f"           {msg if ok else ''}")

        ok, fetch_head = self.git(["rev-parse", "FETCH_HEAD"])
        self.out(f"雲端版本 : {fetch_head if ok else '無法取得'}")
        ok, msg = self.git(["log", "-1", "--pretty=%s", "FETCH_HEAD"])
        self.out(f"           {msg if ok else ''}")

        return True

    def check_pending_files(self):
        self.section("[3] 待更新的檔案數量   <=== 關鍵指標")

        files = self.git_lines(["diff", "HEAD", "FETCH_HEAD", "--name-only", "--"])
        binaries = [
            f for f in files if os.path.splitext(f)[1].lower() in BINARY_EXTENSIONS
        ]

        self.out(f"待更新檔案 : {len(files)} 個")
        self.out(f"其中二進位 : {len(binaries)} 個")
        self.out()
        self.out("判讀方式：")
        self.out("  個位數到數十個  → 正常")
        self.out("  數百個以上      → 索引與工作目錄脫節，這才是根因")
        self.out()

        if len(files) > 200:
            self.summary.append(
                f"待更新檔案高達 {len(files)} 個 → Git 索引與工作目錄脫節"
            )

        if binaries:
            self.out("待更新的二進位檔：")
            for name in binaries:
                self.out(f"    {name}")
            self.out()

        self.out(f"檔案清單（最多列出 60 個）：")
        for name in files[:60]:
            self.out(f"    {name}")
        if len(files) > 60:
            self.out(f"    ... 另有 {len(files) - 60} 個")

    def check_local_changes(self):
        self.section("[4] 本機被修改過的檔案")

        changes = self.git_lines(["status", "--porcelain"])
        self.out(f"共 {len(changes)} 個")
        self.out()
        for line in changes[:60]:
            self.out(f"    {line}")
        if len(changes) > 60:
            self.out(f"    ... 另有 {len(changes) - 60} 個")

    def check_binaries(self):
        self.section("[5] 二進位檔內容比對   <=== 關鍵指標")
        self.out("比對本機檔案與雲端版本的雜湊值。")
        self.out("相同 = Git 根本不需要覆寫它，鎖定與否都無所謂。")
        self.out()

        tracked = []
        for pattern in ["*.dll", "*.pyd", "*.ocx"]:
            tracked.extend(self.git_lines(["ls-files", pattern]))

        if not tracked:
            self.out("版控中沒有任何二進位檔。")
            self.out("（若 .gitignore 已加入 *.dll 但這裡仍列出檔案，")
            self.out("  代表它們早已被追蹤，.gitignore 對它們無效。）")
            return

        differ = []
        for name in tracked:
            ok_local, local_hash = self.git(["hash-object", name])
            ok_remote, remote_hash = self.git(["rev-parse", f"FETCH_HEAD:{name}"])

            if not ok_local:
                self.out(f"    [讀不到] {name}")
                continue
            if not ok_remote:
                self.out(f"    [雲端無] {name}  (雲端已移除此檔)")
                differ.append(name)
                continue

            if local_hash == remote_hash:
                self.out(f"    [相同]   {name}")
            else:
                self.out(f"    [不同]   {name}")
                self.out(f"             本機: {local_hash}")
                self.out(f"             雲端: {remote_hash}")
                differ.append(name)

        self.out()
        if differ:
            self.summary.append(
                f"{len(differ)} 個二進位檔與雲端版本不同：{', '.join(differ[:5])}"
            )
        else:
            self.out("所有二進位檔內容一致 → Git 不需覆寫它們。")
            self.out("若仍出現鎖檔錯誤，代表問題出在索引，而非 DLL 本身。")

    def check_locked(self):
        self.section("[6] 目前被鎖住的二進位檔")
        self.out("（執行本工具前請先關閉醫療系統）")
        self.out()

        locked = []
        for root, dirs, files in os.walk(self.base_path):
            dirs[:] = [
                d
                for d in dirs
                if d not in {".git", "PortableGit", "_temp", "__pycache__", "tts_cache"}
            ]
            for name in files:
                if os.path.splitext(name)[1].lower() not in BINARY_EXTENSIONS:
                    continue
                path = os.path.join(root, name)
                try:
                    with open(path, "ab"):
                        pass
                except Exception:
                    locked.append(os.path.relpath(path, self.base_path))

        if not locked:
            self.out("沒有任何二進位檔被鎖住。")
        else:
            self.out(f"共 {len(locked)} 個檔案仍被鎖住：")
            for name in locked[:20]:
                self.out(f"    {name}")
            self.summary.append(
                f"醫療系統已關閉，但仍有 {len(locked)} 個二進位檔被鎖住"
                "（可能是其他電腦或健保讀卡機軟體佔用）"
            )

    def check_config(self):
        self.section("[7] Git 本機設定")
        ok, output = self.git(["config", "--list", "--local"])
        self.out(output if ok else "無法取得")

        self.section("[8] .gitignore 內容")
        path = os.path.join(self.base_path, ".gitignore")
        if not os.path.exists(path):
            self.out("（無 .gitignore）")
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                self.out(f.read().strip())
        except Exception as e:
            self.out(f"讀取失敗：{e}")

    def check_log(self):
        self.section("[9] update.log 最後 80 行")
        path = os.path.join(self.base_path, "update.log")
        if not os.path.exists(path):
            self.out("（尚無 update.log）")
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f.readlines()[-80:]:
                    self.out(line.rstrip())
        except Exception as e:
            self.out(f"讀取失敗：{e}")

    # ------------------------------------------------------------------
    def run(self):
        self.out("=" * 62)
        self.out(" pymedical 更新診斷報告")
        self.out("=" * 62)

        self.check_environment()

        if self.check_git():
            if self.check_versions():
                self.check_pending_files()
                self.check_local_changes()
                self.check_binaries()
            self.check_config()

        self.check_locked()
        self.check_log()

        # 摘要放在報告最前面，方便一眼看出問題
        header = ["=" * 62, " 診斷摘要", "=" * 62]
        if self.summary:
            for item in self.summary:
                header.append(f"  * {item}")
        else:
            header.append("  未發現明顯異常。")
        header.append("")

        return "\n".join(header + self.lines)


def main():
    base_path = os.path.dirname(os.path.abspath(__file__))
    print()
    print("  " + "=" * 54)
    print("           pymedical 更新診斷工具")
    print("  " + "=" * 54)
    print()
    print("  正在收集資訊，請稍候...")
    print()

    diagnoser = Diagnoser(base_path)
    try:
        report = diagnoser.run()
    except Exception:
        import traceback

        report = "診斷過程發生錯誤：\n" + traceback.format_exc()

    out_path = os.path.join(base_path, "diagnose_result.txt")
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(report)
    except Exception as e:
        print(f"  無法寫入報告檔案：{e}")
        print(report)
        return 1

    # 摘要直接印在畫面上
    for line in report.splitlines():
        if line.startswith("  *") or line.startswith(" 診斷摘要") or "未發現明顯異常" in line:
            print(f"  {line.strip()}")

    print()
    print("  " + "=" * 54)
    print("  收集完成")
    print()
    print(f"  報告檔案：{out_path}")
    print("  請將這個檔案回傳給系統開發人員。")
    print("  " + "=" * 54)
    print()

    if IS_WINDOWS:
        try:
            os.startfile(out_path)
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    code = main()
    try:
        input("  按 Enter 鍵結束...")
    except Exception:
        pass
    sys.exit(code)
