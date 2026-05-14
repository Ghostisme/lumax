"""Configuration for feedback mechanism."""

from pydantic import BaseModel, Field


class FeedbackConfig(BaseModel):
    """Configuration for user feedback on AI responses."""

    enabled: bool = Field(
        default=True,
        description="Whether to enable the feedback mechanism",
    )
    langsmith_sync: bool = Field(
        default=False,
        description="Whether to sync feedback to LangSmith for analytics and model evaluation",
    )
    require_comment_on_negative: bool = Field(
        default=False,
        description="Whether to require a comment when submitting negative feedback",
    )


_feedback_config: FeedbackConfig = FeedbackConfig()


def get_feedback_config() -> FeedbackConfig:
    """Get the current feedback configuration."""
    return _feedback_config


def set_feedback_config(config: FeedbackConfig) -> None:
    """Set the feedback configuration."""
    global _feedback_config
    _feedback_config = config


def load_feedback_config_from_dict(config_dict: dict) -> None:
    """Load feedback configuration from a dictionary."""
    global _feedback_config
    _feedback_config = FeedbackConfig(**config_dict)
