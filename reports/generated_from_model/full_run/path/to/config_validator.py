# config_validator.py

from pydantic import BaseModel, ValidationError, Field
import json

class ConfigSchema(BaseModel):
    # Define your configuration schema here
    api_key: str = Field(..., description="API key for accessing the service")
    timeout: int = Field(default=30, description="Timeout in seconds")
    retries: int = Field(default=3, description="Number of retries on failure")

    # Add more fields as per your configuration requirements

    @classmethod
    def validate_config(cls, config_data):
        try:
            config = cls(**config_data)
            return config
        except ValidationError as e:
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            raise ValueError("Configuration validation failed. Errors:\n" + "\n".join(error_messages))

if __name__ == "__main__":
    # Example usage
    config_data = {
        "api_key": "your_api_key_here",
        "timeout": 20,
        "retries": 5
    }

    try:
        validated_config = ConfigSchema.validate_config(config_data)
        print("Configuration is valid.")
        print(validated_config.json(indent=4))
    except ValueError as e:
        print(e)
