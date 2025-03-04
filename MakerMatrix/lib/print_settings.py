import os

class PrintSettings:
    def __init__(
        self,
        margin: float = 0.1,        # margin as a fraction of text dimensions
        font_size: int = 1,         # default starting font size (points)
        font: str = "arial.ttf",    # path to the font file (fonts are in MakerMatrix.fonts)
        text_color: str = "black",  # text color
        label_len: float = None,    # reserved width for the text area (in inches)
        label_size: int = 12,       # label height (in mm) – e.g. 15mm tape
        rotation: float = 0.0,      # rotation for printing (if needed)
        dpi: int = 600,             # dots per inch
        copies: int = 1             # number of copies to print
    ):
        self.margin = margin
        self.font_size = font_size
        # Use absolute path for font file
        self.font = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts", font)
        self.text_color = text_color
        self.label_len = label_len
        self.label_size = label_size
        self.rotation = rotation
        self.dpi = dpi
        self.copies = copies

    def to_dict(self) -> dict:
        return {
            "margin": self.margin,
            "font_size": self.font_size,
            "font": self.font,
            "text_color": self.text_color,
            "label_len": self.label_len,
            "label_size": self.label_size,
            "rotation": self.rotation,
            "dpi": self.dpi,
            "copies": self.copies
        }
