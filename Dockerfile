FROM python:3.13.0rc2-slim
RUN useradd -r -u 1000 newrelic-lambda-cli
USER newrelic-lambda-cli
WORKDIR /home/newrelic-lambda-cli
RUN pip3 install -U newrelic-lambda-cli --user
ENV PATH /home/newrelic-lambda-cli/.local/bin/:$PATH  
ENTRYPOINT ["newrelic-lambda"]
