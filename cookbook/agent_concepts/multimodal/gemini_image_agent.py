import os
from pathlib import Path

from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.model_tools.gemini import GoogleNativeImageTools

image_tools = GoogleNativeImageTools()

image_agent = Agent(
    name="Gemini Image Generation Agent",
    model=Gemini(id="gemini-2.0-flash"),
    tools=[image_tools],
    description="An AI agent that can generate, edit, and upscale images using Google's Imagen models.",
    instructions=[
        "Use the `generate_image` tool to create a new image from a text prompt.",
        "Use the `upscale_image` tool to increase the resolution of an existing image artifact.",
        "Use the `edit_image` tool to modify an existing image artifact based on a text prompt (optionally with a mask artifact).",
        "For upscale and edit, you need the specific image artifact data from a previous step.",
        "Provide the user's request as the prompt for the image generation/editing.",
        "If the user specifies parameters like number of images, aspect ratio, upscale factor, or edit mode, try to include them in the `config_params` argument for the relevant tool.",
        "Inform the user that Upscale and Edit capabilities require Vertex AI configuration."
    ],
    markdown=True,
)

# Example usage
image_agent.print_response(
    "Hi, can you create a 3d rendered image of a pig with wings and a top hat flying over a happy futuristic scifi city with lots of greenery?"
)

# Example with config_params (Note: Check GoogleNativeImageTools.generate_image docstring
# and Imagen API docs for supported parameters)
# image_agent.print_response(
#     "Create a photorealistic image of a cat wearing sunglasses, aspect ratio 16:9",
#     config_params={"aspect_ratio": "16:9"} # Example, actual param name might differ
# )

# --- Example: Generate Image ---
print("--- Generating Image ---")
response_generate = image_agent.run(
    "Generate an image of a futuristic cityscape at sunset."
)
# Access the generated artifact for potential follow-up actions
generated_artifact_msg = next((msg for msg in response_generate.messages if msg.role == "tool" and msg.tool_name == "generate_image"), None)
generated_artifact = generated_artifact_msg.image_output if generated_artifact_msg and generated_artifact_msg.image_output else None

if generated_artifact:
    print(f"Generated Artifact ID: {generated_artifact.id}")
    # The image is saved to tmp/{generated_artifact.id}.png by the tool
else:
    print("Image generation did not produce an artifact.")

response_generate.display()
print("-------------------------")

# --- Example: Upscale Image (Conceptual - requires artifact from previous step) ---
# print("--- Upscaling Image (Conceptual) ---")
# if generated_artifact:
#     # NOTE: The tool expects the artifact as a dictionary.
#     # In a real application, you'd pass the generated_artifact.model_dump()
#     # or load a previously saved artifact.
#     image_agent.print_response(
#         f"Upscale the image artifact with ID {generated_artifact.id} by a factor of x2.",
#         # This requires modifying the agent or run method to pass tool arguments directly,
#         # or instructing the LLM very precisely to construct the call.
#         # A simpler approach for scripting is calling the tool directly:
#         # upscale_params = {
#         #     "image_artifact": generated_artifact.model_dump(),
#         #     "upscale_factor": "x2"
#         # }
#         # try:
#         #    upscaled_artifact_dict = image_tools.upscale_image(**upscale_params)
#         #    print(f"Upscaled artifact saved to tmp/{upscaled_artifact_dict['id']}.png")
#         # except Exception as e:
#         #    print(f"Upscaling failed: {e}")
#     )
# else:
#     print("Skipping upscale example as no initial artifact was generated.")
# print("-------------------------")


# --- Example: Edit Image (Conceptual - requires artifact from previous step) ---
# print("--- Editing Image (Conceptual) ---")
# if generated_artifact:
#     # NOTE: The tool expects the artifact as a dictionary.
#     image_agent.print_response(
#         f"Edit the image artifact with ID {generated_artifact.id} to make the sky clearer and sunnier.",
#         # As with upscale, passing the artifact dictionary requires specific handling.
#         # Direct tool call example:
#         # edit_params = {
#         #     "image_artifact": generated_artifact.model_dump(),
#         #     "prompt": "Make the sky clearer and sunnier"
#         # }
#         # try:
#         #    edited_artifact_dict = image_tools.edit_image(**edit_params)
#         #    print(f"Edited artifact saved to tmp/{edited_artifact_dict['id']}.png")
#         # except Exception as e:
#         #    print(f"Editing failed: {e}")
#     )
# else:
#     print("Skipping edit example as no initial artifact was generated.")
# print("-------------------------")