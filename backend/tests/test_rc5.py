import ast,io,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.pinterest_cover import normalize_cover
source=ast.parse((Path(__file__).resolve().parents[1]/'app/routers/social.py').read_text())
class HTTPException(Exception):
 def __init__(self,status_code,detail): self.status_code=status_code;self.detail=detail
ns={'HTTPException':HTTPException,'select':MagicMock(),'Publication':MagicMock(),'ContentVariant':MagicMock(),'Product':object}
for name in ['_prepare_copy_edit','_variant']:
 node=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name==name)
 exec(compile(ast.Module(body=[node],type_ignores=[]),'<test>','exec'),ns)
class Tests(unittest.TestCase):
 def test_image_formats(self):
  for fmt in ['PNG','WEBP','JPEG']:
   b=io.BytesIO();Image.new('RGB',(2500,1200),'green').save(b,fmt)
   result=Image.open(io.BytesIO(normalize_cover(b.getvalue())))
   self.assertEqual(result.format,'JPEG');self.assertEqual(result.mode,'RGB');self.assertLessEqual(max(result.size),2000)
 def test_transparency(self):
  b=io.BytesIO();Image.new('RGBA',(10,10),(0,0,0,0)).save(b,'PNG')
  self.assertEqual(Image.open(io.BytesIO(normalize_cover(b.getvalue()))).getpixel((0,0)),(255,255,255))
 def test_bad_image(self):
  with self.assertRaises(ValueError): normalize_cover(b'<html>denied</html>')
 def test_reapproval(self):
  c=SimpleNamespace(id=1,status='approved');v=SimpleNamespace(company_id=1,status='approved');other=SimpleNamespace(status='approved');db=MagicMock();db.scalars.return_value.all.side_effect=[[SimpleNamespace(status='error')],[v,other]]
  ns['_prepare_copy_edit'](v,c,db)
  self.assertEqual((c.status,v.status,other.status),('draft','draft','draft'))
 def test_active_publications_lock(self):
  for status in ['queued','scheduled','publishing','processing','published','sent_to_tiktok']:
   c=SimpleNamespace(id=1,status='approved');db=MagicMock();db.scalars.return_value.all.return_value=[SimpleNamespace(status=status)]
   with self.assertRaises(HTTPException):ns['_prepare_copy_edit'](SimpleNamespace(company_id=1),c,db)
   self.assertEqual(c.status,'approved')
 def test_spoken_copy(self):
  p=SimpleNamespace(title='Tenda Gazebo 3x3',affiliate_url='')
  hook,caption,script,_,_=ns['_variant'](p,'Pinterest',30,'Direto','famílias')
  self.assertIn(p.title,hook);self.assertNotIn('Mostre o produto',script);self.assertNotIn('Tom:',script)
if __name__=='__main__':unittest.main()
