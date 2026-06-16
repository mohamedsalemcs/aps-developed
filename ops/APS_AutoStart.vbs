Set sh = CreateObject("WScript.Shell")
sh.Run "powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""D:\APS_final\aps_backend\ops\start_aps.ps1""", 0, False
