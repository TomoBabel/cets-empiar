import cets_data_model.models.models as cets_models


def make_scale_transformation(
        input_cs: str, 
        output_cs: str, 
        scale: list[float, float, float]
) -> cets_models.Scale:
    
    return cets_models.Scale.model_construct(
        scale=scale, 
        transformation_type="scale", 
        name=f"{input_cs}_to_{output_cs}_scale_{'_'.join(map(str, scale))}", 
        input=input_cs, 
        output=output_cs
    )


def make_coordinate_transformation(
        type: str, 
        input_cs: str, 
        output_cs: str, 
        params: list
) -> cets_models.Scale:
    
    if type == "scale":
        if len(params[0]) != 3:
            raise ValueError("Scale transformation requires three parameters for x, y, z scaling.")
        transformation = make_scale_transformation(
            input_cs, output_cs, params[0]
        )
    else:
        raise ValueError(f"Unsupported transformation type: {type}")
    
    return transformation
