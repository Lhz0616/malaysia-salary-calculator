import logging
import os
import subprocess
import sys
import tempfile
import urllib.request

from PySide6.QtCore import QThread, Signal


class UpdateDownloaderThread(QThread):
    """
    Background worker thread to download the installer binary.
    Emits progress signals to update the UI progress bar.
    """
    progress = Signal(int, int)  # (downloaded_bytes, total_bytes)
    download_finished = Signal(str)  # downloaded installer file path
    error_occurred = Signal(str)  # error message

    def __init__(self, download_url: str, parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self._is_cancelled = False

    def cancel(self):
        """Cancel ongoing download."""
        self._is_cancelled = True

    def run(self):
        installer_path = os.path.join(tempfile.gettempdir(), "MalaysianSalaryCalculator_Setup.exe")
        logging.info(f"Starting update download from: {self.download_url}")
        try:
            req = urllib.request.Request(
                self.download_url,
                headers={"User-Agent": "MalaysianPayrollEngine-UpdateDownloader"}
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                total_bytes = int(response.headers.get("Content-Length", 0))
                downloaded_bytes = 0
                chunk_size = 64 * 1024  # 64 KB chunks

                with open(installer_path, "wb") as f:
                    while True:
                        if self._is_cancelled:
                            break
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded_bytes += len(chunk)
                        self.progress.emit(downloaded_bytes, total_bytes)

            if self._is_cancelled:
                logging.info("Update download cancelled by user.")
                if os.path.exists(installer_path):
                    try:
                        os.remove(installer_path)
                    except OSError:
                        pass
                return

            logging.info(f"Update downloaded successfully to {installer_path} ({downloaded_bytes} bytes)")
            self.download_finished.emit(installer_path)
        except Exception as e:
            logging.error(f"Download error: {e}")
            if not self._is_cancelled:
                self.error_occurred.emit(str(e))


def apply_update_and_restart(installer_path: str):
    """
    Launches a fully detached Windows background updater script via ShellExecute that:
    1. Runs independently from the calling application process.
    2. Waits for the current application to release file locks.
    3. Runs the Inno Setup installer silently (UsePreviousAppDir auto-detects install location).
    4. Relaunches the updated application.
    5. Logs all actions to %TEMP%\\msc_updater.log.
    """
    temp_dir = tempfile.gettempdir()
    vbs_path = os.path.join(temp_dir, "msc_update.vbs")
    log_path = os.path.join(temp_dir, "msc_updater.log")

    # Determine the exact path of the currently running software and its directory
    if getattr(sys, "frozen", False):
        target_exe = os.path.abspath(sys.executable)
    else:
        candidate_exe = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "dist", "MalaysianSalaryCalculator", "MalaysianSalaryCalculator.exe"))
        if os.path.exists(candidate_exe):
            target_exe = candidate_exe
        else:
            target_exe = os.path.abspath(sys.executable)

    target_dir = os.path.dirname(target_exe)

    logging.info(f"Applying update: installer={installer_path}, target_exe={target_exe}, target_dir={target_dir}, log={log_path}")

    # Escape double quotes for VBScript literal strings
    escaped_installer = installer_path.replace('"', '""')
    escaped_target_exe = target_exe.replace('"', '""')
    escaped_target_dir = target_dir.replace('"', '""')
    escaped_log_path = log_path.replace('"', '""')

    vbs_content = f"""Option Explicit
Dim WshShell, FSO, logFile
Dim installer, targetExe, targetDir, cmdInstall, exitCode, i

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

On Error Resume Next
Set logFile = FSO.CreateTextFile("{escaped_log_path}", True)
On Error GoTo 0

Sub LogMsg(msg)
    If Not logFile Is Nothing Then
        logFile.WriteLine("[" & Now & "] " & msg)
    End If
End Sub

LogMsg("=== Malaysian Salary Calculator Updater Started ===")
installer = "{escaped_installer}"
targetExe = "{escaped_target_exe}"
targetDir = "{escaped_target_dir}"

LogMsg("Installer: " & installer)
LogMsg("Target Exe: " & targetExe)
LogMsg("Target Dir: " & targetDir)

' 1. Wait for calling application process to completely terminate and release file handles
LogMsg("Waiting for application process to exit...")
WScript.Sleep 2000

' 2. If an existing uninstaller exists in the target directory, run it silently to cleanly remove old files
Dim uninstaller, cmdUninstall
uninstaller = FSO.BuildPath(targetDir, "unins000.exe")
If FSO.FileExists(uninstaller) Then
    LogMsg("Existing installation found. Running uninstaller: " & uninstaller)
    cmdUninstall = Chr(34) & uninstaller & Chr(34) & " /VERYSILENT /SUPPRESSMSGBOXES /NORESTART"
    WshShell.Run cmdUninstall, 0, True
    LogMsg("Previous version uninstalled cleanly.")
    WScript.Sleep 1000
End If

' 3. Run Inno Setup installer silently to install the updated files
If FSO.FileExists(installer) Then
    cmdInstall = Chr(34) & installer & Chr(34) & " /VERYSILENT /SUPPRESSMSGBOXES /FORCECLOSEAPPLICATIONS /DIR=" & Chr(34) & targetDir & Chr(34)
    LogMsg("Executing installer command: " & cmdInstall)
    exitCode = WshShell.Run(cmdInstall, 0, True)
    LogMsg("Installer completed with exit code: " & exitCode)
Else
    LogMsg("ERROR: Installer file not found: " & installer)
End If

WScript.Sleep 1000

' 4. Relaunch the updated application
If targetExe <> "" Then
    For i = 1 To 10
        If FSO.FileExists(targetExe) Then
            LogMsg("Relaunching application: " & targetExe)
            WshShell.CurrentDirectory = targetDir
            WshShell.Run Chr(34) & targetExe & Chr(34), 1, False
            LogMsg("Application relaunch command sent successfully.")
            Exit For
        Else
            LogMsg("Waiting for target exe... attempt " & i)
            WScript.Sleep 500
        End If
    Next
Else
    LogMsg("ERROR: Target exe path is empty.")
End If

' 4. Clean up temporary installer and self
LogMsg("Cleaning up temporary files...")
WScript.Sleep 2000
On Error Resume Next
If FSO.FileExists(installer) Then
    FSO.DeleteFile installer, True
End If
If Not logFile Is Nothing Then
    logFile.Close()
End If
FSO.DeleteFile WScript.ScriptFullName, True
"""

    with open(vbs_path, "w", encoding="utf-8") as f:
        f.write(vbs_content)

    if sys.platform == "win32":
        try:
            os.startfile(vbs_path)
        except Exception as e:
            logging.warning(f"os.startfile failed, falling back to subprocess: {e}")
            flags = getattr(subprocess, "DETACHED_PROCESS", 0x00000008) | getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0x01000000)
            subprocess.Popen(["wscript.exe", "//B", "//Nologo", vbs_path], creationflags=flags)
