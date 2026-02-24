FROM    767512458197.dkr.ecr.us-east-1.amazonaws.com/plateiq/base:3.8

ENV     CHROME_VERSION "110.0.5481.77-1"
ENV     CHROMEDRIVER_VERSION "110.0.5481.77"

RUN     apt-get update && \
        apt-get install -y curl fonts-liberation libappindicator3-1 libasound2 libatk-bridge2.0-0 \
            libatk1.0-0 libatspi2.0-0 libgbm1 libgdk-pixbuf2.0-0 libgtk-3-0 libpango-1.0-0 libpangocairo-1.0-0 \
            libxcomposite1 libxcursor1 libxi6 libxrandr2 libxss1 libxtst6 xdg-utils unzip net-tools && \
        wget -O /chrome.deb "https://dl.google.com/linux/chrome/deb/pool/main/g/google-chrome-stable/google-chrome-stable_${CHROME_VERSION}_amd64.deb" && \
        (dpkg -i /chrome.deb || apt-get install -y --fix-broken --no-install-recommends) && \
        wget -O /chromedriver.zip "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" && \
        unzip /chromedriver.zip && \
        apt-get clean && \
        rm -rf /var/lib/apt/lists/* && \
        rm /chrome.deb /chromedriver.zip

ENV     DOCKERIZE_VERSION v0.6.1
RUN     wget https://github.com/jwilder/dockerize/releases/download/$DOCKERIZE_VERSION/dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
        && tar -C /usr/local/bin -xzvf dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz \
        && rm dockerize-linux-amd64-$DOCKERIZE_VERSION.tar.gz

WORKDIR /app

ENV     PYTHONUNBUFFERED=1
EXPOSE  5000

ENTRYPOINT ["/app/bin/entrypoint.sh"]

COPY    ./requirements.txt  /var/
ARG     GITHUB_ACCESS_TOKEN
RUN     GITHUB_ACCESS_TOKEN=$GITHUB_ACCESS_TOKEN /app/bin/pip3 install -r /var/requirements.txt

COPY    . /app

ENV     WEBPORT 5000

RUN     LOCAL_ENV=True /app/bin/python3 manage.py collectstatic --noinput

ARG     BUILD_VERSION
# Check for mandatory build arguments
RUN     : "${BUILD_VERSION:?Build argument needs to be set and non-empty.}"
ENV     APP_VERSION=$BUILD_VERSION
