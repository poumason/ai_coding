from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_SETS_DIR = REPO_ROOT / "data" / "golden_sets"

# langfuse.get_client() and the anthropic SDK read their config straight from
# os.environ, so make sure .env is actually loaded into the process environment
# (not just parsed into the Settings model below) before either is constructed.
load_dotenv(REPO_ROOT / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    langfuse_public_key: str
    langfuse_secret_key: str
    langfuse_host: str = "https://cloud.langfuse.com"

    agent_endpoint: str = ""
    agent_api_key: str = ""

    judge_model: str = "claude-opus-5-5"


def get_settings() -> Settings:
    return Settings()
