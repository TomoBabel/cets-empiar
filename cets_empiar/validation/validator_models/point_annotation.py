import logging
from cets_data_model.models.models import PointSet3D, Tomogram
from pydantic import field_validator, model_validator, ValidationError
from typing import Literal, Optional, Dict, Any


logger = logging.getLogger(__name__)


class ValidatedPointSet3D(PointSet3D):
    
    @staticmethod
    def _get_cs_names(coordinate_systems):
        """Extract coordinate system names from list of coordinate system objects"""
        return {cs.name for cs in coordinate_systems if hasattr(cs, 'name')}
    
    @staticmethod
    def _check_coordinate_systems_without_transformation(
        anno_coordinate_systems, 
        tomo_coordinate_systems
    ):
        """Verify annotation and tomogram share exactly one common coordinate system"""
        anno_cs_names = ValidatedPointSet3D._get_cs_names(anno_coordinate_systems)
        tomo_cs_names = ValidatedPointSet3D._get_cs_names(tomo_coordinate_systems)
        
        if common_cs := anno_cs_names & tomo_cs_names:
            if len(common_cs) == 1:
                return list(common_cs)[0]
            raise ValueError(
                f"Multiple common coordinate systems for annotation and tomogram: {common_cs}. "
                "Cannot determine which to use."
            )
        
        raise ValueError(
            f"No common coordinate systems. Annotation has {anno_cs_names}, "
            f"tomogram has {tomo_cs_names}."
        )
    
    @staticmethod
    def _check_coordinate_system_with_transformation(
        anno_coordinate_transformations,
        anno_coordinate_systems,
        tomo_coordinate_systems
    ):
        """Find a transformation that bridges annotation and tomogram coordinate systems"""
        anno_cs_names = ValidatedPointSet3D._get_cs_names(anno_coordinate_systems)
        tomo_cs_names = ValidatedPointSet3D._get_cs_names(tomo_coordinate_systems)
        
        for transformation in anno_coordinate_transformations:
            input_cs = transformation.input if hasattr(transformation, 'input') else None
            output_cs = transformation.output if hasattr(transformation, 'output') else None
            
            if not input_cs or not output_cs:
                continue
            
            if (
                (input_cs in tomo_cs_names and output_cs in anno_cs_names) or
                (input_cs in anno_cs_names and output_cs in tomo_cs_names)
            ):
                return transformation, output_cs if input_cs in tomo_cs_names else input_cs
        
        raise ValueError(
            "Annotation coordinate system doesn't have a transformation to/from "
            "tomogram coordinate system"
        )
    
    @staticmethod
    def _apply_coordinate_transformation(coordinates, transformation):
        """Apply a coordinate transformation to a list of points"""
        if hasattr(transformation, 'transformation_type'):
            trans_type = transformation.transformation_type
        elif hasattr(transformation, 'scale'):
            trans_type = 'scale'
        else:
            raise ValueError("Cannot determine transformation type")
        
        if trans_type == "scale":
            scale_factors = transformation.scale
            transformed_coordinates = [
                [x * scale_factors[0], y * scale_factors[1], z * scale_factors[2]]
                for x, y, z in coordinates
            ]
            return transformed_coordinates
        else:
            raise NotImplementedError(f"Transformation type {trans_type} not supported yet.")
    
    @staticmethod
    def _get_transformed_coordinates(annotation_coords, anno_transformations, anno_cs, tomo_cs):
        """Transform annotation coordinates to tomogram coordinate system if needed"""

        coordinates = annotation_coords
        target_cs_name = None
        
        if not anno_transformations:
            target_cs_name = ValidatedPointSet3D._check_coordinate_systems_without_transformation(
                anno_cs,
                tomo_cs
            )
        else:
            transformation, target_cs_name = ValidatedPointSet3D._check_coordinate_system_with_transformation(
                anno_transformations,
                anno_cs,
                tomo_cs
            )
            coordinates = ValidatedPointSet3D._apply_coordinate_transformation(
                coordinates,
                transformation
            )
        
        return coordinates, target_cs_name
    
    @staticmethod
    def _check_points_within_bounds(coordinates, bounds):
        """Check if all points fall within specified 3D bounds"""
        x_bounds, y_bounds, z_bounds = bounds
        
        out_of_bounds = []
        for i, point in enumerate(coordinates):
            x, y, z = point
            if not (x_bounds[0] <= x <= x_bounds[1] and
                    y_bounds[0] <= y <= y_bounds[1] and
                    z_bounds[0] <= z <= z_bounds[1]):
                out_of_bounds.append((i, point))
        
        return out_of_bounds
    
    @classmethod
    def validate_with_tomogram(cls, annotation_dict: dict, tomogram: Tomogram):
        """
        Validate annotation against a tomogram, checking:
        1. Coordinate systems are compatible
        2. Transformations are valid
        3. Transformed coordinates fall within tomogram bounds
        """
        
        annotation = cls.model_validate(annotation_dict)
        
        anno_cs = annotation.coordinate_systems or []
        tomo_cs = tomogram.coordinate_systems or []
        
        if not anno_cs:
            raise ValueError("Annotation must have at least one coordinate system")
        if not tomo_cs:
            raise ValueError("Tomogram must have at least one coordinate system")
        
        coordinates = annotation.origin3D
        if not coordinates:
            raise ValueError("No 'origin3D' field found in point_set_3D annotation")
        
        anno_transformations = annotation.coordinate_transformations or []
        
        try:
            transformed_coords, target_cs_name = cls._get_transformed_coordinates(
                coordinates,
                anno_transformations,
                anno_cs,
                tomo_cs
            )
        except ValueError as e:
            logger.error(f"Coordinate transformation failed: {e}")
            raise
        
        target_cs = None
        for cs in tomo_cs:
            if hasattr(cs, 'name') and cs.name == target_cs_name:
                target_cs = cs
                break
        
        if not target_cs:
            raise ValueError(f"Target coordinate system '{target_cs_name}' not found in tomogram")
        
        # Determine bounds based on coordinate system
        # For voxel coordinates, use tomogram dimensions
        # For physical coordinates, check against transformed bounds
        if 'voxel' in target_cs_name.lower():
            if not all([tomogram.width, tomogram.height, tomogram.depth]):
                logger.warning("Tomogram missing dimension information, skipping bounds check")
                return annotation
            
            bounds = (
                (0, tomogram.width),
                (0, tomogram.height),
                (0, tomogram.depth)
            )
        else:
            # For physical coordinate systems, transform tomogram dimensions
            # Find the scale transformation from tomogram
            scale_transform = None
            if tomogram.coordinate_transformations:
                for trans in tomogram.coordinate_transformations:
                    if (hasattr(trans, 'output') and trans.output == target_cs_name and
                        hasattr(trans, 'scale')):
                        scale_transform = trans
                        break
            
            if scale_transform and all([tomogram.width, tomogram.height, tomogram.depth]):
                scale = scale_transform.scale
                bounds = (
                    (0, tomogram.width * scale[0]),
                    (0, tomogram.height * scale[1]),
                    (0, tomogram.depth * scale[2])
                )
            else:
                logger.warning("Cannot determine physical bounds, skipping bounds check")
                return annotation
        
        # Check if points are within bounds
        out_of_bounds = cls._check_points_within_bounds(transformed_coords, bounds)
        
        if out_of_bounds:
            error_msg = f"Found {len(out_of_bounds)} points outside tomogram bounds {bounds}:\n"
            
            for idx, point in out_of_bounds[:5]:
                error_msg += f"  Point {idx}: {point}\n"
            if len(out_of_bounds) > 5:
                error_msg += f"  ... and {len(out_of_bounds) - 5} more"
            raise ValueError(error_msg)
        
        logger.info(f"All {len(transformed_coords)} points are within tomogram bounds")
        return annotation
