from PIL import Image
from pathlib import Path

src = Path("assets/icon.png")
dst = Path("assets/icon.ico")

img = Image.open(src).convert("RGBA")
img.save(dst, sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
print(f"saved {dst}")