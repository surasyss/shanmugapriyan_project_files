#!/bin/bash

if git diff-index --quiet HEAD --; then
  # Deploying Dependecies
  npm install --save-local

  # Generating Android Build
  echo 'Generating Android Product'
  cp src/utils/react.gradle node_modules/react-native/react.gradle
  npx jetify && npm run build-sandbox:android && cd android && ./gradlew app:assembleRelease
  cd ..
  cp android/app/build/outputs/apk/release/app-release.apk deploy/android/sandbox/
  cd deploy/android/sandbox
  source venv/bin/activate
  pip install -r requirements.txt
  python diawi-cli.py app-release.apk
  git add -A
  git stash
else
    echo "There are some changes! Commit everything to get started"
fi
