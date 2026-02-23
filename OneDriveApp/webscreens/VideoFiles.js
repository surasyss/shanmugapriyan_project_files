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

// import VideoPlayer from 'react-native-rn-videoplayer';

// const windowWidth = Dimensions.get('window').width;
// const windowHeight = Dimensions.get('window').height;

export default class VideoExample extends Component {

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


    render() {
        const data_st = this.props.route.params;
        console.log(data_st);
        return (
            <View style={styles.container} >
            {/* <VideoPlayer 
                url={data_st['@microsoft.graph.downloadUrl']}
                ref={(ref) => {
                    this.player = ref
                }}
                lockControl={true}
                autoPlay={true}
                // style={{ flex: 1 }}
                moreSetting={() => null}
                /> */}
                <Text>noting ....</Text>
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
