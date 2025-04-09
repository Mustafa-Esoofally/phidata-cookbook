"""
Defines Toolkits for native Google model capabilities (Imagen, potentially others)
that are invoked via specific client methods rather than standard function calling.
"""

import json
import os
from os import getenv
from pathlib import Path
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
    from google.genai.types import (
        GenerateImagesConfig,
        Image,
        UpscaleImageConfig,
        EditImageConfig,
        RawReferenceImage,
        MaskReferenceImage,
        MaskReferenceConfig,
    )
except ImportError:
    log_error("`google-genai` not installed. Please install it using `pip install google-genai`")
    # Allow class definition but tools will fail later if called
    genai = None
    GeminiClient = None
    ClientError = None
    ServerError = None
    GenerateImagesConfig = None
    Image = None
    UpscaleImageConfig = None
    EditImageConfig = None
    RawReferenceImage = None
    MaskReferenceImage = None
    MaskReferenceConfig = None


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
        default_upscale_model: str = "imagen-3.0-generate-001", # For later
        default_edit_model: str = "imagen-3.0-capability-001", # For later
        enable_generate: bool = True,
        enable_upscale: bool = True, # Add when implemented
        enable_edit: bool = True, # Add when implemented
        **kwargs,
    ):
        super().__init__(name="google_native_image_tools", **kwargs)

        if not genai:
            log_error("google-genai library not found. GoogleNativeImageTools will not function.")
            self.client = None
            return

        self.client: Optional[GeminiClient] = None
        self.default_generate_model = default_generate_model
        self.default_upscale_model = default_upscale_model
        self.default_edit_model = default_edit_model

        client_config: Dict[str, Any] = {}
        self.use_vertex = vertexai or getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() == "true"

        if not self.use_vertex:
            log_info("Configuring GoogleNativeImageTools for standard API key access.")
            resolved_api_key = api_key or getenv("GOOGLE_API_KEY")
            if not resolved_api_key:
                log_error("GOOGLE_API_KEY not set. Needed for non-Vertex AI Imagen access.")
                # Continue initialization, but client calls will fail
            else:
                log_info("Using GOOGLE_API_KEY.")
                client_config["api_key"] = resolved_api_key
        else:
            log_info("Configuring GoogleNativeImageTools for Vertex AI access.")
            resolved_project_id = project_id or getenv("GOOGLE_CLOUD_PROJECT")
            resolved_location = location or getenv("GOOGLE_CLOUD_LOCATION")
            log_info(f"Using Vertex AI with Project ID: {resolved_project_id}, Location: {resolved_location}")
            client_config["vertexai"] = True
            client_config["project"] = resolved_project_id
            client_config["location"] = resolved_location
            if not client_config["project"]:
                 log_error("GOOGLE_CLOUD_PROJECT not set. Needed for Vertex AI Imagen access.")
                 # Continue initialization, but client calls will fail

        client_config = {k: v for k, v in client_config.items() if v is not None}

        if client_params:
            log_info(f"Applying additional client parameters: {client_params}")
            client_config.update(client_params)

        try:
            self.client = genai.Client(**client_config)
            log_info("GoogleNativeImageTools initialized successfully.")
        except Exception as e:
            log_error(f"Failed to initialize google.genai.Client for Imagen: {e}")
            self.client = None # Ensure client is None if init fails

        if enable_generate:
            self.register(self.generate_image)
        if enable_upscale:
            self.register(self.upscale_image) # <-- Register upscale
        if enable_edit:
            self.register(self.edit_image) # <-- Register edit
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
        log_info(f"Received config_params: {config_params}")

        gen_config = None
        if config_params:
            try:
                # Filter None values from user dict before passing
                filtered_params = {k: v for k, v in config_params.items() if v is not None}
                gen_config = GenerateImagesConfig(**filtered_params)
            except Exception as e:
                 log_warning(f"Invalid config_params provided: {e}. Using default config.")
                 gen_config = GenerateImagesConfig() # Use defaults if user config fails
        else:
            log_info("No config_params provided, using default GenerateImagesConfig.")
            gen_config = GenerateImagesConfig() # Default config if none provided

        try:
            log_info(f"Calling generate_images API with prompt: '{prompt}', config: {gen_config}")
            response = self.client.models.generate_images(
                model=target_model,
                prompt=prompt,
                config=gen_config,
            )

            # Log the raw response structure for debugging
            # log_info(f"Received raw response from Imagen API: {response}")

            if response.generated_images and response.generated_images[0].image:
                img: Image = response.generated_images[0].image
                # --- DEBUG: Inspect attributes of the Image object ---
                # log_info(f"Attributes of img object (type: {type(img)}): {dir(img)}")
                # --- END DEBUG ---
                artifact = ImageArtifact(
                    id=str(uuid4()),
                    content=img.image_bytes, # Corrected attribute
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
                log_info(f"Successfully generated image artifact: {artifact.id}")

                # --- Save image locally ---
                try:
                    # Define the target directory using pathlib
                    target_dir = Path("tmp")
                    # Ensure the target directory exists
                    target_dir.mkdir(parents=True, exist_ok=True)
                    # Construct the full filepath using pathlib
                    filename = f"{artifact.id}.png"
                    filepath = target_dir / filename

                    with open(filepath, "wb") as f:
                        f.write(artifact.content)
                    log_info(f"Saved generated image to local file: {filepath}")
                    # Optionally add filepath to metadata
                    artifact_dict = artifact.model_dump()
                    if artifact_dict.get("metadata"):
                        artifact_dict["metadata"]["local_filepath"] = str(filepath) # Store as string
                    else:
                       artifact_dict["metadata"] = {"local_filepath": str(filepath)}
                    # Return the updated dictionary representation
                    return artifact_dict
                except Exception as e:
                    log_warning(f"Failed to save generated image {artifact.id} locally: {e}")
                    # Still return the original artifact dict even if saving failed
                    return artifact.model_dump()
                # --- End save image ---

                # # Return dictionary representation for the agent - Now handled within try/except
                # return artifact.model_dump()
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

    def upscale_image(
        self,
        image_artifact: Dict[str, Any],
        upscale_factor: str,
        model_id: Optional[str] = None,
        config_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Upscales an existing image using Google's Imagen models.
        NOTE: This tool requires Vertex AI configuration and is not supported with standard API Keys.

        Args:
            image_artifact: The dictionary representation of the ImageArtifact to upscale (must contain 'content' bytes).
            upscale_factor: The factor by which to upscale (e.g., 'x2', 'x4'). Check API docs for supported factors.
            model_id: The specific Imagen model ID to use for upscaling (e.g., 'imagen-3.0-generate-001').
                      Defaults to the upscale model specified during toolkit initialization.
            config_params: Optional dictionary of parameters for UpscaleImageConfig.

        Returns:
            A dictionary representing the generated upscaled ImageArtifact.
        """
        if not self.client:
            error_msg = "Imagen client not initialized. Cannot upscale image."
            log_error(error_msg)
            raise ToolError(error_msg)

        if not self.use_vertex:
            error_msg = "Image upscaling requires Vertex AI configuration. It is not supported with standard API keys."
            log_error(error_msg)
            raise ToolError(error_msg)

        if not image_artifact or 'content' not in image_artifact or not isinstance(image_artifact['content'], bytes):
             error_msg = "Invalid input: 'image_artifact' must be a dictionary containing 'content' as bytes."
             log_error(error_msg)
             raise ToolError(error_msg)

        target_model = model_id or self.default_upscale_model
        log_info(f"Attempting to upscale image artifact {image_artifact.get('id', 'unknown')} with model: {target_model}")
        log_info(f"Received upscale_factor: {upscale_factor}, config_params: {config_params}")

        upscale_config = None
        if config_params:
            try:
                filtered_params = {k: v for k, v in config_params.items() if v is not None}
                upscale_config = UpscaleImageConfig(**filtered_params)
            except Exception as e:
                log_warning(f"Invalid config_params for UpscaleImageConfig: {e}. Using default config.")
                upscale_config = UpscaleImageConfig()
        else:
            log_info("No config_params provided, using default UpscaleImageConfig.")
            upscale_config = UpscaleImageConfig()

        try:
            # Reconstruct the Image object from bytes
            input_image_obj = Image(image_bytes=image_artifact['content'])

            log_info(f"Calling upscale_image API with factor: {upscale_factor}, config: {upscale_config}")
            response = self.client.models.upscale_image(
                model=target_model,
                image=input_image_obj,
                upscale_factor=upscale_factor,
                config=upscale_config,
            )

            if response.generated_images and response.generated_images[0].image:
                img: Image = response.generated_images[0].image
                upscaled_artifact = ImageArtifact(
                    id=str(uuid4()),
                    content=img.image_bytes,
                    mime_type=img.mime_type or upscale_config.output_mime_type or "image/png",
                    model_id=target_model,
                    prompt=f"Upscaled from artifact {image_artifact.get('id', 'unknown')}", # Add reference
                    metadata={
                        "rai_reason": response.generated_images[0].rai_reason
                        if hasattr(response.generated_images[0], "rai_reason")
                           and response.generated_images[0].rai_reason
                        else None,
                        "raw_response_metadata": response.metadata.to_dict()
                        if hasattr(response, "metadata") and response.metadata
                        else None,
                        "original_artifact_id": image_artifact.get('id')
                    }
                )
                log_info(f"Successfully generated upscaled image artifact: {upscaled_artifact.id}")

                # Save locally
                try:
                    target_dir = Path("tmp")
                    target_dir.mkdir(parents=True, exist_ok=True)
                    filename = f"{upscaled_artifact.id}.png"
                    filepath = target_dir / filename
                    with open(filepath, "wb") as f:
                        f.write(upscaled_artifact.content)
                    log_info(f"Saved upscaled image to local file: {filepath}")
                    artifact_dict = upscaled_artifact.model_dump()
                    if artifact_dict.get("metadata"):
                         artifact_dict["metadata"]["local_filepath"] = str(filepath)
                    else:
                        artifact_dict["metadata"] = {"local_filepath": str(filepath)}
                    return artifact_dict
                except Exception as e:
                    log_warning(f"Failed to save upscaled image {upscaled_artifact.id} locally: {e}")
                    return upscaled_artifact.model_dump()
            else:
                error_msg = "Image upscaling succeeded but no image data found in response."
                log_error(error_msg)
                raise ToolError(error_msg)

        except (ClientError, ServerError) as e:
            error_msg = f"Imagen API error during image upscaling: {e}"
            log_error(error_msg)
            raise ToolError(error_msg) from e
        except Exception as e:
            error_msg = f"Unknown error during image upscaling: {e}"
            log_error(error_msg)
            raise ToolError(error_msg) from e

    # --- Placeholder for edit_image implementation ---
    def edit_image(
        self,
        image_artifact: Dict[str, Any],
        prompt: str,
        mask_artifact: Optional[Dict[str, Any]] = None,
        model_id: Optional[str] = None,
        config_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Edits an existing image based on a text prompt using Google's Imagen models.
        Optionally accepts a mask image.
        NOTE: This tool requires Vertex AI configuration and is not supported with standard API Keys.

        Args:
            image_artifact: The dictionary representation of the base ImageArtifact to edit.
            prompt: The text prompt describing the edit.
            mask_artifact: Optional dictionary representation of an ImageArtifact to use as a mask.
                         If provided, often used with edit_mode='EDIT_MODE_INPAINT_OUTPAINT'.
            model_id: The specific Imagen model ID to use for editing (e.g., 'imagen-3.0-capability-001').
                      Defaults to the edit model specified during toolkit initialization.
            config_params: Optional dictionary of parameters for EditImageConfig (e.g., {'edit_mode': 'EDIT_MODE_PRODUCT_IMAGE'}).

        Returns:
            A dictionary representing the generated edited ImageArtifact.
        """
        if not self.client:
            error_msg = "Imagen client not initialized. Cannot edit image."
            log_error(error_msg)
            raise ToolError(error_msg)

        if not self.use_vertex:
            error_msg = "Image editing requires Vertex AI configuration. It is not supported with standard API keys."
            log_error(error_msg)
            raise ToolError(error_msg)

        if not image_artifact or 'content' not in image_artifact or not isinstance(image_artifact['content'], bytes):
             error_msg = "Invalid input: 'image_artifact' must be a dictionary containing 'content' as bytes."
             log_error(error_msg)
             raise ToolError(error_msg)

        if mask_artifact and ('content' not in mask_artifact or not isinstance(mask_artifact['content'], bytes)):
            log_warning("Invalid 'mask_artifact' provided, ignoring mask. It must be a dictionary containing 'content' as bytes.")
            mask_artifact = None # Ignore invalid mask

        target_model = model_id or self.default_edit_model
        log_info(f"Attempting to edit image artifact {image_artifact.get('id', 'unknown')} with model: {target_model}")
        log_info(f"Using prompt: '{prompt}', Mask provided: {bool(mask_artifact)}, Config_params: {config_params}")

        edit_config = None
        if config_params:
            try:
                filtered_params = {k: v for k, v in config_params.items() if v is not None}
                edit_config = EditImageConfig(**filtered_params)
            except Exception as e:
                log_warning(f"Invalid config_params for EditImageConfig: {e}. Using default config.")
                edit_config = EditImageConfig()
        else:
            log_info("No config_params provided, using default EditImageConfig.")
            edit_config = EditImageConfig()

        try:
            # Reconstruct input Image object(s)
            input_image_obj = Image(image_bytes=image_artifact['content'])
            reference_images = [RawReferenceImage(reference_id=1, reference_image=input_image_obj)]

            if mask_artifact:
                mask_image_obj = Image(image_bytes=mask_artifact['content'])
                # Simple mask reference - API might need more specific MaskReferenceConfig depending on use case
                reference_images.append(RawReferenceImage(reference_id=2, reference_image=mask_image_obj))
                log_info("Using provided mask image.")
                # Note: Depending on the desired edit/mask behavior, a MaskReferenceImage
                # with a specific MaskReferenceConfig might be needed instead of a second RawReferenceImage.
                # Example (if API expects background mask): reference_images.append(MaskReferenceImage(...))

            log_info(f"Calling edit_image API with prompt: '{prompt}', config: {edit_config}")
            response = self.client.models.edit_image(
                model=target_model,
                prompt=prompt,
                reference_images=reference_images,
                config=edit_config,
            )

            if response.generated_images and response.generated_images[0].image:
                img: Image = response.generated_images[0].image
                edited_artifact = ImageArtifact(
                    id=str(uuid4()),
                    content=img.image_bytes,
                    mime_type=img.mime_type or edit_config.output_mime_type or "image/png",
                    model_id=target_model,
                    prompt=prompt, # Keep the edit prompt
                    metadata={
                        "rai_reason": response.generated_images[0].rai_reason
                        if hasattr(response.generated_images[0], "rai_reason")
                           and response.generated_images[0].rai_reason
                        else None,
                        "raw_response_metadata": response.metadata.to_dict()
                        if hasattr(response, "metadata") and response.metadata
                        else None,
                        "original_artifact_id": image_artifact.get('id'),
                        "mask_artifact_id": mask_artifact.get('id') if mask_artifact else None,
                    }
                )
                log_info(f"Successfully generated edited image artifact: {edited_artifact.id}")

                # Save locally
                try:
                    target_dir = Path("tmp")
                    target_dir.mkdir(parents=True, exist_ok=True)
                    filename = f"{edited_artifact.id}.png"
                    filepath = target_dir / filename
                    with open(filepath, "wb") as f:
                        f.write(edited_artifact.content)
                    log_info(f"Saved edited image to local file: {filepath}")
                    artifact_dict = edited_artifact.model_dump()
                    if artifact_dict.get("metadata"):
                        artifact_dict["metadata"]["local_filepath"] = str(filepath)
                    else:
                        artifact_dict["metadata"] = {"local_filepath": str(filepath)}
                    return artifact_dict
                except Exception as e:
                    log_warning(f"Failed to save edited image {edited_artifact.id} locally: {e}")
                    return edited_artifact.model_dump()
            else:
                error_msg = "Image editing succeeded but no image data found in response."
                log_error(error_msg)
                raise ToolError(error_msg)

        except (ClientError, ServerError) as e:
            error_msg = f"Imagen API error during image editing: {e}"
            log_error(error_msg)
            raise ToolError(error_msg) from e
        except Exception as e:
            error_msg = f"Unknown error during image editing: {e}"
            log_error(error_msg)
            raise ToolError(error_msg) from e
    # --- End Placeholder ---
