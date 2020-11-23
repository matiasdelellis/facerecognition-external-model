# Facerecognition External Model
This is only the reference model, to implement any external model for the Nextcloud Face Recognition application. This implements the same [model 1](https://github.com/matiasdelellis/facerecognition/wiki/Models#model-1) that already exists in the Facial Recognition application, but it allows to run it on an external machine, which can be faster, and thus free up important resources from the server where you have Nextcloud installed.

## Dependencies
* Dlib python bindings.
* Flask

## Install
Just clone this repo and install the resnet models.
```
[matias@nube ~]$ git clone https://github.com/matiasdelellis/facerecognition-external-model.git
Clonando en 'facerecognition-external-model'...
remote: Enumerating objects: 4, done.
remote: Counting objects: 100% (4/4), done.
remote: Compressing objects: 100% (4/4), done.
remote: Total 4 (delta 0), reused 4 (delta 0), pack-reused 0
Desempaquetando objetos: 100% (4/4), 1.38 KiB | 1.38 MiB/s, listo.
[matias@nube ~]$ cd facerecognition-external-model/
[matias@nube facerecognition-external-model]$ make download-models 
mkdir -p vendor/models/1
wget https://github.com/davisking/dlib-models/raw/94cdb1e40b1c29c0bfcaf7355614bfe6da19460e/mmod_human_face_detector.dat.bz2 -O vendor/models/1/mmod_human_face_detector.dat.bz2
bzip2 -d vendor/models/1/mmod_human_face_detector.dat.bz2
mkdir -p vendor/models/1
wget https://github.com/davisking/dlib-models/raw/2a61575dd45d818271c085ff8cd747613a48f20d/dlib_face_recognition_resnet_model_v1.dat.bz2 -O vendor/models/1/dlib_face_recognition_resnet_model_v1.dat.bz2
bzip2 -d vendor/models/1/dlib_face_recognition_resnet_model_v1.dat.bz2
mkdir -p vendor/models/1
wget https://github.com/davisking/dlib-models/raw/4af9b776281dd7d6e2e30d4a2d40458b1e254e40/shape_predictor_5_face_landmarks.dat.bz2 -O vendor/models/1/shape_predictor_5_face_landmarks.dat.bz2
bzip2 -d vendor/models/1/shape_predictor_5_face_landmarks.dat.bz2
[matias@nube facerecognition-external-model]$
```

## Usage

### Configure Service

You must generate a shared api key and save it in the file `api.key`.
```
[matias@nube facerecognition-external-model]$ openssl rand -base64 32
NZ9ciQuH0djnyyTcsDhNL7so6SVrR01znNnv0iXLrSk=
[matias@nube facerecognition-external-model]$ echo NZ9ciQuH0djnyyTcsDhNL7so6SVrR01znNnv0iXLrSk= > api.key 
```

### Launch Service
```
[matias@nube facerecognition-external-model]$ export FLASK_APP=facerecognition-external-model.py
[matias@nube facerecognition-external-model]$ flask run
 * Serving Flask app "facerecognition-external-model.py"
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: off
 * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
```

Note that this Service is running on `http://127.0.0.1:5000/`

### Use
You must configure Nextcloud, indicating that you have an external model at this address, and the shared api key. So, you must add these lines to your `config/config.php` file.
```
[matias@nube ~]$ cat nextcloud/config/config.php
<?php
$CONFIG = array (
  ...........................................
  'externalModelUrl' => 'http://127.0.0.1:5000',
  'externalModelApiKey' => 'NZ9ciQuH0djnyyTcsDhNL7so6SVrR01znNnv0iXLrSk=',
  ...............................
);
```

You can now configure the external model (which is the 5), in the same way that it did until now.
```
[matias@nube nextcloud]$ sudo -u apache php occ face:setup -m 5
The files of model 5 (ExternalModel) are already installed
The model 5 (ExternalModel) was configured as default
```

... and that's all my friends. You can now continue with the backgroud_task. :smiley:
