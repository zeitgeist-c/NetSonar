import os
import subprocess
from pathlib import Path

def create_shortcut():
    cwd = Path.cwd().absolute()
    desktop = Path(os.environ["USERPROFILE"]) / "Desktop"
    shortcut_path = desktop / "NetSonar.lnk"
    
    pythonw = cwd / ".venv" / "Scripts" / "pythonw.exe"
    main_py = cwd / "main.py"
    icon_path = cwd / "netsonar.ico"
    
    # PowerShell script to create shortcut
    ps_commands = [
        f'$WshShell = New-Object -ComObject WScript.Shell',
        f'$Shortcut = $WshShell.CreateShortcut("{shortcut_path}")',
        f'$Shortcut.TargetPath = "{pythonw}"',
        f'$Shortcut.Arguments = """{main_py}"""',
        f'$Shortcut.WorkingDirectory = "{cwd}"',
        f'$Shortcut.IconLocation = "{icon_path}"',
        f'$Shortcut.Save()',
        # Set Run as Administrator bit (Offset 21, bit 5)
        f'$bytes = [System.IO.File]::ReadAllBytes("{shortcut_path}")',
        f'$bytes[21] = $bytes[21] -bor 0x20',
        f'[System.IO.File]::WriteAllBytes("{shortcut_path}", $bytes)'
    ]
    
    ps_script = "; ".join(ps_commands)
    
    print(f"Creating shortcut at: {shortcut_path}")
    subprocess.run(["powershell", "-Command", ps_script], check=True)
    print("Shortcut created successfully!")

if __name__ == "__main__":
    create_shortcut()
