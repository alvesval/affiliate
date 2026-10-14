"""Normalize stored real product references before Pinterest publication."""
import io
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError

def normalize_cover(data: bytes) -> bytes:
    if not data or len(data)>20*1024*1024:
        raise ValueError('A capa deve ser uma imagem de até 20 MB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.width*image.height>40000000:
                    raise ValueError('A capa excede 40 milhões de pixels.')
                image.seek(0)
                image=ImageOps.exif_transpose(image).convert('RGBA')
                image.thumbnail((2000,2000),Image.Resampling.LANCZOS)
                canvas=Image.new('RGB',image.size,'white')
                canvas.paste(image,mask=image.getchannel('A'))
                out=io.BytesIO()
                canvas.save(out,format='JPEG',quality=90,optimize=True)
                return out.getvalue()
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError,Image.DecompressionBombWarning) as exc:
        raise ValueError('Não foi possível ler a capa. Envie uma foto real em JPEG, PNG ou WebP.') from exc
