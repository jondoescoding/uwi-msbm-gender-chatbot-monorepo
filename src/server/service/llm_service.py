# LOCAL IMPORT
from server.core.config import get_settings

from abc import ABC, abstractmethod
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_core.language_models.chat_models import BaseChatModel
from typing import Dict, Any, Union

# Get settings instance
settings = get_settings()

ModelConfig = Union[Dict[str, Any], str]

def initialize_models(model_configs: Dict[str, ModelConfig], model_initializer: callable) -> Dict[str, BaseChatModel]:
    """
    Initialize models based on the provided configurations and initializer function.

    Args:
        model_configs (Dict[str, ModelConfig]): A dictionary of model configurations.
        model_initializer (callable): A function to initialize each model.

    Returns:
        Dict[str, BaseChatModel]: A dictionary of initialized models.
    """
    models = {}
    for name, config in model_configs.items():
        models[name] = model_initializer(name, config)
    return models

class ModelProvider(ABC):
    def __init__(self):
        self.models = {}
        self._initialize_models()

    @abstractmethod
    def _initialize_models(self):
        pass

    def get_model(self, name) -> BaseChatModel:
        if name in self.models:
            return self.models[name]
        else:
            raise ValueError(f"Model '{name}' not found.")

    @abstractmethod
    def _get_model_configs(self) -> Dict[str, ModelConfig]:
        """
        Get the model configurations for this provider.

        Returns:
            Dict[str, ModelConfig]: A dictionary of model configurations.
        """
        pass

    @abstractmethod
    def _initialize_model(self, name: str, config: ModelConfig) -> BaseChatModel:
        """
        Initialize a single model based on its name and configuration.

        Args:
            name (str): The name of the model.
            config (ModelConfig): The configuration for the model.

        Returns:
            BaseChatModel: An initialized chat model.
        """
        pass

    def _initialize_models(self):
        self.models = initialize_models(self._get_model_configs(), self._initialize_model)

class OpenAI(ModelProvider):
    def _get_model_configs(self) -> Dict[str, ModelConfig]:
        return {
            "gpt3_5": {"model": "gpt-3.5-turbo", "temperature": 0},
            "gpt4o": {"model": "gpt-4o", "temperature": 0.5},
            "gpt4o_mini": {"model": "gpt-4o", "temperature": 0}
        }

    def _initialize_model(self, name: str, config: ModelConfig) -> BaseChatModel:
        if not isinstance(config, dict) or "model" not in config or "temperature" not in config:
            raise ValueError(f"Invalid configuration for OpenAI model {name}")
        return ChatOpenAI(
            model=config["model"],
            temperature=config["temperature"],
            api_key=settings.OPENAI_API_KEY,
            verbose=True
        )

class Groq(ModelProvider):
    def _get_model_configs(self) -> Dict[str, ModelConfig]:
        return {
            "groq70b": "llama3-groq-70b-8192-tool-use-preview",
            "groq8b": "llama3-8b-8192",
            "groqMistral": "mixtral-8x7b-32768"
        }

    def _initialize_model(self, name: str, config: ModelConfig) -> BaseChatModel:
        if not isinstance(config, str):
            raise ValueError(f"Invalid configuration for Groq model {name}")
        return ChatGroq(
            temperature=0,
            model=config,
            api_key=settings.GROQ_API_KEY,
            verbose=True
        )