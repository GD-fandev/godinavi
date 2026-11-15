"""Researched client HUD rectangles projected using reproduced renderer geometry."""
import math

# Extracted client UI text rectangles; see godinavi3/research/FINDINGS.md.
TEXT = {'DUR_ARMOR_LOW': {'h': 15, 'w': 32, 'x': 1, 'y': 13},
 'DUR_ARMOR_VALUE': {'h': 15, 'w': 36, 'x': -1, 'y': 13},
 'DUR_SHIELD_LOW': {'h': 15, 'w': 32, 'x': 1, 'y': 13},
 'DUR_SHIELD_VALUE': {'h': 15, 'w': 36, 'x': -1, 'y': 13},
 'DUR_WEAPON_LOW': {'h': 15, 'w': 32, 'x': 1, 'y': 13},
 'DUR_WEAPON_VALUE': {'h': 15, 'w': 36, 'x': -1, 'y': 13},
 'MAINHUD_EXP_PERCENT': {'h': 12, 'w': 185, 'x': 3, 'y': 16},
 'MAP_NAME': {'h': 22, 'w': 240, 'x': 8, 'y': 0},
 'MAP_NAME_BOSS': {'h': 22, 'w': 240, 'x': 8, 'y': 0},
 'MAP_POS': {'h': 22, 'w': 58, 'x': 7, 'y': 0},
 'STATUSPOPUP_EXP_PERCENT': {'h': 18, 'w': 58, 'x': 67, 'y': 75}}

def logical_size(size, scale):
    # Native round-half-up followed by AND ~3, minimum 4.
    return tuple(max(4, math.floor(v / scale + 0.5) & ~3) for v in size)

def logical_regions(size, scale, geometry=None):
    w,h = geometry['logical_size'] if geometry else logical_size(size, scale)
    center = int((w-800)/2)
    def text(key, origin):
        r=TEXT[key]; x=origin[0]+r["x"]; y=origin[1]+r["y"]
        return (x,y,x+r["w"],y+r["h"])
    result = {"map":text("MAP_NAME",(58,1)), "coordinates":text("MAP_POS",(58,23)),
              # Status panel origin C+175,H-102; gauge local 107,23 (323x12).
              # Text follows its fill endpoint; include the native 1px text outline.
              "experience?":(center+281,h-80,center+606,h-66),
              "buff":(center+664,h-46,center+685,h-25)}
    for part,x in (("weapon",670),("armor",705),("shield",740)):
        result["durability:"+part]=text("DUR_"+part.upper()+"_VALUE",(center+x,h-90))
        result["icon:"+part]=(center+x,h-90,center+x+34,h-77)
        # Steam LOW branch: same icon at H-140, LOW text (1,13,32,15).
        result["durability_low:"+part]=text("DUR_"+part.upper()+"_LOW",(center+x,h-140))
        result["icon_low:"+part]=(center+x,h-140,center+x+34,h-127)
    return result

def regions(size, scale, geometry=None):
    # The render surface is aligned to four pixels; presentation fills the
    # Win32 client area, which can differ by 1–3 pixels on either axis.
    render = geometry.get('render_size',size) if geometry else size
    sx,sy = scale*size[0]/render[0],scale*size[1]/render[1]
    def project(b):
        return (max(0,min(size[0],math.floor(b[0]*sx))),max(0,min(size[1],math.floor(b[1]*sy))),
                max(0,min(size[0],math.ceil(b[2]*sx))),max(0,min(size[1],math.ceil(b[3]*sy))))
    return {k:project(b) for k,b in logical_regions(size,scale,geometry).items()}
