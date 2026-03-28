Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Get the directory where this VBS file is located
strPath = fso.GetParentFolderName(WScript.ScriptFullName)
strBat = strPath & "\launcher.bat"

' Run launcher.bat hidden (0 = hidden window)
WshShell.Run Chr(34) & strBat & Chr(34), 0, False
