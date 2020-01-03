FROM python:3.7-alpine
RUN adduser -D -s /bin/bash newrelic-lambda-cli
USER newrelic-lambda-cli
WORKDIR /home/newrelic-lambda-cli
RUN pip3 install -U newrelic-lambda-cli --user
ENV PATH /home/newrelic-lambda-cli/.local/bin/:$PATH  
ENTRYPOINT ["newrelic-lambda"]
