"""Read client-defined regions; no screenshot templates or position searches."""
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

ASSETS=Path(__file__).parent/'assets'
ICONS={p:np.array(Image.open(ASSETS/f'playmenu8x6_{i}.png').convert('RGBA'))
       for p,i in (('weapon',312),('armor',313),('shield',314))}


def similarity(image, box, template):
    if box[2]<=box[0] or box[3]<=box[1]:
        return 0.0
    sample=np.asarray(image.crop(box).convert('RGB'))
    scores=[]
    # Fractional UI scaling may filter the source texture. Compare both sampling
    # modes at the exact native rectangle; do not search or move the rectangle.
    for interpolation in (cv2.INTER_NEAREST,cv2.INTER_LINEAR):
        scaled=cv2.resize(template,(sample.shape[1],sample.shape[0]),interpolation=interpolation)
        mask=scaled[:,:,3]>=240
        if mask.sum()<8:
            continue
        a=sample[mask].astype(float).ravel(); b=scaled[:,:,:3][mask].astype(float).ravel()
        a-=a.mean(); b-=b.mean()
        denominator=np.linalg.norm(a)*np.linalg.norm(b)
        scores.append(float(np.dot(a,b)/denominator) if denominator>1e-8 else 0.0)
    return max(scores,default=0.0)


def icon_structure_score(image,box,template):
    """Compare low-frequency shape inside opaque pixels at the same fixed ROI."""
    if box[2]<=box[0] or box[3]<=box[1]:
        return 0.0
    sample=np.asarray(image.crop(box).convert('RGB')).astype(float)
    scaled=cv2.resize(template,(sample.shape[1],sample.shape[0]),interpolation=cv2.INTER_LINEAR)
    mask=cv2.erode((scaled[:,:,3]>=240).astype('uint8'),np.ones((3,3),np.uint8)).astype(bool)
    if mask.sum()<8:
        return 0.0
    a=cv2.GaussianBlur(sample,(0,0),1)[mask].ravel()
    b=cv2.GaussianBlur(scaled[:,:,:3].astype(float),(0,0),1)[mask].ravel()
    a-=a.mean();b-=b.mean()
    denominator=np.linalg.norm(a)*np.linalg.norm(b)
    return float(np.dot(a,b)/denominator) if denominator>1e-8 else 0.0


def icon_color_error(image,box,template):
    """Absolute RGB evidence, at the same fixed ROI as the shape comparison."""
    if box[2]<=box[0] or box[3]<=box[1]:
        return 1.0
    sample=np.asarray(image.crop(box).convert('RGB')).astype(float)
    scaled=cv2.resize(template,(sample.shape[1],sample.shape[0]),interpolation=cv2.INTER_LINEAR)
    mask=cv2.erode((scaled[:,:,3]>=240).astype('uint8'),np.ones((3,3),np.uint8)).astype(bool)
    if mask.sum()<8:
        return 1.0
    a=cv2.GaussianBlur(sample,(0,0),1)
    b=cv2.GaussianBlur(scaled[:,:,:3].astype(float),(0,0),1)
    return float(np.mean(np.abs(a[mask]-b[mask]))/255)
