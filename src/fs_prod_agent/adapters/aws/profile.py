"""AWS profile switch. Raising here imports no AWS SDK. Fill this in when an account exists."""

from typing import NoReturn


class AwsProfileUnavailable(RuntimeError):
    """build('aws') was called and no AWS or Bedrock account is configured."""


def build_aws() -> NoReturn:
    raise AwsProfileUnavailable(
        "AWS profile is not configured. The local profile runs without an AWS or Bedrock account. "
        "Filling in this function is the switch: AgentCore memory, a Bedrock model, and BedrockAgentCoreApp."
    )
