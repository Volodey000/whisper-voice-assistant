Set fso = CreateObject("Scripting.FileSystemObject")
currentDir = fso.GetParentFolderName(WScript.ScriptFullName)

Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = currentDir

pythonExe = currentDir & "\.venv\Scripts\pythonw.exe"
If Not fso.FileExists(pythonExe) Then
    pythonExe = currentDir & "\.venv\Scripts\python.exe"
End If

' Проверяем, существует ли .venv и установлены ли все ключевые пакеты (PyQt6, torch, faster_whisper)
needsSetup = False
If Not fso.FileExists(pythonExe) Then
    needsSetup = True
Else
    ' Быстрая проверка работоспособности виртуального окружения и ключевых компонентов
    ret = WshShell.Run("""" & pythonExe & """ -c ""import sys, PyQt6, torch, faster_whisper""", 0, True)
    If ret <> 0 Then
        needsSetup = True
    End If
End If

' Если .venv отсутствует, поврежден или библиотеки еще не установлены — запускаем start_whisper.bat с видимым окном
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
