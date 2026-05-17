' launch_solar.vbs
' Starts Solar Monitor without showing a console window.
' Place this file in the project root alongside main.py.
' The Task Scheduler points to this file, not to python.exe directly.

Dim oShell
Set oShell = CreateObject("WScript.Shell")

' Change this path if your Python installation is elsewhere.
' Using "pythonw.exe" also works but VBS with wscript is more reliable
' for virtualenv setups.
Dim projectDir
projectDir = "A:\Personal coding\Solar Desktop App"

Dim pythonExe
' Try the venv first, fall back to system Python
Dim venvPython
venvPython = projectDir & "\.venv\Scripts\pythonw.exe"

Dim fso
Set fso = CreateObject("Scripting.FileSystemObject")
If fso.FileExists(venvPython) Then
    pythonExe = venvPython
Else
    ' Fall back to system pythonw (no console window)
    pythonExe = "pythonw.exe"
End If

' 0 = hidden window, False = don't wait for exit
oShell.Run """" & pythonExe & """ """ & projectDir & "\main.py""", 0, False

Set oShell = Nothing
Set fso    = Nothing