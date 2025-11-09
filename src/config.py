
from pydantic_settings import BaseSettings
from pydantic import model_validator
from pathlib import Path



class MainSettings(BaseSettings):

    frontend_origin: str
    database_url: str
    debug_db: bool
    docs_url: str | None = "/docs"
    redoc_url: str | None = "/redoc"
    openapi_url: str | None = "/openapi.json"
    environment: str = "development"

    class Config:
        env_file = Path(__file__).parent.parent/'.env'
        extra = "ignore"

    @model_validator(mode="after")
    def disable_docs_in_prod(self):
        if self.environment == "production":
            self.docs_url = None
            self.redoc_url = None
            self.openapi_url = None
        return self


main_settings =  MainSettings()


 
