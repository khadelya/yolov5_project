from pyproj import Transformer, pyproj
from osgeo import gdal, osr
import json
import os


def JsonToNewCoord(TifFileName, JsonFileName):
    # projwin_srs = "EPSG:2326"
    ds=gdal.Open(f'{TifFileName}.tif')
    prj=ds.GetProjection()
    srs=osr.SpatialReference(wkt=prj)
    src_epsg = int(srs.GetAuthorityCode(None)) # src - .tif file
    json_epsg = 4326 # EPSG WGS 84 of json file
    transformer = Transformer.from_crs(json_epsg, src_epsg)

    with open(f"{JsonFileName}.json", "r+") as f:
        train = json.load(f)
        features = train["features"]
        for feature in features:
            coordinates = feature["geometry"]["coordinates"][0]
            for coordinate in coordinates:
                lat, long = coordinate
                coordinate[1], coordinate[0] = transformer.transform(long, lat)

    with open(f'{JsonFileName}_new_coord.json', 'w', encoding='utf-8') as f:
        json.dump(train, f, ensure_ascii=False, indent=2)
    return


# Json file should be in the new coordinates f'{JsonFileName}_new_coord.json'
def CropTif(TifFileName, JsonFileName):
    with open(f"{JsonFileName}_new_coord.json", "r") as f:
        train = json.load(f)
        features = train["features"]
        for i in range(len(features)):
            xmin = train["features"][i]["geometry"]["coordinates"][0][0][0]
            ymin = train["features"][i]["geometry"]["coordinates"][0][0][1]
            xmax = train["features"][i]["geometry"]["coordinates"][0][2][0]
            ymax = train["features"][i]["geometry"]["coordinates"][0][1][1]
            window = (xmin, ymax, xmax, ymin)
            gdal.Translate(f'../data/images/train/output_crop_raster_{i}.tif', f'{TifFileName}.tif', projWin = window)
    return

def GetBoxCoordinates(feature):
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

def GetPixelValues(box_coordinates, UpperLeft, pixelSize):
    xmin_px = round((box_coordinates[0] - UpperLeft[0]) / pixelSize[0]) # round((x_coord - UpperLeftX) / pixelSizeX)
    ymin_px = round((UpperLeft[1] - box_coordinates[1]) / pixelSize[1]) # round((UpperLeftY - y_coord) / pixelSizeY)
    xmax_px = round((box_coordinates[2] - UpperLeft[0]) / pixelSize[0])
    ymax_px = round((UpperLeft[1] - box_coordinates[3]) / pixelSize[1])
    return [xmin_px, ymin_px, xmax_px, ymax_px]

def Convert(size, box):
    dw = 1. / size[0]
    dh = 1. / size[1]
    x = (box[0] + box[2]) * dw / 2
    y = (box[1] + box[3]) * dh / 2
    w = (box[2] - box[0]) * dw
    h = (box[3] - box[1]) * dh
    return (x, y, w, h)

def ConvertAnnotation(TifFileName, JsonFileNameTrain, JsonFileNameManual):
    # crop tif file
    JsonToNewCoord(TifFileName, JsonFileNameTrain)
    with open(f"{JsonFileNameTrain}_new_coord.json", "r") as f:
        train = json.load(f)
        features_train = train["features"]
    num_of_files = len(features_train)
    CropTif(TifFileName, JsonFileNameTrain)

    JsonToNewCoord(TifFileName,JsonFileNameManual)

    with open(f"{JsonFileNameManual}_new_coord.json", "r") as f:
        data = json.load(f)
        features = data["features"]
    for i in range(num_of_files):
        raster = gdal.Open(f'../data/images/train/output_crop_raster_{i}.tif')
        gt = raster.GetGeoTransform()
        pixelSizeX = gt[1]
        pixelSizeY =-gt[5]
        width = raster.RasterXSize
        height = raster.RasterYSize
        UpperLeftX = gt[0] # xmin
        UpperLeftY = gt[3] # ymax
        LowerRightX = gt[0] + width*gt[1] + height*gt[2] # xmax
        LowerRightY = gt[3] + width*gt[4] + height*gt[5] # ymin

        outfile = open(f'../data/labels/train/output_crop_raster_{i}.txt', 'a+')

        for feature in features:
            sum = 0
            coordinates = feature["geometry"]["coordinates"][0]
            for i in range(len(coordinates)):
                if (UpperLeftX <= coordinates[i][0] <= LowerRightX) & (LowerRightY <= coordinates[i][1] <= UpperLeftY):
                    sum += 1

            if sum == len(coordinates):
                box_coordinates = GetBoxCoordinates(feature)
                cls_id = 0
                box = GetPixelValues(box_coordinates, (UpperLeftX, UpperLeftY), (pixelSizeX, pixelSizeY))
                bbox = Convert((width, height), box)
                outfile.write(str(cls_id) + " " + " ".join([str(a) for a in bbox]) + '\n')

        outfile.close()

if __name__ == '__main__':
    ConvertAnnotation('orthophoto', 'boat_ANNOTATIONS_TRAIN', 'boat_ANNOTATIONS_MANUAL')