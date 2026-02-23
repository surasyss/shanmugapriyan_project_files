# Plate IQ Mobile App
<div>
    <a href="https://github.com/nodejs/node">
      <img src="https://img.shields.io/badge/NodeJS-10.9+-green.svg">
    </a>
    <a href="https://www.npmjs.com/">
      <img src="https://img.shields.io/badge/NPM-6.x-brightgreen.svg">
    </a>
    <a href="https://code.visualstudio.com/">
      <img src="https://img.shields.io/badge/%20-VS%20Code-686968.svg?logo=visual-studio-code">
    </a>
  </div>
  
## Steps
- Install Node version (10.X)
- npm install


## iOS Steps
- Install CocoaPods --- `sudo gem install cocoapods`
- `cd ios && pod install`
- Make sure to have simulator setup
- `npm run ios`

## iOS Steps for Real Device
- Install CocoaPods --- `sudo gem install cocoapods`
- Install IOS-Deploy --- `npm install -g ios-deploy`
- `cd ios && pod install`
- Make sure to have real device connected to Mac
- `npm run ios:device`

## Android Steps
- Install & Setup Android SDK
- `cd android & touch local.properties`
- Save `sdk.dir=/Users/<username>/Library/Android/sdk` in `local.properties`
- Make sure to have emulator running or actual device connected
- `npm run android`


## Troubleshooting
- If you face `Duplicate Resources` error in `Android Release Build`, add following code to 
`node_modules/react_native/react.gradle` after `doFirst {}`

```
    def flavorPathSegment = ""
    android.productFlavors.all { flavor ->
        if (targetName.toLowerCase().contains(flavor.name)) {
            flavorPathSegment = flavor.name
        }
    }
    
    doLast {
        def moveFunc = { resSuffix ->
            File originalDir = file("$buildDir/generated/res/react/${flavorPathSegment}release/drawable-${resSuffix}")
                if (originalDir.exists()) {
                    File destDir = file("$buildDir/../src/main/res/drawable-${resSuffix}")
                    ant.move(file: originalDir, tofile: destDir)
                }
            }

        def moveRawFunc = { dir ->
            File originalDir = file("$buildDir/generated/res/react/${flavorPathSegment}release/${dir}")
            if (originalDir.exists()) {
                File destDir = file("$buildDir/../src/main/res/${dir}")
                ant.move(file: originalDir, tofile: destDir)
            }
        }

        moveFunc.curry("ldpi").call()
        moveFunc.curry("mdpi").call()
        moveFunc.curry("hdpi").call()
        moveFunc.curry("xhdpi").call()
        moveFunc.curry("xxhdpi").call()
        moveFunc.curry("xxxhdpi").call()
        moveRawFunc.curry("raw").call()
    }
```
