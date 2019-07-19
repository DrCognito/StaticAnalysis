from PIL import Image, ImageFont, ImageDraw

# text = 'First'
# font = ImageFont.truetype('arialbd.ttf', 20)
# # width, height = font.getsize(text)
# width, height = (80, 20)

# image1 = Image.new('RGBA', (20, 80), (0, 0, 0, 255))
# draw1 = ImageDraw.Draw(image1)

# image2 = Image.new('RGBA', (width, height), (0, 0, 0, 255))
# draw2 = ImageDraw.Draw(image2)
# offset = font.getsize(text)[0]
# draw2.text(((width - offset)/2, 0), text=text, font=font, fill=(255, 255, 255))


# image2 = image2.rotate(90, expand=1)
# px, py = 0, 0
# sx, sy = image2.size
# image1.paste(image2, (px, py, px + sx, py + sy), image2)

# image1.show()
size=(20, 80)
outline_colour = (255, 255, 255, 255)
background_colour = (255, 255, 255, 255)

out_box = Image.new('RGBA', size, background_colour)
canvas = ImageDraw.Draw(out_box)

canvas.rectangle([(0, 0), (size[0], size[1])], fill=None, outline=outline_colour)

firstPick = False
# Text
if firstPick:
    text = "First"
    text_image = Image.new('RGBA', (size[1], size[0]), (0, 0, 0, 255))
    text_canv = ImageDraw.Draw(text_image)

    font_size = size[0]
    font = ImageFont.truetype('arialbd.ttf', font_size)
    offset = font.getsize(text)[0]
    text_canv.text(((size[1] - offset)/2, 0), text=text,
                    font=font, fill=(255, 255, 255))

    text_image = text_image.rotate(90, expand=1)
    px, py = 0, 0
    sx, sy = text_image.size
    out_box.paste(text_image, (px, py, px + sx, py + sy), text_image)

out_box.show()