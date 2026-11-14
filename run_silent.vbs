Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)

Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = currentDir

pythonExe = currentDir & "\.venv\Scripts\pythonw.exe"
If Not fso.FileExists(pythonExe) Then
    pythonExe = currentDir & "\.venv\Scripts\python.exe"
End If

' Проверяем, существует ли .venv и работает ли python на текущем компьютере
needsSetup = False
If Not fso.FileExists(pythonExe) Then
    needsSetup = True
Else
    ' Быстрая проверка работоспособности виртуального окружения (код возврата)
    ret = WshShell.Run("""" & pythonExe & """ -c ""import sys""", 0, True)
    If ret <> 0 Then
        needsSetup = True
    End If
End If

' Если .venv отсутствует или скопирован с другого ПК — запускаем start_whisper.bat для самодиагностики
If needsSetup Then
    WshShell.Run """" & currentDir & "\start_whisper.bat""", 1, False
    WScript.Quit
End If

args = ""
For Each arg In WScript.Arguments
    args = args & " " & arg
Next

cmdLine = """" & pythonExe & """ """ & currentDir & "\main.py""" & args
WshShell.Run cmdLine, 0, False
Set WshShell = Nothing
