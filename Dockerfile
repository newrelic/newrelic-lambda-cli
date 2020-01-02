FROM python:3.7-slim
RUN useradd -ms /bin/bash newrelic-cli
USER newrelic-cli
WORKDIR /home/newrelic-cli
RUN pip3 install newrelic-lambda-cli --user
ENV PATH /home/newrelic-cli/.local/bin/:$PATH  
ENTRYPOINT ["newrelic-lambda"]
