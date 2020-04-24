FROM python:3.7.4-alpine3.10

LABEL name="AutomateActions" \
      description="AutomateActions is python automation framework with rest api" \
      url="https://github.com/ExtensiveAutomation" \
      maintainer="d.machard@gmail.com"

WORKDIR /home/extensive

COPY . /home/extensive/

RUN true \
    && adduser -D extensive \
    && apk add --update --no-cache curl \
    && pip install --no-cache-dir pycnic jsonpath_ng \
    && cd /home/extensive \
    && chmod 755 start.sh \
    && chown -R extensive:extensive /home/extensive \
    && true
    
USER extensive

EXPOSE 8081/tcp

ENTRYPOINT ["/home/extensive/start.sh"]
