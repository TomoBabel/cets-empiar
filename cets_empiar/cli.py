import logging
import typer
from rich.logging import RichHandler
from typing import Annotated, Optional

from cets_empiar.validation.validation import validate_cets

from cets_empiar.empiar_to_cets.empiar_conversion import convert_empiar_entry_to_cets_dataset
from cets_empiar.thumbnails.cets_data_thumbnail_generation import ProjectionMethod, create_cets_data_thumbnails


app = typer.Typer()


logging.basicConfig(
    level=logging.INFO,
    format="%(name)s - %(asctime)s - %(levelname)s - %(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger()


@app.command("empiar-to-cets")
def convert_empiar_to_cets(
        accession_id: Annotated[
            str, 
            typer.Argument(
                help="The EMPIAR accession ID for the entry to be converted."
            )
        ],
):
    
    convert_empiar_entry_to_cets_dataset(accession_id)


@app.command("create-thumbnails")
def create_thumbnail_images(
        accession_id: Annotated[
            str, 
            typer.Argument(
                help="The EMPIAR accession ID for the CETS object to create thumbnails for."
            )
        ],
        thumbnail_size: Annotated[
            Optional[tuple[int, int]], 
            typer.Option(
                "--thumbnail-size", 
                "-t", 
                help="Size of the output thumbnails in pixels, as [x, y]. Deafult is [256, 256].",
            )
        ] = (256, 256),
        projection_method: Annotated[
            Optional[ProjectionMethod], 
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

    create_cets_data_thumbnails(accession_id, thumbnail_size, projection_method, limit_projection, limit_annotation)


@app.command("validate")
def validate_cets_data(
    accession_id: Annotated[
        str, 
        typer.Argument(
        help="The EMPIAR accession ID for the CETS object to validate."
        )
    ],
): 
    
    validate_cets(accession_id)


if __name__ == "__main__":
    app()
