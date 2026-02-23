import 'react-native-gesture-handler';
import React, { Component } from 'react';
import { CommonActions, useNavigation } from '@react-navigation/native' // <-- import useNavigation hook

import { Platform, StyleSheet, Image, Text, View, Button, WebView, Dimensions } from 'react-native';

const windowWidth = Dimensions.get('screen').width;
const windowHeight = Dimensions.get('screen').height;

export default class SampleDemo extends React.Component {

  constructor()  {  
    super();  
       
    this.state = {  
      isPasswordVisible: true,
      text_access : true,
      access_token: ''
    }  
  } 
  

  render() {
    console.log("=======", windowWidth, windowHeight);
    return (
      <View style = {styles.container}>
        <View style = {styles.innerview} >
          <View style = {styles.redbox} />
          <View style = {styles.bluebox} />
          <View style = {styles.blackbox} />
        </View>
      </View>
    )
}

}


const styles = StyleSheet.create ({
  container: {
    flex : 1,
    backgroundColor: '#99C68E',
  },
  innerview: {
    flexDirection: "row",
    backgroundColor: '#BAB86C', 
    width: windowWidth,
    aspectRatio: 2,
  },
  redbox: {
    aspectRatio: 1,
    width: '34%',
    backgroundColor: '#98AFC7'
  },
  bluebox: {
    aspectRatio: 1,
    width: '34%',
    backgroundColor: '#6D7B8D'
  },
  blackbox: {
    aspectRatio: 1,
    width: '34%',
    backgroundColor: '#FED8B1'
  },
  lastbox: {
    aspectRatio: 1,
    width: '34%',
    backgroundColor: '#38ACEC'
  },
})

