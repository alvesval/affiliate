"""Normalize small profile images and discard EXIF/embedded metadata."""
import io
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_UPLOAD = 3 * 1024 * 1024
MAX_PIXELS = 16_000_000

def normalize_avatar(data: bytes) -> bytes:
    if len(data)>MAX_UPLOAD:
        raise ValueError('Envie uma imagem de até 3 MB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                if source.format not in {'JPEG','PNG','WEBP'}:
                    raise ValueError('Use uma imagem JPG, PNG ou WebP.')
                if source.width*source.height>MAX_PIXELS:
                    raise ValueError('Use uma imagem com até 16 milhões de pixels.')
                image=ImageOps.exif_transpose(source)
                image=ImageOps.fit(image,(256,256),method=Image.Resampling.LANCZOS).convert('RGBA')
                background=Image.new('RGB',image.size,'white')
                background.paste(image,mask=image.getchannel('A'))
                output=io.BytesIO()
                background.save(output,format='JPEG',quality=85,optimize=True)
                return output.getvalue()
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError,Image.DecompressionBombWarning):
        raise ValueError('Não foi possível ler a imagem. Envie um arquivo JPG, PNG ou WebP válido.')
