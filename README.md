# Face Recognition External Model 👪
This service implements the same [models](https://github.com/matiasdelellis/facerecognition/wiki/Models) that already exists in the Nextcloud [Face Recognition](https://github.com/matiasdelellis/facerecognition) application, but it allows to run it on an external machine, which can be faster, and thus free up important resources from the server where you have Nextcloud installed.

Take this also as a reference model, since you can implement any external model for the Nextcloud Face Recognition application. You can implement an external model using your favorite machine learning tool, with the programming language you love.. ❤️

## Privacy
Take into account how the service works. You must send a copy of each of your images (or of your clients), from your Nextcloud instance to the server where you run this service.
The image files are sent via POST, and are immediately deleted after being analyzed. The shared API key is sent in the headers of each queries. This is only as secure as the connection between the two communicating devices. If you run it outside your local network, you should minimally use it behind an HTTPS proxy, which protects your data.

So, please. Think seriously about data security before running this service outside of your local network. 😉

## Usage
### API key
An shared API key is used to control access to the service. It can be any alphanumeric key, but it is recommended to create it automatically.
```sh
[matias@services ~]$ openssl rand -base64 32 > api.key
[matias@services ~]$ cat api.key 
NZ9ciQuH0djnyyTcsDhNL7so6SVrR01znNnv0iXLrSk=
```

### Docker
The fastest way to get this up and running without manual installation and configuration is a docker image. You only have to define the api key and the exposed port:
```sh
# Expose the service on 8080 TCP port and send the API key as a file and clear API_KEY enviroment variable. By default it uses model 4 for facial recognition.
[matias@services ~]$ docker run --rm -i -p 8080:5000 -v /path/to/api.key:/app/api.key -e APKI_KEY= --name facerecognition matiasdelellis/facerecognition-external-model:v0.2.0
# You can pass the API key as an environment variable, but it is a practice that is not recommended because it is exposed on the command line.
[matias@services ~]$ docker run --rm -i -p 8080:5000 -e API_KEY="NZ9ciQuH0djnyyTcsDhNL7so6SVrR01znNnv0iXLrSk=" --name facerecognition matiasdelellis/facerecognition-external-model:v0.2.0
# You can change the default model using the `FACE_MODEL` environment variable.
# If you do not set the API key, it remains "some-super-secret-api-key". Needless to say, it is not advisable to leave it by default.
[matias@services ~]$ docker run --rm -i -p 8080:5000 -e FACE_MODEL=3 --name facerecognition matiasdelellis/facerecognition-external-model:v0.2.0 
```

### Test
Check that the service is running using the `/welcome` endpoint.
```sh
[matias@services ~]$ curl localhost:8080/welcome
{"facerecognition-external-model":"welcome","model":3,"version":"0.2.0"}
```

You must obtain the IP where you run the service.
```sh
[matias@services facerecognition-external-model]$ hostname -I
192.168.1.123
```

...and do the same test on the server that hosts your nextcloud instance.
```sh
[matias@cloud ~]$ curl 192.168.1.123:8080/welcome
{"facerecognition-external-model":"welcome","model":3,"version":"0.2.0"}
```

## Configure Nextcloud
If the service is accessible, you can now configure Nextcloud indicating that you have an external model at this address, and the API key used to communicate with it.
```sh
[matias@cloud nextcloud]$ php occ config:system:set facerecognition.external_model_url --value 192.168.1.123:8080
System config value facerecognition.external_model_url set to string 192.168.1.123:8080
[matias@cloud nextcloud]$ php occ config:system:set facerecognition.external_model_api_key --value NZ9ciQuH0djnyyTcsDhNL7so6SVrR01znNnv0iXLrSk=
System config value facerecognition.external_model_api_key set to string NZ9ciQuH0djnyyTcsDhNL7so6SVrR01znNnv0iXLrSk=
```

You can now configure the external model (which is the 5), in the same way that it did until now.
```
[matias@cloud nextcloud]$ php occ face:setup -m 5
The files of model 5 (ExternalModel) are already installed
The model 5 (ExternalModel) was configured as default
```

... and that's all my friends. You can now continue with the backgroud_task. :smiley:
