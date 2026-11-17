import logging
from pathlib import Path

from PIL import Image

from ...models.genericstats import GenericStats, SubStats
from ...models.stillretry import StillRetry
from .. import hookimpl
from ..base_plugin import BasePlugin

from .config import BlitzWacheConfig

logger = logging.getLogger(__name__)


def image_brightness(file: Path) -> tuple[float, float]:
    """returns (mean brightness 0-255, share of near-black pixels 0-1) based on a downscaled greyscale histogram"""
    with Image.open(file) as img:
        grey = img.convert("L")
        grey.thumbnail((160, 160))
        hist = grey.histogram()
    total = sum(hist) or 1
    mean = sum(level * count for level, count in enumerate(hist)) / total
    dark_share = sum(hist[:10]) / total
    return mean, dark_share


class BlitzWache(BasePlugin[BlitzWacheConfig]):
    def __init__(self):
        super().__init__()
        self._config: BlitzWacheConfig = BlitzWacheConfig()
        self._dark_in_row = 0
        self._last_mean: float | None = None
        self._retries_total = 0
        self._failure = False

    @hookimpl
    def acq_still_check(self, file: Path) -> StillRetry | None:
        if not self._config.common.enabled:
            return None

        try:
            mean, dark_share = image_brightness(file)
        except Exception as exc:
            logger.warning(f"could not analyze brightness of {file}: {exc}")
            return None

        self._last_mean = mean
        logger.info(f"brightness check: mean={mean:.1f}, dark pixels={dark_share:.0%}")

        if mean < self._config.common.dark_mean_below:
            self._dark_in_row += 1
            if self._dark_in_row >= self._config.common.failure_after_dark_in_row and not self._failure:
                self._failure = True
                logger.error(f"BLITZAUSFALL? {self._dark_in_row} zu dunkle Fotos in Folge. Bitte Blitz pruefen!")
            if self._config.retry.retry_dark:
                self._retries_total += 1
                return StillRetry(
                    parameters={"iso": self._config.retry.retry_dark_iso, "shutterspeed": self._config.retry.retry_dark_shutterspeed},
                    reason=f"Foto zu dunkel (Helligkeit {mean:.1f}), Blitz evtl. ausgefallen",
                )
            return None

        # photo is fine or only overexposed: dark streak ends, failure state resolved
        self._dark_in_row = 0
        self._failure = False

        if mean > self._config.common.bright_mean_above and self._config.retry.retry_bright:
            self._retries_total += 1
            return StillRetry(
                parameters={"iso": self._config.retry.retry_bright_iso, "shutterspeed": self._config.retry.retry_bright_shutterspeed},
                reason=f"Foto ueberbelichtet (Helligkeit {mean:.1f})",
            )
        return None

    @hookimpl
    def get_stats(self) -> GenericStats | None:
        return GenericStats(
            id="blitz_wache",
            name="Blitz-Wache",
            stats=[
                SubStats("Status", "BLITZAUSFALL?" if self._failure else "ok"),
                SubStats("Zu dunkle Fotos in Folge", self._dark_in_row),
                SubStats("Letzte Helligkeit", self._last_mean, decimals=1),
                SubStats("Wiederholungen gesamt", self._retries_total),
            ],
        )
