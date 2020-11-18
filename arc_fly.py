import tkinter as tk
from PIL import ImageTk, Image
import math

class SampleApp(tk.Tk):

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        self.geometry('600x600')

        self.canvas = tk.Canvas(width=600, height=600)
        self.canvas.pack(fill="both", expand=True)

        self.img_raw = Image.open("work/flugzeug.png")
        self.img = ImageTk.PhotoImage(self.img_raw)

    def _create_token(self, coord, color):
        (x, y) = coord
        self.canvas.create_oval(x-5, y-5, x+5, y+5,
                                outline=color, fill=color, tags="token")

    def create(self, fx, fy, tx, ty, d=40):
        self._create_token((fx, fy), "green")  # from
        self._create_token((tx, ty), "pink")   # to


        sx = (fx + tx) / 2 + d * math.sin(math.atan2(ty - fy, tx - fx))
        sy = (fy + ty) / 2 - d * math.cos(math.atan2(ty - fy, tx - fx))

        self.canvas.create_line((fx, fy), (sx, sy), (tx, ty), smooth=True)

        ix = fx / 2 + tx / 2 + d * math.sin(math.atan2(ty - fy, tx - fx)) / 2
        iy =  fy/2 + ty/2 - d * math.cos(math.atan2(ty - fy, tx - fx)) / 2





        # rotation:
        self.img = ImageTk.PhotoImage(self.img_raw
                                      .resize((50, 50), Image.ANTIALIAS)
                                      .rotate(-math.degrees(math.atan2(ty - fy, tx - fx))))
        self.canvas.create_image(50, 50, image=self.img, anchor=tk.CENTER, tags="fly")
        self.canvas.coords(self.canvas.find_withtag("fly"), (ix, iy))





if __name__ == "__main__":
     app = SampleApp()
     app.create(598, 433, 106, 223)
     app.mainloop()

