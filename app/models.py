from pydantic import BaseModel

class Provider(BaseModel):
    name: str
    client_id:str
    client_secret: str