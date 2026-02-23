import { DeviceEventEmitter, Platform } from 'react-native';
import MusicFiles from 'react-native-get-music-files';
import CameraRoll from '@react-native-community/cameraroll';
import AsyncStorage from '@react-native-async-storage/async-storage';
var RNFS = require('react-native-fs');

var directory = null;
var value = false;
    export const fetchFileList = async () =>{
          if(Platform.OS == 'android'){
          await RNFS.readDir(RNFS.ExternalStorageDirectoryPath)
            .then((result) => {
              result.sort((a,b)=>{
                if(a.name > b.name){
                    return 1;
                }
                if(a.name < b.name){
                    return -1;
                }
                return 0;
           });
           const list = result.reduce(function (r, a) {
            r[a.name[0]] = r[a.name[0]] || [];
            r[a.name[0]].push(a);
            return r;
        }, Object.create(null));
          DeviceEventEmitter.emit('fileList', list);
          }
          )
            .catch((err) => {
            });
          }
          else if(Platform.OS == 'ios'){
            await RNFS.readDir(RNFS.LibraryDirectoryPath)
            .then((result) => {
              result.sort((a,b)=>{
                if(a.name > b.name){
                    return 1;
                }
                if(a.name < b.name){
                    return -1;
                }
                return 0;
           });
           const list = result.reduce(function (r, a) {
            r[a.name[0]] = r[a.name[0]] || [];
            r[a.name[0]].push(a);
            return r;
        }, Object.create(null));
          DeviceEventEmitter.emit('fileList', list);
          }
          )
            .catch((err) => {
            });
          }

    }