Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

strPath = fso.GetParentFolderName(WScript.ScriptFullName)
strBat = strPath & "\launcher.bat"

' Run launcher.bat hidden, wait for it to finish
WshShell.Run Chr(34) & strBat & Chr(34), 0, True

' Cleanup: kill server process using saved PID
strPidFile = strPath & "\data\server.pid"
If fso.FileExists(strPidFile) Then
    Set f = fso.OpenTextFile(strPidFile, 1)
    pid = Trim(f.ReadLine)
    f.Close
    If pid <> "" Then
        WshShell.Run "taskkill /f /pid " & pid & " /t >nul 2>&1", 0, False
    End If
    fso.DeleteFile strPidFile
End If
