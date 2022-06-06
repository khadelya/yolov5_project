from pyproj import Transformer, pyproj
from osgeo import gdal, osr
import json
import os


def json_to_new_coord(tif_file_name, json_file_name):
    # projwin_srs = "EPSG:2326"
    ds=gdal.Open(f'{tif_file_name}.tif')
    prj=ds.GetProjection()
    srs=osr.SpatialReference(wkt=prj)
    src_epsg = int(srs.GetAuthorityCode(None)) # src - .tif file
    JSON_EPSG = 4326 # EPSG WGS 84 of json file
    transformer = Transformer.from_crs(JSON_EPSG, src_epsg)

    with open(f"{json_file_name}.json", "r+") as f:
        train = json.load(f)
        features = train["features"]
        for feature in features:
            coordinates = feature["geometry"]["coordinates"][0]
            for coordinate in coordinates:
                latitude, longitude = coordinate
                coordinate[1], coordinate[0] = transformer.transform(longitude, latitude)

    with open(f'{json_file_name}_new_coord.json', 'w', encoding='utf-8') as f:
        json.dump(train, f, ensure_ascii=False, indent=2)
    return


# Json file should be in the new coordinates f'{json_file_name}_new_coord.json'
def crop_tif(tif_file_name, json_file_name):
    with open(f"{json_file_name}_new_coord.json", "r") as f:
        train = json.load(f)
        features = train["features"]
        for i in range(len(features)):
            xmin = train["features"][i]["geometry"]["coordinates"][0][0][0]
            ymin = train["features"][i]["geometry"]["coordinates"][0][0][1]
            xmax = train["features"][i]["geometry"]["coordinates"][0][2][0]
            ymax = train["features"][i]["geometry"]["coordinates"][0][1][1]
            window = (xmin, ymax, xmax, ymin)
            gdal.Translate(f'../data/images/train/output_crop_raster_{i}.tif', f'{tif_file_name}.tif', projWin = window)
    return

def get_box_coordinates(feature):
    x_list = []
    y_list = []
    coordinates = feature["geometry"]["coordinates"][0]
    for i in range(len(coordinates)):
        x_list.append(coordinates[i][0])
        y_list.append(coordinates[i][1])

    xmin = min(x_list)
    ymax = max(y_list)
    xmax = max(x_list)
    ymin = min(y_list)

    box_coordinates = [xmin, ymax, xmax, ymin]
    return box_coordinates

# features[0]["geometry"]["coordinates"][0][0][0]

def get_pixel_values(box_coordinates, UpperLeft, pixelSize):
    xmin_px = round((box_coordinates[0] - UpperLeft[0]) / pixelSize[0]) # round((x_coord - upper_left_x) / px_size_x)
    ymin_px = round((UpperLeft[1] - box_coordinates[1]) / pixelSize[1]) # round((upper_left_y - y_coord) / px_size_y)
    xmax_px = round((box_coordinates[2] - UpperLeft[0]) / pixelSize[0])
    ymax_px = round((UpperLeft[1] - box_coordinates[3]) / pixelSize[1])
    return [xmin_px, ymin_px, xmax_px, ymax_px]

def convert(size, box):
    width_norm = 1. / size[0]
    height_norm = 1. / size[1]
    x_center = (box[0] + box[2]) * width_norm / 2
    y_center = (box[1] + box[3]) * height_norm / 2
    width = (box[2] - box[0]) * width_norm
    height = (box[3] - box[1]) * height_norm
    return (x_center, y_center, width, height)

def convert_annotation(tif_file_name, json_file_name_train, json_file_name_manual):
    # crop tif file
    json_to_new_coord(tif_file_name, json_file_name_train)
    with open(f"{json_file_name_train}_new_coord.json", "r") as f:
        train = json.load(f)
        features_train = train["features"]
    num_of_files = len(features_train)
    crop_tif(tif_file_name, json_file_name_train)

    json_to_new_coord(tif_file_name,json_file_name_manual)

    with open(f"{json_file_name_manual}_new_coord.json", "r") as f:
        data = json.load(f)
        features = data["features"]
    for i in range(num_of_files):
        raster = gdal.Open(f'../data/images/train/output_crop_raster_{i}.tif')
        gt = raster.GetGeoTransform()
        px_size_x = gt[1]
        px_size_y =-gt[5]
        width = raster.RasterXSize
        height = raster.RasterYSize
        upper_left_x = gt[0] # xmin
        upper_left_y = gt[3] # ymax
        lower_right_x = gt[0] + width*gt[1] + height*gt[2] # xmax
        lower_right_y = gt[3] + width*gt[4] + height*gt[5] # ymin

        outfile = open(f'../data/labels/train/output_crop_raster_{i}.txt', 'a+')

        for feature in features:
            sum = 0
            coordinates = feature["geometry"]["coordinates"][0]
            for i in range(len(coordinates)):
                if (upper_left_x<=coordinates[i][0]<=lower_right_x) & (lower_right_y<=coordinates[i][1]<=upper_left_y):
                    sum += 1

            if sum == len(coordinates):
                box_coordinates = get_box_coordinates(feature)
                class_id = 0
                box = get_pixel_values(box_coordinates, (upper_left_x, upper_left_y), (px_size_x, px_size_y))
                bounding_box = convert((width, height), box)
                outfile.write(str(class_id) + " " + " ".join([str(bbox_coordinate) for bbox_coordinate in bounding_box]) + '\n')

        outfile.close()

if __name__ == '__main__':
    convert_annotation('orthophoto', 'boat_ANNOTATIONS_TRAIN', 'boat_ANNOTATIONS_MANUAL')