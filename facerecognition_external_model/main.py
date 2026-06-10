import json
import os
from functools import wraps
from typing import Callable, List, Any, Optional, Tuple

import cv2
import dlib
import numpy
from deepface.models import FacialRecognition
from deepface.modules import (
    modeling,
    detection,
    preprocessing,
)
from flask import Flask, request, abort
from numpy import ndarray

# Info
PACKAGE_VERSION = "1.0.0"

# Model files
DETECTOR_PATH = "vendor/models/mmod_human_face_detector.dat"
PREDICTOR_PATH = "vendor/models/shape_predictor_5_face_landmarks.dat"
FACE_REC_MODEL_PATH = "vendor/models/dlib_face_recognition_resnet_model_v1.dat"

CNN_DETECTOR: dlib.cnn_face_detection_model_v1 | None = None
PREDICTOR: dlib.shape_predictor | None = None
FACE_REC: dlib.face_recognition_model_v1 | None = None
HOG_DETECTOR: dlib.fhog_object_detector | None = None

MAX_IMG_SIZE = 3840 * 2160

# Facenet512 with retinaface seems to perform the best out of all the models & backends
DEEPFACE_MODEL_NAME = "Facenet512"
DEEPFACE_MODEL_BACKEND = "retinaface"
DEEPFACE_MODEL_NORMALIZATION = "Facenet2018"

folder_path = "images"

# Model service
app = Flask(__name__)
try:
    FACE_MODEL = int(os.environ["FACE_MODEL"])
except KeyError:
    FACE_MODEL = 4


# model 1 face detection
def cnn_detect(img: ndarray) -> list[dict[str, Any]]:
    dets: list[dlib.mmod_rectangle] = CNN_DETECTOR(img)

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
def hog_detect(img: ndarray) -> list:
    dets: dlib.rectangles = HOG_DETECTOR(img, 1)

    faces = []

    det: dlib.rectangle
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
def cnn_hog_detect(img: ndarray) -> list:
    cnn_faces = cnn_detect(img)
    if len(cnn_faces) == 0:
        return []

    hog_faces = hog_detect(img)
    detected_faces = []
    for proposed_face in cnn_faces:
        detected_faces.append(validate_face(proposed_face, hog_faces))
    return detected_faces


def deepface_detect(img: ndarray) -> list:
    img = img[:, :, ::-1]  # convert from RGB to BGR

    return deepface_extract_faces(img=img)


def deepface_get_model(name: str) -> FacialRecognition:
    return modeling.build_model(task="facial_recognition", model_name=name)


def deepface_extract_faces(
        img: ndarray,
        max_faces: Optional[int] = None,
) -> List[dict[str, Any]]:
    img_objs = detection.extract_faces(
        img_path=img,
        detector_backend=DEEPFACE_MODEL_BACKEND,
        grayscale=False,
        enforce_detection=False,
        align=True,
        color_face="bgr",  # ensure output is already in BGR
        max_faces=max_faces,
    )

    faces = []
    for img_obj in img_objs:
        sub_img: ndarray = img_obj["face"]

        embedding = deepface_compute_embeddings(sub_img, deepface_get_model(DEEPFACE_MODEL_NAME))
        facial_area = img_obj["facial_area"]
        x = facial_area["x"]
        y = facial_area["y"]
        w = facial_area["w"]
        h = facial_area["h"]

        left_eye: Tuple[int, int] = facial_area["left_eye"]
        right_eye: Tuple[int, int] = facial_area["right_eye"]
        nose: Optional[Tuple[int, int]] = facial_area.get("nose")
        mouth_left: Optional[Tuple[int, int]] = facial_area.get("mouth_left")
        mouth_right: Optional[Tuple[int, int]] = facial_area.get("mouth_right")

        landmarks = [
            {"x": left_eye[0], "y": left_eye[1]},
            {"x": right_eye[0], "y": right_eye[1]}
        ]
        if nose is not None:
            landmarks.append({"x": nose[0], "y": nose[1]})
        if mouth_left is not None:
            landmarks.append({"x": mouth_left[0], "y": mouth_left[1]})
        if mouth_right is not None:
            landmarks.append({"x": mouth_right[0], "y": mouth_right[1]})

        faces.append({
            "detection_confidence": img_obj["confidence"],
            "left": x,
            "top": y,
            "right": x + w,
            "bottom": y + h,
            "landmarks": landmarks,
            "descriptor": embedding
        })
    return faces


def deepface_compute_embeddings(img: ndarray, model: FacialRecognition):
    target_size: Tuple[int, int] = model.input_shape

    # resize to expected shape of ml model
    img = preprocessing.resize_image(
        img=img,
        # thanks to DeepId (!)
        target_size=(target_size[1], target_size[0]),
    )
    # custom normalization
    img = preprocessing.normalize_input(img=img, normalization=DEEPFACE_MODEL_NORMALIZATION)
    return model.forward(img)


DETECT_FACES_FUNCTIONS: List[Callable[[ndarray], list] | None] = [
    None,
    cnn_detect,
    None,
    hog_detect,
    cnn_hog_detect,
    None,
    None,
    deepface_detect,
]


def open_dlib_models():
    global CNN_DETECTOR, HOG_DETECTOR, PREDICTOR, FACE_REC

    if FACE_REC is not None:
        return

    if FACE_MODEL == 7:
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
            with open('../api.key', 'r') as apikey:
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
    img: ndarray = dlib.load_rgb_image(image_path)

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

    img: ndarray = dlib.load_rgb_image(filename)

    if numpy.shape(img)[0] * numpy.shape(img)[1] > MAX_IMG_SIZE:
        abort(412)

    if FACE_REC is None:
        open_dlib_models()

    if FACE_MODEL != 7:
        face_json = compute_dlib(face_json, img)
    else:
        face_json = compute_deepface(face_json, img)

    os.remove(filename)

    return {"filename": filename, "face": face_json}


def compute_deepface(face_json: dict, img: ndarray) -> dict:
    img = img[:, :, ::-1].copy()  # convert from RGB to BGR

    region = jsonToRect(face_json)

    # Expand the region by a bit, to allow for leeway for different models
    # The current face should still be the primary face in the image
    expand_percentage = 10
    expand_x = int(img.shape[1] * expand_percentage / 100)
    expand_y = int(img.shape[0] * expand_percentage / 100)

    # If faces are close to the upper boundary, the expanded w/h can be outside the image
    # Add a black border around the image to avoid this.
    border_expanded = cv2.copyMakeBorder(img, expand_y, expand_y, expand_x, expand_x, cv2.BORDER_CONSTANT, value=[0, 0, 0])

    x_shift = region.left() - expand_x
    y_shift = region.top() - expand_y

    # this is correct, don't worry about it
    cropped_face = border_expanded[region.top():(region.bottom() + expand_y * 2), region.left():(region.right() + expand_x * 2)]

    updated_faces = deepface_extract_faces(cropped_face, 1)

    if len(updated_faces) < 1:
        return {}

    updated_face = updated_faces[0]

    face_json["detection_confidence"] = updated_face["detection_confidence"]
    face_json["left"] = updated_face["left"] + x_shift
    face_json["top"] = updated_face["top"] + y_shift
    face_json["right"] = updated_face["right"] + x_shift
    face_json["bottom"] = updated_face["bottom"] + y_shift
    face_json["landmarks"] = [{"x": landmark["x"] + x_shift, "y": landmark["y"] + y_shift} for landmark in updated_face["landmarks"]]
    face_json["descriptor"] = updated_face["descriptor"]

    return face_json


def compute_dlib(face_json, img: ndarray) -> dict:
    shape: dlib.full_object_detection = PREDICTOR(img, jsonToRect(face_json))
    descriptor: dlib.vector = FACE_REC.compute_face_descriptor(img, shape)

    face_json["landmarks"] = shapeToList(shape)
    face_json["descriptor"] = descriptorToList(descriptor)

    return face_json


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
            not (
                    os.path.exists(DETECTOR_PATH)
                    and os.path.exists(PREDICTOR_PATH)
                    and os.path.exists(FACE_REC_MODEL_PATH)
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


def jsonToRect(json: dict) -> dlib.rectangle:
    return dlib.rectangle(
        json["left"], json["top"], json["right"], json["bottom"]
    )


def overlap_percent(first: dict[str, int], second: dict[str, int]) -> float:
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
