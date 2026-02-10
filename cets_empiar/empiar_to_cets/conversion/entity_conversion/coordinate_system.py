import cets_data_model.models.models as cets_models

COORDINATE_SYSTEMS = {
    "default_image_voxel": cets_models.CoordinateSystem.model_construct(
        name="default_image_voxel", 
        axes=[
            cets_models.Axis.model_construct(name="default voxel axis X", axis_unit="voxel", axis_type="array"),
            cets_models.Axis.model_construct(name="default voxel axis Y", axis_unit="voxel", axis_type="array"),
            cets_models.Axis.model_construct(name="default voxel axis Z", axis_unit="voxel", axis_type="array"),
        ]
    ), 
    "physical_sampling_angstrom": cets_models.CoordinateSystem.model_construct(
        name="physical_sampling_angstrom", 
        axes=[
            cets_models.Axis.model_construct(name="physical sampling angstrom axis X", axis_unit="angstrom", axis_type="space"),
            cets_models.Axis.model_construct(name="physical sampling angstrom axis Y", axis_unit="angstrom", axis_type="space"),
            cets_models.Axis.model_construct(name="physical sampling angstrom axis Z", axis_unit="angstrom", axis_type="space"),
        ]
    )
}
