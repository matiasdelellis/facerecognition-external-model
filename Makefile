FACE_MODEL ?= 4

default: serve

define get_dat_file
	mkdir -p $(dir $1)
	cd $(dir $1);\
	wget $(2);\
	bzip2 -d $(notdir $(2))
endef

vendor/models/mmod_human_face_detector.dat:
	$(call get_dat_file,$(@),https://github.com/davisking/dlib-models/raw/94cdb1e40b1c29c0bfcaf7355614bfe6da19460e/mmod_human_face_detector.dat.bz2)

vendor/models/dlib_face_recognition_resnet_model_v1.dat:
	$(call get_dat_file,$(@),https://github.com/davisking/dlib-models/raw/2a61575dd45d818271c085ff8cd747613a48f20d/dlib_face_recognition_resnet_model_v1.dat.bz2)

vendor/models/shape_predictor_5_face_landmarks.dat:
	$(call get_dat_file,$(@),https://github.com/davisking/dlib-models/raw/4af9b776281dd7d6e2e30d4a2d40458b1e254e40/shape_predictor_5_face_landmarks.dat.bz2)

download-models: vendor/models/mmod_human_face_detector.dat vendor/models/dlib_face_recognition_resnet_model_v1.dat vendor/models/shape_predictor_5_face_landmarks.dat

serve: download-models
	export FLASK_APP=app/facerecognition-external-model.py;\
	export FACE_MODEL=$(FACE_MODEL);\
	flask run
