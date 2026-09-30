from pydantic import BaseModel, ConfigDict
class ProductIn(BaseModel):
    marketplace:str; external_id:str; title:str; category:str="Geral"; price:float; original_price:float=0; commission_rate:float=0; affiliate_url:str=""
class ProductOut(ProductIn):
    id:int
    model_config=ConfigDict(from_attributes=True)
