import 'react-native-gesture-handler';
import React, { Component } from 'react';

import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  FlatList,
  Dimensions,
  Image
} from 'react-native';

import VideoPlayer from 'react-native-rn-videoplayer';

// const windowWidth = Dimensions.get('window').width;
// const windowHeight = Dimensions.get('window').height;

class videoExample extends Component {
  
    constructor()  {  
      super();  
         
      this.state = {  
        currentTime : 0,
        duration : 0,
        isFullScreen : false,
        isLoading : true,
        paused: false,
        text_access : true,
        access_token: '',
        playerState : 0,
      }  
    }
  
    fileInfoDetais() {
  
      // var file_data = require('./video/sample-mp4-file.mp4');
  
      console.log("==================>", windowWidth, windowHeight);
    
  
      
    }
  
    render() {
      const data_st = this.props.route.params;
      console.log(data_st);
      return (
        <View style={styles.container} >
          <VideoPlayer 
              url={data_st['@microsoft.graph.downloadUrl']}
              ref={(ref) => {
                this.player = ref
              }}
              lockControl={true}
              autoPlay={true}
              // style={{ flex: 1 }}
              moreSetting={() => null}
              />
          </View>
        );
    }
  }
  
  const styles = StyleSheet.create({
    container: {
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      backgroundColor: '#F5FCFF',
    },
    videoTag:{
      flex: 1,
      justifyContent: 'center',
      alignItems: 'center',
      backgroundColor: '#C0C0C0',
    },
    videoView:{
      // position: 'absolute',
    },
    mute_icon: {
      height: 30,
      width: 30,
      // bottom: -20,
      // padding: 10
    },
  });

  export default videoExample;
