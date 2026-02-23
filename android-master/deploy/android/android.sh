#!/bin/bash

# Deploying Dependecies
npm install --save-local

# Generating Android Build
echo 'Generating Android Product'
cp src/utils/react.gradle node_modules/react-native/react.gradle
npx jetify && npm run build:android && cd android && ./gradlew bundleRelease

# Uploading to s3 Bucket
echo 'Uploading to S3 Bucket'
aws s3 cp app/build/outputs/bundle/release/app.aab s3://dev.qubiqle.invoices



versionName=$(awk '/ versionName /' app/build.gradle)
versionName=${versionName/versionName/}
versionName=${versionName// /}
versionName=${versionName//\"}


curl --http1.1 https://upload.bugsnag.com/react-native-source-map -F apiKey=bf3bbdc9857317e812df4e57924b8e3b -F appVersion=${versionName} -F dev=false -F platform=android -F sourceMap=@app/src/main/assets/release.bundle.map -F bundle=@app/src/main/assets/index.android.bundle

node_modules/@sentry/cli/bin/sentry-cli releases --org qubiqle-plateiq --project android-product files com.qubiqle.plateiq-1.10.11.1 upload-sourcemaps --dist 38 --strip-prefix ./ --rewrite android/app/src/main/assets/
