from geojson import Feature, Polygon, FeatureCollection
from pyproj import Transformer, pyproj
from osgeo import gdal, osr
import os, glob
import geojson
import json


def pixel_coordinates_to_feature(bbox_px, upper_left, px_size):
    xmin = bbox_px[0] * px_size[0] + upper_left[0]
    ymax = upper_left[1] - bbox_px[1] * px_size[1]
    xmax = bbox_px[2] * px_size[0] + upper_left[0]
    ymin = upper_left[1] - bbox_px[3] * px_size[1]

    feature = Feature(
        geometry=Polygon(
            [[(xmin, ymin), (xmin, ymax), (xmax, ymax), (xmax, ymin), (xmin, ymin)]]
        )
    )

    return feature


# YOLOv5 Annotation Format
# One row per object.
# Each row is [class, x_center, y_center, width, height] format.
# Box coordinates are normalized by the dimensions of the image.
def convert_normalized_to_pixel_coordinates(tif_width, tif_height, bounding_box):
    x_center = bounding_box[0]
    y_center = bounding_box[1]
    width_bbox = bounding_box[2] / 2
    height_bbox = bounding_box[3] / 2

    xmin_px = round((x_center - width_bbox) * tif_width)
    ymin_px = round((y_center - height_bbox) * tif_height)
    xmax_px = round((x_center + width_bbox) * tif_width)
    ymax_px = round((y_center + height_bbox) * tif_height)

    bbox_px = [xmin_px, ymin_px, xmax_px, ymax_px]

    return bbox_px


def results_to_json():
    path_to_labels_detected = "../runs/detect/boat_detected_exp10/labels"
    files = os.listdir(path=path_to_labels_detected)
    for file in files:
        path_to_images = "../data/images/train"
        path_to_file_tif = os.path.join(path_to_images, file.replace("txt", "tif"))

        raster = gdal.Open(path_to_file_tif)

        prj = raster.GetProjection()
        src = osr.SpatialReference(wkt=prj)
        src_epsg = int(src.GetAuthorityCode(None))  # src - .tif file
        JSON_EPSG = 4326  # EPSG WGS 84 of json file
        transformer = Transformer.from_crs(src_epsg, JSON_EPSG)

        gt = raster.GetGeoTransform()
        px_size_x = gt[1]
        px_size_y = -gt[5]
        tif_width = raster.RasterXSize
        tif_height = raster.RasterYSize
        upper_left_x = gt[0]  # xmin
        upper_left_y = gt[3]  # ymax
        lower_right_x = upper_left_x + tif_width * px_size_x  # xmax
        lower_right_y = upper_left_y - tif_height * px_size_y  # ymin

        upper_left_y, upper_left_x = transformer.transform(upper_left_y, upper_left_x)

        lower_right_y, lower_right_x = transformer.transform(
            lower_right_y, lower_right_x
        )

        px_size_x_json = (lower_right_x - upper_left_x) / tif_width
        px_size_y_json = (upper_left_y - lower_right_y) / tif_height

        path_to_file_txt = os.path.join(path_to_labels_detected, file)

        features = []

        with open(path_to_file_txt, "r") as f:
            for line in f:
                bounding_box = line[2:].split()
                bounding_box = list(map(float, bounding_box))
                bbox_px = convert_normalized_to_pixel_coordinates(
                    tif_width, tif_height, bounding_box
                )
                feature = px_to_feature(
                    bbox_px,
                    (upper_left_x, upper_left_y),
                    (px_size_x_json, px_size_y_json),
                )
                features.append(feature)

            feature_collection = FeatureCollection(features)

            with open(f"{file[:-4]}.json", "w", encoding="utf-8") as f:
                geojson.dump(feature_collection, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    results_to_json()
