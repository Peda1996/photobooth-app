from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import SettingsConfigDict

from ... import CONFIG_PATH
from ...services.config.baseconfig import BaseConfig


class Common(BaseModel):
    model_config = ConfigDict(title="Allgemein")

    enabled: bool = Field(default=True, description="Fotos nach der Aufnahme auf Helligkeit pruefen und bei Blitzausfall reagieren.")
    dark_mean_below: float = Field(default=18, ge=0, le=255, description="Mittlere Helligkeit (0-255) unter der ein Foto als zu dunkel gilt.")
    bright_mean_above: float = Field(default=240, ge=0, le=255, description="Mittlere Helligkeit (0-255) ueber der ein Foto als ueberbelichtet gilt.")
    failure_after_dark_in_row: int = Field(default=3, ge=1, le=20, description="Anzahl zu dunkler Fotos in Folge, ab der ein Blitzausfall gemeldet wird.")


class Retry(BaseModel):
    model_config = ConfigDict(title="Wiederholung")

    retry_dark: bool = Field(default=True, description="Bei zu dunklem Foto sofort neu aufnehmen (Umgebungslicht-Werte).")
    retry_dark_iso: str = Field(default="Auto", description="ISO fuer den Wiederholungsversuch bei zu dunklem Foto.")
    retry_dark_shutterspeed: str = Field(default="1/60", description="Belichtungszeit fuer den Wiederholungsversuch bei zu dunklem Foto.")

    retry_bright: bool = Field(default=True, description="Bei ueberbelichtetem Foto sofort neu aufnehmen.")
    retry_bright_iso: str = Field(default="100", description="ISO fuer den Wiederholungsversuch bei ueberbelichtetem Foto.")
    retry_bright_shutterspeed: str = Field(default="1/4000", description="Belichtungszeit fuer den Wiederholungsversuch bei ueberbelichtetem Foto.")


class BlitzWacheConfig(BaseConfig):
    model_config = SettingsConfigDict(
        title="Blitz-Wache (Helligkeitskontrolle) Plugin Config",
        json_file=f"{CONFIG_PATH}plugin_blitzwache.json",
        env_prefix="blitzwache-",
    )

    common: Common = Common()
    retry: Retry = Retry()
