from typing import Callable, Tuple
from flask import Flask, request, abort
from functools import wraps
import dlib
import os
import json
import numpy


# Info
PACKAGE_VERSION = "1.0.0"

# Model files
DETECTOR_PATH = "vendor/models/mmod_human_face_detector.dat"
PREDICTOR_PATH = "vendor/models/shape_predictor_5_face_landmarks.dat"
FACE_REC_MODEL_PATH = "vendor/models/dlib_face_recognition_resnet_model_v1.dat"

CNN_DETECTOR: object = None
PREDICTOR: object = None
FACE_REC: object = None

MAX_IMG_SIZE = 3840 * 2160

folder_path = "images"

# Model service
app = Flask(__name__)
try:
    FACE_MODEL = int(os.environ["FACE_MODEL"])
except KeyError:
    FACE_MODEL = 4

# model 1 face detection
def cnn_detect(img: numpy.ndarray) -> list:
    dets: list = CNN_DETECTOR(img)

    faces = []
    for det in dets:
        rec: object = dlib.rectangle(
            det.rect.left(), det.rect.top(), det.rect.right(), det.rect.bottom()
        )
        shape: dlib.full_object_detection = PREDICTOR(img, rec)
        descriptor: dlib.vector = FACE_REC.compute_face_descriptor(img, shape)
        faces.append(
            {
                "detection_confidence": det.confidence,
                "left": det.rect.left(),
                "top": det.rect.top(),
                "right": det.rect.right(),
                "bottom": det.rect.bottom(),
                "landmarks": shapeToList(shape),
                "descriptor": descriptorToList(descriptor),
            }
        )
    return faces


# model 3 face detection
def hog_detect(img: numpy.ndarray) -> list:
    dets: list = HOG_DETECTOR(img, 1)

    faces = []
    for det in dets:
        landmarks: dlib.full_object_detection = PREDICTOR(img, det)
        descriptor = FACE_REC.compute_face_descriptor(img, landmarks)
        faces.append(
            {
                "detection_confidence": 1.1,
                "left": det.left(),
                "top": det.top(),
                "right": det.right(),
                "bottom": det.bottom(),
                "landmarks": shapeToList(landmarks),
                "descriptor": descriptorToList(descriptor),
            }
        )
    return faces


# model 4 face detection
def cnn_hog_detect(img: numpy.ndarray) -> Tuple[int, list]:
    cnn_faces = cnn_detect(img)
    if len(cnn_faces) == 0:
        return []

    hog_faces = hog_detect(img)
    detected_faces = []
    for proposed_face in cnn_faces:
        detected_faces.append(validate_face(proposed_face, hog_faces))
    return detected_faces


DETECT_FACES_FUNCTIONS: Tuple[Callable[[numpy.ndarray], Tuple[int, list]]] = (
    None,
    cnn_detect,
    None,
    hog_detect,
    cnn_hog_detect,
)

def open_dlib_models():
    global CNN_DETECTOR, HOG_DETECTOR, PREDICTOR, FACE_REC

    if FACE_REC is not None:
        return

    # we don't need the cnn detector for model 3
    if FACE_MODEL != 3:
        CNN_DETECTOR = dlib.cnn_face_detection_model_v1(DETECTOR_PATH)
    # we need the hog detector for models 3 and 4
    if FACE_MODEL in (3, 4):
        HOG_DETECTOR = dlib.get_frontal_face_detector()

    PREDICTOR = dlib.shape_predictor(PREDICTOR_PATH)
    FACE_REC = dlib.face_recognition_model_v1(FACE_REC_MODEL_PATH)


#
# Model service
#

# Security of model service
def require_appkey(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if 'API_KEY' in os.environ:
            key = os.environ.get('API_KEY')
        else:
            with open('api.key', 'r') as apikey:
                key = apikey.read().replace('\n', '')
        if request.headers.get('x-api-key') and request.headers.get('x-api-key') == key:
            return view_function(*args, **kwargs)
        else:
            abort(401)

    return decorated_function

# Endpoints
@app.route("/detect", methods=["POST"])
@require_appkey
def detect_faces() -> dict:
    uploaded_file = request.files["file"]

    filename = os.path.basename(uploaded_file.filename)

    image_path = os.path.join(folder_path, filename)
    uploaded_file.save(image_path)
    img: numpy.ndarray = dlib.load_rgb_image(image_path)

    if numpy.shape(img)[0] * numpy.shape(img)[1] > MAX_IMG_SIZE:
        abort(412)

    if FACE_REC is None:
        open_dlib_models()

    faces = DETECT_FACES_FUNCTIONS[FACE_MODEL](img)

    os.remove(image_path)

    return {"filename": filename, "faces-count": len(faces), "faces": faces}

@app.route("/compute", methods=["POST"])
@require_appkey
def compute():
    uploaded_file = request.files["file"]
    face_json: dict = json.loads(request.form.get("face"))

    filename: str = os.path.basename(uploaded_file.filename)
    uploaded_file.save(filename)

    img: numpy.ndarray = dlib.load_rgb_image(filename)

    if numpy.shape(img)[0] * numpy.shape(img)[1] > MAX_IMG_SIZE:
        abort(412)

    if FACE_REC is None:
        open_dlib_models()

    shape: dlib.full_object_detection = PREDICTOR(img, jsonToRect(face_json))
    descriptor: dlib.vector = FACE_REC.compute_face_descriptor(img, shape)

    os.remove(filename)

    face_json["landmarks"] = shapeToList(shape)
    face_json["descriptor"] = descriptorToList(descriptor)

    return {"filename": filename, "face": face_json}

@app.route("/open")
@require_appkey
def open_model():
    open_dlib_models()
    return {"preferred_mimetype": "image/jpeg", "maximum_area": MAX_IMG_SIZE}

@app.route("/health")
def health():
    return 'ok'

@app.route("/welcome")
def welcome():
    if (
        (
            not os.path.exists(DETECTOR_PATH)
        )
        or (
            not os.path.exists(PREDICTOR_PATH)
        )
        or (
            not os.path.exists(FACE_REC_MODEL_PATH)
        )
    ):
        return {
            "facerecognition-external-model":
                "Neural network files are missing. Install them with 'make download-models",
            "version": PACKAGE_VERSION
        }
    return {"facerecognition-external-model": "welcome", "version": PACKAGE_VERSION, "model": FACE_MODEL}

#
# Conversion utilities
#
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


def overlap_percent(first: dlib.rectangle, second: dlib.rectangle) -> float:
    # if there is not intersection, return 0.0
    # (right is a larger value than left, bottom is larger than top)
    if (
        first["left"] >= second["right"]
        or second["left"] >= first["right"]
        or first["top"] >= second["bottom"]
        or second["top"] >= first["bottom"]
    ):
        return 0.0

    # find the corners of the overlapping area
    left = max(first["left"], second["left"])
    right = max(first["right"], second["right"])
    top = max(first["top"], second["top"])
    bottom = max(first["bottom"], second["bottom"])

    # areas
    first_area = (first["right"] - first["left"]) * (
        first["bottom"] - first["top"]
    )
    second_area = (second["right"] - second["left"]) * (
        second["bottom"] - second["top"]
    )
    overlap_area = (right - left) * (bottom - top)

    return overlap_area / (first_area + second_area - overlap_area)


def validate_face(proposed_face: dict, face_list: list) -> dict:
    for face in face_list:
        overlap = overlap_percent(proposed_face, face)
        if overlap >= 0.35:
            return proposed_face
    proposed_face["detection_confidence"] *= 0.8
    return proposed_face
