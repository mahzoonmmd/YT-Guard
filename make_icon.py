import sys
from PyQt6.QtWidgets import QApplication
from ytguard.widgets import make_app_icon
app = QApplication(sys.argv)
make_app_icon(256).save("assets/icon.png")
from PIL import Image
Image.open("assets/icon.png").save("assets/icon.ico", sizes=[(256,256),(128,128),(64,64),(32,32),(16,16)])
print("icon.ico created")
