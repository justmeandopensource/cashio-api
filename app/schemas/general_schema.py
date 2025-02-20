from pydantic import BaseModel

class RegisterResponse(BaseModel):
    message: str
