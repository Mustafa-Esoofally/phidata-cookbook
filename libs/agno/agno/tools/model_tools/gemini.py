"""
Defines Toolkits for native Google model capabilities (Imagen, potentially others)
that are invoked via specific client methods rather than standard function calling.
"""

import json
from os import getenv
from typing import Any, Dict, List, Optional
from uuid import uuid4

from agno.exceptions import ToolError
from agno.media import ImageArtifact
from agno.tools import Toolkit
from agno.utils.log import log_error, log_info, log_warning

try:
    from google import genai
    from google.genai import Client as GeminiClient
    from google.genai.errors import ClientError, ServerError
    from google.genai.types import GenerateImagesConfig, Image
except ImportError:
    log_error("`google-genai` not installed. Please install it using `pip install google-genai`")
    # Allow class definition but tools will fail later if called
    genai = None
    GeminiClient = None
    ClientError = None
    ServerError = None
    GenerateImagesConfig = None
    Image = None


class GoogleNativeImageTools(Toolkit):
    """
    Provides tools to interact with Google's native Imagen capabilities.

    Requires google-genai library and appropriate API credentials.
    Imagen API access may require allowlisting.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        vertexai: bool = False,
        project_id: Optional[str] = None,
        location: Optional[str] = None,
        client_params: Optional[Dict[str, Any]] = None,
        default_generate_model: str = "imagen-3.0-generate-002", # Example default
        # default_upscale_model: str = "imagen-3.0-generate-001", # For later
        # default_edit_model: str = "imagen-3.0-capability-001", # For later
        enable_generate: bool = True,
        # enable_upscale: bool = False, # Add when implemented
        # enable_edit: bool = False, # Add when implemented
        **kwargs,
    ):
        super().__init__(name="google_native_image_tools", **kwargs)

        if not genai:
            log_error("google-genai library not found. GoogleNativeImageTools will not function.")
            self.client = None
            return

        self.client: Optional[GeminiClient] = None
        self.default_generate_model = default_generate_model
        # self.default_upscale_model = default_upscale_model
        # self.default_edit_model = default_edit_model

        client_config: Dict[str, Any] = {}
        use_vertex = vertexai or getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() == "true"

        if not use_vertex:
            resolved_api_key = api_key or getenv("GOOGLE_API_KEY")
            if not resolved_api_key:
                log_error("GOOGLE_API_KEY not set. Needed for non-Vertex AI Imagen access.")
                # Continue initialization, but client calls will fail
            else:
                client_config["api_key"] = resolved_api_key
        else:
            log_info("Using Vertex AI for Imagen tools")
            client_config["vertexai"] = True
            client_config["project"] = project_id or getenv("GOOGLE_CLOUD_PROJECT")
            client_config["location"] = location or getenv("GOOGLE_CLOUD_LOCATION")
            if not client_config["project"]:
                 log_error("GOOGLE_CLOUD_PROJECT not set. Needed for Vertex AI Imagen access.")
                 # Continue initialization, but client calls will fail

        client_config = {k: v for k, v in client_config.items() if v is not None}

        if client_params:
            client_config.update(client_params)

        try:
            self.client = genai.Client(**client_config)
            log_info("GoogleNativeImageTools initialized successfully.")
        except Exception as e:
            log_error(f"Failed to initialize google.genai.Client for Imagen: {e}")
            self.client = None # Ensure client is None if init fails

        if enable_generate:
            self.register(self.generate_image)
        # Register other tools when implemented

    def generate_image(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        config_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generates an image based on a text prompt using Google's Imagen models.
        Note: Imagen API access may require allowlisting.

        Args:
            prompt: The text prompt describing the image to generate.
            model_id: The specific Imagen model ID to use (e.g., 'imagen-3.0-generate-002').
                      Defaults to the model specified during toolkit initialization.
            config_params: Optional dictionary of parameters for GenerateImagesConfig
                           (e.g., {'number_of_images': 1, 'output_mime_type': 'image/png'}).

        Returns:
            A dictionary representing the generated ImageArtifact containing image bytes and metadata.
            Returns an error dictionary if generation fails.
        """
        if not self.client:
            error_msg = "Imagen client not initialized. Cannot generate image."
            log_error(error_msg)
            raise ToolError(error_msg)

        target_model = model_id or self.default_generate_model
        log_info(f"Attempting to generate image with model: {target_model}")

        gen_config = None
        if config_params:
            try:
                # Filter None values from user dict before passing
                filtered_params = {k: v for k, v in config_params.items() if v is not None}
                gen_config = GenerateImagesConfig(**filtered_params)
                log_info(f"Using GenerateImagesConfig: {gen_config}")
            except Exception as e:
                 log_warning(f"Invalid config_params provided: {e}. Using default config.")
                 gen_config = GenerateImagesConfig() # Use defaults if user config fails
        else:
            gen_config = GenerateImagesConfig() # Default config if none provided

        try:
            response = self.client.models.generate_images(
                model=target_model,
                prompt=prompt,
                config=gen_config,
            )

            if response.generated_images and response.generated_images[0].image:
                img: Image = response.generated_images[0].image
                artifact = ImageArtifact(
                    id=str(uuid4()),
                    content=img.data, # Image data should be in .data
                    mime_type=img.mime_type or gen_config.output_mime_type or "image/png",
                    model_id=target_model,
                    prompt=prompt,
                    # Add RAI reason if available and requested in config
                    metadata={
                        "rai_reason": response.generated_images[0].rai_reason
                        if hasattr(response.generated_images[0], "rai_reason")
                           and response.generated_images[0].rai_reason
                        else None,
                        "raw_response_metadata": response.metadata.to_dict() # Add raw metadata
                        if hasattr(response, "metadata") and response.metadata
                        else None
                    }
                )
                log_info(f"Successfully generated image: {artifact.id}")
                # Return dictionary representation for the agent
                return artifact.model_dump()
            else:
                error_msg = "Image generation succeeded but no image data found in response."
                log_error(error_msg)
                raise ToolError(error_msg)

        except (ClientError, ServerError) as e:
            error_msg = f"Imagen API error during image generation: {e}"
            log_error(error_msg)
            raise ToolError(error_msg) from e
        except Exception as e:
            error_msg = f"Unknown error during image generation: {e}"
            log_error(error_msg)
            raise ToolError(error_msg) from e
