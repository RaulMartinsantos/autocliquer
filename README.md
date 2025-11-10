🖱️ Customizable Auto Clicker (Windows)

A simple and customizable Auto Clicker built with Python and Tkinter, allowing users to automate mouse clicks at a specific position and interval.
You can easily configure the click coordinates, the time interval, and whether the program should perform an Alt+Tab action after each click.

🚀 Features

⏰ Customizable click interval (minutes and seconds)

📍 Capture mouse coordinates for precise clicking

🔁 Optional Alt+Tab between clicks

💾 Automatically saves your configuration (config.json)

🖥️ Simple GUI built with Tkinter

⚙️ Hotkey support — start or stop with F8

🧩 Requirements

This script was built for Windows and requires Python 3.8+.

Install Dependencies:
pip install pynput keyboard

🎮 Controls
Action	Shortcut / Button
Start / Pause clicking	F8 or Start button
Open settings	⚙️ button (top-right)
Capture mouse position	“Capture next mouse position” button
Save configuration	“Save” button
Exit program	Close window (X)
🧾 Configuration File

Settings are automatically stored in config.json:

{
  "x": 500,
  "y": 300,
  "minutes": 2,
  "seconds": 10,
  "enable_alt_tab": true
}


You can edit this file manually if needed.

⚠️ Notes

The program uses WinAPI (ctypes) to perform mouse clicks.

It is intended for educational and personal automation purposes only.

Some antivirus software may flag auto-clickers as potentially unsafe — this is a false positive.

🧑‍💻 Author

Developed by: Raul Santos
📅 Version: 1.0
💬 Feel free to modify or improve this project
