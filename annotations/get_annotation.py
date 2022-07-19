from pyproj import Transformer, pyproj
from osgeo import gdal, osr
import json
import os


def json_to_new_coordinates(tif_file_path, json_file_path):
    ds = gdal.Open(tif_file_path)
    prj = ds.GetProjection()
    src = osr.SpatialReference(wkt=prj)
    src_epsg = int(src.GetAuthorityCode(None))  # src - .tif file
    JSON_EPSG = 4326  # EPSG WGS 84 of json file
    transformer = Transformer.from_crs(JSON_EPSG, src_epsg)

    with open(json_file_path, "r+") as f:
        train = json.load(f)
        features = train["features"]
        for feature in features:
            coordinates = feature["geometry"]["coordinates"][0]
            for coordinate in coordinates:
                latitude, longitude = coordinate
                coordinate[1], coordinate[0] = transformer.transform(
                    longitude, latitude
                )

    with open(
        json_file_path.replace(".json", "_new_coord.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(train, f, ensure_ascii=False, indent=2)
    return


def crop_tif(tif_file_path, json_file_path):
    with open(json_file_path.replace(".json", "_new_coord.json"), "r") as f:
        train = json.load(f)
        features = train["features"]
        for i in range(len(features)):
            xmin = train["features"][i]["geometry"]["coordinates"][0][0][0]
            ymin = train["features"][i]["geometry"]["coordinates"][0][0][1]
            xmax = train["features"][i]["geometry"]["coordinates"][0][2][0]
            ymax = train["features"][i]["geometry"]["coordinates"][0][1][1]
            window = (xmin, ymax, xmax, ymin)
            gdal.Translate(
                f"../data/images/train/output_crop_raster_{i}.tif",
                tif_file_path,
                projWin=window,
            )
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


def get_pixel_values(box_coordinates, upper_left, px_size):
    xmin_px = round(
        (box_coordinates[0] - upper_left[0]) / px_size[0]
    )  # round((x_coord - upper_left_x) / px_size_x)
    ymin_px = round(
        (upper_left[1] - box_coordinates[1]) / px_size[1]
    )  # round((upper_left_y - y_coord) / px_size_y)
    xmax_px = round((box_coordinates[2] - upper_left[0]) / px_size[0])
    ymax_px = round((upper_left[1] - box_coordinates[3]) / px_size[1])
    return [xmin_px, ymin_px, xmax_px, ymax_px]


def convert(size, box):
    width_norm = 1.0 / size[0]
    height_norm = 1.0 / size[1]
    x_center = (box[0] + box[2]) * width_norm / 2
    y_center = (box[1] + box[3]) * height_norm / 2
    width = (box[2] - box[0]) * width_norm
    height = (box[3] - box[1]) * height_norm
    return (x_center, y_center, width, height)


def convert_annotation(tif_file_path, json_file_path_train, json_file_path_manual):
    # crop tif file
    json_to_new_coordinates(tif_file_path, json_file_path_train)
    with open(json_file_path_train.replace(".json", "_new_coord.json"), "r") as f:
        train = json.load(f)
        features_train = train["features"]
    num_of_files = len(features_train)
    crop_tif(tif_file_path, json_file_path_train)

    json_to_new_coordinates(tif_file_path, json_file_path_manual)

    with open(json_file_path_manual.replace(".json", "_new_coord.json"), "r") as f:
        data = json.load(f)
        features = data["features"]
    for i in range(num_of_files):
        raster = gdal.Open(f"../data/images/train/output_crop_raster_{i}.tif")
        gt = raster.GetGeoTransform()
        px_size_x = gt[1]
        px_size_y = -gt[5]
        width = raster.RasterXSize
        height = raster.RasterYSize
        upper_left_x = gt[0]  # xmin
        upper_left_y = gt[3]  # ymax
        lower_right_x = gt[0] + width * gt[1] + height * gt[2]  # xmax
        lower_right_y = gt[3] + width * gt[4] + height * gt[5]  # ymin

        outfile = open(f"../data/labels/train/output_crop_raster_{i}.txt", "a+")

        for feature in features:
            sum = 0
            coordinates = feature["geometry"]["coordinates"][0]
            for i in range(len(coordinates)):
                if (upper_left_x <= coordinates[i][0] <= lower_right_x) & (
                    lower_right_y <= coordinates[i][1] <= upper_left_y
                ):
                    sum += 1

            if sum == len(coordinates):
                box_coordinates = get_box_coordinates(feature)
                class_id = 0
                box = get_pixel_values(
                    box_coordinates,
                    (upper_left_x, upper_left_y),
                    (px_size_x, px_size_y),
                )
                bounding_box = convert((width, height), box)
                outfile.write(
                    str(class_id)
                    + " "
                    + " ".join(
                        [str(bbox_coordinate) for bbox_coordinate in bounding_box]
                    )
                    + "\n"
                )

        outfile.close()


with open("worker-config.json", "r") as f:
    worker_config = json.load(f)
    tif_file_path = worker_config["parameters"]["resource_tif"]
    json_file_path_train = worker_config["parameters"]["annotations_train"]
    json_file_path_manual = worker_config["parameters"]["annotations_manual"]


if __name__ == "__main__":
    convert_annotation(tif_file_path, json_file_path_train, json_file_path_manual)
