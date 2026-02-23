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

class NormalVideoExample extends Component {
  
    constructor()  {  
      super();  
         
      this.state = {  
        currentTime : 0,
        duration : 0,
      }  
    }

  
    render() {
        
      return (
        <View style={styles.container} >
            <Text> hello </Text>
          {/* <VideoPlayer 
              url={"xxxxx.mp4"}
              ref={(ref) => {
                this.player = ref
              }}
              lockControl={true}
              autoPlay={false}
              paused={true}
              // style={{ flex: 1 }}
              moreSetting={() => null}
              /> */}
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

  export default NormalVideoExample;
  