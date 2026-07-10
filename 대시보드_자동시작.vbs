Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\user\AS자동화\대시보드"
WshShell.Run "cmd /c streamlit run dashboard.py --server.port 8502", 0, False