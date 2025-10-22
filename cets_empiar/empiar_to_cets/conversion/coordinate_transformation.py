
def make_scale_transformation(
        input_cs: str, 
        output_cs: str, 
        scale: tuple[float, float, float]
) -> dict:
    
    return {
        "transformation_type": "scale",
        "scale": scale, 
        "name": f"{input_cs}_to_{output_cs}_scale_{'_'.join(map(str, scale))}", 
        "input": input_cs, 
        "output": output_cs
    }


def make_coordinate_transformation(
        type: str, 
        input_cs: str, 
        output_cs: str, 
        params: list
) -> dict:
    
    if type == "scale":
        if len(params[0]) != 3:
            raise ValueError("Scale transformation requires three parameters for x, y, z scaling.")
        transformation = make_scale_transformation(
            input_cs, output_cs, params[0]
        )
    else:
        raise ValueError(f"Unsupported transformation type: {type}")
    
    return transformation
