from pydantic import BaseModel, HttpUrl

class MetadataRequest(BaseModel): 
     url: HttpUrl