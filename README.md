# Facerecognition External Model
This is only the reference model, to implement any external model for the Nextcloud Face Recognition application. This implements the same [models](https://github.com/matiasdelellis/facerecognition/wiki/Models) that already exists in the Facial Recognition application, but it allows to run it on an external machine, which can be faster, and thus free up important resources from the server where you have Nextcloud installed.

## Privacy
Take into account how the application works. You must send a copy of each of your images (or of your clients), from your Nextcloud instance to the Server where you run this service.
The images are sent via POST, and are immediately deleted after being analyzed. The api key is sent in the headers of each queries. This is only as secure as the connection between the two communicating devices. If you run it outside your local network, you should minimally use it behind an HTTPS proxy, which protects your data.

So, please. Think seriously about data security before running this service outside of your local network.

## Dependencies
* python3-flask
* python3-dlib
* python3-numpy

## Install
Just clone this repo and install the models. Use FACE_MODEL to specify rhe desired model.
```
[matias@laptop ~]$ git clone https://github.com/matiasdelellis/facerecognition-external-model.git
Clonando en 'facerecognition-external-model'...
remote: Enumerating objects: 4, done.
remote: Counting objects: 100% (4/4), done.
remote: Compressing objects: 100% (4/4), done.
remote: Total 4 (delta 0), reused 4 (delta 0), pack-reused 0
Desempaquetando objetos: 100% (4/4), 1.38 KiB | 1.38 MiB/s, listo.
[matias@laptop ~]$ cd facerecognition-external-model/
[matias@laptop facerecognition-external-model]$ make FACE_MODEL=1 download-models 
mkdir -p vendor/models/1
wget https://github.com/davisking/dlib-models/raw/94cdb1e40b1c29c0bfcaf7355614bfe6da19460e/mmod_human_face_detector.dat.bz2 -O vendor/models/1/mmod_human_face_detector.dat.bz2
bzip2 -d vendor/models/1/mmod_human_face_detector.dat.bz2
mkdir -p vendor/models/1
wget https://github.com/davisking/dlib-models/raw/2a61575dd45d818271c085ff8cd747613a48f20d/dlib_face_recognition_resnet_model_v1.dat.bz2 -O vendor/models/1/dlib_face_recognition_resnet_model_v1.dat.bz2
bzip2 -d vendor/models/1/dlib_face_recognition_resnet_model_v1.dat.bz2
mkdir -p vendor/models/1
wget https://github.com/davisking/dlib-models/raw/4af9b776281dd7d6e2e30d4a2d40458b1e254e40/shape_predictor_5_face_landmarks.dat.bz2 -O vendor/models/1/shape_predictor_5_face_landmarks.dat.bz2
bzip2 -d vendor/models/1/shape_predictor_5_face_landmarks.dat.bz2
[matias@laptop facerecognition-external-model]$
```

## Usage

### Configure Service

You must generate a shared api key and save it in the file `api.key`.
```
[matias@laptop facerecognition-external-model]$ openssl rand -base64 32
NZ9ciQuH0djnyyTcsDhNL7so6SVrR01znNnv0iXLrSk=
[matias@nube facerecognition-external-model]$ echo NZ9ciQuH0djnyyTcsDhNL7so6SVrR01znNnv0iXLrSk= > api.key
```

We must obtain the IP of the machine that runs this service.
```
[matias@laptop facerecognition-external-model]$ hostname -I
192.168.1.103
```

### Launch Service
Launch the service indicating this IP and some TCP port such as `8080`. Also, specify the recognition model desired, using the `FACE_MODEL` environment variable (if not specified, model 1 will be used).
```
[matias@laptop facerecognition-external-model]$ export FLASK_APP=facerecognition-external-model.py
[matias@laptop facerecognition-external-model]$ export FACE_MODEL=1
[matias@laptop facerecognition-external-model]$ flask run -h 192.168.1.103 -p 8080
 * Serving Flask app "facerecognition-external-model.py"
 * Environment: production
   WARNING: This is a development server. Do not use it in a production deployment.
   Use a production WSGI server instead.
 * Debug mode: off
 * Running on http://192.168.1.103:8080/ (Press CTRL+C to quit)
```

Or you can just run: `make FACE_MODEL=1 serve`.

Note that this service is running on `http://192.168.1.103:8080/`

### Test
You can test if the service is running using curl.
```
[matias@laptop ~]$ curl http://192.168.1.103:8080/welcome
{"facerecognition-external-model":"welcome","version":"0.1.0"}
```

Now, on the machine that you have the nextclood instance, you must check that it can access the service.
```
[matias@nube ~]$ curl http://192.168.1.103:8080/welcome
{"facerecognition-external-model":"welcome","version":"0.1.0"}
```

If curl responds something like the following, surely you have a firewall with port `8080` closed, and you should open it.
```
[matias@nube ~]$ curl http://192.168.1.103:8080/welcome
curl: (7) Failed to connect to 192.168.1.103 port 8080: No route to host
```

### Use
If the service is accessible, you can now configure Nextcloud, indicating that you have an external model at this address, and the shared api key. So, you must add these lines to your `config/config.php` file.
```
[matias@nube ~]$ cat nextcloud/config/config.php
<?php
$CONFIG = array (
  ...........................................
  'facerecognition.external_model_url' => 'http://192.168.1.103:8080',
  'facerecognition.external_model_api_key' => 'NZ9ciQuH0djnyyTcsDhNL7so6SVrR01znNnv0iXLrSk=',
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
