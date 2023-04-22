# Radiant fountain 7.33
# Pixels1 = [202, 783] # Ancient
Pixels1 = [116, 872]
# Dire fountain 7.33
# Pixels2 = [802, 240] # Ancient
Pixels2 = [894, 150]
pixelDistX = abs(Pixels1[0] - Pixels2[0])
pixelDistY = abs(Pixels1[1] - Pixels2[1])

# Radiant Fountain Parser Coords
ParserCoord1 = [8928.000000, 9446.000000]
# Dire Foutain Parser Coords
ParserCoord2 = [23792.000000, 23232.000000]
parserDistX = abs(ParserCoord1[0] - ParserCoord2[0])
parserDistY = abs(ParserCoord1[1] - ParserCoord2[1])

# Scaling ratios between the two schemes
perPixelX = parserDistX/pixelDistX
perPixelY = parserDistY/pixelDistY

maxPixelsX = 1000
maxPixelsY = 1000
# Find the extents of the pixel map
minX = ParserCoord1[0] - Pixels1[0]*perPixelX
maxX = minX + maxPixelsX*perPixelX

# Y starts from the top
minY = ParserCoord1[1] - (maxPixelsY - Pixels1[1])*perPixelY
maxY = minY + maxPixelsY*perPixelY

PIXELMAP_EXTENT = [minX, maxX, minY, maxY]

if __name__ == "__main__":
    print(PIXELMAP_EXTENT)