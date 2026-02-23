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

import Icon from 'react-native-vector-icons/dist/FontAwesome';
import ImageZoom from 'react-native-image-pan-zoom';
// import ImageView from "react-native-image-viewing";


const windowWidth = Dimensions.get('window').width;
const windowHeight = Dimensions.get('window').height;


export default class VideoFileExample extends Component {

  constructor()  {  
    super();  
    this.state = {  
      isPasswordVisible: true,
      image_url : ''
    }  
  }
  

  render() {

    const data_st = this.props.route.params;

    const images = [
      {
        uri: data_st['@microsoft.graph.downloadUrl'],
      }]

    var viewHeight = Math.round(data_st.image.height/ 2);
    var viewWidth = Math.round(data_st.image.width/ 2);

    console.log("======>", data_st.image.height, data_st.image.width, viewHeight, viewWidth);

    if(data_st.image.height < 500 && data_st.image.width > data_st.image.height){


        if (data_st.image.width - data_st.image.height < 50){
            var viewHeight = 400;
            var viewWidth = 400;
        }else if (data_st.image.width - data_st.image.height < 100){
            var viewHeight = 340;
            var viewWidth = 400;
        }

    }else if(data_st.image.height < 500 && data_st.image.width < data_st.image.height){
    
      var viewHeight = 400;
      var viewWidth = 240;
    }else if(data_st.image.height > 1000 && data_st.image.width < data_st.image.height){

       if (data_st.image.height - data_st.image.width > 1000){
          var viewHeight = 1100;
          var viewWidth = 400;
       }else{
          var viewHeight = 600;
          var viewWidth = 400;
       }
      
    }else if (data_st.image.height > 1000 && data_st.image.width > data_st.image.height){
       console.log("========")
      var viewHeight = 400;
      var viewWidth = 600;

    }

     
    return (
      <ImageZoom cropWidth={Dimensions.get('window').width}
                 cropHeight={Dimensions.get('window').height}
                imageWidth={viewWidth}
                imageHeight={viewHeight}>
        <Image style={{width:viewWidth, height:viewHeight}}
                source={{uri:data_st['@microsoft.graph.downloadUrl']}}/>
      </ImageZoom>
      
    )
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent : 'center'
  },

})