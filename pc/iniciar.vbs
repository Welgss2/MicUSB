Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
pyw = ""
paths = Split(shell.ExpandEnvironmentStrings("%PATH%"), ";")
For Each folderPath In paths
  folderPath = Replace(folderPath, Chr(34), "")
  candidate = fso.BuildPath(folderPath, "pyw.exe")
  If fso.FileExists(candidate) Then
    pyw = candidate
    Exit For
  End If
Next
If pyw = "" Then WScript.Quit 1
shell.Run Chr(34) & pyw & Chr(34) & " " & Chr(34) & folder & "\micusb.py" & Chr(34), 0, False
