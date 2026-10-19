from lma_agent import config


def test_config_values():
    assert config.BASE_URL == "https://api.groq.com/openai/v1"
    assert config.MODEL == "openai/gpt-oss-120b"
    assert config.MAX_STEPS == 15
    assert config.TEMPERATURE == 0.0
    assert config.MAX_RETRIES == 3
    assert isinstance(config.GROQ_API_KEY, str)
