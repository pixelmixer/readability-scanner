FROM python:3.10.15-alpine3.20
ADD . /src
WORKDIR /src

RUN apk add --update nodejs=20.15.1-r0 npm
RUN npm install -g nodemon

# Set the environment variable
ENV SKLEARN_ALLOW_DEPRECATED_SKLEARN_PACKAGE_INSTALL=True

RUN pip install -r requirements.txt

# Install automatic instrumentation
RUN opentelemetry-bootstrap --action=install

# Run the application with automatic instrumentation
CMD ["opentelemetry-instrument", "hug", "-f", "api.py"]