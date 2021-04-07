FROM python:3.7
MAINTAINER René Knaebel <rene.knaebel@bbaw.de>

# copy the dependencies file to the working directory
COPY requirements.txt /requirements.txt
RUN pip install -U pip wheel setuptools
RUN pip install -r /requirements.txt

# set the working directory in the container
WORKDIR /displacy

# copy the content of the local src directory to the working directory
COPY app app
COPY main.py .

# command to run on container start
CMD python main.py --host 0.0.0.0 --port 5050 --data /data/ --limit 10
