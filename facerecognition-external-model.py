from flask import Flask, request, abort
from functools import wraps
import dlib
import os
import json
import numpy

# Model files
detector_paths = (
    "vendor/models/1/mmod_human_face_detector.dat",
    "vendor/models/2/mmod_human_face_detector.dat",
    None,
)
predictor_paths = (
    "vendor/models/1/shape_predictor_5_face_landmarks.dat",
    "vendor/models/2/shape_predictor_68_face_landmarks.dat",
    "vendor/models/3/shape_predictor_5_face_landmarks.dat",
)
face_rec_model_paths = (
    "vendor/models/1/dlib_face_recognition_resnet_model_v1.dat",
    "vendor/models/2/dlib_face_recognition_resnet_model_v1.dat",
    "vendor/models/3/dlib_face_recognition_resnet_model_v1.dat",
)

# Check image folder
folder_path = "images"
if not os.path.exists(folder_path):
    os.mkdir(folder_path)

# Clean old files if exists.
for filename in os.listdir(folder_path):
    os.unlink(os.path.join(folder_path, filename))

# Model service
app = Flask(__name__)
try:
    faceModel = int(os.environ["FACE_MODEL"]) - 1
except KeyError:
    faceModel = 0


# Security of model service
def require_appkey(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        with open("api.key", "r") as apikey:
            key = apikey.read().replace("\n", "")
        if (
            request.headers.get("x-api-key")
            and request.headers.get("x-api-key") == key
        ):
            return view_function(*args, **kwargs)
        else:
            abort(401)

    return decorated_function


# Model service endpints
@app.route("/detect", methods=["POST"])
@require_appkey
def detect_faces() -> dict:
    uploaded_file: str = request.files["file"]

    filename = os.path.basename(uploaded_file.filename)

    image_path = os.path.join(folder_path, filename)
    uploaded_file.save(image_path)

    response: dict = {"filename": filename}

    detector: object = dlib.cnn_face_detection_model_v1(
        detector_paths[faceModel]
    )
    sp: object = dlib.shape_predictor(predictor_paths[faceModel])
    facerec: object = dlib.face_recognition_model_v1(
        face_rec_model_paths[faceModel]
    )

    img: numpy.ndarray = dlib.load_rgb_image(image_path)
    dets: list = detector(img)

    response["faces-count"] = len(dets)

    faces = []
    for k, d in enumerate(dets):
        rec: object = dlib.rectangle(
            d.rect.left(), d.rect.top(), d.rect.right(), d.rect.bottom()
        )
        shape: dlib.full_object_detection = sp(img, rec)
        descriptor: dlib.vector = facerec.compute_face_descriptor(img, shape)
        faces.append(
            {
                "detection_confidence": d.confidence,
                "left": d.rect.left(),
                "top": d.rect.top(),
                "right": d.rect.right(),
                "bottom": d.rect.bottom(),
                "landmarks": shapeToList(shape),
                "descriptor": descriptorToList(descriptor),
            }
        )

    response["faces"] = faces

    os.remove(image_path)

    return response


@app.route("/compute", methods=["POST"])
@require_appkey
def compute():
    uploaded_file = request.files["file"]
    face_json: object = json.loads(request.form.get("face"))

    filename = os.path.basename(uploaded_file.filename)
    uploaded_file.save(filename)

    response = {"filename": filename}

    sp = dlib.shape_predictor(predictor_paths[faceModel])
    facerec = dlib.face_recognition_model_v1(face_rec_model_paths[faceModel])

    img: numpy.ndarray = dlib.load_rgb_image(filename)

    shape: dlib.full_object_detection = sp(img, jsonToRect(face_json))
    descriptor: dlib.vector = facerec.compute_face_descriptor(img, shape)

    face_json["landmarks"] = shapeToList(shape)
    face_json["descriptor"] = descriptorToList(descriptor)

    response["face"] = face_json

    os.remove(filename)

    return response


@app.route("/open")
@require_appkey
def open_model():
    return {"preferred_mimetype": "image/jpeg", "maximum_area": 3840 * 2160}


@app.route("/welcome")
def welcome():
    if (
        (
            detector_paths[faceModel]
            and not os.path.exists(detector_paths[faceModel])
        )
        or (
            predictor_paths[faceModel]
            and not os.path.exists(predictor_paths[faceModel])
        )
        or (
            face_rec_model_paths[faceModel]
            and not os.path.exists(face_rec_model_paths[faceModel])
        )
    ):
        return {
            "facerecognition-external-model":
                "Neural network files are missing. Install it",
            "version": "0.1.0",
        }
    return {"facerecognition-external-model": "welcome", "version": "0.1.0"}


# Conversion utilities
def shapeToList(shape):
    partList = []
    for i in range(shape.num_parts):
        partList.append({"x": shape.part(i).x, "y": shape.part(i).y})
    return partList


def descriptorToList(descriptor):
    descriptorList = []
    for i in range(len(descriptor)):
        descriptorList.append(descriptor[i])
    return descriptorList


def jsonToRect(json) -> dlib.rectangle:
    return dlib.rectangle(
        json["top"], json["right"], json["bottom"], json["left"]
    )
