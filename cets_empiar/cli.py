import logging
import typer
from pathlib import Path
from rich.logging import RichHandler
from typing import Annotated, Optional

from cets_empiar.empiar_to_cets import empiar_conversion
from cets_empiar.settings import get_settings
from cets_empiar.thumbnails import cets_data_thumbnail_generation
from cets_empiar.validation import validation

cets_empiar = typer.Typer()

logging.basicConfig(
    level=logging.INFO,
    format="%(name)s - %(asctime)s - %(levelname)s - %(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger()

settings = get_settings()


@cets_empiar.command("empiar-to-cets")
def convert_empiar_to_cets(
    definition_path: Annotated[
        Path, 
        typer.Option(
            "--definition-path", 
            "-dp", 
            case_sensitive=False, 
            help="Path to EMPIAR definition yaml file."
        )
    ], 
    cets_output_dir: Annotated[
        Optional[Path], 
        typer.Option(
            "--cets-output-dir", 
            "-cod", 
            case_sensitive=False, 
            help="Directory for output CETS json file. If not provided, will be saved in default output directory."
        )
    ] = settings.default_cets_output_dir
):
    
    empiar_conversion.convert_empiar_entry_to_cets(definition_path, cets_output_dir)


@cets_empiar.command("create-thumbnails")
def create_thumbnail_images(
    cets_path: Annotated[
        Path, 
        typer.Option(
            "--cets-path", 
            "-cp", 
            case_sensitive=False, 
            help="Path to EMPIAR CETS json file."
        )
    ], 
    cets_output_dir: Annotated[
        Optional[Path], 
        typer.Option(
            "--cets-output-dir", 
            "-cod", 
            case_sensitive=False, 
            help="Directory for output thumbnail. If not provided, will be saved in default output directory."
        )
    ] = settings.default_cets_output_dir, 
    thumbnail_size: Annotated[
        Optional[tuple[int, int]], 
        typer.Option(
            "--thumbnail-size", 
            "-t", 
            help="Size of the output thumbnails in pixels, as [x, y]. Deafult is [256, 256].",
        )
    ] = (256, 256),
    projection_method: Annotated[
        Optional[cets_data_thumbnail_generation.ProjectionMethod], 
        typer.Option(
            "--projection-method", 
            "-p",
            help="Method for projection on z-axis, must be one of 'max', 'mean', or 'middle'. Default is max.",
        )
    ] = "max",
    limit_projection: Annotated[
        Optional[float], 
        typer.Option(
            "--limit-projection", 
            "-lp", 
            min=0.0, 
            max=1.0, 
            help="Proportion of slices to project over, about the central slice of the tomogram. Defailt is 0.5 (half slices).",
        )
    ] = 0.5,
    limit_annotation: Annotated[
        Optional[float], 
        typer.Option(
            "--limit-annotation", 
            "-la", 
            min=0.0, 
            max=1.0, 
            help="Proportion of annotation points to accept, about the central slice of the tomogram. Default is 0.5 (half depth).",
        )
    ] = 0.5,
):

    cets_data_thumbnail_generation.create_cets_data_thumbnails(
        cets_path, 
        cets_output_dir, 
        thumbnail_size, 
        projection_method, 
        limit_projection, 
        limit_annotation, 
    )


@cets_empiar.command("validate")
def validate_cets_data(
    cets_path: Annotated[
        Path, 
        typer.Option(
            "--cets-path", 
            "-cp", 
            case_sensitive=False, 
            help="Path to EMPIAR CETS json file."
        )
    ]
): 
    
    validation.validate_cets(cets_path)


if __name__ == "__main__":
    cets_empiar()
