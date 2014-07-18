### Cydonix portal requirements and installation guide

#### Requirements

* Python version 2
* Pip
* Sleekxmpp
* Django framework
* Django rest framework

#### Installing requirements

* Download and install "python version 2" from **https://www.python.org/download/**
* Install "pip" by following the steps at **http://pip.readthedocs.org/en/latest/installing.html**
* Install "sleekxmpp" from the terminal executing the command: **pip install git+https://github.com/TracyWebTech/SleekXMPP@fix-gevent**
* Install "django framework" from the terminal executing the command: **pip install Django==1.5**
* Install "django rest framework" from the terminal executing the command: **pip install djangorestframework**

### How to start the cydonix portal

#### Running the Django server

* From the terminal in the django server's main folder, use the command: **python manage.py runserver 0.0.0.0:8000**

#### Running the Portal XMPP Client python script

* From the terminal in the django server's main folder, use the command: **python <nowiki>Portal_XMPP_Client.py</nowiki> -c config.ini**

* You can also provide the option **-l <nowiki><</nowiki>logfile name and path<nowiki>></nowiki>**
