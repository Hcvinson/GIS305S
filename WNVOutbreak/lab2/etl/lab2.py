import requests
import yaml
import arcpy  # import the arcpy library
from GSheetsEtl import GSheetsEtl  # import the ETL functions created


def setup():
    # open and load in the yaml file so it cna be referenced as config_dict
    with open('config/wnvoutbreak.yaml') as f:
        config_dict = yaml.load(f, Loader=yaml.FullLoader)
    return config_dict


def etl():
    # running the GsheetsElt script with the yaml file as an input
    print("Running ELT process.")
    etl_instance = GSheetsEtl(config_dict)
    etl_instance.process()


def buffer(layer_name, buff_dist):
    # Buffer the chosen layer by a set distance
    units = "feet"
    output_buffer = f"buff_{layer_name}"
    print(f"Buffering {layer_name} to generate {output_buffer}")
    arcpy.Buffer_analysis(layer_name, output_buffer, f"{buff_dist} {units}", "FULL", "ROUND", "ALL")


def intersect(inter_layer_list):
    # Find where the buffers intersect
    output_inter = input("\nWhat would you like to name your intersect layer?\n")
    arcpy.analysis.Intersect(inter_layer_list, output_inter)
    return output_inter


def spatial_join(lyr_inter):
    # finding the addresses that fall within the buffer intersection
    output_sjoin = input("\nWhat would you like to name your spatial join layer?\n")
    print(f"Finding address that fall in the area of concern.")
    arcpy.analysis.SpatialJoin("Addresses", lyr_inter, output_sjoin)
    return output_sjoin


def sym_diff(lyr_inter):
    # removing the areas that have opted out of being sprayed
    out_sym_diff = input("What would you like to name the new intersect layer that is missing the opt-out areas?\n")
    arcpy.analysis.SymDiff(lyr_inter, "buff_avoid_points", out_sym_diff)
    return out_sym_diff


def main():
    # created a list of the layers to be buffered
    buff_layer_list = ["Mosquito_Larval_Sites", "Wetlands", "Lakes_and_Reservoirs", "OSMP_Properties"]

    for layer in buff_layer_list:
        # Goes through the list of layers that need to be buffered and runs the buffer function on each one
        buff_dist = input(f"\nHow far would you like to buffer {layer}\n")
        buffer(layer, buff_dist)

        # a list of the output layers after being buffered
    inter_layer_list = ["buff_Mosquito_Larval_Sites", "buff_Wetlands", "buff_Lakes_and_Reservoirs",
                        "buff_OSMP_Properties"]
    # assigns the return form the intersect function to the variable lyr_inter and runs the function
    lyr_inter = intersect(inter_layer_list)
    print(f"Creating a layer named {lyr_inter} that shows where the layers:\n{inter_layer_list} intersect.")

    avoid_buff_dist = input("There are some addresses that have opted-out of pesticide spraying.\n"
                            "How many feet would you like to avoid spraying around these addresses?\n")

    avoid_points = "avoid_points"
    # Runs the buffer function on the avoid points, so we have a polygon to use in the sym_diff function
    buffer(avoid_points, avoid_buff_dist)
    # Removes the buffered avoid points from the intersect layer created earlier and creates a variable out of the
    # returned output
    lyr_sym_diff = sym_diff(lyr_inter)
    print(f"Removing opt-out areas to create a new layer named {lyr_sym_diff}")

    # creates a variable equal to  project path to the geodatabase
    proj_path = f"{config_dict.get('proj_dir')}arcgis\westnileoutbreak\WestNileOutbreak.gdb"
    # creates a variable equal to  project path to the aprx
    aprx = arcpy.mp.ArcGISProject(rf"{config_dict.get('proj_dir')}arcgis\westnileoutbreak\WestNileOutbreak.aprx")
    map_doc = aprx.listMaps()[0]

    # Adds the intersect layer missing the buffer around the avoid points output to the map
    map_doc.addDataFromPath(rf"{proj_path}\{lyr_sym_diff}")
    # Saves the project
    aprx.save()

    # Runs the spatial join function on the output from the sym_diff function
    lyr_sjoin = spatial_join(lyr_sym_diff)

    addAOCCount = 0

    with arcpy.da.SearchCursor(lyr_sjoin, ["Join_Count"]) as joinCursor:
        for x in joinCursor:
            # Creating a search cursor and iteration through the attributes in the Join_Count field
            if x[0] == 1:
                # If statement add 1 to a variable set to 0, so it can count each instance that 1 shows up
                addAOCCount = addAOCCount + 1

    print(f"There are {addAOCCount} addresses in the area of concern.")

    aprx.save()


if __name__ == '__main__':
    global config_dict
    config_dict = setup()
    print(config_dict)
    etl()
    main()
